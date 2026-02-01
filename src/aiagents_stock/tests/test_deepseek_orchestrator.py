
import pytest
from unittest.mock import Mock, MagicMock
from aiagents_stock.infrastructure.ai.orchestrator import DeepSeekAnalysisOrchestrator
from aiagents_stock.domain.analysis.model import StockAnalysis, StockInfo, AgentRole
from aiagents_stock.domain.analysis.dto import StockDataBundle
from aiagents_stock.domain.analysis.ports import LLMClient

class MockLLMClient(LLMClient):
    def __init__(self):
        self.call_chat = Mock(return_value="Mock Analysis Result")
    
    def call_reasoner(self, messages):
        pass

def test_deepseek_orchestrator_flow():
    # Setup
    mock_llm = MockLLMClient()
    orchestrator = DeepSeekAnalysisOrchestrator(llm_client=mock_llm)
    
    stock_info = StockInfo(symbol="000001", name="Test Stock", current_price=10.0)
    analysis = StockAnalysis(stock_info=stock_info)
    
    bundle = StockDataBundle(
        stock_info={"symbol": "000001", "name": "Test Stock"},
        stock_data=None,
        indicators={"ma5": 10.0, "rsi": 50},
        financial_data={"financial_ratios": {"ROE": 0.15}},
        quarterly_data=None, # Mocking empty data for simplicity
        fund_flow_data=None,
        risk_data=None,
        sentiment_data=None,
        news_data=None
    )
    
    enabled_agents = [AgentRole.TECHNICAL, AgentRole.FUNDAMENTAL]
    
    # Execute
    result_analysis = orchestrator.perform_analysis(analysis, bundle, enabled_agents)
    
    # Verify
    assert len(result_analysis.reviews) == 2
    assert AgentRole.TECHNICAL in result_analysis.reviews
    assert AgentRole.FUNDAMENTAL in result_analysis.reviews
    
    # Verify LLM calls
    # 2 agents + 1 discussion + 1 decision = 4 calls
    assert mock_llm.call_chat.call_count >= 4 
    
    # Check if final decision was attempted
    # Since mock returns "Mock Analysis Result", the JSON parsing will fail 
    # and it should fallback to storing the text
    assert result_analysis.final_decision is not None
    assert "decision_text" in result_analysis.final_decision
    assert result_analysis.final_decision["decision_text"] == "Mock Analysis Result"

def test_deepseek_orchestrator_decision_parsing():
    # Setup with JSON returning mock
    mock_llm = MockLLMClient()
    mock_json = '{"rating": "买入", "target_price": "20.0"}'
    
    # Configure mock to return JSON only for the final decision call
    # We can inspect call args to distinguish, but for simplicity let's make it always return JSON 
    # or use side_effect
    
    def side_effect(messages):
        content = messages[-1]["content"]
        if "最终投资决策" in content:
            return mock_json
        return "Generic Analysis"
        
    mock_llm.call_chat.side_effect = side_effect
    
    orchestrator = DeepSeekAnalysisOrchestrator(llm_client=mock_llm)
    
    stock_info = StockInfo(symbol="000001", name="Test Stock", current_price=10.0)
    analysis = StockAnalysis(stock_info=stock_info)
    bundle = StockDataBundle(stock_info={}, stock_data=None, indicators={})
    
    # Execute with just one agent to reach decision faster
    orchestrator.perform_analysis(analysis, bundle, [AgentRole.TECHNICAL])
    
    # Verify
    assert analysis.final_decision["rating"] == "买入"
    assert analysis.final_decision["target_price"] == "20.0"
