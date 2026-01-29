#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

该模块负责管理项目的所有配置项，包括：
1. API密钥配置（DeepSeek、Tushare）
2. 股票数据源配置（默认周期、间隔）
3. 量化交易配置（MiniQMT）
4. 股票数据API配置（TDX）

所有配置项优先从环境变量中读取，提供默认值作为 fallback，确保系统在不同环境下都能正常运行。

使用方法：
- 在项目根目录创建 .env 文件，配置相应的环境变量
- 导入本模块的配置项直接使用
"""

import os

from dotenv import load_dotenv

# 加载环境变量（override=True 强制覆盖已存在的环境变量）
load_dotenv(override=True)

# DeepSeek API配置
# 用于AI分析和生成报告
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Tushare配置
# 用于获取股票基础数据和财务数据
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 股票数据源配置
# 默认获取1年数据，日线级别
DEFAULT_PERIOD = "1y"  # 默认获取1年数据
DEFAULT_INTERVAL = "1d"  # 默认日线数据

# MiniQMT量化交易配置
# 用于执行量化交易策略
MINIQMT_CONFIG = {
    "enabled": os.getenv("MINIQMT_ENABLED", "false").lower() == "true",  # 是否启用
    "account_id": os.getenv("MINIQMT_ACCOUNT_ID", ""),  # 账户ID
    "host": os.getenv("MINIQMT_HOST", "127.0.0.1"),  # 主机地址
    "port": int(os.getenv("MINIQMT_PORT", "58610")),  # 端口号
}

# TDX股票数据API配置
# 项目地址：github.com/oficcejo/tdx-api
# 用于获取股票历史数据和实时数据
TDX_CONFIG = {
    "enabled": os.getenv("TDX_ENABLED", "false").lower() == "true",  # 是否启用
    "base_url": os.getenv("TDX_BASE_URL", "http://192.168.1.222:8181"),  # API基础地址
}
