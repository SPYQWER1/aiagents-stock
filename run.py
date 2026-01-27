#!/usr/bin/env python3
"""
AI股票分析系统启动脚本
运行命令: python run.py
"""

import os
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path


def check_requirements():
    """检查必要的依赖是否安装"""
    required_modules = ["akshare", "openai", "pandas", "plotly", "streamlit", "yfinance"]
    missing_modules = [name for name in required_modules if find_spec(name) is None]

    if missing_modules:
        print(f"❌ 缺少依赖包: {', '.join(missing_modules)}")
        print("请运行: pip install -r requirements.txt")
        return False

    print("✅ 所有依赖包已安装")
    return True


def check_config():
    """检查配置文件"""
    try:
        src_path = Path(__file__).resolve().parent / "src"
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        from aiagents_stock.core import config

        if not config.DEEPSEEK_API_KEY:
            print("⚠️  警告: DeepSeek API Key 未配置")
            print("请在config.py中设置 DEEPSEEK_API_KEY")
            return False
        print("✅ 配置文件检查通过")
        return True
    except ImportError:
        print("❌ 配置文件config.py不存在")
        return False


def main():
    """主函数"""
    print("🚀 启动AI股票分析系统...")
    print("=" * 50)

    # 检查依赖
    if not check_requirements():
        return

    # 检查配置
    check_config()

    # 启动Streamlit应用
    print("🌐 正在启动Web界面...")
    print("📝 访问地址: http://localhost:8503")
    print("⏹️  按 Ctrl+C 停止服务")
    print("=" * 50)

    try:
        os.environ.setdefault("NODE_NO_WARNINGS", "1")
        env = os.environ.copy()
        env.setdefault("NODE_NO_WARNINGS", "1")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.port",
                "8503",
                "--server.address",
                "127.0.0.1",
            ],
            env=env,
        )
    except KeyboardInterrupt:
        print("\n👋 感谢使用AI股票分析系统！")


if __name__ == "__main__":
    main()
