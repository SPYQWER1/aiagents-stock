"""
Streamlit 应用入口，供本地和 Docker 部署统一使用。
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
