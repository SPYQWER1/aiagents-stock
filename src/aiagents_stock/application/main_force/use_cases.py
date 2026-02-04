import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiagents_stock.domain.main_force.model import MainForceAnalysis, MainForceStock
from aiagents_stock.domain.main_force.ports import MainForceAIAnalyzer, MainForceAnalysisRepository, MainForceProvider

logger = logging.getLogger(__name__)

class AnalyzeMainForceUseCase:
    
    def __init__(
        self,
        provider: MainForceProvider,
        analyzer: MainForceAIAnalyzer,
        repository: MainForceAnalysisRepository
    ):
        self.provider = provider
        self.analyzer = analyzer
        self.repository = repository
        
    def execute(
        self,
        days_ago: int = 10,
        final_n: int = 5,
        max_range_change: float = 20.0,
        min_market_cap: float = 50.0,
        max_market_cap: float = 2000.0,
        start_date: str = None
    ) -> MainForceAnalysis:
        
        start_time = datetime.now()
        analysis = MainForceAnalysis(params={
            "days_ago": days_ago,
            "final_n": final_n,
            "max_range_change": max_range_change,
            "min_market_cap": min_market_cap,
            "max_market_cap": max_market_cap,
            "start_date": start_date
        })
        
        try:
            # 1. 获取数据
            success, stocks, msg = self.provider.get_main_force_stocks(
                start_date=start_date,
                days_ago=days_ago,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                max_range_change=max_range_change
            )
            
            if not success:
                analysis.error = msg
                return analysis
                
            analysis.raw_stocks = stocks
            
            # 2. 过滤数据
            # 注意：Provider可能已经做了一部分过滤，这里做更严格的业务过滤
            filtered_stocks = [
                s for s in stocks 
                if s.range_change <= max_range_change 
                and min_market_cap <= s.market_cap <= max_market_cap
            ]
            analysis.filtered_stocks = filtered_stocks
            
            if not filtered_stocks:
                analysis.error = "过滤后没有符合条件的股票"
                return analysis
                
            # 3. 生成摘要
            summary = self._generate_summary(filtered_stocks)
            
            # 4. AI 分析 (这里我们选择串行执行，确保逻辑清晰)
            # 在实际UI中，可能需要流式反馈，但UseCase层负责核心业务逻辑编排
            
            # 4.1 资金流向分析
            analysis.fund_flow_analysis = self.analyzer.analyze_fund_flow(filtered_stocks, summary)
            
            # 4.2 行业分析
            analysis.industry_analysis = self.analyzer.analyze_industry(filtered_stocks, summary)
            
            # 4.3 基本面分析
            analysis.fundamental_analysis = self.analyzer.analyze_fundamental(filtered_stocks, summary)
            
            # 5. 综合选股
            analysis.recommendations = self.analyzer.select_best_stocks(
                filtered_stocks,
                analysis.fund_flow_analysis,
                analysis.industry_analysis,
                analysis.fundamental_analysis,
                final_n
            )
            
            if not analysis.recommendations:
                analysis.error = "AI未能生成有效推荐结果(解析为空)"
                analysis.success = False
                return analysis
            
            analysis.success = True
            
        except Exception as e:
            logger.error(f"主力选股分析失败: {e}", exc_info=True)
            analysis.error = str(e)
            analysis.success = False
        finally:
            analysis.total_time = (datetime.now() - start_time).total_seconds()
            # 6. 保存结果 (仅在成功或部分成功时保存，方便回溯)
            if analysis.success or analysis.raw_stocks:
                try:
                    analysis.id = self.repository.save(analysis)
                except Exception as e:
                    logger.error(f"保存分析结果失败: {e}")
            
        return analysis

    def _generate_summary(self, stocks: List[MainForceStock]) -> str:
        count = len(stocks)
        avg_change = sum(s.range_change for s in stocks) / count if count > 0 else 0
        avg_cap = sum(s.market_cap for s in stocks) / count if count > 0 else 0
        
        industries = {}
        for s in stocks:
            industries[s.industry] = industries.get(s.industry, 0) + 1
        top_industries = sorted(industries.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return (
            f"本次共筛选出 {count} 只主力资金净流入股票。\n"
            f"平均区间涨跌幅: {avg_change:.2f}%，平均市值: {avg_cap:.2f}亿。\n"
            f"主要分布行业: {', '.join([f'{k}({v})' for k, v in top_industries])}。"
        )

class GetMainForceHistoryUseCase:
    def __init__(self, repository: MainForceAnalysisRepository):
        self.repository = repository
        
    def execute(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.repository.get_history(limit)
        
    def get_by_id(self, record_id: int) -> Optional[MainForceAnalysis]:
        return self.repository.get_by_id(record_id)
        
    def delete(self, record_id: int) -> bool:
        return self.repository.delete(record_id)
