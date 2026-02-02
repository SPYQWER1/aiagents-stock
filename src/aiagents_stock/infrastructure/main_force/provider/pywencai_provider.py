#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyWencai主力资金数据提供者实现
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

import pandas as pd
import pywencai

from aiagents_stock.domain.main_force.ports import MainForceProvider
from aiagents_stock.domain.main_force.model import MainForceStock

logger = logging.getLogger(__name__)

class PyWencaiMainForceProvider(MainForceProvider):
    """基于PyWencai的主力资金数据提供者"""

    def get_main_force_stocks(
        self, 
        start_date: str = None, 
        days_ago: int = None, 
        min_market_cap: float = None, 
        max_market_cap: float = None,
        max_range_change: float = None,
        top_n: int = None
    ) -> Tuple[bool, List[MainForceStock], str]:
        """获取主力资金净流入股票"""
        try:
            # 1. 获取原始数据
            success, df, msg = self._fetch_raw_data(start_date, days_ago, min_market_cap, max_market_cap)
            if not success or df is None:
                return False, [], msg

            # 2. 筛选数据
            if max_range_change is not None:
                df = self._filter_stocks(df, max_range_change, min_market_cap, max_market_cap)
            
            # 3. 排序并取Top N
            if top_n is not None:
                df = self._get_top_stocks(df, top_n)
            
            # 4. 转换为领域对象
            stocks = self._convert_to_domain_objects(df)
            
            return True, stocks, f"成功获取 {len(stocks)} 只股票"
            
        except Exception as e:
            error_msg = f"获取主力选股数据失败: {str(e)}"
            logger.error(f"\n❌ {error_msg}")
            return False, [], error_msg

    def _fetch_raw_data(
        self, start_date: str = None, days_ago: int = None, min_market_cap: float = None, max_market_cap: float = None
    ) -> Tuple[bool, pd.DataFrame, str]:
        """获取原始数据"""
        try:
            # 如果没有提供开始日期，根据days_ago计算
            if not start_date:
                if days_ago is None:
                    days_ago = 10 # 默认10天
                date_obj = datetime.now() - timedelta(days=days_ago)
                start_date = f"{date_obj.year}年{date_obj.month}月{date_obj.day}日"
            
            logger.info(f"\n{'='*60}")
            logger.info("🔍 主力选股 - 数据获取中")
            logger.info(f"{'='*60}")
            logger.info(f"开始日期: {start_date}")
            logger.info("目标: 获取主力资金净流入排名前100名股票")
            
            # 构建查询语句
            queries = [
                # 方案1: 完整查询（最优）
                f"{start_date}以来主力资金净流入排名，并计算区间涨跌幅，市值{min_market_cap}-{max_market_cap}亿之间，非科创非st，"
                f"所属同花顺行业，总市值，净利润，营收，市盈率，市净率，"
                f"盈利能力评分，成长能力评分，营运能力评分，偿债能力评分，"
                f"现金流评分，资产质量评分，流动性评分，资本充足性评分",
                # 方案2: 简化查询
                f"{start_date}以来主力资金净流入，并计算区间涨跌幅，市值{min_market_cap}-{max_market_cap}亿，非科创非st，"
                f"所属同花顺行业，总市值，净利润，营收，市盈率，市净率",
                # 方案3: 基础查询
                f"{start_date}以来主力资金净流入排名，并计算区间涨跌幅，市值{min_market_cap}-{max_market_cap}亿，非科创非st，"
                f"所属行业，总市值",
                # 方案4: 最简查询
                f"{start_date}以来主力资金净流入前100名，并计算区间涨跌幅，市值{min_market_cap}-{max_market_cap}亿，非st非科创板，所属行业，总市值",
            ]
            
            # 尝试不同的查询方案
            for i, query in enumerate(queries, 1):
                logger.info(f"\n尝试方案 {i}/{len(queries)}...")
                # logger.info(f"查询语句: {query[:100]}...")
                
                try:
                    result = pywencai.get(query=query, loop=True)
                    
                    if result is None:
                        logger.warning(f"  ⚠️ 方案{i}返回None，尝试下一个方案")
                        continue
                        
                    # 转换为DataFrame
                    df_result = self._convert_to_dataframe(result)
                    
                    if df_result is None or df_result.empty:
                        logger.warning(f"  ⚠️ 方案{i}数据为空，尝试下一个方案")
                        continue
                        
                    # 成功获取数据
                    logger.info(f"  ✅ 方案{i}成功！获取到 {len(df_result)} 只股票")
                    return True, df_result, "Success"
                    
                except Exception as e:
                    logger.warning(f"  ❌ 方案{i}失败: {str(e)}")
                    time.sleep(2)  # 失败后等待2秒再试
                    continue
                    
            # 所有方案都失败
            error_msg = "所有查询方案都失败了，请检查网络或稍后重试"
            logger.error(f"\n❌ {error_msg}")
            return False, None, error_msg

        except Exception as e:
            return False, None, str(e)

    def _convert_to_dataframe(self, result) -> pd.DataFrame:
        """转换问财返回结果为DataFrame"""
        try:
            if isinstance(result, pd.DataFrame):
                return result
            elif isinstance(result, dict):
                # 检查是否有嵌套的tableV1结构
                if "tableV1" in result:
                    table_data = result["tableV1"]
                    if isinstance(table_data, pd.DataFrame):
                        return table_data
                    elif isinstance(table_data, list):
                        return pd.DataFrame(table_data)
                # 直接转换字典
                return pd.DataFrame([result])
            elif isinstance(result, list):
                return pd.DataFrame(result)
            else:
                return None
        except Exception as e:
            logger.error(f"  转换DataFrame失败: {e}", exc_info=True)
            return None

    def _filter_stocks(
        self,
        df: pd.DataFrame,
        max_range_change: float = None,
        min_market_cap: float = None,
        max_market_cap: float = None,
    ) -> pd.DataFrame:
        """智能筛选股票"""
        if df is None or df.empty:
            return df
            
        logger.info(f"\n{'='*60}")
        logger.info("🔍 智能筛选中...")
        
        filtered_df = df.copy()
        
        # 1. 筛选区间涨跌幅
        interval_pct_col = self._find_column(df, [
            "区间涨跌幅:前复权", "区间涨跌幅:前复权(%)", "区间涨跌幅(%)", "区间涨跌幅",
            "涨跌幅:前复权", "涨跌幅:前复权(%)", "涨跌幅(%)", "涨跌幅"
        ])
        
        if interval_pct_col:
            # Handle percentage strings if necessary (though _safe_float handles it elsewhere, pandas needs help here)
            # But usually it's numeric. Let's assume numeric or coerce.
            filtered_df[interval_pct_col] = pd.to_numeric(filtered_df[interval_pct_col], errors="coerce")
            filtered_df = filtered_df[
                (filtered_df[interval_pct_col].notna()) & (filtered_df[interval_pct_col] < max_range_change)
            ]
            
        # 2. 筛选市值
        market_cap_col = self._find_column(df, ["总市值", "市值"])
        if market_cap_col:
            # 使用统一的标准化方法（处理单位并转换为亿）
            self._normalize_currency_column(filtered_df, market_cap_col)
            
            if min_market_cap and max_market_cap:
                filtered_df = filtered_df[
                    (filtered_df[market_cap_col].notna())
                    & (filtered_df[market_cap_col] >= min_market_cap)
                    & (filtered_df[market_cap_col] <= max_market_cap)
                ]
            
        # 3. 去除ST股票
        if "股票简称" in filtered_df.columns:
            filtered_df = filtered_df[~filtered_df["股票简称"].str.contains("ST", na=False)]
            
        return filtered_df

    def _get_top_stocks(self, df: pd.DataFrame, top_n: int) -> pd.DataFrame:
        """获取前N名"""
        if df is None or df.empty:
            return df
            
        main_fund_col = self._find_column(df, [
            "区间主力资金流向", "区间主力资金净流入", "主力资金流向", 
            "主力资金净流入", "主力净流入"
        ])
        
        if main_fund_col:
            # 标准化资金流向列（处理单位）
            self._normalize_currency_column(df, main_fund_col)
            return df.nlargest(top_n, main_fund_col)
        else:
            return df.head(top_n)

    def _convert_to_domain_objects(self, df: pd.DataFrame) -> List[MainForceStock]:
        """转换为领域对象"""
        if df is None or df.empty:
            return []
            
        # 预处理：标准化关键列
        # 1. 查找列
        market_cap_col = self._find_column(df, ["总市值", "市值"])
        main_fund_col = self._find_column(df, [
            "区间主力资金流向", "区间主力资金净流入", "主力资金流向", 
            "主力资金净流入", "主力净流入"
        ])
        
        # 2. 标准化金额列（转换为亿）
        if market_cap_col:
            self._normalize_currency_column(df, market_cap_col)
        if main_fund_col:
            self._normalize_currency_column(df, main_fund_col)
            
        stocks = []
        for _, row in df.iterrows():
            # 查找关键字段
            interval_pct_col = self._find_column(df, [
                "区间涨跌幅:前复权", "区间涨跌幅:前复权(%)", "区间涨跌幅(%)", "区间涨跌幅",
                "涨跌幅:前复权", "涨跌幅:前复权(%)", "涨跌幅(%)", "涨跌幅"
            ])
            
            # 提取评分
            scores = {}
            score_keywords = ["评分", "能力"]
            for col in df.columns:
                if any(keyword in col for keyword in score_keywords):
                    scores[col] = row.get(col, "N/A")
            
            # 动态查找其他列
            industry_col = self._find_column(df, ["所属同花顺行业", "所属行业", "行业"])
            revenue_col = self._find_column(df, ["营业收入", "营收"])
            net_profit_col = self._find_column(df, ["净利润"])
            pe_col = self._find_column(df, ["市盈率"])
            pb_col = self._find_column(df, ["市净率"])

            stock = MainForceStock(
                symbol=str(row.get("股票代码", "N/A")),
                name=str(row.get("股票简称", "N/A")),
                industry=str(row.get(industry_col, "N/A")) if industry_col else "N/A",
                market_cap=self._safe_float(row.get(market_cap_col, 0)) if market_cap_col else 0.0,
                range_change=self._safe_float(row.get(interval_pct_col, 0)) if interval_pct_col else 0.0,
                main_fund_inflow=self._safe_float(row.get(main_fund_col, 0)) if main_fund_col else 0.0,
                pe_ratio=self._safe_float(row.get(pe_col, None)) if pe_col else 0.0,
                pb_ratio=self._safe_float(row.get(pb_col, None)) if pb_col else 0.0,
                revenue=str(row.get(revenue_col, "N/A")) if revenue_col else "N/A",
                net_profit=str(row.get(net_profit_col, "N/A")) if net_profit_col else "N/A",
                scores=scores,
                raw_data=row.to_dict()
            )
            stocks.append(stock)
            
        return stocks

    def _normalize_currency_column(self, df: pd.DataFrame, col: str):
        """标准化金额列（统一转换为亿）"""
        if col not in df.columns:
            return
            
        def parse_val(val):
            if isinstance(val, str):
                val = val.strip()
                if '亿' in val:
                    try:
                        return float(val.replace('亿', '')) * 100000000
                    except:
                        return 0.0
                elif '万' in val:
                    try:
                        return float(val.replace('万', '')) * 10000
                    except:
                        return 0.0
            return val
            
        # 先处理字符串单位
        df[col] = df[col].apply(parse_val)
        # 转换为数字
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 判断单位并转换
        # 如果最大值 > 10万，认为是元，转换为亿
        if df[col].max() > 100000:
            df[col] = df[col] / 100000000

    def _find_column(self, df: pd.DataFrame, possible_names: List[str]) -> str:
        """查找匹配的列名"""
        for name in possible_names:
            for col in df.columns:
                if name in col:
                    return col
        return None

    def _safe_float(self, value):
        """安全转换为float"""
        try:
            if isinstance(value, str):
                value = value.replace('%', '')
            return float(value)
        except (ValueError, TypeError):
            return 0.0
