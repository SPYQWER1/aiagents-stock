from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from aiagents_stock.core.model_config import model_options
from aiagents_stock.db.database import db
from aiagents_stock.features.monitor.monitor_service import monitor_service
from aiagents_stock.web.config import DEFAULT_PERIOD, PERIOD_OPTIONS
from aiagents_stock.web.navigation import View, get_current_view, set_current_view
from aiagents_stock.web.services.analysis_service import check_api_key


@dataclass(frozen=True)
class SidebarState:
    """侧边栏输出状态。"""

    api_key_configured: bool
    selected_model: str
    period: str
    current_view: View


def _render_model_selector() -> str:
    """渲染模型选择器并返回选择结果。"""

    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 AI模型选择")
    return st.sidebar.selectbox(
        "选择AI模型",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        help="DeepSeek Reasoner提供更强的推理能力，但响应时间可能更长",
    )


def _render_system_status() -> None:
    """渲染系统状态信息（监测服务、记录数等）。"""

    st.sidebar.markdown("### 📊 系统状态")
    monitor_status = "🟢 运行中" if monitor_service.running else "🔴 已停止"
    st.sidebar.markdown(f"**监测服务**: {monitor_status}")

    try:
        from aiagents_stock.features.monitor.monitor_db import monitor_db

        stocks = monitor_db.get_monitored_stocks()
        notifications = monitor_db.get_pending_notifications()
        record_count = db.get_record_count()
        st.sidebar.markdown(f"**分析记录**: {record_count}条")
        st.sidebar.markdown(f"**监测股票**: {len(stocks)}只")
        st.sidebar.markdown(f"**待处理**: {len(notifications)}条")
    except Exception:
        return


def _render_help() -> None:
    """渲染侧边栏帮助信息。"""

    with st.sidebar.expander("💡 使用帮助"):
        st.markdown("""
            **股票代码格式**
            - 🇨🇳 A股：6位数字（如600519）
            - 🇭🇰 港股：1-5位数字（如700、00700）或HK前缀（如HK00700）
            - 🇺🇸 美股：字母代码（如AAPL）

            **功能说明**
            - **股票分析**：AI团队深度分析个股
            - **选股板块**：主力资金选股策略
            - **策略分析**：智策板块、智瞰龙虎
            - **投资管理**：持仓分析、实时监测
            - **历史记录**：查看分析历史

            **AI分析流程**
            1. 数据获取 → 2. 技术分析
            3. 基本面分析 → 4. 资金分析
            5. 情绪数据(ARBR) → 6. 新闻(qstock)
            7. AI团队分析 → 8. 团队讨论 → 9. 决策
            """)


def render_sidebar() -> SidebarState:
    """渲染侧边栏并返回关键状态。"""

    current_view = get_current_view()

    with st.sidebar:
        st.markdown("### 🔍 功能导航")

        if st.button("🏠 股票分析", width="stretch", key="nav_home", help="首页，单只股票的深度分析"):
            set_current_view(View.HOME)
            st.rerun()

        st.markdown("---")

        with st.expander("🎯 选股板块", expanded=True):
            st.markdown("**根据不同策略筛选优质股票**")
            if st.button("💰 主力选股", width="stretch", key="nav_main_force", help="基于主力资金流向的选股策略"):
                set_current_view(View.MAIN_FORCE)
                st.rerun()
            if st.button("🐂 低价擒牛", width="stretch", key="nav_low_price_bull", help="低价高成长股票筛选策略"):
                set_current_view(View.LOW_PRICE_BULL)
                st.rerun()
            if st.button("📊 小市值策略", width="stretch", key="nav_small_cap", help="小盘高成长股票筛选策略"):
                set_current_view(View.SMALL_CAP)
                st.rerun()
            if st.button("📈 净利增长", width="stretch", key="nav_profit_growth", help="净利润增长稳健股票筛选策略"):
                set_current_view(View.PROFIT_GROWTH)
                st.rerun()

        with st.expander("📊 策略分析", expanded=True):
            st.markdown("**AI驱动的板块和龙虎榜策略**")
            if st.button("🎯 智策板块", width="stretch", key="nav_sector_strategy", help="AI板块策略分析"):
                set_current_view(View.SECTOR_STRATEGY)
                st.rerun()
            if st.button("🐉 智瞰龙虎", width="stretch", key="nav_longhubang", help="龙虎榜深度分析"):
                set_current_view(View.LONGHUBANG)
                st.rerun()

        with st.expander("💼 投资管理", expanded=True):
            st.markdown("**持仓跟踪与实时监测**")
            if st.button("📊 持仓分析", width="stretch", key="nav_portfolio", help="投资组合分析与定时跟踪"):
                set_current_view(View.PORTFOLIO)
                st.rerun()
            if st.button(
                "🤖 AI盯盘", width="stretch", key="nav_smart_monitor", help="DeepSeek AI自动盯盘决策交易（支持A股T+1）"
            ):
                set_current_view(View.SMART_MONITOR)
                st.rerun()
            if st.button("📡 实时监测", width="stretch", key="nav_monitor", help="价格监控与预警提醒"):
                set_current_view(View.MONITOR)
                st.rerun()

        st.markdown("---")
        if st.button("📖 历史记录", width="stretch", key="nav_history", help="查看历史分析记录"):
            set_current_view(View.HISTORY)
            st.rerun()

        if st.button("⚙️ 环境配置", width="stretch", key="nav_config", help="系统设置与API配置"):
            set_current_view(View.CONFIG)
            st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ 系统配置")

        api_key_ok = check_api_key()
        if api_key_ok:
            st.success("✅ API已连接")
        else:
            st.error("❌ API未配置")
            st.caption("请在.env中配置API密钥")

        st.markdown("---")
        selected_model = _render_model_selector()
        st.session_state.selected_model = selected_model

        st.markdown("---")
        _render_system_status()

        st.markdown("---")
        st.markdown("### 📊 分析参数")
        period = st.selectbox(
            "数据周期",
            list(PERIOD_OPTIONS),
            index=list(PERIOD_OPTIONS).index(DEFAULT_PERIOD) if DEFAULT_PERIOD in PERIOD_OPTIONS else 0,
            help="选择历史数据的时间范围",
        )

        st.markdown("---")
        _render_help()

    return SidebarState(
        api_key_configured=api_key_ok,
        selected_model=selected_model,
        period=period,
        current_view=current_view,
    )
