"""
新架构回归测试：单股分析（mock AI）+ 落库读取。

该测试用于验证 domain/application/infrastructure 的最小骨架能够独立运行，
且不依赖 Streamlit 运行时。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import pandas as pd

from aiagents_stock.application.analysis.use_cases import AnalyzeSingleStockUseCase
from aiagents_stock.db.database import StockAnalysisDatabase
from aiagents_stock.domain.analysis.dto import (
    FundFlowData,
    NewsData,
    StockDataBundle,
    StockRequest,
)
from aiagents_stock.domain.analysis.model import AgentRole, AnalysisContent, StockAnalysis
from aiagents_stock.domain.analysis.ports import (
    MarketDataProvider,
    OptionalDataProvider,
)
from aiagents_stock.domain.analysis.services import AnalysisOrchestrator
from aiagents_stock.infrastructure.persistence.sqlite.analysis_repository import SqliteStockAnalysisRepository


@dataclass(frozen=True)
class FakeMarketDataProvider(MarketDataProvider):
    """测试用数据源：返回固定的行情与财务数据。"""

    bundle: StockDataBundle
    financial_data: Any

    def get_stock_data_bundle(self, *, symbol: str, period: str) -> StockDataBundle:
        return self.bundle

    def get_financial_data(self, *, symbol: str) -> Any:
        return self.financial_data


@dataclass(frozen=True)
class FakeOptionalDataProvider(OptionalDataProvider):
    """用于测试的 Mock 扩展数据提供者。"""

    def get_quarterly_data(self, *, symbol: str) -> Any | None:
        return None

    def get_fund_flow_data(self, *, symbol: str) -> FundFlowData | None:
        if symbol == "000001":
            return FundFlowData(data={"flow": "up"})
        return None

    def get_sentiment_data(self, *, symbol: str, stock_data: Any) -> Any | None:
        return None

    def get_news_data(self, *, symbol: str) -> NewsData | None:
        if symbol == "000001":
            return NewsData(data=[{"title": "good news"}])
        return None

    def get_risk_data(self, *, symbol: str) -> Any | None:
        return None


@dataclass
class FakeAnalysisOrchestrator(AnalysisOrchestrator):
    """测试用编排器：模拟 AI 分析过程"""
    
    def perform_analysis(self, analysis: StockAnalysis, data_bundle: Any, enabled_agents: List[AgentRole]) -> StockAnalysis:
        # 模拟分析过程：为每个启用的 Agent 添加评审
        for role in enabled_agents:
            content = AnalysisContent(
                summary=f"{role.value} analysis",
                details={"raw": "detail"},
                focus_areas=["area1"],
                raw_output=f"Mock output for {role.value}"
            )
            analysis.add_review(role, content, agent_name=f"{role.value}_Agent")
            
        analysis.team_discussion = "team ok"
        analysis.final_decision = {"rating": "中性", "confidence_level": 5}
        return analysis


def test_single_stock_analysis_use_case_persists_and_reads_back(tmp_path):
    # Setup DB and Repository
    db_path = tmp_path / "test_stock_analysis.db"
    database = StockAnalysisDatabase(db_path=str(db_path))
    # Use real repository to test persistence logic too
    repository = SqliteStockAnalysisRepository(database=database)

    # Setup Data
    stock_info = {"symbol": "000001", "name": "平安银行", "current_price": 10.0}
    stock_data = pd.DataFrame(
        [
            {"date": "2024-01-01", "open": 9.5, "high": 10.1, "low": 9.4, "close": 10.0, "volume": 1000},
            {"date": "2024-01-02", "open": 10.0, "high": 10.2, "low": 9.9, "close": 10.1, "volume": 1100},
        ]
    )
    indicators = {"rsi": 50, "ma5": 9.9}
    bundle = StockDataBundle(stock_info=stock_info, stock_data=stock_data, indicators=indicators)

    # Setup Providers
    data_provider = FakeMarketDataProvider(bundle=bundle, financial_data={"pe": 10})
    optional_provider = FakeOptionalDataProvider()
    orchestrator = FakeAnalysisOrchestrator()

    # Instantiate Use Case
    use_case = AnalyzeSingleStockUseCase(
        data_provider=data_provider,
        optional_data_provider=optional_provider,
        orchestrator=orchestrator,
        repository=repository,
    )

    # Execute
    response = use_case.execute(
        request=StockRequest(
            symbol="000001",
            period="1y",
            model="fake-model",
            enabled_analysts={"technical": True},
        )
    )

    # Verify Response
    assert response.record_id > 0
    assert response.bundle.stock_info["symbol"] == "000001"
    # Check if result is mapped correctly from orchestrator
    assert response.analysis_result.final_decision["rating"] == "中性"
    assert "technical" in response.analysis_result.agents_results
    assert response.analysis_result.agents_results["technical"]["analysis"] == "Mock output for technical"

    # Verify Persistence (using new repo)
    saved_agg = repository.find_by_id(str(response.record_id))
    assert saved_agg is not None
    assert saved_agg.stock_info.symbol == "000001"
    assert saved_agg.period == "1y"
    assert saved_agg.final_decision["rating"] == "中性"


def test_single_stock_analysis_use_case_handles_optional_data(tmp_path):
    stock_info = {"symbol": "000001", "name": "平安银行"}
    stock_data = pd.DataFrame([{"close": 10.0}])
    bundle = StockDataBundle(stock_info=stock_info, stock_data=stock_data, indicators={})

    data_provider = FakeMarketDataProvider(bundle=bundle, financial_data={})
    optional_provider = FakeOptionalDataProvider()
    
    # Spy Orchestrator
    @dataclass
    class SpyOrchestrator(AnalysisOrchestrator):
        received_bundle: StockDataBundle = None
        
        def perform_analysis(self, analysis: StockAnalysis, data_bundle: Any, enabled_agents: List[AgentRole]) -> StockAnalysis:
            self.received_bundle = data_bundle
            return analysis

    orchestrator = SpyOrchestrator()
    
    db_path = tmp_path / "test_optional_data.db"
    database = StockAnalysisDatabase(db_path=str(db_path))
    repository = SqliteStockAnalysisRepository(database=database)

    use_case = AnalyzeSingleStockUseCase(
        data_provider=data_provider,
        optional_data_provider=optional_provider,
        orchestrator=orchestrator,
        repository=repository,
    )

    use_case.execute(
        request=StockRequest(
            symbol="000001",
            period="1y",
            model="test",
            enabled_analysts={"fund_flow": True, "news": True, "technical": True},
        )
    )

    assert orchestrator.received_bundle is not None
    assert orchestrator.received_bundle.fund_flow_data is not None
    assert orchestrator.received_bundle.fund_flow_data.data == {"flow": "up"}
    assert orchestrator.received_bundle.news_data is not None
    assert orchestrator.received_bundle.news_data.data == [{"title": "good news"}]
    # 验证未启用的数据不应该存在于 optional_data 中
    assert orchestrator.received_bundle.quarterly_data is None
