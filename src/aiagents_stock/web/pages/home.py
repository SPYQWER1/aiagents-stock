from __future__ import annotations

import json
import time
import pandas as pd
from typing import Any

import streamlit as st

from aiagents_stock.container import DIContainer
from aiagents_stock.application.analysis.use_cases import BatchAnalysisItemResult
from aiagents_stock.web.components.analysis_display import (
    display_agents_analysis,
    display_final_decision,
    display_stock_chart,
    display_stock_info,
    display_team_discussion,
)
from aiagents_stock.web.config import (
    BATCH_MAX_WORKERS,
    BATCH_TIMEOUT_SECONDS,
    MAX_BATCH_STOCKS_RECOMMENDED,
    EnabledAnalysts,
)
from aiagents_stock.web.adapters.analysis_adapter import (
    analyze_batch_stocks_via_use_case,
    analyze_single_stock_via_use_case,
    get_financial_data,
    get_stock_data,
)
from aiagents_stock.web.utils.parsers import parse_stock_list
from aiagents_stock.web.utils.session_state import reset_all_analysis_state, reset_batch_analysis_state


def render_header() -> None:
    """渲染顶部标题栏。"""

    st.markdown(
        """
    <div class="top-nav">
        <h1 class="nav-title">📈 复合多AI智能体股票团队分析系统</h1>
        <p class="nav-subtitle">投资分析平台 | Multi-Agent Stock Analysis System</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def _render_mode_and_inputs() -> tuple[str, str, bool, str]:
    """渲染模式选择与输入区，返回（模式、输入、按钮点击、批量模式）。"""

    col_mode1, col_mode2 = st.columns([1, 3])
    
    # 自动切换到批量模式
    idx = 0
    if st.session_state.get("batch_analysis_input_stocks"):
        idx = 1
        
    with col_mode1:
        analysis_mode = st.radio(
            "分析模式",
            ["单个分析", "批量分析"],
            horizontal=True,
            index=idx
        )

    batch_mode = st.session_state.get("batch_mode", "顺序分析")
    with col_mode2:
        if analysis_mode == "批量分析":
            batch_mode = st.radio(
                "批量模式",
                ["顺序分析", "多线程并行"],
                horizontal=True,
                help="顺序分析：按次序分析，稳定但较慢；多线程并行：同时分析多只，快速但消耗资源",
            )
            st.session_state.batch_mode = batch_mode

    st.markdown("---")

    if analysis_mode == "单个分析":
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            stock_input = st.text_input(
                "🔍 请输入股票代码",
                placeholder="例如: AAPL, 000001, 00700",
                help="支持A股(如000001)、港股(如00700)和美股(如AAPL)",
                key="home_single_stock_input"
            )
        with col2:
            analyze_button = st.button("🚀 开始分析", type="primary", width="stretch")
        with col3:
            if st.button("🔄 清除缓存", width="stretch"):
                st.cache_data.clear()
                st.success("缓存已清除")
    else:
        ## 批量分析输入区
        # 检查是否有从外部传入的预设值
        default_value = ""
        if "batch_analysis_input_stocks" in st.session_state:
            default_value = st.session_state.batch_analysis_input_stocks
            # 消费后清除，避免一直覆盖
            del st.session_state.batch_analysis_input_stocks
        
        # 如果没有预设值，但有 session_state key 对应的值，streamlit 会自动使用
        
        stock_input = st.text_area(
            "🔍 请输入多个股票代码（每行一个或用逗号分隔）",
            value=default_value if default_value else st.session_state.get("home_batch_stock_input", ""),
            placeholder="例如:\n000001\n600036\n00700\n\n或者: 000001, 600036, 00700, AAPL",
            height=120,
            help="支持多种格式：每行一个代码或用逗号分隔。支持A股、港股、美股",
            key="home_batch_stock_input"
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            analyze_button = st.button("🚀 开始批量分析", type="primary", width="stretch")
        with col2:
            if st.button("🔄 清除缓存", width="stretch"):
                st.cache_data.clear()
                st.success("缓存已清除")
        with col3:
            if st.button("🗑️ 清除结果", width="stretch"):
                reset_batch_analysis_state()
                st.success("已清除批量分析结果")
        with col4:
            if st.button("📜 历史记录", width="stretch"):
                st.session_state.view_home_history = True
                st.rerun()

    return analysis_mode, stock_input, analyze_button, batch_mode


def _render_analyst_selector() -> EnabledAnalysts:
    """渲染分析师选择器并返回启用配置。"""

    st.markdown("---")
    st.subheader("👥 分析师团队")

    col1, col2, col3 = st.columns(3)
    with col1:
        enable_technical = st.checkbox("📊 技术分析师", value=True, help="负责技术指标分析、图表形态识别、趋势判断")
        enable_fundamental = st.checkbox("💼 基本面分析师", value=True, help="负责公司财务分析、行业研究、估值分析")
    with col2:
        enable_fund_flow = st.checkbox("💰 资金面分析师", value=True, help="负责资金流向分析、主力行为研究")
        enable_risk = st.checkbox("⚠️ 风险管理师", value=True, help="负责风险识别、风险评估、风险控制策略制定")
    with col3:
        enable_sentiment = st.checkbox("📈 市场情绪分析师", value=True, help="负责市场情绪研究、ARBR指标分析（仅A股）")
        enable_news = st.checkbox("📰 新闻分析师", value=True, help="负责新闻事件分析、舆情研究（仅A股，qstock数据源）")

    selected = []
    if enable_technical:
        selected.append("技术分析师")
    if enable_fundamental:
        selected.append("基本面分析师")
    if enable_fund_flow:
        selected.append("资金面分析师")
    if enable_risk:
        selected.append("风险管理师")
    if enable_sentiment:
        selected.append("市场情绪分析师")
    if enable_news:
        selected.append("新闻分析师")

    if selected:
        st.info(f"✅ 已选择 {len(selected)} 位分析师: {', '.join(selected)}")
    else:
        st.warning("⚠️ 请至少选择一位分析师")

    st.session_state.enable_technical = enable_technical
    st.session_state.enable_fundamental = enable_fundamental
    st.session_state.enable_fund_flow = enable_fund_flow
    st.session_state.enable_risk = enable_risk
    st.session_state.enable_sentiment = enable_sentiment
    st.session_state.enable_news = enable_news

    return EnabledAnalysts(
        technical=enable_technical,
        fundamental=enable_fundamental,
        fund_flow=enable_fund_flow,
        risk=enable_risk,
        sentiment=enable_sentiment,
        news=enable_news,
    )


def _validate_before_run(api_key_ok: bool, enabled: EnabledAnalysts, stock_input: str) -> bool:
    """校验分析前置条件"""

    if not stock_input:
        st.error("❌ 请输入股票代码")
        return False
    if not api_key_ok:
        st.error("❌ 请先配置 DeepSeek API Key")
        return False
    if not any(enabled.as_dict().values()):
        st.error("❌ 请至少选择一位分析师参与分析")
        return False
    return True


def _run_single_analysis_use_case_ui(symbol: str, period: str, enabled: EnabledAnalysts, selected_model: str) -> None:
    """执行并渲染单股分析流程（新架构用例路径）。"""

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # 1. 预加载基础数据（利用 UI 缓存）
        status_text.text("📈 正在获取股票基础数据...")
        progress_bar.progress(10)
        bundle = get_stock_data(symbol, period)

        if bundle.stock_data is None:
            st.error("❌ 无法获取股票历史数据")
            return

        # 渲染基础信息（让用户先看到数据）
        display_stock_info(bundle.stock_info, bundle.indicators)
        display_stock_chart(bundle.stock_data, bundle.stock_info)
        progress_bar.progress(30)

        # 2. 预加载财务数据
        status_text.text("📊 正在获取财务数据...")
        financial_data = get_financial_data(symbol)
        progress_bar.progress(40)

        # 3. 执行 AI 分析（传入预加载数据以提升性能）
        status_text.text("🔍 AI分析师团队正在分析，请稍候...")
        with st.spinner("AI团队分析中..."):
            result = analyze_single_stock_via_use_case(
                symbol=symbol,
                period=period,
                enabled=enabled,
                selected_model=selected_model,
                use_cached_agents=True,
                preloaded_bundle=bundle,
                preloaded_financial_data=financial_data,
            )

        progress_bar.progress(85)

        # 4. 渲染分析结果
        agents_results = result["agents_results"]
        discussion_result = result["discussion_result"]
        final_decision = result["final_decision"]
        record_id = int(result["record_id"])

        display_agents_analysis(agents_results)
        display_team_discussion(discussion_result)
        display_final_decision(final_decision, bundle.stock_info, agents_results, discussion_result)

        progress_bar.progress(100)

        st.session_state.analysis_completed = True
        st.session_state.stock_info = bundle.stock_info
        st.session_state.agents_results = agents_results
        st.session_state.discussion_result = discussion_result
        st.session_state.final_decision = final_decision
        st.session_state.just_completed = True

        st.success(f"✅ 分析完成，记录已保存（ID: {record_id}）")
        status_text.text("✅ 分析完成！")
    except Exception as exc:
        st.error(f"❌ 分析过程中出现错误: {exc}")
    finally:
        progress_bar.empty()
        status_text.empty()


def _run_batch_analysis_ui(stock_list: list[str], period: str, enabled: EnabledAnalysts, selected_model: str, batch_mode: str) -> None:
    """执行并渲染批量分析流程（顺序 / 多线程）。"""

    st.subheader(f"📊 批量分析进行中 ({batch_mode})")
    progress_bar = st.progress(0)
    status_text = st.empty()

    results: list[dict[str, Any]] = []
    total = len(stock_list)
    max_workers = BATCH_MAX_WORKERS if batch_mode == "多线程并行" else 1

    status_text.text(f"🚀 正在分析 {total} 只股票...")
    
    start_time = time.time()
    
    # 调用批量分析用例
    for i, item_result in enumerate(analyze_batch_stocks_via_use_case(
        stock_list=stock_list,
        period=period,
        enabled=enabled,
        selected_model=selected_model,
        max_workers=max_workers,
        timeout_seconds=BATCH_TIMEOUT_SECONDS
    ), 1):
        symbol = item_result.symbol
        
        # 转换结果为字典格式
        result_dict = {
            "symbol": symbol,
            "success": item_result.success,
            "error": item_result.error,
        }
        
        if item_result.success and item_result.data:
            data = item_result.data
            result_dict.update({
                "stock_info": data.bundle.stock_info,
                "indicators": data.bundle.indicators,
                "agents_results": data.analysis_result.agents_results,
                "discussion_result": data.analysis_result.discussion_result,
                "final_decision": data.analysis_result.final_decision,
                "saved_to_db": True,
                "record_id": data.record_id,
            })

        results.append(result_dict)
        
        # 更新进度
        progress_bar.progress(i / total)
        if item_result.success:
            status_text.text(f"✅ [{i}/{total}] {symbol} 分析完成")
        else:
            status_text.text(f"❌ [{i}/{total}] {symbol} 分析失败: {item_result.error}")

    progress_bar.progress(1.0)
    success_count = sum(1 for r in results if r.get("success"))
    failed_count = total - success_count
    saved_count = sum(1 for r in results if r.get("saved_to_db"))
    
    total_time = time.time() - start_time

    # 保存批量分析会话记录
    try:
        save_use_case = DIContainer.create_save_batch_analysis_result_use_case()
        # 构造精简的 results 用于存储 (去掉 stock_info 等大对象)
        simple_results = []
        for r in results:
            simple_r = {
                "symbol": r.get("symbol"),
                "success": r.get("success"),
                "error": r.get("error"),
                "final_decision": r.get("final_decision", "N/A"),
                "record_id": r.get("record_id")
            }
            simple_results.append(simple_r)
            
        save_use_case.execute(
            batch_count=total,
            analysis_mode=batch_mode,
            success_count=success_count,
            failed_count=failed_count,
            total_time=total_time,
            results=simple_results
        )
    except Exception as e:
        st.error(f"⚠️ 保存批量分析历史记录失败: {e}")

    if success_count > 0:
        status_text.success(f"✅ 批量分析完成！成功 {success_count} 只，失败 {failed_count} 只，已保存 {saved_count} 只到历史记录")
        save_failed = [r["symbol"] for r in results if r.get("success") and not r.get("saved_to_db")]
        if save_failed:
            st.warning(f"⚠️ 以下股票分析成功但保存失败: {', '.join(save_failed)}")
    else:
        status_text.error("❌ 批量分析完成，但所有股票都分析失败")

    st.session_state.batch_analysis_results = results
    st.session_state.batch_analysis_mode = batch_mode

    progress_bar.empty()
    status_text.empty()
    st.rerun()


def _display_batch_history():
    """显示批量分析历史记录"""
    
    col_back, col_title = st.columns([1, 4])
    with col_back:
        if st.button("← 返回分析"):
            st.session_state.view_home_history = False
            st.rerun()
            
    st.markdown("## 📚 批量分析历史记录")
    st.markdown("---")
    
    use_case = DIContainer.create_get_batch_analysis_history_use_case()
    
    try:
        history_records = use_case.execute(limit=50)
        
        if not history_records:
             st.info("📝 暂无批量分析历史记录")
             return

        st.markdown(f"### 📋 最近 {len(history_records)} 条记录")
        
        for idx, record in enumerate(history_records):
            results_data = []
            try:
                if isinstance(record["results"], str):
                    results_data = json.loads(record["results"])
                else:
                    results_data = record["results"]
            except:
                results_data = []
            
            success_rate = (record['success_count'] / record['batch_count'] * 100) if record['batch_count'] > 0 else 0
            
            with st.expander(
                f"⚡ {record['created_at']} | "
                f"共{record['batch_count']}只 | "
                f"成功{record['success_count']} | "
                f"成功率{success_rate:.0f}% | "
                f"耗时{record['total_time']:.1f}秒",
                expanded=(idx == 0)
            ):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.write(f"**分析时间**: {record['created_at']}")
                with col2:
                    st.write(f"**模式**: {record['analysis_mode']}")
                with col3:
                    st.write(f"**成功/失败**: {record['success_count']} / {record['failed_count']}")
                with col4:
                    st.write(f"**总耗时**: {record['total_time']:.1f}秒")
                
                # 结果预览
                if results_data:
                    st.markdown("#### 📊 分析结果概览")
                    
                    df_data = []
                    for res in results_data:
                        decision = res.get("final_decision", "N/A")
                        # 如果是 dict (可能来自旧数据或不同结构), 尝试提取
                        if isinstance(decision, dict):
                             decision = str(decision)
                             
                        df_data.append({
                            "股票代码": res.get("symbol", ""),
                            "状态": "✅ 成功" if res.get("success") else "❌ 失败",
                            "决策": decision,
                            "错误信息": res.get("error", "")
                        })
                    
                    st.dataframe(pd.DataFrame(df_data), hide_index=True, width='stretch')

                # 操作按钮
                col_del, col_load = st.columns([1, 1])
                with col_del:
                    if st.button("🗑️ 删除此记录", key=f"del_home_batch_{record['id']}"):
                        if use_case.delete(record['id']):
                            st.success("✅ 删除成功")
                            st.rerun()
                        else:
                            st.error("❌ 删除失败")
                with col_load:
                    if st.button("🔄 加载到输入框", key=f"load_home_batch_{record['id']}"):
                        symbols = []
                        if results_data:
                            for r in results_data:
                                if "symbol" in r:
                                    symbols.append(r["symbol"])
                        
                        if symbols:
                            st.session_state.batch_analysis_input_stocks = ", ".join(symbols)
                            st.session_state.view_home_history = False
                            st.success(f"✅ 已加载 {len(symbols)} 只股票到输入框")
                            st.rerun()
                        else:
                            st.warning("⚠️ 记录中没有有效的股票代码")

    except Exception as e:
        st.error(f"❌ 获取历史记录失败: {str(e)}")


def render_home(*, api_key_ok: bool, period: str, selected_model: str) -> None:
    """渲染首页（单股/批量分析）。"""

    render_header()

    if st.session_state.get("view_home_history"):
        _display_batch_history()
        return

    analysis_mode, stock_input, analyze_button, batch_mode = _render_mode_and_inputs()
    enabled = _render_analyst_selector()

    if analyze_button and _validate_before_run(api_key_ok, enabled, stock_input):
        reset_all_analysis_state()

        if analysis_mode == "单个分析":
            _run_single_analysis_use_case_ui(stock_input.strip(), period, enabled, selected_model)
        else:
            stock_list = parse_stock_list(stock_input)
            if not stock_list:
                st.error("❌ 请输入有效的股票代码")
                return
            if len(stock_list) > MAX_BATCH_STOCKS_RECOMMENDED:
                st.warning(f"⚠️ 检测到 {len(stock_list)} 只股票，建议一次分析不超过{MAX_BATCH_STOCKS_RECOMMENDED}只")
            st.info(f"📊 准备分析 {len(stock_list)} 只股票: {', '.join(stock_list)}")
            _run_batch_analysis_ui(stock_list, period, enabled, selected_model, batch_mode)

    if st.session_state.get("batch_analysis_results"):
        from aiagents_stock.web.pages.batch_results import display_batch_analysis_results

        display_batch_analysis_results(st.session_state.batch_analysis_results, period)
        return

    if st.session_state.get("analysis_completed"):
        if st.session_state.get("just_completed"):
            st.session_state.just_completed = False
            return

        stock_info = st.session_state.stock_info
        agents_results = st.session_state.agents_results
        discussion_result = st.session_state.discussion_result
        final_decision = st.session_state.final_decision

        bundle = get_stock_data(stock_info["symbol"], period)
        display_stock_info(stock_info, bundle.indicators)
        if bundle.stock_data is not None:
            display_stock_chart(bundle.stock_data, stock_info)
        display_agents_analysis(agents_results)
        display_team_discussion(discussion_result)
        display_final_decision(final_decision, stock_info, agents_results, discussion_result)
        return

    if not stock_input:
        from aiagents_stock.web.pages.home_help import show_example_interface

        show_example_interface()
