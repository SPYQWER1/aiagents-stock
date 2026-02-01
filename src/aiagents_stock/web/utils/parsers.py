def parse_stock_list(stock_input: str) -> list[str]:
    """解析批量股票代码输入。"""

    if not stock_input or not stock_input.strip():
        return []

    lines = stock_input.strip().split("\n")
    raw: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "," in line:
            raw.extend([code.strip() for code in line.split(",") if code.strip()])
        elif " " in line:
            raw.extend([code.strip() for code in line.split() if code.strip()])
        else:
            raw.append(line)

    seen: set[str] = set()
    unique: list[str] = []
    for code in raw:
        if code not in seen:
            seen.add(code)
            unique.append(code)
    return unique
