"""
TDX API 测试
"""

import os

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

TDX_API_URL = os.getenv("TDX_BASE_URL", "http://localhost:8090/")


def _tdx_available() -> bool:
    try:
        response = requests.get(f"{TDX_API_URL}/api/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def _extract_kline_list(payload):
    if isinstance(payload, dict) and "data" in payload and payload.get("code") == 0:
        data_obj = payload.get("data") or {}
        if isinstance(data_obj, dict):
            return data_obj.get("List") or []
    if isinstance(payload, list):
        return payload
    return []


@pytest.mark.parametrize("code", ["SZ000001", "000001", "SH600000", "600000"])
def test_tdx_kline_endpoint(code: str):
    if not _tdx_available():
        pytest.skip("TDX API 不可用，跳过集成测试")

    response = requests.get(f"{TDX_API_URL}/api/kline", params={"code": code, "type": "day"}, timeout=10)
    assert response.status_code == 200

    payload = response.json()
    kline_list = _extract_kline_list(payload)
    assert isinstance(kline_list, list)
    assert kline_list
