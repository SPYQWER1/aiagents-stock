from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

SESSION_ANALYSIS_KEYS: tuple[str, ...] = (
    "analysis_completed",
    "stock_info",
    "agents_results",
    "discussion_result",
    "final_decision",
    "just_completed",
)

SESSION_BATCH_KEYS: tuple[str, ...] = (
    "batch_analysis_results",
    "batch_analysis_mode",
)


def delete_session_keys(keys: Iterable[str]) -> None:
    """安全删除会话状态中的指定键。"""

    for key in keys:
        if key in st.session_state:
            del st.session_state[key]


def reset_single_analysis_state() -> None:
    """清除单股分析的结果状态。"""

    delete_session_keys(SESSION_ANALYSIS_KEYS)


def reset_batch_analysis_state() -> None:
    """清除批量分析的结果状态。"""

    delete_session_keys(SESSION_BATCH_KEYS)


def reset_all_analysis_state() -> None:
    """清除所有分析结果状态（单股 + 批量）。"""

    reset_single_analysis_state()
    reset_batch_analysis_state()
