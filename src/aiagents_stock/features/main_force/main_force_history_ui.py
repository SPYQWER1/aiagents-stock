import json

import pandas as pd
import streamlit as st

from aiagents_stock.container import DIContainer
from aiagents_stock.web.navigation import View, set_current_view


def display_selection_history():
    """显示主力选股历史记录"""
    
    # 返回按钮
    col_back, col_stats = st.columns([1, 4])
    with col_back:
        if st.button("← 返回主页"):
            st.session_state.main_force_view_history = False
            st.rerun()

    st.markdown("## 📚 选股历史记录中心")
    st.markdown("---")
    
    _display_selection_history()

def _display_selection_history():
    """显示主力选股（筛选+分析）的历史记录"""
    use_case = DIContainer.create_get_main_force_history_use_case()
    
    try:
        history_records = use_case.execute(limit=50)
        
        if not history_records:
             st.info("📝 暂无选股历史记录")
             return

        st.markdown(f"### 📋 最近 {len(history_records)} 条选股记录")
        
        for idx, record in enumerate(history_records):
            # Parse recommendations length
            try:
                recs = json.loads(record["recommendations"]) if isinstance(record["recommendations"], str) else record["recommendations"]
                rec_count = len(recs)
            except (json.JSONDecodeError, TypeError, ValueError):
                recs = []
                rec_count = 0
                
            with st.expander(
                f"🔍 {record['analysis_date']} | "
                f"获取{record['raw_stocks_count']}只 | "
                f"筛选{record['filtered_stocks_count']}只 | "
                f"推荐{rec_count}只 | "
                f"耗时{record['total_time']:.1f}秒",
                expanded=(idx == 0)
            ):
                 col1, col2, col3, col4 = st.columns(4)
                 with col1:
                     st.write(f"**分析时间**: {record['analysis_date']}")
                 with col2:
                     st.write(f"**获取股票**: {record['raw_stocks_count']}")
                 with col3:
                     st.write(f"**筛选通过**: {record['filtered_stocks_count']}")
                 with col4:
                     st.write(f"**最终推荐**: {rec_count}")
                     
                 # 推荐详情预览
                 if rec_count > 0:
                     st.markdown("#### 🏆 推荐列表")
                     rec_data = []
                     for r in recs:
                        # Handle both dict and object (if deserialized differently)
                        r_dict = r if isinstance(r, dict) else r.__dict__
                        reasons = r_dict.get("reasons", [])
                        
                        if isinstance(reasons, str):
                            first_reason = reasons
                        elif isinstance(reasons, list) and reasons:
                            first_reason = reasons[0]
                        else:
                            first_reason = "N/A"

                        rec_data.append({
                            "代码": r_dict.get("symbol", ""),
                            "名称": r_dict.get("name", ""),
                            "理由": str(first_reason)[:30] + "..."
                        })
                     st.dataframe(pd.DataFrame(rec_data), hide_index=True, width='stretch')
                 
                 # 操作按钮
                 col_del, col_load, col_home = st.columns([1, 1, 1.5])
                 
                 with col_del:
                     if st.button("🗑️ 删除此记录", key=f"del_sel_{record['id']}"):
                         if use_case.delete(record['id']):
                             st.success("✅ 删除成功")
                             st.rerun()
                         else:
                             st.error("❌ 删除失败")
                             
                 with col_load:
                     if st.button("🔄 加载查看详情", key=f"load_sel_{record['id']}"):
                         analysis = use_case.get_by_id(record['id'])
                         if analysis:
                             st.session_state.main_force_result = analysis
                             st.session_state.main_force_view_history = False
                             st.rerun()
                         else:
                             st.error("❌ 加载失败，记录可能不存在")

                 with col_home:
                     if st.button("🚀 发送到主页分析", key=f"home_sel_{record['id']}", help="将推荐股票发送到主页进行批量分析"):
                         symbols = []
                         for r in recs:
                             r_dict = r if isinstance(r, dict) else r.__dict__
                             if "symbol" in r_dict:
                                 symbols.append(r_dict["symbol"])
                         
                         if symbols:
                             # 清理后缀
                             cleaned_symbols = [s.split(".")[0] if "." in s else s for s in symbols]
                             st.session_state.batch_analysis_input_stocks = ", ".join(cleaned_symbols)
                             set_current_view(View.HOME)
                             st.rerun()
                         else:
                             st.warning("⚠️ 没有推荐股票可发送")

    except Exception as e:
        st.error(f"❌ 获取选股历史记录失败: {str(e)}")
