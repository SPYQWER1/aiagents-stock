"""
主力选股分析 UI 模块 (DDD 重构版).

该模块负责展示主力选股分析的界面，包括：
1. 股票代码输入
2. 分析配置（模式、并发数）
3. 调用应用层用例执行批量分析
4. 展示分析进度和结果
5. 跳转至历史记录
"""

import pandas as pd
import streamlit as st

from aiagents_stock.container import DIContainer
from aiagents_stock.domain.main_force.model import MainForceAnalysis
from aiagents_stock.features.main_force.main_force_history_ui import display_selection_history
from aiagents_stock.features.main_force.main_force_pdf_generator import display_report_download_section
from aiagents_stock.web.navigation import View, set_current_view


def _clean_stock_code(code: str) -> str:
    """清理股票代码，移除后缀（如 .SH, .SZ）"""
    if "." in code:
        return code.split(".")[0]
    return code

def display_main_force_stock_selection():
    """显示主力选股分析主界面"""
    
    # 检查 API Key
    if not DIContainer.check_api_key():
        st.warning("⚠️ 请先在 .env 文件中配置 DEEPSEEK_API_KEY")
        return

    # 检查是否查看历史记录
    if st.session_state.get("main_force_view_history", False):
        display_selection_history()
        return

    st.markdown("## 🚀 主力选股 AI 分析")
    st.markdown("此模块对指定的一组股票进行批量 AI 分析，挖掘主力资金动向与投资机会。")
    st.markdown("---")
    
    col_hist, col_blank = st.columns([1, 5])
    with col_hist:
        if st.button("📜 查看历史记录"):
            st.session_state.main_force_view_history = True
            st.rerun()

    # 检查是否有加载的分析结果
    if "main_force_result" in st.session_state and st.session_state.main_force_result:
        st.info("📊 正在查看历史分析结果")
        if st.button("❌ 关闭结果，返回主界面"):
            del st.session_state.main_force_result
            st.rerun()
        
        display_main_force_analysis_result(st.session_state.main_force_result)
        return

    # 0. 智能选股 (新增)
    with st.expander("🔍 智能选股 (从问财获取主力资金流向)", expanded=True):
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            days_ago = st.number_input("统计天数", min_value=1, value=30, help="统计最近多少天的主力资金流向")
        with col_s2:
            min_cap = st.number_input("最小市值(亿)", min_value=0, value=50)
        with col_s3:
            max_cap = st.number_input("最大市值(亿)", min_value=0, value=1000)
        with col_s4:
            top_n = st.number_input("选取前N名", min_value=1, value=5)
            
        if st.button("开始选股", key="btn_smart_select"):
            with st.spinner("正在获取主力资金数据并进行AI分析..."):
                use_case = DIContainer.create_analyze_main_force_use_case()
                analysis = use_case.execute(
                    days_ago=days_ago,
                    min_market_cap=min_cap,
                    max_market_cap=max_cap,
                    final_n=top_n
                )
                
                if analysis.success:
                    display_main_force_analysis_result(analysis)
                    
                    # 如果有推荐股票，自动填入输入框
                    if analysis.recommendations:
                        codes = ", ".join([_clean_stock_code(r.symbol) for r in analysis.recommendations])
                        st.session_state.last_main_force_input = codes
                        
                else:
                    st.error(f"选股分析失败: {analysis.error}")

    # 1. 输入股票代码
    st.subheader("1. 输入股票代码")
    st.markdown("请输入需要分析的股票代码，使用逗号分隔。例如：`600000, 600036, 000001`")
    
    default_stocks = "600000, 600036, 000001"
    if "last_main_force_input" in st.session_state:
        default_stocks = st.session_state.last_main_force_input
        
    stock_input = st.text_area("股票代码列表", value=default_stocks, height=100)
    
    # 2. 发送至主页分析
    st.markdown("---")
    if st.button("🚀 发送至主页批量分析", type="primary", width="stretch"):
        # 清理代码后缀
        cleaned_codes = []
        if stock_input:
            # 简单分割处理，支持逗号、换行
            raw_codes = stock_input.replace("\n", ",").replace("，", ",").split(",")
            cleaned_codes = [_clean_stock_code(c.strip()) for c in raw_codes if c.strip()]
        
        cleaned_input = ", ".join(cleaned_codes)
        
        st.session_state.last_main_force_input = stock_input
        st.session_state.batch_analysis_input_stocks = cleaned_input
        set_current_view(View.HOME)
        st.rerun()



def display_main_force_analysis_result(analysis: MainForceAnalysis):
    """显示主力选股分析结果"""
    st.markdown("### 🎯 分析结果概览")
    
    # 1. 摘要信息
    st.info(f"📊 筛选: {len(analysis.raw_stocks)} -> {len(analysis.filtered_stocks)} -> 推荐 {len(analysis.recommendations)} 只")
    
    # 2. 详细内容 Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "💰 资金流向", 
        "📊 行业分析", 
        "📈 基本面", 
        "🏆 推荐股票",
        "📋 候选列表",
        "📥 下载报告"
    ])
    
    with tab1:
        st.markdown("#### 资金流向分析")
        if analysis.fund_flow_analysis:
            st.markdown(analysis.fund_flow_analysis)
        else:
            st.warning("暂无资金流向分析")
            
    with tab2:
        st.markdown("#### 行业板块分析")
        if analysis.industry_analysis:
            st.markdown(analysis.industry_analysis)
        else:
            st.warning("暂无行业分析")
            
    with tab3:
        st.markdown("#### 基本面分析")
        if analysis.fundamental_analysis:
            st.markdown(analysis.fundamental_analysis)
        else:
            st.warning("暂无基本面分析")
            
    with tab4:
        st.markdown("#### 🏆 精选推荐")
        if analysis.recommendations:
            if st.button("🚀 发送所有推荐股票到主页批量分析", key="home_rec_live"):
                symbols = [_clean_stock_code(rec.symbol) for rec in analysis.recommendations]
                st.session_state.batch_analysis_input_stocks = ", ".join(symbols)
                set_current_view(View.HOME)
                st.rerun()

            for i, rec in enumerate(analysis.recommendations):
                with st.expander(f"第{i+1}名: {rec.symbol} {rec.name}", expanded=(i==0)):
                    st.markdown("##### 💡 核心推荐理由")
                    if isinstance(rec.reasons, list):
                        for reason in rec.reasons:
                            st.markdown(f"- {reason}")
                    else:
                        st.markdown(f"- {rec.reasons}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**建议仓位**: {rec.position}")
                    with col2:
                        st.markdown(f"**投资周期**: {rec.investment_period}")
                    with col3:
                        pass
                        
                    if rec.highlights:
                        st.info(f"**✨ 投资亮点**: {rec.highlights}")
                        
                    if rec.risks:
                        st.warning(f"**⚠️ 风险提示**: {rec.risks}")
                    
                    st.markdown("---")
                    with st.expander("查看详细数据"):
                        st.json(rec.stock_data)
        else:
            st.info("没有推荐股票")
            
    with tab5:
        st.markdown("#### 📋 候选股票列表 (Top 100)")
        if analysis.raw_stocks:
            # Sort by inflow
            sorted_stocks = sorted(analysis.raw_stocks, key=lambda x: x.main_fund_inflow or -float('inf'), reverse=True)[:100]
            
            data = []
            for s in sorted_stocks:
                data.append({
                    "代码": s.symbol,
                    "名称": s.name,
                    "行业": s.industry,
                    "涨跌幅%": s.range_change,
                    "主力净流入(万)": s.main_fund_inflow,
                    "市值(亿)": s.market_cap
                })
            st.dataframe(pd.DataFrame(data), width='stretch')
        else:
            st.info("没有候选股票数据")
            
    with tab6:
        display_report_download_section(analysis)

