from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aiagents_stock.reporting.pdf_generator import display_pdf_export_section


def display_stock_info(stock_info: dict[str, Any], indicators: dict[str, Any] | None) -> None:
    """渲染股票基础信息与关键技术指标。"""

    st.subheader(f"📊 {stock_info.get('name', 'N/A')} ({stock_info.get('symbol', 'N/A')})")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("当前价格", f"{stock_info.get('current_price', 'N/A')}")

    with col2:
        change_percent = stock_info.get("change_percent", "N/A")
        if isinstance(change_percent, (int, float)):
            st.metric("涨跌幅", f"{change_percent:.2f}%", f"{change_percent:.2f}%")
        else:
            st.metric("涨跌幅", f"{change_percent}")

    with col3:
        st.metric("市盈率", f"{stock_info.get('pe_ratio', 'N/A')}")

    with col4:
        st.metric("市净率", f"{stock_info.get('pb_ratio', 'N/A')}")

    with col5:
        market_cap = stock_info.get("market_cap", "N/A")
        if isinstance(market_cap, (int, float)):
            market_cap_str = f"{market_cap/1e9:.2f}B" if market_cap > 1e9 else f"{market_cap/1e6:.2f}M"
            st.metric("市值", market_cap_str)
        else:
            st.metric("市值", f"{market_cap}")

    if not indicators or not isinstance(indicators, dict) or "error" in indicators:
        return

    st.subheader("📈 关键技术指标")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rsi = indicators.get("rsi", "N/A")
        st.metric("RSI", f"{rsi:.2f}" if isinstance(rsi, (int, float)) else f"{rsi}")

    with col2:
        ma20 = indicators.get("ma20", "N/A")
        st.metric("MA20", f"{ma20:.2f}" if isinstance(ma20, (int, float)) else f"{ma20}")

    with col3:
        volume_ratio = indicators.get("volume_ratio", "N/A")
        st.metric("量比", f"{volume_ratio:.2f}" if isinstance(volume_ratio, (int, float)) else f"{volume_ratio}")

    with col4:
        macd = indicators.get("macd", "N/A")
        st.metric("MACD", f"{macd:.4f}" if isinstance(macd, (int, float)) else f"{macd}")


def display_stock_chart(stock_data: pd.DataFrame, stock_info: dict[str, Any]) -> None:
    """渲染股票 K 线与成交量图。"""

    st.subheader("📈 股价走势图")

    data = stock_data
    if "Volume" in data.columns:
        data = data[(data["Volume"] > 0) & (data["Volume"].notna())]

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="K线",
        )
    )

    if "MA5" in data.columns:
        fig.add_trace(go.Scatter(x=data.index, y=data["MA5"], name="MA5", line=dict(color="orange", width=1)))
    if "MA20" in data.columns:
        fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20", line=dict(color="blue", width=1)))
    if "MA60" in data.columns:
        fig.add_trace(go.Scatter(x=data.index, y=data["MA60"], name="MA60", line=dict(color="purple", width=1)))

    if "BB_upper" in data.columns and "BB_lower" in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data["BB_upper"],
                name="布林上轨",
                line=dict(color="red", width=1, dash="dash"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data["BB_lower"],
                name="布林下轨",
                line=dict(color="green", width=1, dash="dash"),
            )
        )

    fig.update_layout(
        title=f"{stock_info.get('name', 'N/A')} ({stock_info.get('symbol', 'N/A')})",
        xaxis_title="日期",
        yaxis_title="价格",
        height=500,
        xaxis_rangebreaks=[dict(bounds=["sat", "mon"])],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, width="stretch", config={"responsive": True})

    if "Volume" not in data.columns:
        return

    fig_volume = go.Figure()
    fig_volume.add_trace(go.Bar(x=data.index, y=data["Volume"], name="成交量", marker_color="lightblue"))
    fig_volume.update_layout(
        title="成交量",
        xaxis_title="日期",
        yaxis_title="成交量",
        height=200,
        xaxis_rangebreaks=[dict(bounds=["sat", "mon"])],
    )
    st.plotly_chart(fig_volume, width="stretch", config={"responsive": True})


def display_agents_analysis(agents_results: dict[str, dict[str, Any]]) -> None:
    """渲染各分析师的报告标签页。"""

    st.subheader("🤖 AI分析师团队报告")

    tab_names: list[str] = []
    tab_contents: list[dict[str, Any]] = []
    for agent_result in agents_results.values():
        tab_names.append(agent_result.get("agent_name", "未知分析师"))
        tab_contents.append(agent_result)

    if not tab_names:
        st.info("📭 暂无分析师报告")
        return

    tabs = st.tabs(tab_names)
    for i, tab in enumerate(tabs):
        with tab:
            agent_result = tab_contents[i]
            st.markdown(
                f"""
            <div class="agent-card">
                <h4>👨‍💼 {agent_result.get('agent_name', '未知')}</h4>
                <p><strong>职责：</strong>{agent_result.get('agent_role', '未知')}</p>
                <p><strong>关注领域：</strong>{', '.join(agent_result.get('focus_areas', []))}</p>
                <p><strong>分析时间：</strong>{agent_result.get('timestamp', '未知')}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
            st.markdown("**📄 分析报告:**")
            st.write(agent_result.get("analysis", "暂无分析"))


def display_team_discussion(discussion_result: Any) -> None:
    """渲染团队讨论内容。"""

    st.subheader("🤝 分析团队讨论")
    st.markdown(
        """
    <div class="agent-card">
        <h4>💭 团队综合讨论</h4>
        <p>各位分析师正在就该股票进行深入讨论，整合不同维度的分析观点...</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.write(discussion_result)


def display_final_decision(
    final_decision: Any,
    stock_info: dict[str, Any],
    agents_results: dict[str, dict[str, Any]] | None = None,
    discussion_result: Any | None = None,
) -> None:
    """渲染最终投资决策，并在数据完整时提供 PDF 导出。"""

    st.subheader("📋 最终投资决策")

    if isinstance(final_decision, dict) and "decision_text" not in final_decision:
        col1, col2 = st.columns([1, 2])

        with col1:
            rating = final_decision.get("rating", "未知")
            rating_color = {"买入": "🟢", "持有": "🟡", "卖出": "🔴"}.get(rating, "⚪")
            st.markdown(
                f"""
            <div class="decision-card">
                <h3 style="text-align: center;">{rating_color} {rating}</h3>
                <h4 style="text-align: center;">投资评级</h4>
            </div>
            """,
                unsafe_allow_html=True,
            )

            confidence = final_decision.get("confidence_level", "N/A")
            st.metric("信心度", f"{confidence}/10")
            st.metric("目标价格", f"{final_decision.get('target_price', 'N/A')}")
            st.metric("建议仓位", f"{final_decision.get('position_size', 'N/A')}")

        with col2:
            st.markdown("**🎯 操作建议:**")
            st.write(final_decision.get("operation_advice", "暂无建议"))

            st.markdown("**📍 关键位置:**")
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.write(f"**进场区间:** {final_decision.get('entry_range', 'N/A')}")
                st.write(f"**止盈位:** {final_decision.get('take_profit', 'N/A')}")
            with col2_2:
                st.write(f"**止损位:** {final_decision.get('stop_loss', 'N/A')}")
                st.write(f"**持有周期:** {final_decision.get('holding_period', 'N/A')}")

        risk_warning = final_decision.get("risk_warning", "")
        if risk_warning:
            st.markdown(
                f"""
            <div class="warning-card">
                <h4>⚠️ 风险提示</h4>
                <p>{risk_warning}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )
    else:
        decision_text = final_decision.get("decision_text", str(final_decision)) if isinstance(final_decision, dict) else str(final_decision)
        st.write(decision_text)

    st.markdown("---")
    if agents_results and discussion_result is not None:
        display_pdf_export_section(stock_info, agents_results, discussion_result, final_decision)
    else:
        st.warning("⚠️ PDF导出功能需要完整的分析数据")

