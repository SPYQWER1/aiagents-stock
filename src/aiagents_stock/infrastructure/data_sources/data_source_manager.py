"""
数据源管理器
实现akshare和tushare的自动切换机制
"""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import numpy as np
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

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


class DataSourceManager:
    """数据源管理器 - 统一管理A股、港股、美股数据获取"""

    def __init__(self):
        self.tushare_token = os.getenv("TUSHARE_TOKEN", "")
        self.tushare_available = False
        self.tushare_api = None

        # 初始化tushare
        if self.tushare_token:
            try:
                import tushare as ts

                ts.set_token(self.tushare_token)
                self.tushare_api = ts.pro_api()
                self.tushare_available = True
                logger.info("✅ Tushare数据源初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ Tushare数据源初始化失败: {e}")
                self.tushare_available = False
        else:
            logger.info("ℹ️ 未配置Tushare Token，将仅使用Akshare数据源")

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        统一获取股票信息（自动识别市场）
        """
        try:
            if is_chinese_stock(symbol):
                return self.get_chinese_stock_info(symbol)
            elif is_hk_stock(symbol):
                return self.get_hk_stock_info(symbol)
            else:
                return self.get_us_stock_info(symbol)
        except Exception as e:
            return {"error": f"获取股票信息失败: {str(e)}"}

    def get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame | Dict[str, Any]:
        """
        统一获取股票历史数据（自动识别市场）
        """
        try:
            if is_chinese_stock(symbol):
                return self.get_chinese_stock_data(symbol, period)
            elif is_hk_stock(symbol):
                return self.get_hk_stock_data(symbol, period)
            else:
                return self.get_us_stock_data(symbol, period, interval)
        except Exception as e:
            return {"error": f"获取股票数据失败: {str(e)}"}

    def get_chinese_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame | Dict[str, Any]:
        """获取A股历史数据"""
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

            df = self.get_stock_hist_data(
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

    def get_hk_stock_data(self, symbol: str, period: str = "1y") -> pd.DataFrame | Dict[str, Any]:
        """获取港股历史数据"""
        try:
            import akshare as ak
            
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
            return {"error": "无法获取港股数据"}
        except Exception as e:
            return {"error": f"获取港股数据失败: {str(e)}"}

    def get_us_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame | Dict[str, Any]:
        """获取美股历史数据"""
        try:
            # yfinance 的 period 参数直接支持 "1y", "6mo" 等
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df is not None and not df.empty:
                # yfinance 返回的 index 已经是 Date/Datetime
                # 只需要确保列名一致
                # yfinance columns: Open, High, Low, Close, Volume, Dividends, Stock Splits
                return df
            return {"error": "无法获取美股数据"}
        except Exception as e:
            return {"error": f"获取美股数据失败: {str(e)}"}

    def get_chinese_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取A股基本信息（整合多个来源）"""
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

            # 1. 基础信息
            basic_info = self.get_stock_basic_info(symbol)
            if basic_info:
                info.update(basic_info)

            # 2. 尝试获取个股详细信息（akshare）
            import akshare as ak
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
                # 如果akshare失败，尝试从tushare获取补充信息
                if self.tushare_available and info["name"] == "未知":
                    try:
                        ts_code = self._convert_to_ts_code(symbol)
                        df = self.tushare_api.daily_basic(
                            ts_code=ts_code, trade_date=datetime.now().strftime("%Y%m%d")
                        )
                        if df is not None and not df.empty:
                            row = df.iloc[0]
                            info["pe_ratio"] = row.get("pe", "N/A")
                            info["pb_ratio"] = row.get("pb", "N/A")
                            info["market_cap"] = row.get("total_mv", "N/A")
                    except Exception as te:
                        logger.warning(f"[Tushare] ❌ 获取失败: {te}")

            # 3. 尝试获取最近交易数据以补充价格信息
            try:
                hist_data = self.get_stock_hist_data(
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

            # 4. 补充市盈率/市净率 (百度接口)
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

    def get_hk_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取港股基本信息"""
        try:
            import akshare as ak
            
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

        except Exception:
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

    def get_us_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取美股基本信息"""
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



    def get_stock_hist_data(self, symbol, start_date=None, end_date=None, adjust="qfq"):
        """
        获取股票历史数据（优先akshare，失败时使用tushare）

        Args:
            symbol: 股票代码（6位数字）
            start_date: 开始日期（格式：'20240101'或'2024-01-01'）
            end_date: 结束日期
            adjust: 复权类型（'qfq'前复权, 'hfq'后复权, ''不复权）

        Returns:
            DataFrame: 包含日期、开盘、收盘、最高、最低、成交量等列
        """
        # 标准化日期格式，统一为无连字符格式
        if start_date:
            start_date = start_date.replace("-", "")
        if end_date:
            end_date = end_date.replace("-", "")
        else:
            # 如果未提供结束日期，使用当前日期
            end_date = datetime.now().strftime("%Y%m%d")

        # 优先使用akshare数据源
        try:
            import akshare as ak

            logger.info(f"[Akshare] 正在获取 {symbol} 的历史数据...")

            # 使用akshare的股票历史数据接口
            df = ak.stock_zh_a_hist(
                symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust=adjust
            )

            if df is not None and not df.empty:
                # 标准化列名，确保返回的数据格式一致
                df = df.rename(
                    columns={
                        "日期": "date",
                        "开盘": "open",
                        "收盘": "close",
                        "最高": "high",
                        "最低": "low",
                        "成交量": "volume",
                        "成交额": "amount",
                        "振幅": "amplitude",
                        "涨跌幅": "pct_change",
                        "涨跌额": "change",
                        "换手率": "turnover",
                    }
                )
                # 转换日期列为datetime类型
                df["date"] = pd.to_datetime(df["date"])
                logger.info(f"[Akshare] ✅ 成功获取 {len(df)} 条数据")
                return df
        except Exception as e:
            logger.warning(f"[Akshare] ❌ 获取失败: {e}")

        # akshare失败，尝试使用tushare作为备用数据源
        if self.tushare_available:
            try:
                logger.info(f"[Tushare] 正在获取 {symbol} 的历史数据（备用数据源）...")

                # 转换股票代码格式（添加市场后缀，如000001.SZ）
                ts_code = self._convert_to_ts_code(symbol)

                # 转换复权类型，适配tushare的参数格式
                adj_dict = {"qfq": "qfq", "hfq": "hfq", "": None}
                adj = adj_dict.get(adjust, "qfq")

                # 使用tushare的日线数据接口
                df = self.tushare_api.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj=adj)

                if df is not None and not df.empty:
                    # 标准化列名，确保与akshare返回格式一致
                    df = df.rename(columns={"trade_date": "date", "vol": "volume", "amount": "amount"})
                    # 转换日期列为datetime类型
                    df["date"] = pd.to_datetime(df["date"])
                    # 按日期排序
                    df = df.sort_values("date")

                    # 转换成交量单位（tushare单位是手，转换为股）
                    df["volume"] = df["volume"] * 100
                    # 转换成交额单位（tushare单位是千元，转换为元）
                    df["amount"] = df["amount"] * 1000

                    logger.info(f"[Tushare] ✅ 成功获取 {len(df)} 条数据")
                    return df
            except Exception as e:
                logger.warning(f"[Tushare] ❌ 获取失败: {e}")

        # 两个数据源都失败
        logger.error("❌ 所有数据源均获取失败")
        return None

    def get_stock_basic_info(self, symbol):
        """
        获取股票基本信息（优先akshare，失败时使用tushare）

        Args:
            symbol: 股票代码

        Returns:
            dict: 股票基本信息
        """
        info = {"symbol": symbol, "name": "未知", "industry": "未知", "market": "未知"}

        # 优先使用akshare
        try:
            import akshare as ak

            logger.info(f"[Akshare] 正在获取 {symbol} 的基本信息...")

            stock_info = ak.stock_individual_info_em(symbol=symbol)
            if stock_info is not None and not stock_info.empty:
                for _, row in stock_info.iterrows():
                    key = row["item"]
                    value = row["value"]

                    if key == "股票简称":
                        info["name"] = value
                    elif key == "所处行业":
                        info["industry"] = value
                    elif key == "上市时间":
                        info["list_date"] = value
                    elif key == "总市值":
                        info["market_cap"] = value
                    elif key == "流通市值":
                        info["circulating_market_cap"] = value

                logger.info("[Akshare] ✅ 成功获取基本信息")
                return info
        except Exception as e:
            logger.warning(f"[Akshare] ❌ 获取失败: {e}")

        # akshare失败，尝试tushare
        if self.tushare_available:
            try:
                logger.info(f"[Tushare] 正在获取 {symbol} 的基本信息（备用数据源）...")

                ts_code = self._convert_to_ts_code(symbol)
                df = self.tushare_api.stock_basic(ts_code=ts_code, fields="ts_code,name,area,industry,market,list_date")

                if df is not None and not df.empty:
                    info["name"] = df.iloc[0]["name"]
                    info["industry"] = df.iloc[0]["industry"]
                    info["market"] = df.iloc[0]["market"]
                    info["list_date"] = df.iloc[0]["list_date"]

                    logger.info("[Tushare] ✅ 成功获取基本信息")
                    return info
            except Exception as e:
                logger.warning(f"[Tushare] ❌ 获取失败: {e}")

        return info

    def get_realtime_quotes(self, symbol):
        """
        获取实时行情数据（优先akshare，失败时使用tushare）

        Args:
            symbol: 股票代码

        Returns:
            dict: 实时行情数据
        """
        quotes = {}

        # 优先使用akshare
        try:
            import akshare as ak

            logger.info(f"[Akshare] 正在获取 {symbol} 的实时行情...")

            df = ak.stock_zh_a_spot_em()
            stock_df = df[df["代码"] == symbol]

            if not stock_df.empty:
                row = stock_df.iloc[0]
                quotes = {
                    "symbol": symbol,
                    "name": row["名称"],
                    "price": row["最新价"],
                    "change_percent": row["涨跌幅"],
                    "change": row["涨跌额"],
                    "volume": row["成交量"],
                    "amount": row["成交额"],
                    "high": row["最高"],
                    "low": row["最低"],
                    "open": row["今开"],
                    "pre_close": row["昨收"],
                }
                logger.info("[Akshare] ✅ 成功获取实时行情")
                return quotes
        except Exception as e:
            logger.warning(f"[Akshare] ❌ 获取失败: {e}")

        # akshare失败，尝试tushare
        if self.tushare_available:
            try:
                logger.info(f"[Tushare] 正在获取 {symbol} 的实时行情（备用数据源）...")

                ts_code = self._convert_to_ts_code(symbol)
                df = self.tushare_api.daily(
                    ts_code=ts_code,
                    start_date=datetime.now().strftime("%Y%m%d"),
                    end_date=datetime.now().strftime("%Y%m%d"),
                )

                if df is not None and not df.empty:
                    row = df.iloc[0]
                    quotes = {
                        "symbol": symbol,
                        "price": row["close"],
                        "change_percent": row["pct_chg"],
                        "volume": row["vol"] * 100,
                        "amount": row["amount"] * 1000,
                        "high": row["high"],
                        "low": row["low"],
                        "open": row["open"],
                        "pre_close": row["pre_close"],
                    }
                    logger.info("[Tushare] ✅ 成功获取实时行情")
                    return quotes
            except Exception as e:
                logger.error(f"[Tushare] ❌ 获取失败: {e}", exc_info=True)

        return quotes

    def get_financial_data(self, symbol, report_type="income"):
        """
        获取财务数据（优先akshare，失败时使用tushare）

        Args:
            symbol: 股票代码
            report_type: 报表类型（'income'利润表, 'balance'资产负债表, 'cashflow'现金流量表）

        Returns:
            DataFrame: 财务数据
        """
        # 优先使用akshare
        try:
            import akshare as ak

            logger.info(f"[Akshare] 正在获取 {symbol} 的财务数据...")

            if report_type == "income":
                df = ak.stock_financial_report_sina(stock=symbol, symbol="利润表")
            elif report_type == "balance":
                df = ak.stock_financial_report_sina(stock=symbol, symbol="资产负债表")
            elif report_type == "cashflow":
                df = ak.stock_financial_report_sina(stock=symbol, symbol="现金流量表")
            else:
                df = None

            if df is not None and not df.empty:
                logger.info("[Akshare] ✅ 成功获取财务数据")
                return df
        except Exception as e:
            logger.warning(f"[Akshare] ❌ 获取失败: {e}")

        # akshare失败，尝试tushare
        if self.tushare_available:
            try:
                logger.info(f"[Tushare] 正在获取 {symbol} 的财务数据（备用数据源）...")

                ts_code = self._convert_to_ts_code(symbol)

                if report_type == "income":
                    df = self.tushare_api.income(ts_code=ts_code)
                elif report_type == "balance":
                    df = self.tushare_api.balancesheet(ts_code=ts_code)
                elif report_type == "cashflow":
                    df = self.tushare_api.cashflow(ts_code=ts_code)
                else:
                    df = None

                if df is not None and not df.empty:
                    logger.info("[Tushare] ✅ 成功获取财务数据")
                    return df
            except Exception as e:
                logger.warning(f"[Tushare] ❌ 获取失败: {e}")

        return None

    def _convert_to_ts_code(self, symbol):
        """
        将6位股票代码转换为tushare格式（带市场后缀）

        Args:
            symbol: 6位股票代码

        Returns:
            str: tushare格式代码（如：000001.SZ）
        """
        if not symbol or len(symbol) != 6:
            return symbol

        # 根据代码判断市场
        if symbol.startswith("6"):
            # 上海主板
            return f"{symbol}.SH"
        elif symbol.startswith("0") or symbol.startswith("3"):
            # 深圳主板和创业板
            return f"{symbol}.SZ"
        elif symbol.startswith("8") or symbol.startswith("4"):
            # 北交所
            return f"{symbol}.BJ"
        else:
            # 默认深圳
            return f"{symbol}.SZ"

    def _convert_from_ts_code(self, ts_code):
        """
        将tushare格式代码转换为6位代码

        Args:
            ts_code: tushare格式代码（如：000001.SZ）

        Returns:
            str: 6位股票代码
        """
        if "." in ts_code:
            return ts_code.split(".")[0]
        return ts_code


# 全局数据源管理器实例
data_source_manager = DataSourceManager()
