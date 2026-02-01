"""
Web 层依赖注入容器。

该模块充当 Composition Root，负责：
1. 实例化基础设施层对象（Repository, Providers, AI Agents）。
2. 管理对象的生命周期（单例/缓存）。
3. 组装应用层 Use Case。

Web 层其他模块应通过此容器获取依赖，而不是直接实例化基础设施类。
"""

import streamlit as st
from typing import Any

from aiagents_stock.application.analysis.use_cases import AnalyzeSingleStockUseCase
from aiagents_stock.core.config_manager import config_manager
from aiagents_stock.db.database import db
from aiagents_stock.domain.analysis.ports import (
    MarketDataProvider,
    OptionalDataProvider,
    AIAnalyzer,
    AnalysisRecordRepository,
    StockAnalysisRepository,
)
from aiagents_stock.domain.analysis.services import AnalysisOrchestrator
from aiagents_stock.infrastructure.ai.deepseek_agents import DeepSeekAnalyzer
from aiagents_stock.infrastructure.ai.llm_client import DeepSeekLLMAdapter, LLMClient
from aiagents_stock.infrastructure.ai.orchestrator import DeepSeekAnalysisOrchestrator
from aiagents_stock.infrastructure.ai_analyzer import DeepSeekAIAnalyzer
from aiagents_stock.infrastructure.market_data_provider import AkshareMarketDataProvider
from aiagents_stock.infrastructure.optional_data_provider import DefaultOptionalDataProvider
from aiagents_stock.infrastructure.persistence.sqlite.analysis_repository import (
    SqliteAnalysisRecordRepository,
    SqliteStockAnalysisRepository,
)
from aiagents_stock.web.config import (
    CACHE_TTL_OPTIONAL_DATA_SECONDS,
    CACHE_TTL_STOCK_DATA_SECONDS,
)


class DIContainer:
    """依赖注入容器"""

    @staticmethod
    def check_api_key() -> bool:
        """检查 DeepSeek API Key 是否配置。"""
        cfg = config_manager.read_env()
        return bool(cfg.get("DEEPSEEK_API_KEY", "").strip())

    @staticmethod
    def get_market_data_provider() -> MarketDataProvider:
        """获取市场数据提供者。"""
        return AkshareMarketDataProvider()

    @staticmethod
    def get_optional_data_provider() -> OptionalDataProvider:
        """获取可选数据提供者。"""
        return DefaultOptionalDataProvider()

    @staticmethod
    def get_analysis_repository() -> AnalysisRecordRepository:
        """获取分析记录仓储（旧版）。"""
        return SqliteAnalysisRecordRepository(database=db)

    @staticmethod
    def get_stock_analysis_repository() -> StockAnalysisRepository:
        """获取股票分析仓储（DDD 新版）。"""
        return SqliteStockAnalysisRepository(database=db)

    @staticmethod
    @st.cache_resource
    def get_cached_ai_agents(model: str) -> DeepSeekAnalyzer:
        """获取缓存的 AI Agents 实例（资源级缓存）。"""
        return DeepSeekAnalyzer(model=model)

    @staticmethod
    def get_ai_analyzer(model: str, use_cache: bool = True) -> AIAnalyzer:
        """获取 AI 分析器（旧版）。"""
        return DeepSeekAIAnalyzer()

    @staticmethod
    def get_llm_client(model: str) -> LLMClient:
        """获取 LLM 客户端。"""
        # 配置文件已由 ConfigManager 统一管理，DeepSeekClient 内部会自动读取环境变量
        return DeepSeekLLMAdapter(model=model)

    @staticmethod
    def get_analysis_orchestrator(model: str) -> AnalysisOrchestrator:
        """获取分析编排器。"""
        llm_client = DIContainer.get_llm_client(model)
        return DeepSeekAnalysisOrchestrator(llm_client=llm_client)

    @staticmethod
    def create_analyze_single_stock_use_case(model: str, use_cache: bool = True) -> AnalyzeSingleStockUseCase:
        """创建单股分析用例。"""
        return AnalyzeSingleStockUseCase(
            data_provider=DIContainer.get_market_data_provider(),
            optional_data_provider=DIContainer.get_optional_data_provider(),
            orchestrator=DIContainer.get_analysis_orchestrator(model),
            repository=DIContainer.get_stock_analysis_repository(),
            # 兼容旧代码，暂时保留
            analyzer=DIContainer.get_ai_analyzer(model, use_cache),
            old_repository=DIContainer.get_analysis_repository(),
        )

