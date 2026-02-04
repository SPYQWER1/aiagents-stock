import json
import logging
import re
from typing import Any, Dict, List

from aiagents_stock.domain.main_force.model import MainForceRecommendation, MainForceStock
from aiagents_stock.domain.main_force.ports import MainForceAIAnalyzer
from aiagents_stock.infrastructure.ai.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

# --- Prompts ---

FUND_FLOW_ANALYSIS_PROMPT = """
你是一名资深的资金面分析师，现在需要你从整体角度分析这批主力资金净流入的股票。

【整体数据摘要】
{summary}

【候选股票详细数据】
{stocks_list}

【分析任务】
请从资金流向的整体角度进行分析，重点关注：

1. **资金流向特征**
   - 哪些板块/行业资金流入最集中？
   - 主力资金的整体行为特征（大规模建仓/试探性进场/板块轮动）
   - 资金流向与涨跌幅的配合情况

2. **优质标的识别**
   - 从资金面角度，哪些股票最值得关注？
   - 主力资金流入大但涨幅不高的潜力股
   - 资金持续流入且趋势明确的股票

3. **板块热点判断**
   - 当前资金最看好哪些板块？
   - 是否有板块轮动迹象？
   - 新兴热点 vs 传统强势板块

4. **投资建议**
   - 从资金面角度，建议重点关注哪3-5只股票？
   - 理由和风险提示

请给出专业、系统的资金面整体分析报告。
"""

INDUSTRY_ANALYSIS_PROMPT = """
你是一名资深的行业板块分析师，现在需要你从行业热点和板块轮动角度分析这批股票。

【整体数据摘要】
{summary}

【候选股票详细数据】
{stocks_list}

【分析任务】
请从行业板块的整体角度进行分析，重点关注：

1. **热点板块识别**
   - 哪些行业/板块最受资金青睐？
   - 热点板块的持续性如何？
   - 是否有新兴热点正在形成？

2. **板块特征分析**
   - 各板块的涨幅与资金流入匹配度
   - 哪些板块处于启动阶段（资金流入但涨幅不大）
   - 哪些板块可能过热（涨幅高但资金流入减弱）

3. **行业前景评估**
   - 主力资金集中的行业，基本面支撑如何？
   - 政策面、产业面是否有催化因素？
   - 行业竞争格局和龙头地位

4. **优质标的推荐**
   - 从行业板块角度，推荐3-5只最具潜力的股票
   - 推荐理由（行业地位、成长空间、催化因素）

请给出专业、深入的行业板块分析报告。
"""

FUNDAMENTAL_ANALYSIS_PROMPT = """
你是一名资深的基本面分析师，现在需要你从财务质量和基本面角度分析这批股票。

【整体数据摘要】
{summary}

【候选股票详细数据】
{stocks_list}

【分析任务】
请从财务基本面的整体角度进行分析，重点关注：

1. **财务质量评估**
   - 整体财务指标健康度如何？
   - 哪些股票盈利能力、成长性突出？
   - 是否存在财务风险较大的股票？

2. **估值水平分析**
   - 市盈率、市净率的整体分布
   - 哪些股票估值合理且有成长空间？
   - 高估值是否有业绩支撑？

3. **成长性评估**
   - 营收、净利润增长情况
   - 哪些股票成长性最好？
   - 成长能力评分较高的股票

4. **优质标的筛选**
   - 从基本面角度，推荐3-5只最优质的股票
   - 推荐理由（财务健康、估值合理、成长性好）

请给出专业、详实的基本面分析报告。
"""

FINAL_SELECTION_PROMPT = """
你是一名资深股票研究员，具有20年以上的投资研究经验。现在需要你综合三位分析师的意见，
从候选股票中精选出{n}只最具投资价值的优质标的。

【候选股票数据】
{stocks_list}

【资金流向分析师观点】
{fund_analysis}

【行业板块分析师观点】
{industry_analysis}

【财务基本面分析师观点】
{fundamental_analysis}

【筛选标准】
1. **主力资金**: 主力资金净流入较多，显示机构看好
2. **涨幅适中**: 区间涨跌幅不是很高（避免追高），还有上涨空间
3. **行业热点**: 所属行业有发展前景，是市场热点
4. **基本面良好**: 财务指标健康，盈利能力强
5. **综合平衡**: 资金、行业、基本面三方面都不错

【任务要求】
综合三位分析师的观点，精选出{n}只最优标的。

对于每只精选股票，请提供：
1. **股票代码和名称**
2. **核心推荐理由**（3-5条，综合资金、行业、基本面）
3. **投资亮点**（最突出的优势）
4. **风险提示**（需要注意的风险）
5. **建议仓位**（如20-30%）
6. **投资周期**（短期/中期/长期）

请按以下JSON格式输出（只输出JSON，不要其他内容）：
```json
{{
  "recommendations": [
    {{
      "rank": 1,
      "symbol": "股票代码",
      "name": "股票名称",
      "reasons": [
        "理由1：资金面角度",
        "理由2：行业板块角度", 
        "理由3：基本面角度"
      ],
      "highlights": "投资亮点描述",
      "risks": "风险提示",
      "position": "建议仓位",
      "investment_period": "投资周期"
    }}
  ]
}}
```

注意：
- 必须严格按照JSON格式输出
- 推荐数量为{n}只
- 按投资价值从高到低排序
- 理由要具体、有说服力，体现三位分析师的综合观点
"""

class DeepSeekMainForceAIAnalyzer(MainForceAIAnalyzer):
    """基于DeepSeek的主力选股AI分析师"""
    
    def __init__(self, client: DeepSeekClient):
        self.client = client
        
    def analyze_fund_flow(self, stocks: List[MainForceStock], summary: str) -> str:
        stocks_str = self._format_stocks_for_fund(stocks)
        prompt = FUND_FLOW_ANALYSIS_PROMPT.format(summary=summary, stocks_list=stocks_str)
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.call_api(messages, temperature=0.7)
        
    def analyze_industry(self, stocks: List[MainForceStock], summary: str) -> str:
        stocks_str = self._format_stocks_for_industry(stocks)
        prompt = INDUSTRY_ANALYSIS_PROMPT.format(summary=summary, stocks_list=stocks_str)
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.call_api(messages, temperature=0.7)
        
    def analyze_fundamental(self, stocks: List[MainForceStock], summary: str) -> str:
        stocks_str = self._format_stocks_for_fundamental(stocks)
        prompt = FUNDAMENTAL_ANALYSIS_PROMPT.format(summary=summary, stocks_list=stocks_str)
        
        messages = [{"role": "user", "content": prompt}]
        return self.client.call_api(messages, temperature=0.7)
        
    def select_best_stocks(
        self, 
        stocks: List[MainForceStock], 
        fund_analysis: str, 
        industry_analysis: str, 
        fundamental_analysis: str, 
        final_n: int
    ) -> List[MainForceRecommendation]:
        
        stocks_str = self._format_stocks_full(stocks)
        prompt = FINAL_SELECTION_PROMPT.format(
            n=final_n,
            fund_analysis=fund_analysis,
            industry_analysis=industry_analysis,
            fundamental_analysis=fundamental_analysis,
            stocks_list=stocks_str
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = self.client.call_api(messages, temperature=0.3) # Lower temperature for structured output
        
        logger.info(f"AI Selection Response: {response}")

        # Parse JSON
        result = self._parse_json_response(response)

        data = result.get("recommendations", [])
        
        recommendations = []
        for item in data:
            # Find original stock data
            symbol = item.get("symbol")
            original_stock = next((s for s in stocks if s.symbol == symbol), None)
            stock_data = original_stock.raw_data if original_stock else {}
            
            # Add computed fields to stock_data for display
            if original_stock:
                stock_data.update({
                    "industry": original_stock.industry,
                    "market_cap": original_stock.market_cap,
                    "range_change": original_stock.range_change,
                    "main_fund_inflow": original_stock.main_fund_inflow,
                    "pe_ratio": original_stock.pe_ratio,
                    "pb_ratio": original_stock.pb_ratio
                })
            
            rec = MainForceRecommendation(
                rank=item.get("rank", 0),
                symbol=symbol,
                name=item.get("name", ""),
                reasons=item.get("reasons", []),
                highlights=item.get("highlights", ""),
                risks=item.get("risks", ""),
                position=item.get("position", ""),
                investment_period=item.get("investment_period", ""),
                stock_data=stock_data
            )
            recommendations.append(rec)
            
        return recommendations

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """尝试解析JSON响应，支持多种格式和修复"""
        candidates = []
        
        # 1. Regex for code blocks
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL | re.IGNORECASE)
        if match:
            candidates.append(match.group(1))
            
        # 2. Find outer braces
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidates.append(response[start:end+1])
            
        # 3. Raw response
        candidates.append(response)
        
        last_error = None
        for json_str in candidates:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try cleanup
                try:
                    fixed_str = re.sub(r',\s*\}', '}', json_str)
                    fixed_str = re.sub(r',\s*\]', ']', fixed_str)
                    # 修复中文引号问题：将中文全角引号替换为英文半角引号
                    fixed_str = fixed_str.replace('"', '"')
                    fixed_str = fixed_str.replace('"', '"')
                    return json.loads(fixed_str)
                except Exception as e:
                    last_error = e
                    continue
                    
        raise ValueError(f"无法从响应中解析出有效的JSON: {last_error}")

    def _format_stocks_for_fund(self, stocks: List[MainForceStock]) -> str:
        lines = ["| 代码 | 名称 | 主力净流入(万) | 涨跌幅(%) | 市值(亿) |"]
        lines.append("|---|---|---|---|---|")
        # Sort by fund inflow
        sorted_stocks = sorted(stocks, key=lambda x: x.main_fund_inflow or -float('inf'), reverse=True)[:30] # Limit to top 30 to save tokens
        for s in sorted_stocks:
            lines.append(f"| {s.symbol} | {s.name} | {s.main_fund_inflow} | {s.range_change} | {s.market_cap} |")
        return "\n".join(lines)

    def _format_stocks_for_industry(self, stocks: List[MainForceStock]) -> str:
        # Group by industry
        industries = {}
        for s in stocks:
            if s.industry not in industries:
                industries[s.industry] = []
            industries[s.industry].append(s)
            
        # Sort industries by count
        sorted_industries = sorted(industries.items(), key=lambda x: len(x[1]), reverse=True)
        
        lines = []
        for ind, items in sorted_industries[:10]: # Top 10 industries
            lines.append(f"### {ind} ({len(items)}只)")
            names = [f"{s.name}({s.range_change}%)" for s in items[:5]] # Top 5 per industry
            lines.append(", ".join(names))
            lines.append("")
        return "\n".join(lines)

    def _format_stocks_for_fundamental(self, stocks: List[MainForceStock]) -> str:
        lines = ["| 代码 | 名称 | PE | PB | 营收 | 净利 |"]
        lines.append("|---|---|---|---|---|---|")
        # Sort by PE (valid positive PE first)
        valid_pe = [s for s in stocks if s.pe_ratio and s.pe_ratio > 0]
        sorted_stocks = sorted(valid_pe, key=lambda x: x.pe_ratio)[:30] # Top 30 lowest PE
        for s in sorted_stocks:
             lines.append(f"| {s.symbol} | {s.name} | {s.pe_ratio} | {s.pb_ratio} | {s.revenue} | {s.net_profit} |")
        return "\n".join(lines)

    def _format_stocks_full(self, stocks: List[MainForceStock]) -> str:
        # Format all info for final selection, maybe top 20 by fund inflow + top 10 by PE + top 10 by range change
        # To ensure diversity and quality. Or just pass the top 50 overall weighted.
        # For simplicity, pass top 50 by fund inflow.
        sorted_stocks = sorted(stocks, key=lambda x: x.main_fund_inflow or -float('inf'), reverse=True)[:50]
        
        lines = ["| 代码 | 名称 | 行业 | 主力净流入 | 涨跌幅 | PE | PB | 评分 |"]
        lines.append("|---|---|---|---|---|---|---|---|")
        for s in sorted_stocks:
            score_str = ", ".join([f"{k}:{v}" for k, v in s.scores.items() if str(v).isdigit() and float(v)>80]) # Only high scores
            lines.append(f"| {s.symbol} | {s.name} | {s.industry} | {s.main_fund_inflow} | {s.range_change} | {s.pe_ratio} | {s.pb_ratio} | {score_str} |")
        return "\n".join(lines)
