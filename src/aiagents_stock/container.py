"""
依赖注入容器 (DI Container).

负责管理应用中的所有依赖关系，包括：
1. 基础设施服务（数据库、API 客户端等）
2. 领域服务（Domain Services）
3. 应用层用例（Application Use Cases）

该模块作为应用的 Composition Root，确保所有对象在使用前都已正确组装。
"""

from __future__ import annotations

import logging
from typing import Optional

from aiagents_stock.application.analysis.use_cases import (
    AnalyzeSingleStockUseCase,
    BatchAnalyzeStocksUseCase,
    GetBatchAnalysisHistoryUseCase,
    SaveBatchAnalysisResultUseCase,
)
from aiagents_stock.application.main_force.use_cases import AnalyzeMainForceUseCase, GetMainForceHistoryUseCase
from aiagents_stock.core.config_manager import config_manager
from aiagents_stock.db.database import StockAnalysisDatabase
from aiagents_stock.infrastructure.adapters.market_data_provider import AkshareMarketDataProvider
from aiagents_stock.infrastructure.adapters.optional_data_provider import DefaultOptionalDataProvider
from aiagents_stock.infrastructure.ai.deepseek_client import DeepSeekClient
from aiagents_stock.infrastructure.ai.orchestrator import DeepSeekAnalysisOrchestrator
from aiagents_stock.infrastructure.analysis.persistence.sqlite_batch_repository import (
    SqliteStockBatchAnalysisRepository,
)
from aiagents_stock.infrastructure.main_force.ai_analyzer import DeepSeekMainForceAIAnalyzer
from aiagents_stock.infrastructure.main_force.persistence.sqlite_repository import SqliteMainForceAnalysisRepository
from aiagents_stock.infrastructure.main_force.provider.pywencai_provider import PyWencaiMainForceProvider
from aiagents_stock.infrastructure.persistence.sqlite.analysis_repository import SqliteStockAnalysisRepository

logger = logging.getLogger(__name__)

class DIContainer:
    """依赖注入容器"""

    # --- Infrastructure Singletons ---
    _market_data_provider: Optional[AkshareMarketDataProvider] = None
    _optional_data_provider: Optional[DefaultOptionalDataProvider] = None
    _analysis_db: Optional[StockAnalysisDatabase] = None
    _stock_analysis_repo: Optional[SqliteStockAnalysisRepository] = None
    _stock_batch_repo: Optional[SqliteStockBatchAnalysisRepository] = None
    _llm_client: Optional[DeepSeekClient] = None
    
    # --- Main Force Singletons ---
    _main_force_repo: Optional[SqliteMainForceAnalysisRepository] = None
    _main_force_provider: Optional[PyWencaiMainForceProvider] = None

    @staticmethod
    def get_main_force_provider() -> PyWencaiMainForceProvider:
        """获取主力资金数据提供者"""
        if DIContainer._main_force_provider is None:
            DIContainer._main_force_provider = PyWencaiMainForceProvider()
        return DIContainer._main_force_provider

    @staticmethod
    def check_api_key() -> bool:
        """检查 DeepSeek API Key 是否配置"""
        config = config_manager.read_env()
        api_key = config.get("DEEPSEEK_API_KEY")
        return bool(api_key and api_key.strip())

    @staticmethod
    def get_market_data_provider() -> AkshareMarketDataProvider:
        """获取市场数据提供者"""
        if DIContainer._market_data_provider is None:
            DIContainer._market_data_provider = AkshareMarketDataProvider()
        return DIContainer._market_data_provider

    @staticmethod
    def get_optional_data_provider() -> DefaultOptionalDataProvider:
        """获取可选数据提供者"""
        if DIContainer._optional_data_provider is None:
            DIContainer._optional_data_provider = DefaultOptionalDataProvider()
        return DIContainer._optional_data_provider

    @staticmethod
    def get_analysis_database() -> StockAnalysisDatabase:
        """获取分析数据库实例"""
        if DIContainer._analysis_db is None:
            DIContainer._analysis_db = StockAnalysisDatabase()
        return DIContainer._analysis_db

    @staticmethod
    def get_stock_analysis_repository() -> SqliteStockAnalysisRepository:
        """获取股票分析仓储"""
        if DIContainer._stock_analysis_repo is None:
            DIContainer._stock_analysis_repo = SqliteStockAnalysisRepository(
                database=DIContainer.get_analysis_database()
            )
        return DIContainer._stock_analysis_repo

    @staticmethod
    def get_stock_batch_repository() -> SqliteStockBatchAnalysisRepository:
        """获取股票批量分析仓储"""
        if DIContainer._stock_batch_repo is None:
            DIContainer._stock_batch_repo = SqliteStockBatchAnalysisRepository()
        return DIContainer._stock_batch_repo

    @staticmethod
    def get_llm_client(model: str = "deepseek-chat") -> DeepSeekClient:
        """获取 LLM 客户端"""
        # Note: DeepSeekClient manages its own config, but we might want to cache it if stateless
        # For now, we return a new instance or managed one. 
        # Since DeepSeekClient is lightweight wrapper around OpenAI client, it's fine.
        # But to be consistent with singleton pattern:
        if DIContainer._llm_client is None:
            DIContainer._llm_client = DeepSeekClient(model=model)
        # Update model if needed
        DIContainer._llm_client.model = model
        return DIContainer._llm_client

    @staticmethod
    def create_analysis_orchestrator(model: str = "deepseek-chat") -> DeepSeekAnalysisOrchestrator:
        """创建分析编排服务"""
        return DeepSeekAnalysisOrchestrator(
            llm_client=DIContainer.get_llm_client(model)
        )

    # --- Use Case Factories ---

    @staticmethod
    def create_analyze_single_stock_use_case(model: str = "deepseek-chat") -> AnalyzeSingleStockUseCase:
        """创建单股分析用例"""
        return AnalyzeSingleStockUseCase(
            data_provider=DIContainer.get_market_data_provider(),
            optional_data_provider=DIContainer.get_optional_data_provider(),
            orchestrator=DIContainer.create_analysis_orchestrator(model),
            repository=DIContainer.get_stock_analysis_repository()
        )

    @staticmethod
    def create_batch_analyze_stocks_use_case(model: str = "deepseek-chat") -> BatchAnalyzeStocksUseCase:
        """创建批量分析用例"""
        return BatchAnalyzeStocksUseCase(
            single_stock_use_case=DIContainer.create_analyze_single_stock_use_case(model)
        )

    @staticmethod
    def create_save_batch_analysis_result_use_case() -> SaveBatchAnalysisResultUseCase:
        """创建保存批量分析结果用例"""
        return SaveBatchAnalysisResultUseCase(
            repository=DIContainer.get_stock_batch_repository()
        )

    @staticmethod
    def create_get_batch_analysis_history_use_case() -> GetBatchAnalysisHistoryUseCase:
        """创建获取批量分析历史用例"""
        return GetBatchAnalysisHistoryUseCase(
            repository=DIContainer.get_stock_batch_repository()
        )

    # --- Main Force Factories ---

    @staticmethod
    def get_main_force_ai_analyzer(model: str = "deepseek-chat") -> DeepSeekMainForceAIAnalyzer:
        """获取主力选股 AI 分析师"""
        return DeepSeekMainForceAIAnalyzer(
            client=DIContainer.get_llm_client(model)
        )

    @staticmethod
    def get_main_force_repository() -> SqliteMainForceAnalysisRepository:
        """获取主力选股分析仓储"""
        if DIContainer._main_force_repo is None:
            DIContainer._main_force_repo = SqliteMainForceAnalysisRepository()
        return DIContainer._main_force_repo

    @staticmethod
    def create_analyze_main_force_use_case(model: str = "deepseek-chat") -> AnalyzeMainForceUseCase:
        """创建主力选股分析用例"""
        return AnalyzeMainForceUseCase(
            provider=DIContainer.get_main_force_provider(),
            analyzer=DIContainer.get_main_force_ai_analyzer(model),
            repository=DIContainer.get_main_force_repository()
        )

    @staticmethod
    def create_get_main_force_history_use_case() -> GetMainForceHistoryUseCase:
        """创建主力选股历史查询用例"""
        return GetMainForceHistoryUseCase(
            repository=DIContainer.get_main_force_repository()
        )
