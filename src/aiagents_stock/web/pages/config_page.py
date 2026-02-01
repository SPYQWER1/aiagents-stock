from __future__ import annotations

import streamlit as st

from aiagents_stock.core.config_manager import config_manager
from aiagents_stock.web.navigation import View, set_current_view


def _mask_secret(value: str) -> str:
    """对敏感字符串做脱敏显示（用于 UI 展示）。"""

    if not value:
        return ""
    if len(value) <= 12:
        return "***"
    return value[:6] + "*" * (len(value) - 10) + value[-4:]


def render_config_page() -> None:
    """渲染环境配置管理页面。"""

    st.subheader("⚙️ 环境配置管理")
    st.markdown(
        """
    <div class="agent-card">
        <p>在这里可以配置系统的环境变量，包括API密钥、数据源配置、量化交易配置等。</p>
        <p><strong>注意：</strong>配置修改后需要重启应用才能在所有后台模块中完全生效。</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    config_info = config_manager.get_config_info()
    if "temp_config" not in st.session_state:
        st.session_state.temp_config = {key: info["value"] for key, info in config_info.items()}

    tab_basic, tab_data, tab_trade, tab_notify = st.tabs(
        ["📝 基本配置", "📊 数据源配置", "🤖 量化交易配置", "📢 通知配置"]
    )

    with tab_basic:
        st.markdown("### DeepSeek API配置")
        api_key_info = config_info["DEEPSEEK_API_KEY"]
        base_url_info = config_info["DEEPSEEK_BASE_URL"]

        current_api_key = st.session_state.temp_config.get("DEEPSEEK_API_KEY", "")
        new_api_key = st.text_input(
            f"🔑 {api_key_info['description']} {'*' if api_key_info['required'] else ''}",
            value=current_api_key,
            type="password",
            help="从 DeepSeek 控制台获取 API Key",
            key="input_deepseek_api_key",
        )
        st.session_state.temp_config["DEEPSEEK_API_KEY"] = new_api_key
        if new_api_key:
            st.success(f"✅ API密钥已设置: {_mask_secret(new_api_key)}")
        else:
            st.warning("⚠️ 未设置API密钥，系统无法使用AI分析功能")

        st.markdown("---")
        current_base_url = st.session_state.temp_config.get("DEEPSEEK_BASE_URL", "")
        new_base_url = st.text_input(
            f"🌐 {base_url_info['description']}",
            value=current_base_url,
            help="一般无需修改，保持默认即可",
            key="input_deepseek_base_url",
        )
        st.session_state.temp_config["DEEPSEEK_BASE_URL"] = new_base_url

    with tab_data:
        st.markdown("### Tushare 数据源（可选）")
        ts_info = config_info["TUSHARE_TOKEN"]
        current_token = st.session_state.temp_config.get("TUSHARE_TOKEN", "")
        new_token = st.text_input(
            f"🔑 {ts_info['description']}",
            value=current_token,
            type="password",
            help="仅在需要 Tushare 作为备用数据源时配置",
            key="input_tushare_token",
        )
        st.session_state.temp_config["TUSHARE_TOKEN"] = new_token

    with tab_trade:
        st.markdown("### MiniQMT 量化交易（可选）")
        enabled = st.session_state.temp_config.get("MINIQMT_ENABLED", "false")
        mini_enabled = st.checkbox("启用 MiniQMT", value=str(enabled).lower() == "true", key="miniqmt_enabled")
        st.session_state.temp_config["MINIQMT_ENABLED"] = "true" if mini_enabled else "false"

        st.session_state.temp_config["MINIQMT_ACCOUNT_ID"] = st.text_input(
            "账户ID",
            value=st.session_state.temp_config.get("MINIQMT_ACCOUNT_ID", ""),
            key="miniqmt_account_id",
        )
        st.session_state.temp_config["MINIQMT_HOST"] = st.text_input(
            "服务器地址",
            value=st.session_state.temp_config.get("MINIQMT_HOST", "127.0.0.1"),
            key="miniqmt_host",
        )
        st.session_state.temp_config["MINIQMT_PORT"] = st.text_input(
            "服务器端口",
            value=st.session_state.temp_config.get("MINIQMT_PORT", "58610"),
            key="miniqmt_port",
        )

    with tab_notify:
        st.markdown("### 邮件通知（可选）")
        email_enabled = st.checkbox(
            "启用邮件通知",
            value=str(st.session_state.temp_config.get("EMAIL_ENABLED", "false")).lower() == "true",
            key="email_enabled",
        )
        st.session_state.temp_config["EMAIL_ENABLED"] = "true" if email_enabled else "false"

        st.session_state.temp_config["SMTP_SERVER"] = st.text_input(
            "SMTP服务器",
            value=st.session_state.temp_config.get("SMTP_SERVER", ""),
            key="smtp_server",
        )
        st.session_state.temp_config["SMTP_PORT"] = st.text_input(
            "SMTP端口",
            value=st.session_state.temp_config.get("SMTP_PORT", "587"),
            key="smtp_port",
        )
        st.session_state.temp_config["EMAIL_FROM"] = st.text_input(
            "发件人邮箱",
            value=st.session_state.temp_config.get("EMAIL_FROM", ""),
            key="email_from",
        )
        st.session_state.temp_config["EMAIL_PASSWORD"] = st.text_input(
            "邮箱授权码",
            value=st.session_state.temp_config.get("EMAIL_PASSWORD", ""),
            type="password",
            key="email_password",
        )
        st.session_state.temp_config["EMAIL_TO"] = st.text_input(
            "收件人邮箱",
            value=st.session_state.temp_config.get("EMAIL_TO", ""),
            key="email_to",
        )

        st.markdown("---")
        st.markdown("### Webhook 通知（可选）")
        webhook_enabled = st.checkbox(
            "启用 Webhook 通知",
            value=str(st.session_state.temp_config.get("WEBHOOK_ENABLED", "false")).lower() == "true",
            key="webhook_enabled",
        )
        st.session_state.temp_config["WEBHOOK_ENABLED"] = "true" if webhook_enabled else "false"

        st.session_state.temp_config["WEBHOOK_TYPE"] = st.selectbox(
            "Webhook类型",
            ["dingtalk", "feishu"],
            index=["dingtalk", "feishu"].index(st.session_state.temp_config.get("WEBHOOK_TYPE", "dingtalk")),
            key="webhook_type",
        )
        st.session_state.temp_config["WEBHOOK_URL"] = st.text_input(
            "Webhook地址",
            value=st.session_state.temp_config.get("WEBHOOK_URL", ""),
            key="webhook_url",
        )
        st.session_state.temp_config["WEBHOOK_KEYWORD"] = st.text_input(
            "Webhook关键词（钉钉安全验证）",
            value=st.session_state.temp_config.get("WEBHOOK_KEYWORD", "aiagents通知"),
            key="webhook_keyword",
        )

    st.markdown("---")
    col1, col2, col3, _ = st.columns([1, 1, 1, 2])

    with col1:
        if st.button("💾 保存配置", type="primary", width="stretch"):
            is_valid, message = config_manager.validate_config(st.session_state.temp_config)
            if not is_valid:
                st.error(f"❌ 配置验证失败: {message}")
            elif config_manager.write_env(st.session_state.temp_config):
                st.success("✅ 配置已保存到 .env 文件")
                try:
                    config_manager.reload_config()
                except Exception as exc:
                    st.warning(f"⚠️ 配置重新加载失败: {exc}")
                st.info("ℹ️ 建议重启应用以确保所有模块读取到最新配置")
                st.rerun()
            else:
                st.error("❌ 保存配置失败")

    with col2:
        if st.button("🔄 重置", width="stretch"):
            st.session_state.temp_config = {key: info["value"] for key, info in config_info.items()}
            st.success("✅ 已重置为当前配置")
            st.rerun()

    with col3:
        if st.button("⬅️ 返回", width="stretch"):
            if "temp_config" in st.session_state:
                del st.session_state.temp_config
            set_current_view(View.HOME)
            st.rerun()

    st.markdown("---")
    with st.expander("📄 查看当前 .env 文件内容（默认脱敏）"):
        reveal = st.checkbox("显示明文（高风险）", value=False)
        current = config_manager.read_env()

        def show(k: str) -> str:
            v = current.get(k, "")
            if reveal:
                return v
            if k in {"DEEPSEEK_API_KEY", "TUSHARE_TOKEN", "EMAIL_PASSWORD", "WEBHOOK_URL"}:
                return _mask_secret(v)
            return v

        env_text = "\n".join(
            [
                "# AI股票分析系统环境配置",
                "# 由系统自动生成和管理",
                "",
                "# ========== DeepSeek API配置 ==========",
                f'DEEPSEEK_API_KEY="{show("DEEPSEEK_API_KEY")}"',
                f'DEEPSEEK_BASE_URL="{show("DEEPSEEK_BASE_URL")}"',
                "",
                "# ========== Tushare数据接口（可选）==========",
                f'TUSHARE_TOKEN="{show("TUSHARE_TOKEN")}"',
                "",
                "# ========== MiniQMT量化交易配置（可选）==========",
                f'MINIQMT_ENABLED="{show("MINIQMT_ENABLED")}"',
                f'MINIQMT_ACCOUNT_ID="{show("MINIQMT_ACCOUNT_ID")}"',
                f'MINIQMT_HOST="{show("MINIQMT_HOST")}"',
                f'MINIQMT_PORT="{show("MINIQMT_PORT")}"',
                "",
                "# ========== 邮件通知配置（可选）==========",
                f'EMAIL_ENABLED="{show("EMAIL_ENABLED")}"',
                f'SMTP_SERVER="{show("SMTP_SERVER")}"',
                f'SMTP_PORT="{show("SMTP_PORT")}"',
                f'EMAIL_FROM="{show("EMAIL_FROM")}"',
                f'EMAIL_PASSWORD="{show("EMAIL_PASSWORD")}"',
                f'EMAIL_TO="{show("EMAIL_TO")}"',
                "",
                "# ========== Webhook通知配置（可选）==========",
                f'WEBHOOK_ENABLED="{show("WEBHOOK_ENABLED")}"',
                f'WEBHOOK_TYPE="{show("WEBHOOK_TYPE")}"',
                f'WEBHOOK_URL="{show("WEBHOOK_URL")}"',
                f'WEBHOOK_KEYWORD="{show("WEBHOOK_KEYWORD")}"',
            ]
        )
        st.code(env_text, language="bash")
