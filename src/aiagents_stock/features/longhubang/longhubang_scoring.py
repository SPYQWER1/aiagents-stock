"""
智瞰龙虎AI智能评分模块
对龙虎榜上榜股票进行综合评分排名
"""

from typing import Dict, List

import pandas as pd


class LonghubangScoring:
    """龙虎榜股票智能评分系统"""

    def __init__(self):
        """初始化评分系统"""
        # 顶级游资名单（根据市场知名度和历史战绩）
        self.top_youzi = [
            "赵老哥",
            "章盟主",
            "92科比",
            "瑞鹤仙",
            "小鳄鱼",
            "养家心法",
            "欢乐海岸",
            "古北路",
            "成都系",
            "佛山系",
            "方新侠",
            "乔帮主",
            "淮海路",
            "东方财富",
            "国信深圳",
            "华泰深圳",
            "中信杭州",
            "招商深圳",
        ]

        # 知名游资（次一级）
        self.famous_youzi = [
            "深股通",
            "沪股通",
            "北向资金",
            "中金公司",
            "中信证券",
            "国泰君安",
            "海通证券",
            "广发证券",
            "华泰证券",
            "招商证券",
        ]

        # 机构关键词
        self.institution_keywords = ["机构专用", "机构", "基金", "保险", "社保", "QFII", "RQFII", "券商", "信托"]

        self.logger.info("[智瞰龙虎] 评分系统初始化完成")

    def calculate_stock_score(self, stock_data: List[Dict]) -> float:
        """
        计算单个股票的综合评分

        Args:
            stock_data: 该股票的所有龙虎榜记录

        Returns:
            综合评分 (0-100分)
        """
        if not stock_data:
            return 0.0

        # 1. 买入资金含金量评分 (0-30分)
        capital_quality_score = self._calculate_capital_quality(stock_data)

        # 2. 净买入额评分 (0-25分)
        net_inflow_score = self._calculate_net_inflow_score(stock_data)

        # 3. 卖出压力评分 (0-20分)
        sell_pressure_score = self._calculate_sell_pressure_score(stock_data)

        # 4. 机构共振评分 (0-15分)
        institution_score = self._calculate_institution_score(stock_data)

        # 5. 其他加分项 (0-10分)
        bonus_score = self._calculate_bonus_score(stock_data)

        # 综合评分
        total_score = capital_quality_score + net_inflow_score + sell_pressure_score + institution_score + bonus_score

        return round(total_score, 1)

    def _calculate_capital_quality(self, stock_data: List[Dict]) -> float:
        """
        计算买入资金含金量评分 (0-30分)
        顶级游资加分多，普通游资加分少
        """
        score = 0.0
        max_score = 30.0

        buyers = []
        for record in stock_data:
            buy_amount = record.get("买入金额", 0) or record.get("mrje", 0)
            # 确保转换为数值类型
            try:
                buy_amount = float(buy_amount) if buy_amount else 0
            except (ValueError, TypeError):
                buy_amount = 0

            if buy_amount > 0:
                youzi_name = record.get("游资名称", "") or record.get("yzmc", "")
                yingye_bu = record.get("营业部", "") or record.get("yyb", "")
                buyers.append({"name": youzi_name, "yingye_bu": yingye_bu, "amount": float(buy_amount)})

        if not buyers:
            return 0.0

        # 顶级游资：每个加8-10分
        top_youzi_count = 0
        for buyer in buyers:
            for top in self.top_youzi:
                if top in buyer["name"] or top in buyer["yingye_bu"]:
                    top_youzi_count += 1
                    score += 10.0
                    break

        # 知名游资：每个加4-6分
        famous_youzi_count = 0
        for buyer in buyers:
            is_top = any(top in buyer["name"] or top in buyer["yingye_bu"] for top in self.top_youzi)
            if not is_top:
                for famous in self.famous_youzi:
                    if famous in buyer["name"] or famous in buyer["yingye_bu"]:
                        famous_youzi_count += 1
                        score += 5.0
                        break

        # 普通游资：每个加1-2分
        ordinary_count = len(buyers) - top_youzi_count - famous_youzi_count
        score += ordinary_count * 1.5

        # 限制最高分
        return min(score, max_score)

    def _calculate_net_inflow_score(self, stock_data: List[Dict]) -> float:
        """
        计算净买入额评分 (0-25分)
        真金白银越多分数越高
        """
        max_score = 25.0

        # 计算总净流入
        total_net_inflow = 0.0
        for record in stock_data:
            net_inflow = record.get("净流入金额", 0) or record.get("jlrje", 0)
            try:
                net_inflow = float(net_inflow) if net_inflow else 0
                total_net_inflow += net_inflow
            except (ValueError, TypeError):
                pass

        if total_net_inflow <= 0:
            return 0.0

        # 净流入分段评分
        # 1000万以下：0-10分
        # 1000-5000万：10-18分
        # 5000万-1亿：18-22分
        # 1亿以上：22-25分
        net_inflow_wan = total_net_inflow / 10000  # 转换为万元

        if net_inflow_wan < 1000:
            score = (net_inflow_wan / 1000) * 10
        elif net_inflow_wan < 5000:
            score = 10 + ((net_inflow_wan - 1000) / 4000) * 8
        elif net_inflow_wan < 10000:
            score = 18 + ((net_inflow_wan - 5000) / 5000) * 4
        else:
            score = 22 + min((net_inflow_wan - 10000) / 10000, 1) * 3

        return min(score, max_score)

    def _calculate_sell_pressure_score(self, stock_data: List[Dict]) -> float:
        """
        计算卖出压力评分 (0-20分)
        卖出压力越小分数越高
        """
        max_score = 20.0

        total_buy = 0.0
        total_sell = 0.0

        for record in stock_data:
            buy_amount = record.get("买入金额", 0) or record.get("mrje", 0)
            sell_amount = record.get("卖出金额", 0) or record.get("mcje", 0)

            try:
                buy_amount = float(buy_amount) if buy_amount else 0
                total_buy += buy_amount
            except (ValueError, TypeError):
                pass

            try:
                sell_amount = float(sell_amount) if sell_amount else 0
                total_sell += sell_amount
            except (ValueError, TypeError):
                pass

        if total_buy == 0:
            return 0.0

        # 计算卖出比例
        sell_ratio = total_sell / total_buy if total_buy > 0 else 1.0

        # 卖出压力评分
        # 卖出比例0-10%：20分
        # 卖出比例10-30%：15-20分
        # 卖出比例30-50%：10-15分
        # 卖出比例50-80%：5-10分
        # 卖出比例80%以上：0-5分
        if sell_ratio < 0.1:
            score = 20.0
        elif sell_ratio < 0.3:
            score = 20.0 - (sell_ratio - 0.1) / 0.2 * 5
        elif sell_ratio < 0.5:
            score = 15.0 - (sell_ratio - 0.3) / 0.2 * 5
        elif sell_ratio < 0.8:
            score = 10.0 - (sell_ratio - 0.5) / 0.3 * 5
        else:
            score = 5.0 - min(sell_ratio - 0.8, 0.2) / 0.2 * 5

        return max(0, min(score, max_score))

    def _calculate_institution_score(self, stock_data: List[Dict]) -> float:
        """
        计算机构共振评分 (0-15分)
        机构+游资共振最高分
        """
        max_score = 15.0

        has_institution = False
        has_youzi = False
        institution_count = 0
        youzi_count = 0

        for record in stock_data:
            buy_amount = record.get("买入金额", 0) or record.get("mrje", 0)
            try:
                buy_amount = float(buy_amount) if buy_amount else 0
            except (ValueError, TypeError):
                buy_amount = 0

            if buy_amount <= 0:
                continue

            youzi_name = record.get("游资名称", "") or record.get("yzmc", "")
            yingye_bu = record.get("营业部", "") or record.get("yyb", "")

            # 检查是否是机构
            if any(keyword in youzi_name or keyword in yingye_bu for keyword in self.institution_keywords):
                has_institution = True
                institution_count += 1
            else:
                has_youzi = True
                youzi_count += 1

        # 评分逻辑
        if has_institution and has_youzi:
            # 机构+游资共振：最高分
            score = 15.0
        elif has_institution:
            # 仅机构：8-12分
            score = min(8 + institution_count * 2, 12)
        elif has_youzi:
            # 仅游资：5-10分
            score = min(5 + youzi_count * 1, 10)
        else:
            score = 0.0

        return min(score, max_score)

    def _calculate_bonus_score(self, stock_data: List[Dict]) -> float:
        """
        计算其他加分项 (0-10分)
        买卖比例、主力集中度、热门概念等
        """
        max_score = 10.0
        score = 0.0

        if not stock_data:
            return 0.0

        # 1. 主力集中度加分 (0-3分)
        # 如果资金集中在少数几个席位，说明主力信心强
        seat_count = len(stock_data)
        if seat_count == 1:
            score += 3.0
        elif seat_count == 2:
            score += 2.5
        elif seat_count == 3:
            score += 2.0
        elif seat_count <= 5:
            score += 1.5
        else:
            score += 1.0

        # 2. 热门概念加分 (0-3分)
        all_concepts = []
        for record in stock_data:
            concepts = record.get("概念", "") or record.get("gl", "")
            if concepts:
                all_concepts.extend([c.strip() for c in str(concepts).split(",")])

        hot_keywords = [
            "人工智能",
            "AI",
            "ChatGPT",
            "算力",
            "新能源",
            "芯片",
            "半导体",
            "军工",
            "医药",
            "消费",
            "5G",
            "新材料",
            "量子",
            "光伏",
            "储能",
            "锂电池",
            "汽车",
            "游戏",
            "传媒",
            "元宇宙",
        ]

        concept_score = 0
        for concept in all_concepts:
            if any(keyword in concept for keyword in hot_keywords):
                concept_score += 0.3

        score += min(concept_score, 3.0)

        # 3. 连续上榜加分 (0-2分)
        # 这里简化处理，如果有多条记录可能表示连续上榜
        if len(stock_data) >= 3:
            score += 2.0
        elif len(stock_data) == 2:
            score += 1.0

        # 4. 买卖比例优秀加分 (0-2分)
        total_buy = 0.0
        total_sell = 0.0
        for r in stock_data:
            try:
                buy = float(r.get("买入金额", 0) or r.get("mrje", 0) or 0)
                total_buy += buy
            except (ValueError, TypeError):
                pass
            try:
                sell = float(r.get("卖出金额", 0) or r.get("mcje", 0) or 0)
                total_sell += sell
            except (ValueError, TypeError):
                pass

        if total_buy > 0:
            buy_sell_ratio = total_buy / (total_sell + 1)
            if buy_sell_ratio >= 10:
                score += 2.0
            elif buy_sell_ratio >= 5:
                score += 1.5
            elif buy_sell_ratio >= 3:
                score += 1.0

        return min(score, max_score)

    def score_all_stocks(self, data_list: List[Dict]) -> pd.DataFrame:
        """
        对所有上榜股票进行评分排名

        Args:
            data_list: 龙虎榜数据列表

        Returns:
            评分排名DataFrame
        """
        if not data_list:
            return pd.DataFrame()

        # 按股票代码分组
        stocks_dict = {}
        for record in data_list:
            code = record.get("股票代码") or record.get("gpdm")
            name = record.get("股票名称") or record.get("gpmc")

            if not code:
                continue

            if code not in stocks_dict:
                stocks_dict[code] = {"code": code, "name": name, "records": []}

            stocks_dict[code]["records"].append(record)

        # 计算每只股票的评分
        results = []
        for code, stock_info in stocks_dict.items():
            records = stock_info["records"]

            # 计算各维度评分
            capital_quality = self._calculate_capital_quality(records)
            net_inflow = self._calculate_net_inflow_score(records)
            sell_pressure = self._calculate_sell_pressure_score(records)
            institution = self._calculate_institution_score(records)
            bonus = self._calculate_bonus_score(records)

            total_score = capital_quality + net_inflow + sell_pressure + institution + bonus

            # 计算实际数据（安全转换）
            total_buy = 0.0
            total_sell = 0.0
            total_net = 0.0
            for r in records:
                try:
                    buy = float(r.get("买入金额", 0) or r.get("mrje", 0) or 0)
                    total_buy += buy
                except (ValueError, TypeError):
                    pass
                try:
                    sell = float(r.get("卖出金额", 0) or r.get("mcje", 0) or 0)
                    total_sell += sell
                except (ValueError, TypeError):
                    pass
                try:
                    net = float(r.get("净流入金额", 0) or r.get("jlrje", 0) or 0)
                    total_net += net
                except (ValueError, TypeError):
                    pass

            # 统计买入席位数（安全比较）
            buy_seats = 0
            for r in records:
                try:
                    buy = float(r.get("买入金额", 0) or r.get("mrje", 0) or 0)
                    if buy > 0:
                        buy_seats += 1
                except (ValueError, TypeError):
                    pass

            # 统计机构数量
            institution_count = sum(
                1
                for r in records
                if any(
                    kw in (r.get("游资名称", "") or r.get("yzmc", ""))
                    or kw in (r.get("营业部", "") or r.get("yyb", ""))
                    for kw in self.institution_keywords
                )
            )

            # 判断机构参与
            has_institution = institution_count > 0

            results.append(
                {
                    "排名": 0,  # 稍后填充
                    "排名_display": "",  # 用于显示奖牌
                    "股票名称": stock_info["name"],
                    "股票代码": code,
                    "综合评分": round(total_score, 1),
                    "资金含金量": round(capital_quality, 0),
                    "净买入额": round(net_inflow, 0),
                    "卖出压力": round(sell_pressure, 0),
                    "机构共振": round(institution, 0),
                    "加分项": round(bonus, 0),
                    "顶级游资": self._count_top_youzi(records),
                    "买方数": buy_seats,
                    "机构参与": "✅" if has_institution else "❌",
                    "净流入": round(total_net, 2),
                }
            )

        # 转换为DataFrame并排序
        df = pd.DataFrame(results)
        if df.empty:
            return df

        df = df.sort_values("综合评分", ascending=False).reset_index(drop=True)
        df["排名"] = range(1, len(df) + 1)

        # 添加奖牌显示
        df["排名_display"] = df["排名"].astype(str)
        if len(df) >= 1:
            df.loc[0, "排名_display"] = "🥇 1"
        if len(df) >= 2:
            df.loc[1, "排名_display"] = "🥈 2"
        if len(df) >= 3:
            df.loc[2, "排名_display"] = "🥉 3"

        return df

    def _count_top_youzi(self, records: List[Dict]) -> int:
        """统计顶级游资数量"""
        count = 0
        for record in records:
            buy_amount = record.get("买入金额", 0) or record.get("mrje", 0)
            try:
                buy_amount = float(buy_amount) if buy_amount else 0
            except (ValueError, TypeError):
                buy_amount = 0

            if buy_amount <= 0:
                continue

            youzi_name = record.get("游资名称", "") or record.get("yzmc", "")
            yingye_bu = record.get("营业部", "") or record.get("yyb", "")

            if any(top in youzi_name or top in yingye_bu for top in self.top_youzi):
                count += 1

        return count

    def get_score_explanation(self) -> str:
        """获取评分维度说明"""
        explanation = """
        【AI智能评分维度说明】
        
        📊 总分100分，由5个维度组成：
        
        1️⃣ 买入资金含金量 (0-30分)
           - 顶级游资（赵老哥、章盟主等）：每个+10分
           - 知名游资（深股通、中信等）：每个+5分
           - 普通游资：每个+1.5分
           
        2️⃣ 净买入额评分 (0-25分)
           - 净流入1000万以下：0-10分
           - 净流入1000-5000万：10-18分
           - 净流入5000万-1亿：18-22分
           - 净流入1亿以上：22-25分
           
        3️⃣ 卖出压力评分 (0-20分)
           - 卖出比例0-10%：20分（压力极小）
           - 卖出比例10-30%：15-20分（压力较小）
           - 卖出比例30-50%：10-15分（压力中等）
           - 卖出比例50-80%：5-10分（压力较大）
           - 卖出比例80%以上：0-5分（压力极大）
           
        4️⃣ 机构共振评分 (0-15分)
           - 机构+游资共振：15分（最强信号）
           - 仅机构买入：8-12分
           - 仅游资买入：5-10分
           
        5️⃣ 其他加分项 (0-10分)
           - 主力集中度：席位越少越集中，+1-3分
           - 热门概念：AI、新能源、芯片等，+0-3分
           - 连续上榜：连续多日上榜，+0-2分
           - 买卖比例优秀：买入远大于卖出，+0-2分
        
        💡 评分越高，表示该股票受到资金青睐程度越高，
           但仍需结合市场环境、技术面等因素综合判断！
        """
        return explanation


# 测试函数
if __name__ == "__main__":
    # 配置基本日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("测试智瞰龙虎评分系统")
    logger.info("=" * 60)

    # 创建测试数据
    test_data = [
        {
            "股票代码": "001337",
            "股票名称": "四川黄金",
            "游资名称": "92科比",
            "营业部": "兴业证券股份有限公司南京天元东路证券营业部",
            "买入金额": 14470401,
            "卖出金额": 15080,
            "净流入金额": 14455321,
            "概念": "贵金属,黄金概念,次新股",
        },
        {
            "股票代码": "001337",
            "股票名称": "四川黄金",
            "游资名称": "赵老哥",
            "营业部": "某证券公司",
            "买入金额": 10000000,
            "卖出金额": 0,
            "净流入金额": 10000000,
            "概念": "贵金属,黄金概念",
        },
    ]

    scoring = LonghubangScoring()

    # 测试评分
    df_result = scoring.score_all_stocks(test_data)

    logger.info("\n评分结果：")
    # 使用 to_string() 避免打印 DataFrame 时截断
    logger.info("\n" + df_result.to_string())

    logger.info("\n" + scoring.get_score_explanation())
