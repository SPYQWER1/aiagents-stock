#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 应用主入口

该模块是 AI Agents Stock 系统的 Web 应用主入口，负责：
1. 配置 Streamlit 应用的基本设置
2. 处理页面路由和导航
3. 渲染各个功能模块的 UI 界面
4. 处理全局异常和错误显示

主要功能模块包括：
- 历史记录管理
- 实时监测
- 主力选股
- 低价擒牛
- 小市值策略
- 盈利增长
- 智策板块
- 智瞰龙虎
- 智能盯盘
- 投资组合管理
- 系统配置
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
import logging

import streamlit as st
from aiagents_stock.infrastructure.logging_config import setup_logging

# 初始化日志
setup_logging(log_dir="logs", log_level=logging.INFO)

if TYPE_CHECKING:
    from aiagents_stock.web.navigation import View


def _ensure_src_on_path() -> None:
    """
    确保 src 目录在 sys.path 中，便于以脚本方式运行时导入包。

    该函数会计算 src 目录的绝对路径，并将其添加到 sys.path 的开头，
    确保所有模块都能正确导入，无论从哪个目录运行应用。
    """
    src_dir = Path(__file__).resolve().parents[2]
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _render_current_view(*, view: "View", api_key_ok: bool, period: str, selected_model: str) -> None:
    """
    根据当前视图路由渲染对应页面。

    该函数根据传入的 view 参数，动态导入并渲染对应的页面组件，
    实现了基于路由的页面导航功能。

    Args:
        view: 当前视图枚举值，决定渲染哪个页面
        api_key_ok: API 密钥是否配置正确
        period: 时间周期选择
        selected_model: 选定的 AI 模型
    """
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

    # 默认渲染主页
    from aiagents_stock.web.pages.home import render_home

    render_home(api_key_ok=api_key_ok, period=period, selected_model=selected_model)


def main() -> None:
    """
    Streamlit 应用主函数。

    该函数是应用的入口点，负责：
    1. 确保 src 目录在路径中
    2. 配置 Streamlit 应用的页面设置
    3. 应用全局样式
    4. 渲染侧边栏导航
    5. 根据导航选择渲染对应页面
    6. 处理全局异常并显示错误信息
    """
    _ensure_src_on_path()

    from aiagents_stock.web.components.sidebar import render_sidebar
    from aiagents_stock.web.config import APP_INITIAL_SIDEBAR_STATE, APP_LAYOUT, APP_PAGE_ICON, APP_PAGE_TITLE
    from aiagents_stock.web.styles import apply_global_styles

    # 配置 Streamlit 页面设置
    st.set_page_config(
        page_title=APP_PAGE_TITLE,
        page_icon=APP_PAGE_ICON,
        layout=APP_LAYOUT,
        initial_sidebar_state=APP_INITIAL_SIDEBAR_STATE,
    )

    # 应用全局样式
    apply_global_styles()

    # 渲染侧边栏并获取导航状态
    sidebar_state = render_sidebar()

    try:
        # 根据导航状态渲染对应页面
        _render_current_view(
            view=sidebar_state.current_view,
            api_key_ok=sidebar_state.api_key_configured,
            period=sidebar_state.period,
            selected_model=sidebar_state.selected_model,
        )
    except Exception as exc:
        # 显示错误信息
        st.error("❌ 页面渲染失败，请刷新或检查配置。")
        with st.expander("错误详情"):
            st.exception(exc)


if __name__ == "__main__":
    main()
