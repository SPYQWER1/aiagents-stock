"""
市场数据提供者实现。

该模块实现了 MarketDataProvider 端口，直接对接 Akshare/Tushare/YFinance 等外部数据源。
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import akshare as ak
import numpy as np
import pandas as pd
import ta
import yfinance as yf

from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.domain.analysis.ports import MarketDataProvider
from aiagents_stock.infrastructure.data_sources.data_source_manager import data_source_manager

logger = logging.getLogger(__name__)



def is_chinese_stock(symbol: str) -> bool:
    """判断是否为中国A股"""
    # 简单判断：包含数字且长度为6位的认为是中国A股
    return symbol.isdigit() and len(symbol) == 6


def is_hk_stock(symbol: str) -> bool:
    """判断是否为港股"""
    # 港股代码通常是1-5位数字，或者前面带HK/hk前缀
    if symbol.upper().startswith("HK"):
        return True
    # 纯数字且长度在1-5位之间，认为可能是港股
    if symbol.isdigit() and 1 <= len(symbol) <= 5:
        return True
    return False


def normalize_hk_code(symbol: str) -> str:
    """规范化港股代码为5位格式（如700 -> 00700）"""
    # 移除HK前缀
    if symbol.upper().startswith("HK"):
        symbol = symbol[2:]
    # 补齐到5位
    return symbol.zfill(5)


@dataclass(frozen=True)
class AkshareMarketDataProvider(MarketDataProvider):
    """
    基于 Akshare/Tushare/YFinance 的市场数据提供者实现。
    """

    def get_stock_data_bundle(self, *, symbol: str, period: str) -> StockDataBundle:
        """获取股票数据聚合包（含 K 线、指标）。"""
        
        # 1. 获取基本信息
        stock_info = self._get_stock_info(symbol)

        # 2. 获取历史数据
        # 转换 period 格式以适配内部逻辑 (e.g. "1y" is standard)
        raw_stock_data = self._get_stock_data(symbol, period=period)
        
        if isinstance(raw_stock_data, dict) and raw_stock_data.get("error"):
            return StockDataBundle(
                stock_info=stock_info,
                stock_data=None,
                indicators={"error": raw_stock_data.get("error")},
            )

        stock_data: pd.DataFrame = raw_stock_data
        
        # 3. 计算技术指标
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
        try:
            if is_chinese_stock(symbol):
                return self._get_chinese_financial_data(symbol)
            elif is_hk_stock(symbol):
                return self._get_hk_financial_data(symbol)
            else:
                return self._get_us_financial_data(symbol)
        except Exception as e:
            return {"error": f"获取财务数据失败: {str(e)}"}

    def get_stock_info(self, *, symbol: str) -> dict[str, Any]:
        """获取股票基本信息。"""
        return self._get_stock_info(symbol)

    # --- Internal Implementation Methods (Ported from StockDataFetcher) ---

    def _get_stock_info(self, symbol: str) -> dict[str, Any]:
        try:
            if is_chinese_stock(symbol):
                return self._get_chinese_stock_info(symbol)
            elif is_hk_stock(symbol):
                return self._get_hk_stock_info(symbol)
            else:
                return self._get_us_stock_info(symbol)
        except Exception as e:
            return {"error": f"获取股票信息失败: {str(e)}"}

    def _get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame | dict[str, Any]:
        try:
            if is_chinese_stock(symbol):
                return self._get_chinese_stock_data(symbol, period)
            elif is_hk_stock(symbol):
                return self._get_hk_stock_data(symbol, period)
            else:
                return self._get_us_stock_data(symbol, period, interval)
        except Exception as e:
            return {"error": f"获取股票数据失败: {str(e)}"}

    def _get_chinese_stock_info(self, symbol: str) -> dict[str, Any]:
        try:
            info = {
                "symbol": symbol,
                "name": "未知",
                "current_price": "N/A",
                "change_percent": "N/A",
                "pe_ratio": "N/A",
                "pb_ratio": "N/A",
                "market_cap": "N/A",
                "market": "中国A股",
                "exchange": "上海/深圳证券交易所",
            }

            # 使用数据源管理器获取基本信息
            basic_info = data_source_manager.get_stock_basic_info(symbol)
            if basic_info:
                info.update(basic_info)

            # 方法1: 尝试获取个股详细信息（akshare）
            try:
                stock_info = ak.stock_individual_info_em(symbol=symbol)
                if stock_info is not None and not stock_info.empty:
                    for _, row in stock_info.iterrows():
                        key = row["item"]
                        value = row["value"]

                        if key == "股票简称":
                            info["name"] = value
                        elif key == "总市值":
                            try:
                                if value and value != "-":
                                    info["market_cap"] = float(value)
                            except Exception:
                                pass
                        elif key == "市盈率-动态":
                            try:
                                if value and value != "-":
                                    pe_value = float(value)
                                    if 0 < pe_value <= 1000:
                                        info["pe_ratio"] = pe_value
                            except Exception:
                                pass
                        elif key == "市净率":
                            try:
                                if value and value != "-":
                                    pb_value = float(value)
                                    if 0 < pb_value <= 100:
                                        info["pb_ratio"] = pb_value
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"[Akshare] 获取个股详细信息失败: {e}")
                # 如果akshare失败，尝试从tushare获取
                if data_source_manager.tushare_available and info["name"] == "未知":
                    try:
                        ts_code = data_source_manager._convert_to_ts_code(symbol)
                        df = data_source_manager.tushare_api.daily_basic(
                            ts_code=ts_code, trade_date=datetime.now().strftime("%Y%m%d")
                        )
                        if df is not None and not df.empty:
                            row = df.iloc[0]
                            info["pe_ratio"] = row.get("pe", "N/A")
                            info["pb_ratio"] = row.get("pb", "N/A")
                            info["market_cap"] = row.get("total_mv", "N/A")
                    except Exception as te:
                        logger.warning(f"[Tushare] ❌ 获取失败: {te}")

            # 尝试获取最近交易数据以补充价格信息
            try:
                hist_data = data_source_manager.get_stock_hist_data(
                    symbol=symbol,
                    start_date=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d"),
                    adjust="qfq",
                )

                if hist_data is not None and not hist_data.empty:
                    if "close" in hist_data.columns:
                        latest = hist_data.iloc[-1]
                        info["current_price"] = latest["close"]
                        if len(hist_data) > 1:
                            prev_close = hist_data.iloc[-2]["close"]
                            change_pct = ((latest["close"] - prev_close) / prev_close) * 100
                            info["change_percent"] = round(change_pct, 2)
            except Exception as e2:
                logger.warning(f"获取历史数据也失败: {e2}")

            # 补充市盈率/市净率
            if info["pe_ratio"] == "N/A":
                try:
                    pe_data = ak.stock_zh_valuation_baidu(symbol=symbol, indicator="市盈率(TTM)")
                    if pe_data is not None and not pe_data.empty:
                        latest_pe = pe_data.iloc[-1]["value"]
                        if latest_pe and latest_pe != "-":
                            pe_val = float(latest_pe)
                            if 0 < pe_val <= 1000:
                                info["pe_ratio"] = pe_val
                except Exception:
                    pass

            if info["pb_ratio"] == "N/A":
                try:
                    pb_data = ak.stock_zh_valuation_baidu(symbol=symbol, indicator="市净率")
                    if pb_data is not None and not pb_data.empty:
                        latest_pb = pb_data.iloc[-1]["value"]
                        if latest_pb and latest_pb != "-":
                            pb_val = float(latest_pb)
                            if 0 < pb_val <= 100:
                                info["pb_ratio"] = pb_val
                except Exception:
                    pass

            return info

        except Exception as e:
            logger.error(f"获取中国股票信息完全失败: {e}", exc_info=True)
            return {
                "symbol": symbol,
                "name": f"股票{symbol}",
                "current_price": "N/A",
                "change_percent": "N/A",
                "pe_ratio": "N/A",
                "pb_ratio": "N/A",
                "market_cap": "N/A",
                "market": "中国A股",
                "exchange": "上海/深圳证券交易所",
            }

    def _get_hk_stock_info(self, symbol: str) -> dict[str, Any]:
        try:
            hk_code = normalize_hk_code(symbol)
            info = {
                "symbol": hk_code,
                "name": "未知",
                "current_price": "N/A",
                "change_percent": "N/A",
                "pe_ratio": "N/A",
                "pb_ratio": "N/A",
                "market_cap": "N/A",
                "market": "香港股市",
                "exchange": "香港交易所",
            }

            try:
                realtime_df = ak.stock_hk_spot_em()
                if realtime_df is not None and not realtime_df.empty:
                    stock_data = realtime_df[realtime_df["代码"] == hk_code]
                    if not stock_data.empty:
                        row = stock_data.iloc[0]
                        info["name"] = row.get("名称", "未知")
                        info["current_price"] = row.get("最新价", "N/A")
                        info["change_percent"] = row.get("涨跌幅", "N/A")
                        
                        market_cap = row.get("总市值", "N/A")
                        if market_cap != "N/A":
                            try:
                                info["market_cap"] = float(market_cap)
                            except Exception:
                                pass

                        pe = row.get("市盈率", "N/A")
                        if pe != "N/A" and pe != "-":
                            try:
                                pe_val = float(pe)
                                if 0 < pe_val <= 1000:
                                    info["pe_ratio"] = pe_val
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"获取港股实时数据失败: {e}")

            if info["current_price"] == "N/A":
                try:
                    hist_df = ak.stock_hk_hist(
                        symbol=hk_code,
                        period="daily",
                        start_date=(datetime.now() - timedelta(days=5)).strftime("%Y%m%d"),
                        end_date=datetime.now().strftime("%Y%m%d"),
                        adjust="qfq",
                    )
                    if hist_df is not None and not hist_df.empty:
                        latest = hist_df.iloc[-1]
                        info["current_price"] = latest["收盘"]
                        if len(hist_df) > 1:
                            prev_close = hist_df.iloc[-2]["收盘"]
                            change_pct = ((latest["收盘"] - prev_close) / prev_close) * 100
                            info["change_percent"] = round(change_pct, 2)
                except Exception as e:
                    logger.warning(f"获取港股历史数据失败: {e}")

            return info

        except Exception as e:
            return {
                "symbol": symbol,
                "name": f"港股{symbol}",
                "current_price": "N/A",
                "change_percent": "N/A",
                "pe_ratio": "N/A",
                "pb_ratio": "N/A",
                "market_cap": "N/A",
                "market": "香港股市",
                "exchange": "香港交易所",
            }

    def _get_us_stock_info(self, symbol: str) -> dict[str, Any]:
        try:
            time.sleep(1) # Avoid rate limit
            ticker = yf.Ticker(symbol)
            
            try:
                hist = ticker.history(period="2d")
                if not hist.empty:
                    current_price = hist["Close"].iloc[-1]
                    if len(hist) > 1:
                        prev_close = hist["Close"].iloc[-2]
                        change_percent = ((current_price - prev_close) / prev_close) * 100
                    else:
                        change_percent = "N/A"
                else:
                    current_price = "N/A"
                    change_percent = "N/A"
            except Exception:
                current_price = "N/A"
                change_percent = "N/A"

            try:
                info = ticker.info
                pe_ratio = info.get("trailingPE", info.get("forwardPE", "N/A"))
                if pe_ratio == "N/A" or pe_ratio is None or (isinstance(pe_ratio, float) and np.isnan(pe_ratio)):
                    pe_ratio = "N/A"
                
                pb_ratio = info.get("priceToBook", "N/A")
                if pb_ratio == "N/A" or pb_ratio is None or (isinstance(pb_ratio, float) and np.isnan(pb_ratio)):
                    pb_ratio = "N/A"

                if current_price == "N/A":
                    current_price = info.get("currentPrice", info.get("regularMarketPrice", "N/A"))

                if change_percent == "N/A":
                    change_percent = info.get("regularMarketChangePercent", "N/A")
                    if change_percent != "N/A" and change_percent is not None:
                        change_percent = change_percent * 100

                return {
                    "symbol": symbol,
                    "name": info.get("longName", info.get("shortName", "N/A")),
                    "current_price": current_price,
                    "change_percent": change_percent,
                    "market_cap": info.get("marketCap", "N/A"),
                    "pe_ratio": pe_ratio,
                    "pb_ratio": pb_ratio,
                    "dividend_yield": info.get("dividendYield", "N/A"),
                    "beta": info.get("beta", "N/A"),
                    "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                    "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
                    "sector": info.get("sector", "N/A"),
                    "industry": info.get("industry", "N/A"),
                    "market": "美股",
                    "exchange": info.get("exchange", "N/A"),
                }
            except Exception:
                return {
                    "symbol": symbol,
                    "name": f"美股{symbol}",
                    "current_price": current_price,
                    "change_percent": change_percent,
                    "market_cap": "N/A",
                    "pe_ratio": "N/A",
                    "pb_ratio": "N/A",
                    "dividend_yield": "N/A",
                    "beta": "N/A",
                    "52_week_high": "N/A",
                    "52_week_low": "N/A",
                    "sector": "N/A",
                    "industry": "N/A",
                    "market": "美股",
                    "exchange": "N/A",
                }

        except Exception as e:
            return {"error": f"获取美股信息失败: {str(e)}"}

    def _get_chinese_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame | dict[str, Any]:
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            if period == "1y":
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            elif period == "6mo":
                start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            elif period == "3mo":
                start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
            else:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            df = data_source_manager.get_stock_hist_data(
                symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq"
            )

            if df is not None and not df.empty:
                df = df.rename(
                    columns={
                        "date": "Date",
                        "open": "Open",
                        "close": "Close",
                        "high": "High",
                        "low": "Low",
                        "volume": "Volume",
                    }
                )

                if "Date" not in df.columns and df.index.name == "date":
                    df.index.name = "Date"
                elif "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"])
                    df.set_index("Date", inplace=True)

                return df
            else:
                return {"error": "所有数据源均无法获取历史数据"}
        except Exception as e:
            return {"error": f"获取中国股票数据失败: {str(e)}"}

    def _get_hk_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame | dict[str, Any]:
        try:
            hk_code = normalize_hk_code(symbol)
            end_date = datetime.now().strftime("%Y%m%d")
            if period == "1y":
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
            elif period == "6mo":
                start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
            elif period == "3mo":
                start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
            elif period == "1mo":
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
            else:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            df = ak.stock_hk_hist(
                symbol=hk_code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq"
            )

            if df is not None and not df.empty:
                df = df.rename(
                    columns={
                        "日期": "Date",
                        "开盘": "Open",
                        "收盘": "Close",
                        "最高": "High",
                        "最低": "Low",
                        "成交量": "Volume",
                    }
                )
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
                return df
            else:
                return {"error": "无法获取港股历史数据"}
        except Exception as e:
            return {"error": f"获取港股数据失败: {str(e)}"}

    def _get_us_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame | dict[str, Any]:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                return df
            else:
                return {"error": "无法获取历史数据"}
        except Exception as e:
            return {"error": f"获取美股数据失败: {str(e)}"}

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame | dict[str, Any]:
        try:
            if isinstance(df, dict) and "error" in df:
                return df

            if "Volume" in df.columns:
                df = df[(df["Volume"] > 0) & (df["Volume"].notna())]

            df["MA5"] = ta.trend.sma_indicator(df["Close"], window=5)
            df["MA10"] = ta.trend.sma_indicator(df["Close"], window=10)
            df["MA20"] = ta.trend.sma_indicator(df["Close"], window=20)
            df["MA60"] = ta.trend.sma_indicator(df["Close"], window=60)

            df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

            macd = ta.trend.MACD(df["Close"])
            df["MACD"] = macd.macd()
            df["MACD_signal"] = macd.macd_signal()
            df["MACD_histogram"] = macd.macd_diff()

            bollinger = ta.volatility.BollingerBands(df["Close"])
            df["BB_upper"] = bollinger.bollinger_hband()
            df["BB_middle"] = bollinger.bollinger_mavg()
            df["BB_lower"] = bollinger.bollinger_lband()

            df["K"] = ta.momentum.stoch(df["High"], df["Low"], df["Close"])
            df["D"] = ta.momentum.stoch_signal(df["High"], df["Low"], df["Close"])

            df["Volume_MA5"] = ta.trend.sma_indicator(df["Volume"], window=5)
            df["Volume_ratio"] = df["Volume"] / df["Volume_MA5"]

            return df
        except Exception as e:
            return {"error": f"计算技术指标失败: {str(e)}"}

    def _get_latest_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        try:
            if isinstance(df, dict) and "error" in df:
                return df

            latest = df.iloc[-1]
            return {
                "price": latest["Close"],
                "ma5": latest["MA5"],
                "ma10": latest["MA10"],
                "ma20": latest["MA20"],
                "ma60": latest["MA60"],
                "rsi": latest["RSI"],
                "macd": latest["MACD"],
                "macd_signal": latest["MACD_signal"],
                "bb_upper": latest["BB_upper"],
                "bb_lower": latest["BB_lower"],
                "k_value": latest["K"],
                "d_value": latest["D"],
                "volume_ratio": latest["Volume_ratio"],
            }
        except Exception as e:
            return {"error": f"获取当前指标失败: {str(e)}"}

    def _get_chinese_financial_data(self, symbol: str) -> dict[str, Any]:
        financial_data = {
            "symbol": symbol,
            "balance_sheet": None,
            "income_statement": None,
            "cash_flow": None,
            "financial_ratios": {},
            "quarter_data": None,
        }

        try:
            try:
                balance_sheet = ak.stock_financial_abstract_ths(symbol=symbol, indicator="资产负债表")
                if balance_sheet is not None and not balance_sheet.empty:
                    financial_data["balance_sheet"] = balance_sheet.head(8).to_dict("records")
            except Exception:
                pass

            try:
                income_statement = ak.stock_financial_abstract_ths(symbol=symbol, indicator="利润表")
                if income_statement is not None and not income_statement.empty:
                    financial_data["income_statement"] = income_statement.head(8).to_dict("records")
            except Exception:
                pass

            try:
                cash_flow = ak.stock_financial_abstract_ths(symbol=symbol, indicator="现金流量表")
                if cash_flow is not None and not cash_flow.empty:
                    financial_data["cash_flow"] = cash_flow.head(8).to_dict("records")
            except Exception:
                pass

            try:
                financial_abstract = ak.stock_financial_abstract(symbol=symbol)
                if financial_abstract is not None and not financial_abstract.empty:
                    key_indicators = [
                        "净资产收益率(ROE)", "总资产报酬率(ROA)", "销售毛利率", "销售净利率",
                        "资产负债率", "流动比率", "速动比率", "存货周转率",
                        "应收账款周转率", "总资产周转率", "营业收入同比增长", "净利润同比增长",
                    ]
                    indicator_rows = financial_abstract[financial_abstract["指标"].isin(key_indicators)]
                    if not indicator_rows.empty:
                        date_columns = [col for col in financial_abstract.columns if col not in ["选项", "指标"]]
                        if date_columns:
                            latest_date = date_columns[0]
                            financial_ratios = {"报告期": latest_date}
                            for _, row in indicator_rows.iterrows():
                                indicator_name = row["指标"]
                                value = row.get(latest_date, "N/A")
                                if value is not None and not (isinstance(value, float) and pd.isna(value)):
                                    try:
                                        financial_ratios[indicator_name] = str(value)
                                    except Exception:
                                        financial_ratios[indicator_name] = "N/A"
                                else:
                                    financial_ratios[indicator_name] = "N/A"
                            financial_data["financial_ratios"] = financial_ratios
            except Exception:
                pass

            return financial_data
        except Exception as e:
            logger.error(f"获取中国股票财务数据失败: {e}", exc_info=True)
            return financial_data

    def _get_hk_financial_data(self, symbol: str) -> dict[str, Any]:
        hk_code = normalize_hk_code(symbol)
        financial_data = {
            "symbol": hk_code,
            "balance_sheet": None,
            "income_statement": None,
            "cash_flow": None,
            "financial_ratios": {},
            "quarter_data": None,
            "data_source": "eastmoney",
            "note": "港股财务数据来自东方财富",
        }

        try:
            try:
                financial_indicator = ak.stock_hk_financial_indicator_em(symbol=hk_code)
                if financial_indicator is not None and not financial_indicator.empty:
                    indicator_dict = financial_indicator.iloc[0].to_dict()
                    financial_data["financial_ratios"] = {
                        "基本每股收益": self._safe_convert(indicator_dict.get("基本每股收益(元)", "N/A")),
                        "每股净资产": self._safe_convert(indicator_dict.get("每股净资产(元)", "N/A")),
                        "每股股息TTM": self._safe_convert(indicator_dict.get("每股股息TTM(港元)", "N/A")),
                        "派息比率": self._safe_convert(indicator_dict.get("派息比率(%)", "N/A")),
                        "每股经营现金流": self._safe_convert(indicator_dict.get("每股经营现金流(元)", "N/A")),
                        "股息率TTM": self._safe_convert(indicator_dict.get("股息率TTM(%)", "N/A")),
                        "总市值": self._safe_convert(indicator_dict.get("总市值(港元)", "N/A")),
                        "港股市值": self._safe_convert(indicator_dict.get("港股市值(港元)", "N/A")),
                        "营业总收入": self._safe_convert(indicator_dict.get("营业总收入", "N/A")),
                        "营业收入环比增长": self._safe_convert(indicator_dict.get("营业总收入滚动环比增长(%)", "N/A")),
                        "销售净利率": self._safe_convert(indicator_dict.get("销售净利率(%)", "N/A")),
                        "净利润": self._safe_convert(indicator_dict.get("净利润", "N/A")),
                        "净利润环比增长": self._safe_convert(indicator_dict.get("净利润滚动环比增长(%)", "N/A")),
                        "ROE股东权益回报率": self._safe_convert(indicator_dict.get("股东权益回报率(%)", "N/A")),
                        "市盈率": self._safe_convert(indicator_dict.get("市盈率", "N/A")),
                        "市净率": self._safe_convert(indicator_dict.get("市净率", "N/A")),
                        "ROA总资产回报率": self._safe_convert(indicator_dict.get("总资产回报率(%)", "N/A")),
                        "法定股本": self._safe_convert(indicator_dict.get("法定股本(股)", "N/A")),
                        "已发行股本": self._safe_convert(indicator_dict.get("已发行股本(股)", "N/A")),
                        "每手股": self._safe_convert(indicator_dict.get("每手股", "N/A")),
                    }
                else:
                    financial_data["note"] = "未获取到财务数据"
            except Exception as e:
                financial_data["note"] = f"获取财务数据失败: {str(e)}"

            return financial_data
        except Exception as e:
            financial_data["note"] = f"获取失败: {str(e)}"
            return financial_data

    def _get_us_financial_data(self, symbol: str) -> dict[str, Any]:
        financial_data = {
            "symbol": symbol,
            "balance_sheet": None,
            "income_statement": None,
            "cash_flow": None,
            "financial_ratios": {},
            "quarter_data": None,
        }

        try:
            stock = yf.Ticker(symbol)
            info = stock.info

            try:
                balance_sheet = stock.balance_sheet
                if balance_sheet is not None and not balance_sheet.empty:
                    financial_data["balance_sheet"] = balance_sheet.iloc[:, :4].to_dict("index")
            except Exception:
                pass

            try:
                income_stmt = stock.income_stmt
                if income_stmt is not None and not income_stmt.empty:
                    financial_data["income_statement"] = income_stmt.iloc[:, :4].to_dict("index")
            except Exception:
                pass

            try:
                cash_flow = stock.cashflow
                if cash_flow is not None and not cash_flow.empty:
                    financial_data["cash_flow"] = cash_flow.iloc[:, :4].to_dict("index")
            except Exception:
                pass

            financial_data["financial_ratios"] = {
                "ROE": info.get("returnOnEquity", "N/A"),
                "ROA": info.get("returnOnAssets", "N/A"),
                "毛利率": info.get("grossMargins", "N/A"),
                "营业利润率": info.get("operatingMargins", "N/A"),
                "净利率": info.get("profitMargins", "N/A"),
                "资产负债率": info.get("debtToEquity", "N/A"),
                "流动比率": info.get("currentRatio", "N/A"),
                "速动比率": info.get("quickRatio", "N/A"),
                "EPS": info.get("trailingEps", "N/A"),
                "每股账面价值": info.get("bookValue", "N/A"),
                "股息率": info.get("dividendYield", "N/A"),
                "派息率": info.get("payoutRatio", "N/A"),
                "收入增长": info.get("revenueGrowth", "N/A"),
                "盈利增长": info.get("earningsGrowth", "N/A"),
            }

            return financial_data
        except Exception:
            return financial_data

    def _safe_convert(self, value: Any) -> Any:
        if value is None or value == "" or (isinstance(value, float) and np.isnan(value)):
            return "N/A"
        try:
            if isinstance(value, str):
                value = value.replace("%", "").replace(",", "")
                return float(value)
            return value
        except Exception:
            return value
