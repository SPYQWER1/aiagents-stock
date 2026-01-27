from __future__ import annotations

from typing import Any

import streamlit as st

from aiagents_stock.db.database import db
from aiagents_stock.features.monitor.monitor_service import monitor_service
from aiagents_stock.web.components.analysis_display import (
    display_agents_analysis,
    display_final_decision,
    display_stock_info,
    display_team_discussion,
)
from aiagents_stock.web.navigation import View, set_current_view
from aiagents_stock.web.utils.parsing import extract_first_float, extract_float_range


def render_history() -> None:
    """渲染历史记录页面（列表 + 详情）。"""

    if "viewing_record_id" in st.session_state:
        render_record_detail(st.session_state.viewing_record_id)
        return

    st.subheader("📚 历史分析记录")
    records = db.get_all_records()
    if not records:
        st.info("📭 暂无历史分析记录")
        return

    st.write(f"📊 共找到 {len(records)} 条分析记录")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 搜索股票代码或名称", placeholder="输入股票代码或名称进行搜索")
    with col2:
        st.write("")
        st.write("")
        if st.button("🔄 刷新列表"):
            st.rerun()

    filtered_records = records
    if search_term:
        needle = search_term.lower()
        filtered_records = [r for r in records if needle in r["symbol"].lower() or needle in r["stock_name"].lower()]

    if not filtered_records:
        st.warning("🔍 未找到匹配的记录")
        return

    for record in filtered_records:
        rating = record.get("rating", "未知")
        rating_color = {
            "买入": "🟢",
            "持有": "🟡",
            "卖出": "🔴",
            "强烈买入": "🟢",
            "强烈卖出": "🔴",
        }.get(rating, "⚪")

        title = f"{rating_color} {record['stock_name']} ({record['symbol']}) - {record['analysis_date']}"
        with st.expander(title):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                st.write(f"**股票代码:** {record['symbol']}")
                st.write(f"**股票名称:** {record['stock_name']}")
            with col2:
                st.write(f"**分析时间:** {record['analysis_date']}")
                st.write(f"**数据周期:** {record['period']}")
                st.write(f"**投资评级:** **{rating}**")
            with col3:
                if st.button("👀 查看详情", key=f"view_{record['id']}"):
                    st.session_state.viewing_record_id = record["id"]
                    st.rerun()
            with col4:
                if st.button("➕ 监测", key=f"add_monitor_{record['id']}"):
                    st.session_state.add_to_monitor_id = record["id"]
                    st.session_state.viewing_record_id = record["id"]
                    st.rerun()

            col5, _, _, _ = st.columns(4)
            with col5:
                if st.button("🗑️ 删除", key=f"delete_{record['id']}"):
                    if db.delete_record(record["id"]):
                        st.success("✅ 记录已删除")
                        st.rerun()
                    else:
                        st.error("❌ 删除失败")


def _render_add_to_monitor_dialog(record: dict[str, Any]) -> None:
    """渲染“加入监测”表单，并在提交后写入监测数据库。"""

    st.markdown("---")
    st.subheader("➕ 加入监测")

    final_decision = record.get("final_decision")
    if not isinstance(final_decision, dict):
        st.warning("⚠️ 无法从分析结果中提取关键数据")
        if st.button("❌ 取消"):
            if "add_to_monitor_id" in st.session_state:
                del st.session_state.add_to_monitor_id
            st.rerun()
        return

    entry_min, entry_max = extract_float_range(final_decision.get("entry_range", "N/A"))
    take_profit = extract_first_float(final_decision.get("take_profit", "N/A")) or 0.0
    stop_loss = extract_first_float(final_decision.get("stop_loss", "N/A")) or 0.0
    rating = final_decision.get("rating", "买入")

    entry_min = float(entry_min or 0.0)
    entry_max = float(entry_max or 0.0)

    from aiagents_stock.features.monitor.monitor_db import monitor_db

    existing_stocks = monitor_db.get_monitored_stocks()
    is_duplicate = any(stock["symbol"] == record["symbol"] for stock in existing_stocks)
    if is_duplicate:
        st.warning(f"⚠️ {record['symbol']} 已经在监测列表中。继续添加将创建重复监测项。")

    st.info(
        f"""
        **从分析结果中提取的数据：**
        - 进场区间: {entry_min} - {entry_max}
        - 止盈位: {take_profit if take_profit > 0 else '未设置'}
        - 止损位: {stop_loss if stop_loss > 0 else '未设置'}
        - 投资评级: {rating}
        """
    )

    with st.form(key=f"monitor_form_{record['id']}"):
        st.markdown("**请确认或修改监测参数：**")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("🎯 关键位置")
            new_entry_min = st.number_input("进场区间最低价", value=float(entry_min), step=0.01, format="%.2f")
            new_entry_max = st.number_input("进场区间最高价", value=float(entry_max), step=0.01, format="%.2f")
            new_take_profit = st.number_input("止盈价位", value=float(take_profit), step=0.01, format="%.2f")
            new_stop_loss = st.number_input("止损价位", value=float(stop_loss), step=0.01, format="%.2f")
        with col2:
            st.subheader("⚙️ 监测设置")
            check_interval = st.slider("监测间隔(分钟)", 5, 120, 30)
            notification_enabled = st.checkbox("启用通知", value=True)
            new_rating = st.selectbox(
                "投资评级",
                ["买入", "持有", "卖出"],
                index=["买入", "持有", "卖出"].index(rating) if rating in ["买入", "持有", "卖出"] else 0,
            )

        col_a, col_b, _ = st.columns(3)
        with col_a:
            submit = st.form_submit_button("✅ 确认加入监测", type="primary", width="stretch")
        with col_b:
            cancel = st.form_submit_button("❌ 取消", width="stretch")

        if cancel:
            if "add_to_monitor_id" in st.session_state:
                del st.session_state.add_to_monitor_id
            st.rerun()

        if not submit:
            return

        if not (new_entry_min > 0 and new_entry_max > 0 and new_entry_max > new_entry_min):
            st.error("❌ 请输入有效的进场区间（最低价应小于最高价，且都大于0）")
            return

        try:
            entry_range = {"min": new_entry_min, "max": new_entry_max}
            stock_id = monitor_db.add_monitored_stock(
                symbol=record["symbol"],
                name=record["stock_name"],
                rating=new_rating,
                entry_range=entry_range,
                take_profit=new_take_profit if new_take_profit > 0 else None,
                stop_loss=new_stop_loss if new_stop_loss > 0 else None,
                check_interval=check_interval,
                notification_enabled=notification_enabled,
            )
            st.success(f"✅ 已成功将 {record['symbol']} 加入监测列表！")
            st.balloons()
            monitor_service.manual_update_stock(stock_id)

            if "add_to_monitor_id" in st.session_state:
                del st.session_state.add_to_monitor_id
            if "viewing_record_id" in st.session_state:
                del st.session_state.viewing_record_id
            st.session_state.monitor_jump_highlight = record["symbol"]
            set_current_view(View.MONITOR)
            st.rerun()
        except Exception as exc:
            st.error(f"❌ 加入监测失败: {exc}")


def render_record_detail(record_id: str) -> None:
    """渲染单条分析记录详情。"""

    st.markdown("---")
    st.subheader("📋 详细分析记录")

    record = db.get_record_by_id(record_id)
    if not record:
        st.error("❌ 记录不存在")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("股票代码", record["symbol"])
    with col2:
        st.metric("股票名称", record["stock_name"])
    with col3:
        st.metric("分析时间", record["analysis_date"])

    st.subheader("📊 股票基本信息")
    stock_info = record.get("stock_info") or {}
    display_stock_info(stock_info, None)

    agents_results = record.get("agents_results") or {}
    discussion_result = record.get("discussion_result")
    final_decision = record.get("final_decision")

    if agents_results:
        display_agents_analysis(agents_results)
    if discussion_result:
        display_team_discussion(discussion_result)
    if final_decision:
        display_final_decision(final_decision, stock_info, agents_results, discussion_result)

    st.markdown("---")
    st.subheader("🎯 操作")

    if st.session_state.get("add_to_monitor_id") == record_id:
        _render_add_to_monitor_dialog(record)
    else:
        col1, _ = st.columns([1, 3])
        with col1:
            if st.button("➕ 加入监测", type="primary", width="stretch"):
                st.session_state.add_to_monitor_id = record_id
                st.rerun()

    st.markdown("---")
    if st.button("⬅️ 返回历史记录列表"):
        if "viewing_record_id" in st.session_state:
            del st.session_state.viewing_record_id
        if "add_to_monitor_id" in st.session_state:
            del st.session_state.add_to_monitor_id
        st.rerun()
