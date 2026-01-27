from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from aiagents_stock.web.navigation import View

def _ensure_src_on_path() -> None:
    """确保 src 目录在 sys.path 中，便于以脚本方式运行时导入包。"""


    src_dir = Path(__file__).resolve().parents[2]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _render_current_view(*, view: "View", api_key_ok: bool, period: str, selected_model: str) -> None:
    """根据当前视图路由渲染对应页面。"""

    from aiagents_stock.web.navigation import View

    if view == View.HISTORY:
        from aiagents_stock.web.pages.history import render_history

        render_history()
        return

    if view == View.MONITOR:
        from aiagents_stock.features.monitor.monitor_manager import display_monitor_manager

        display_monitor_manager()
        return

    if view == View.MAIN_FORCE:
        from aiagents_stock.features.main_force.main_force_ui import display_main_force_selector

        display_main_force_selector()
        return

    if view == View.LOW_PRICE_BULL:
        from aiagents_stock.features.low_price_bull.low_price_bull_ui import display_low_price_bull

        display_low_price_bull()
        return

    if view == View.SMALL_CAP:
        from aiagents_stock.features.small_cap.small_cap_ui import display_small_cap

        display_small_cap()
        return

    if view == View.PROFIT_GROWTH:
        from aiagents_stock.features.profit_growth.profit_growth_ui import display_profit_growth

        display_profit_growth()
        return

    if view == View.SECTOR_STRATEGY:
        from aiagents_stock.features.sector_strategy.sector_strategy_ui import display_sector_strategy

        display_sector_strategy()
        return

    if view == View.LONGHUBANG:
        from aiagents_stock.features.longhubang.longhubang_ui import display_longhubang

        display_longhubang()
        return

    if view == View.SMART_MONITOR:
        from aiagents_stock.features.smart_monitor.smart_monitor_ui import smart_monitor_ui

        smart_monitor_ui()
        return

    if view == View.PORTFOLIO:
        from aiagents_stock.features.portfolio.portfolio_ui import display_portfolio_manager

        display_portfolio_manager()
        return

    if view == View.CONFIG:
        from aiagents_stock.web.pages.config_page import render_config_page

        render_config_page()
        return

    from aiagents_stock.web.pages.home import render_home

    render_home(api_key_ok=api_key_ok, period=period, selected_model=selected_model)


def main() -> None:
    """Streamlit 应用入口。"""

    _ensure_src_on_path()

    from aiagents_stock.web.components.sidebar import render_sidebar
    from aiagents_stock.web.config import APP_INITIAL_SIDEBAR_STATE, APP_LAYOUT, APP_PAGE_ICON, APP_PAGE_TITLE
    from aiagents_stock.web.styles import apply_global_styles

    st.set_page_config(
        page_title=APP_PAGE_TITLE,
        page_icon=APP_PAGE_ICON,
        layout=APP_LAYOUT,
        initial_sidebar_state=APP_INITIAL_SIDEBAR_STATE,
    )
    apply_global_styles()

    sidebar_state = render_sidebar()

    try:
        _render_current_view(
            view=sidebar_state.current_view,
            api_key_ok=sidebar_state.api_key_configured,
            period=sidebar_state.period,
            selected_model=sidebar_state.selected_model,
        )
    except Exception as exc:
        st.error("❌ 页面渲染失败，请刷新或检查配置。")
        with st.expander("错误详情"):
            st.exception(exc)


if __name__ == "__main__":
    main()
