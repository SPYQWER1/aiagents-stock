from __future__ import annotations

import re
from typing import Any

_FLOAT_RE = re.compile(r"\d+\.?\d*")


def _clean_numeric_text(value: Any) -> str:
    """清理包含货币符号/单位的数字文本。"""

    return str(value).replace("¥", "").replace("元", "").replace("$", "").strip()


def extract_first_float(value: Any) -> float | None:
    """从字符串中提取第一个浮点数。"""

    text = _clean_numeric_text(value)
    matches = _FLOAT_RE.findall(text)
    if not matches:
        return None
    try:
        return float(matches[0])
    except Exception:
        return None


def extract_float_range(value: Any) -> tuple[float | None, float | None]:
    """从字符串中提取两个浮点数作为区间。"""

    text = _clean_numeric_text(value)
    matches = _FLOAT_RE.findall(text)
    if len(matches) >= 2:
        try:
            return float(matches[0]), float(matches[1])
        except Exception:
            return None, None

    for sep in ("-", "~", "至", "到"):
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) == 2:
                left = extract_first_float(parts[0])
                right = extract_first_float(parts[1])
                return left, right

    return None, None
