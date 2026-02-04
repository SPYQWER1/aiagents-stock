"""
Streamlit 应用云端部署入口 (Entry point for Streamlit Cloud/Docker)

该文件主要用于 Streamlit Cloud 或其他云平台部署时的入口识别。
本地开发建议使用 `python run.py` 启动，包含完整的环境检查。
"""

import os
import sys
from pathlib import Path


def main():
    os.environ.setdefault("NODE_NO_WARNINGS", "1")

    src_path = Path(__file__).resolve().parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from aiagents_stock.web.app import main as web_main

    web_main()


if __name__ == "__main__":
    main()
