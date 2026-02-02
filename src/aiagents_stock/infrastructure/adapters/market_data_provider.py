"""
市场数据提供者实现。

该模块实现了 MarketDataProvider 端口，作为适配器将底层数据源（通过 DataSourceManager 获取）
转换为领域层所需的 StockDataBundle 格式。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd
import ta

from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.domain.analysis.ports import MarketDataProvider
from aiagents_stock.infrastructure.data_sources.data_source_manager import data_source_manager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AkshareMarketDataProvider(MarketDataProvider):
    """
    基于 DataSourceManager 的市场数据提供者实现。
    """

    def get_stock_data_bundle(self, *, symbol: str, period: str) -> StockDataBundle:
        """获取股票数据聚合包（含 K 线、指标）。"""
        
        # 1. 获取基本信息 (DataSourceManager 自动处理 A股/港股/美股)
        stock_info = self._get_stock_info(symbol)

        # 2. 获取历史数据 (DataSourceManager 自动处理 A股/港股/美股)
        # 转换 period 格式以适配内部逻辑 (e.g. "1y" is standard)
        raw_stock_data = self._get_stock_data(symbol, period=period)
        
        if isinstance(raw_stock_data, dict) and raw_stock_data.get("error"):
            return StockDataBundle(
                stock_info=stock_info,
                stock_data=None,
                indicators={"error": raw_stock_data.get("error")},
            )

        stock_data: pd.DataFrame = raw_stock_data
        
        # 3. 计算技术指标 (通用逻辑，不依赖数据源)
        with_indicators = self._calculate_technical_indicators(stock_data)
        
        if isinstance(with_indicators, dict) and with_indicators.get("error"):
            return StockDataBundle(
                stock_info=stock_info,
                stock_data=stock_data,
                indicators={"error": with_indicators.get("error")},
            )

        # 4. 提取最新指标快照
        indicators_snapshot = self._get_latest_indicators(with_indicators)
        if isinstance(indicators_snapshot, dict) and indicators_snapshot.get("error"):
            indicators: dict[str, Any] | None = {"error": indicators_snapshot.get("error")}
        else:
            indicators = indicators_snapshot

        return StockDataBundle(
            stock_info=stock_info, 
            stock_data=with_indicators, 
            indicators=indicators
        )

    def get_financial_data(self, *, symbol: str) -> Any:
        """获取财务数据。"""
        # DataSourceManager 目前主要支持 A股财务数据
        # 对于港美股，DataSourceManager 如果没有实现，会返回 None 或错误信息
        # 这里直接透传调用，未来在 DataSourceManager 中扩展
        return data_source_manager.get_financial_data(symbol)

    def get_stock_info(self, *, symbol: str) -> dict[str, Any]:
        """获取股票基本信息。"""
        return self._get_stock_info(symbol)

    # --- Internal Implementation Methods ---

    def _get_stock_info(self, symbol: str) -> dict[str, Any]:
        """内部获取股票信息方法"""
        return data_source_manager.get_stock_info(symbol)

    def _get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame | dict[str, Any]:
        """内部获取股票数据方法"""
        return data_source_manager.get_stock_data(symbol, period, interval)

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame | dict[str, Any]:
        """计算技术指标（通用）。"""
        try:
            # 确保数据按日期升序排列
            df = df.sort_index(ascending=True)

            if len(df) < 30:
                return {"error": "数据量不足，无法计算技术指标"}

            # MA
            df["MA5"] = ta.trend.sma_indicator(df["Close"], window=5)
            df["MA20"] = ta.trend.sma_indicator(df["Close"], window=20)
            df["MA60"] = ta.trend.sma_indicator(df["Close"], window=60)

            # MACD
            macd = ta.trend.MACD(df["Close"])
            df["MACD"] = macd.macd()
            df["MACD_signal"] = macd.macd_signal()
            df["MACD_hist"] = macd.macd_diff()

            # RSI
            df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

            # KDJ (Stochastic)
            stoch = ta.momentum.StochasticOscillator(
                high=df["High"], low=df["Low"], close=df["Close"], window=9, smooth_window=3
            )
            df["K"] = stoch.stoch()
            df["D"] = stoch.stoch_signal()
            df["J"] = 3 * df["K"] - 2 * df["D"]

            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
            df["BB_upper"] = bollinger.bollinger_hband()
            df["BB_middle"] = bollinger.bollinger_mavg()
            df["BB_lower"] = bollinger.bollinger_lband()

            # Volume MA
            df["Vol_MA5"] = ta.trend.sma_indicator(df["Volume"], window=5)
            df["Vol_MA20"] = ta.trend.sma_indicator(df["Volume"], window=20)

            # 填充 NaN (主要是前面的数据)
            df = df.bfill()

            return df

        except Exception as e:
            return {"error": f"计算技术指标失败: {str(e)}"}

    def _get_latest_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """提取最新一天的指标快照。"""
        try:
            if df is None or df.empty:
                return {"error": "数据为空"}

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            # 趋势判断
            trend = "震荡"
            if latest["MA5"] > latest["MA20"] > latest["MA60"]:
                trend = "多头排列"
            elif latest["MA5"] < latest["MA20"] < latest["MA60"]:
                trend = "空头排列"

            # 信号判断
            signals = []
            
            # MACD 金叉/死叉
            if latest["MACD"] > latest["MACD_signal"] and prev["MACD"] <= prev["MACD_signal"]:
                signals.append("MACD金叉")
            elif latest["MACD"] < latest["MACD_signal"] and prev["MACD"] >= prev["MACD_signal"]:
                signals.append("MACD死叉")

            # KDJ 金叉/死叉
            if latest["K"] > latest["D"] and prev["K"] <= prev["D"]:
                signals.append("KDJ金叉")
            elif latest["K"] < latest["D"] and prev["K"] >= prev["D"]:
                signals.append("KDJ死叉")

            # RSI 超买/超卖
            if latest["RSI"] > 70:
                signals.append("RSI超买")
            elif latest["RSI"] < 30:
                signals.append("RSI超卖")

            return {
                "date": str(latest.name.date()) if hasattr(latest.name, "date") else str(latest.name),
                "close": float(latest["Close"]),
                "change_percent": float(((latest["Close"] - prev["Close"]) / prev["Close"] * 100)) if len(df) > 1 else 0.0,
                "ma5": float(latest["MA5"]),
                "ma20": float(latest["MA20"]),
                "ma60": float(latest["MA60"]),
                "rsi": float(latest["RSI"]),
                "kdj": f"K:{latest['K']:.1f} D:{latest['D']:.1f} J:{latest['J']:.1f}",
                "macd": f"DIF:{latest['MACD']:.2f} DEA:{latest['MACD_signal']:.2f} MACD:{latest['MACD_hist']:.2f}",
                "trend": trend,
                "signals": signals,
            }

        except Exception as e:
            return {"error": f"提取指标快照失败: {str(e)}"}
