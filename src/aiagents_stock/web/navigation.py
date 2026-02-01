from __future__ import annotations

from enum import Enum

import streamlit as st


class View(str, Enum):
    """应用内视图路由。"""

    HOME = "home"
    HISTORY = "history"
    MONITOR = "monitor"
    MAIN_FORCE = "main_force"
    LOW_PRICE_BULL = "low_price_bull"
    SMALL_CAP = "small_cap"
    PROFIT_GROWTH = "profit_growth"
    SECTOR_STRATEGY = "sector_strategy"
    LONGHUBANG = "longhubang"
    SMART_MONITOR = "smart_monitor"
    PORTFOLIO = "portfolio"
    CONFIG = "config"


SESSION_KEY_VIEW = "current_view"


_LEGACY_VIEW_FLAGS: dict[str, View] = {
    "show_history": View.HISTORY,
    "show_monitor": View.MONITOR,
    "show_main_force": View.MAIN_FORCE,
    "show_low_price_bull": View.LOW_PRICE_BULL,
    "show_small_cap": View.SMALL_CAP,
    "show_profit_growth": View.PROFIT_GROWTH,
    "show_sector_strategy": View.SECTOR_STRATEGY,
    "show_longhubang": View.LONGHUBANG,
    "show_smart_monitor": View.SMART_MONITOR,
    "show_portfolio": View.PORTFOLIO,
    "show_config": View.CONFIG,
}


def migrate_legacy_navigation_state() -> None:
    """将旧版布尔导航状态迁移到单一的 current_view。"""

    if SESSION_KEY_VIEW in st.session_state:
        return
    for key, view in _LEGACY_VIEW_FLAGS.items():
        if st.session_state.get(key):
            st.session_state[SESSION_KEY_VIEW] = view.value
            return
    st.session_state[SESSION_KEY_VIEW] = View.HOME.value


def get_current_view() -> View:
    """获取当前视图。"""

    migrate_legacy_navigation_state()
    raw = st.session_state.get(SESSION_KEY_VIEW, View.HOME.value)
    try:
        return View(raw)
    except Exception:
        st.session_state[SESSION_KEY_VIEW] = View.HOME.value
        return View.HOME


def set_current_view(view: View) -> None:
    """设置当前视图。"""

    st.session_state[SESSION_KEY_VIEW] = view.value
