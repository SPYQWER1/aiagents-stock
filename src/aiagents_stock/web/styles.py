from __future__ import annotations

import streamlit as st

APP_CSS = """
<style>
    /* 全局样式 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        background-attachment: fixed;
    }

    .stApp {
        background: transparent;
    }

    /* 主容器 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        margin-top: 1rem;
    }

    /* 顶部导航栏 */
    .top-nav {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }

    .nav-title {
        font-size: 2rem;
        font-weight: 800;
        color: white;
        text-align: center;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        letter-spacing: 1px;
    }

    .nav-subtitle {
        text-align: center;
        color: rgba(255, 255, 255, 0.9);
        font-size: 0.95rem;
        margin-top: 0.5rem;
        font-weight: 300;
    }

    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
    }

    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: white;
        font-weight: 600;
        font-size: 1.1rem;
        padding: 0 2rem;
        border: none;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateY(-2px);
    }

    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #667eea !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    /* 侧边栏美化 */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        padding-top: 2rem;
    }

    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: white !important;
    }

    .css-1d391kg .stMarkdown, [data-testid="stSidebar"] .stMarkdown {
        color: rgba(255, 255, 255, 0.95) !important;
    }

    /* 分析师卡片 */
    .agent-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }

    .agent-card:hover {
        transform: translateX(5px);
    }

    /* 决策卡片 */
    .decision-card {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 2rem;
        border-radius: 15px;
        border: 3px solid #4caf50;
        margin: 1.5rem 0;
        box-shadow: 0 8px 30px rgba(76, 175, 80, 0.2);
    }

    /* 警告卡片 */
    .warning-card {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #ff9800;
        box-shadow: 0 4px 15px rgba(255, 152, 0, 0.2);
    }

    /* 指标卡片 */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border-top: 4px solid #667eea;
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
    }

    /* 按钮美化 */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
    }

    /* 输入框美化 */
    .stTextInput>div>div>input {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem;
        font-size: 1rem;
        transition: border-color 0.3s ease;
    }

    .stTextInput>div>div>input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* 进度条美化 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }

    /* 成功/错误/警告/信息消息框 */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }

    /* 图表容器 */
    .js-plotly-plot {
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }

    /* Expander美化 */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        font-weight: 600;
    }

    /* 数据框美化 */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    }

    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 响应式设计 */
    @media (max-width: 768px) {
        .nav-title {
            font-size: 1.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.9rem;
            padding: 0 1rem;
        }
    }
</style>
"""


def apply_global_styles() -> None:
    """注入全局 CSS 样式。"""

    st.markdown(APP_CSS, unsafe_allow_html=True)
