from __future__ import annotations

from dataclasses import dataclass

APP_PAGE_TITLE = "复合多AI智能体股票团队分析系统"
APP_PAGE_ICON = "📈"
APP_LAYOUT = "wide"
APP_INITIAL_SIDEBAR_STATE = "expanded"

PERIOD_OPTIONS: tuple[str, ...] = ("1y", "6mo", "3mo", "1mo")
DEFAULT_PERIOD = "1y"

CACHE_TTL_STOCK_DATA_SECONDS = 300
CACHE_TTL_OPTIONAL_DATA_SECONDS = 1800

MAX_BATCH_STOCKS_RECOMMENDED = 20
BATCH_MAX_WORKERS = 3
BATCH_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class EnabledAnalysts:
    """用户启用的分析师配置。"""

    technical: bool = True
    fundamental: bool = True
    fund_flow: bool = True
    risk: bool = True
    sentiment: bool = False
    news: bool = False

    def as_dict(self) -> dict[str, bool]:
        """转换为下游 AI 分析组件需要的字典格式。"""

        return {
            "technical": self.technical,
            "fundamental": self.fundamental,
            "fund_flow": self.fund_flow,
            "risk": self.risk,
            "sentiment": self.sentiment,
            "news": self.news,
        }
