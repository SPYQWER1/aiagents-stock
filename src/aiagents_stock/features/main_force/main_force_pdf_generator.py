import base64
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from aiagents_stock.domain.main_force.model import MainForceAnalysis


def generate_main_force_markdown_report(analysis: MainForceAnalysis):
    """生成主力选股Markdown格式的分析报告"""

    # 获取当前时间
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

    # 获取分析参数
    params = analysis.params
    start_date = params.get("start_date", "N/A")
    min_cap = params.get("min_market_cap", 50)
    max_cap = params.get("max_market_cap", 5000)
    max_change = params.get("max_range_change", 50)

    markdown_content = f"""
# 主力选股AI分析报告

**生成时间**: {current_time}

---

## 📊 选股参数

| 项目 | 值 |
|------|-----|
| **起始日期** | {start_date} |
| **市值范围** | {min_cap}亿 - {max_cap}亿 |
| **最大涨跌幅** | {max_change}% |
| **初始数据量** | {len(analysis.raw_stocks)}只 |
| **筛选后数量** | {len(analysis.filtered_stocks)}只 |
| **最终推荐** | {len(analysis.recommendations)}只 |

---

## 🤖 AI分析师团队报告

"""

    # 添加资金流向分析
    if analysis.fund_flow_analysis:
        markdown_content += f"""
### 💰 资金流向分析师

{analysis.fund_flow_analysis}

---

"""

    # 添加行业板块分析
    if analysis.industry_analysis:
        markdown_content += f"""
### 📊 行业板块及市场热点分析师

{analysis.industry_analysis}

---

"""

    # 添加财务基本面分析
    if analysis.fundamental_analysis:
        markdown_content += f"""
### 📈 财务基本面分析师

{analysis.fundamental_analysis}

---

"""

    # 添加精选推荐
    markdown_content += """
## ⭐ 精选推荐股票

"""

    if analysis.recommendations:
        for rec in analysis.recommendations:
            # Construct reason text
            reason_text = rec.highlights if rec.highlights else ""
            if rec.reasons:
                reason_text += "\n\n" + "\n".join([f"- {r}" for r in rec.reasons])
            
            markdown_content += f"""
### 【第{rec.rank}名】{rec.symbol} - {rec.name}

**推荐理由**:
{reason_text}

**关键指标**:
"""
            if rec.stock_data:
                stock_data = rec.stock_data
                markdown_content += f"""
- **所属行业**: {stock_data.get('industry', 'N/A')}
- **市值**: {stock_data.get('market_cap', 'N/A')}
- **主力资金流向**: {stock_data.get('main_fund_inflow', 'N/A')}
- **区间涨跌幅**: {stock_data.get('range_change', 'N/A')}%
- **市盈率**: {stock_data.get('pe_ratio', 'N/A')}
- **市净率**: {stock_data.get('pb_ratio', 'N/A')}

"""

            if "scores" in rec.stock_data:
                scores = rec.stock_data["scores"]
                if scores:
                    markdown_content += "**能力评分**:\n"
                    for score_name, score_value in scores.items():
                        markdown_content += f"- {score_name}: {score_value}\n"
                    markdown_content += "\n"
            
            # Add Position and Period advice if available
            if hasattr(rec, 'position') and rec.position:
                markdown_content += f"**建议仓位**: {rec.position}\n\n"
            if hasattr(rec, 'investment_period') and rec.investment_period:
                markdown_content += f"**投资周期**: {rec.investment_period}\n\n"

            markdown_content += "---\n\n"
    else:
        markdown_content += "暂无推荐股票\n\n---\n\n"

    # 添加候选股票列表（前100名，按主力资金排序）
    # Use filtered stocks or raw stocks? Usually raw stocks is better for full view, 
    # but filtered stocks are the candidates. Let's use filtered_stocks if available, else raw_stocks.
    # Actually, the user wants "Candidate List", which usually implies those who passed filters.
    # But the old code used raw_stocks. Let's use raw_stocks but sorted.
    candidate_stocks = analysis.raw_stocks
    
    if candidate_stocks:
        markdown_content += """
## 📋 候选股票完整列表（按主力资金净流入排序）

"""
        # Sort by main_fund_inflow descending
        sorted_stocks = sorted(candidate_stocks, key=lambda x: x.main_fund_inflow or -float('inf'), reverse=True)[:100]
        
        markdown_content += "| 序号 | 股票代码 | 股票名称 | 行业 | 主力净流入(万) | 涨跌幅(%) | 市值(亿) | 市盈率 | 市净率 |\n"
        markdown_content += "|------|----------|----------|------|--------------|-----------|----------|--------|--------|\n"
        
        for idx, stock in enumerate(sorted_stocks, 1):
            row_data = [
                str(idx),
                str(stock.symbol),
                str(stock.name),
                str(stock.industry),
                f"{stock.main_fund_inflow:.2f}" if stock.main_fund_inflow is not None else "N/A",
                f"{stock.range_change:.2f}" if stock.range_change is not None else "N/A",
                f"{stock.market_cap:.2f}" if stock.market_cap is not None else "N/A",
                f"{stock.pe_ratio:.2f}" if stock.pe_ratio is not None else "N/A",
                f"{stock.pb_ratio:.2f}" if stock.pb_ratio is not None else "N/A"
            ]
            markdown_content += "| " + " | ".join(row_data) + " |\n"

        markdown_content += "\n"

    # 添加免责声明
    markdown_content += f"""
---

## 📝 免责声明

本报告由AI系统生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。请在做出投资决策前咨询专业的投资顾问。

---

*报告生成时间: {current_time}*  
*主力选股AI分析系统 v2.0*
"""

    return markdown_content


def generate_html_content(markdown_content):
    """将Markdown转换为HTML"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>主力选股AI分析报告</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
        }
        h3 {
            color: #2980b9;
            margin-top: 25px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        tr:hover {
            background-color: #f0f0f0;
        }
        .disclaimer {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 15px;
            margin-top: 30px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #7f8c8d;
            font-style: italic;
        }
        hr {
            border: none;
            height: 2px;
            background-color: #ecf0f1;
            margin: 20px 0;
        }
        strong {
            color: #2c3e50;
        }
        ul, ol {
            margin: 10px 0;
            padding-left: 30px;
        }
        li {
            margin: 5px 0;
        }
    </style>
</head>
<body>
    <div class="container">
"""

    # 简单的Markdown到HTML转换
    html_body = markdown_content
    html_body = html_body.replace("\n# ", "\n<h1>").replace("\n## ", "\n<h2>").replace("\n### ", "\n<h3>")
    html_body = html_body.replace("# ", "<h1>").replace("## ", "<h2>").replace("### ", "<h3>")
    html_body = html_body.replace("\n---\n", "\n<hr>\n")

    # 处理粗体文本
    html_body = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html_body)

    # 处理表格
    lines = html_body.split("\n")
    in_table = False
    processed_lines = []

    for line in lines:
        if "|" in line and not in_table and line.strip().startswith("|"):
            processed_lines.append("<table>")
            in_table = True
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            processed_lines.append("<tr>")
            for cell in cells:
                processed_lines.append(f"<th>{cell}</th>")
            processed_lines.append("</tr>")
        elif "|" in line and in_table:
            if "---" not in line:
                cells = [cell.strip() for cell in line.split("|")[1:-1]]
                processed_lines.append("<tr>")
                for cell in cells:
                    processed_lines.append(f"<td>{cell}</td>")
                processed_lines.append("</tr>")
        elif in_table and "|" not in line:
            processed_lines.append("</table>")
            in_table = False
            processed_lines.append(line)
        else:
            processed_lines.append(line)

    if in_table:
        processed_lines.append("</table>")

    html_body = "\n".join(processed_lines)

    # 处理列表
    html_body = re.sub(r"\n- (.*)", r"\n<li>\1</li>", html_body)
    html_body = re.sub(r"(<li>.*</li>)\n(?!<li>)", r"<ul>\1</ul>\n", html_body)
    html_body = re.sub(r"(<li>.*</li>\n)+", lambda m: "<ul>\n" + m.group(0) + "</ul>\n", html_body)

    # 处理换行
    html_body = html_body.replace("\n\n", "</p><p>")
    html_body = "<p>" + html_body + "</p>"

    html_content += html_body
    html_content += """
    </div>
</body>
</html>
"""

    return html_content


def create_download_link(content, filename, link_text):
    """创建下载链接"""
    b64 = base64.b64encode(content.encode()).decode()
    href = f'<a href="data:text/markdown;base64,{b64}" download="{filename}" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">{link_text}</a>'
    return href


def create_html_download_link(content, filename, link_text):
    """创建HTML下载链接"""
    b64 = base64.b64encode(content.encode("utf-8")).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}" style="display: inline-block; padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 5px;">{link_text}</a>'
    return href


def display_report_download_section(analysis: MainForceAnalysis):
    """显示报告下载区域"""

    st.markdown("---")
    st.markdown("### 📥 下载分析报告")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📄 Markdown格式")
        st.caption("适合编辑和进一步处理")

        # 生成Markdown报告
        markdown_content = generate_main_force_markdown_report(analysis)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_filename = f"主力选股分析报告_{timestamp}.md"

        # 创建下载链接
        md_link = create_download_link(markdown_content, md_filename, "📥 下载Markdown报告")
        st.markdown(md_link, unsafe_allow_html=True)

        # 显示预览
        with st.expander("👀 预览Markdown内容"):
            st.code(markdown_content[:2000] + "..." if len(markdown_content) > 2000 else markdown_content)

    with col2:
        st.markdown("#### 🌐 HTML格式")
        st.caption("可在浏览器中打开查看")

        # 生成HTML报告
        html_content = generate_html_content(markdown_content)

        # 生成文件名
        html_filename = f"主力选股分析报告_{timestamp}.html"

        # 创建下载链接
        html_link = create_html_download_link(html_content, html_filename, "📥 下载HTML报告")
        st.markdown(html_link, unsafe_allow_html=True)

        # 显示说明
        st.info("💡 HTML报告可以直接在浏览器中打开，格式美观易读")

    # 添加CSV下载（候选股票列表）
    if analysis.raw_stocks:
        st.markdown("---")
        st.markdown("#### 📊 候选股票数据")

        # 转换为DataFrame
        data = []
        for stock in analysis.raw_stocks:
            data.append({
                "股票代码": stock.symbol,
                "股票名称": stock.name,
                "所属行业": stock.industry,
                "总市值(亿)": stock.market_cap,
                "区间涨跌幅(%)": stock.range_change,
                "主力净流入(万)": stock.main_fund_inflow,
                "市盈率": stock.pe_ratio,
                "市净率": stock.pb_ratio
            })
        
        df = pd.DataFrame(data)
        
        # 按主力资金排序
        if "主力净流入(万)" in df.columns:
             df = df.sort_values(by="主力净流入(万)", ascending=False)

        # 导出为CSV
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        csv_filename = f"主力选股候选列表_{timestamp}.csv"

        st.download_button(
            label="📥 下载候选股票CSV", data=csv, file_name=csv_filename, mime="text/csv", width="content"
        )

# Alias for compatibility
generate_main_force_report = generate_main_force_markdown_report
