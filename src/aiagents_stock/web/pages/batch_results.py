from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from aiagents_stock.web.components.analysis_display import (
    display_agents_analysis,
    display_final_decision,
    display_stock_chart,
    display_stock_info,
    display_team_discussion,
)
from aiagents_stock.web.services.analysis_service import get_stock_data


def display_batch_analysis_results(results: list[dict[str, Any]], period: str) -> None:
    """显示批量分析结果（对比视图）。"""

    st.subheader("📊 批量分析结果对比")

    total = len(results)
    success_results = [r for r in results if r.get("success")]
    failed_results = [r for r in results if not r.get("success")]
    saved_count = sum(1 for r in results if r.get("saved_to_db", False))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总数", total)
    with col2:
        st.metric("成功", len(success_results), delta=None, delta_color="normal")
    with col3:
        st.metric("失败", len(failed_results), delta=None, delta_color="inverse")
    with col4:
        st.metric("已保存", saved_count, delta=None, delta_color="normal")

    if saved_count > 0:
        st.info(f"💾 已有 {saved_count} 只股票的分析结果保存到历史记录，可在侧边栏点击「📖 历史记录」查看")

    st.markdown("---")

    if failed_results:
        with st.expander(f"❌ 查看失败的 {len(failed_results)} 只股票", expanded=False):
            for result in failed_results:
                st.error(f"**{result.get('symbol', 'N/A')}**: {result.get('error', '未知错误')}")

    save_failed_results = [r for r in success_results if not r.get("saved_to_db", False)]
    if save_failed_results:
        with st.expander(f"⚠️ 查看分析成功但保存失败的 {len(save_failed_results)} 只股票", expanded=False):
            for result in save_failed_results:
                db_error = result.get("db_error", "未知错误")
                stock_info = result.get("stock_info") or {}
                st.warning(f"**{result.get('symbol', 'N/A')} - {stock_info.get('name', 'N/A')}**: {db_error}")

    if not success_results:
        st.warning("⚠️ 没有成功分析的股票")
        return

    view_mode = st.radio(
        "显示模式",
        ["对比表格", "详细卡片"],
        horizontal=True,
        help="对比表格：横向对比多只股票；详细卡片：逐个查看详细分析",
    )
    if view_mode == "对比表格":
        display_comparison_table(success_results)
    else:
        display_detailed_cards(success_results, period)


def display_comparison_table(results: list[dict[str, Any]]) -> None:
    """显示批量分析结果的对比表格。"""

    st.subheader("📋 股票对比表格")

    comparison_data: list[dict[str, Any]] = []
    for result in results:
        stock_info = result.get("stock_info") or {}
        indicators = result.get("indicators") or {}
        final_decision = result.get("final_decision")

        if isinstance(final_decision, dict):
            rating = final_decision.get("rating", "N/A")
            confidence = final_decision.get("confidence_level", "N/A")
            target_price = final_decision.get("target_price", "N/A")
        else:
            rating = "N/A"
            confidence = "N/A"
            target_price = "N/A"

        if isinstance(confidence, (int, float)):
            confidence = str(confidence)

        comparison_data.append(
            {
                "股票代码": stock_info.get("symbol", "N/A"),
                "股票名称": stock_info.get("name", "N/A"),
                "当前价格": stock_info.get("current_price", "N/A"),
                "涨跌幅(%)": stock_info.get("change_percent", "N/A"),
                "市盈率": stock_info.get("pe_ratio", "N/A"),
                "市净率": stock_info.get("pb_ratio", "N/A"),
                "RSI": indicators.get("rsi", "N/A"),
                "MACD": indicators.get("macd", "N/A"),
                "投资评级": rating,
                "信心度": confidence,
                "目标价格": target_price,
            }
        )

    df = pd.DataFrame(comparison_data)
    st.dataframe(df, width="stretch", height=400)
    st.caption("💡 投资评级说明：强烈买入 > 买入 > 持有 > 卖出 > 强烈卖出")

    st.markdown("---")
    st.subheader("🔍 快速筛选")

    col1, col2 = st.columns(2)
    with col1:
        rating_filter = st.multiselect(
            "按评级筛选", options=df["投资评级"].unique().tolist(), default=df["投资评级"].unique().tolist()
        )
    with col2:
        sort_by = st.selectbox("排序方式", ["默认", "涨跌幅降序", "涨跌幅升序", "信心度降序", "RSI降序"])

    filtered_df = df[df["投资评级"].isin(rating_filter)]
    if sort_by == "涨跌幅降序":
        filtered_df = filtered_df.sort_values("涨跌幅(%)", ascending=False)
    elif sort_by == "涨跌幅升序":
        filtered_df = filtered_df.sort_values("涨跌幅(%)", ascending=True)
    elif sort_by == "信心度降序":
        filtered_df = filtered_df.sort_values("信心度", ascending=False)
    elif sort_by == "RSI降序":
        filtered_df = filtered_df.sort_values("RSI", ascending=False)

    if filtered_df.empty:
        st.info("没有符合条件的股票")
        return
    st.dataframe(filtered_df, width="stretch")


def display_detailed_cards(results: list[dict[str, Any]], period: str) -> None:
    """显示逐只股票的详细分析卡片视图。"""

    st.subheader("📇 详细分析卡片")
    stock_options = [f"{r['stock_info']['symbol']} - {r['stock_info']['name']}" for r in results if r.get("stock_info")]
    if not stock_options:
        st.info("📭 暂无可展示的详细结果")
        return

    selected_stock = st.selectbox("选择股票", options=stock_options)
    selected_index = stock_options.index(selected_stock)
    result = results[selected_index]

    stock_info = result["stock_info"]
    indicators = result.get("indicators")
    agents_results = result.get("agents_results") or {}
    discussion_result = result.get("discussion_result")
    final_decision = result.get("final_decision")

    try:
        bundle = get_stock_data(stock_info["symbol"], period)
        display_stock_info(stock_info, indicators if indicators is not None else bundle.indicators)
        if bundle.stock_data is not None:
            display_stock_chart(bundle.stock_data, stock_info)
        display_agents_analysis(agents_results)
        display_team_discussion(discussion_result)
        display_final_decision(final_decision, stock_info, agents_results, discussion_result)
    except Exception as exc:
        st.error(f"显示详细信息时出错: {exc}")
