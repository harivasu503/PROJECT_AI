import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL
from datetime import datetime

def send_daily_report(portfolio_data, theme_analysis, stock_news):
    date_str = datetime.now().strftime("%A, %d %B %Y")

    # ---- PORTFOLIO TABLE ----
    portfolio_html = ""
    total_pnl = 0
    for s in portfolio_data:
        if "error" in s:
            portfolio_html += f"<tr><td>{s['name']}</td><td colspan='7' style='color:red'>Error: {s['error']}</td></tr>"
            continue
        day_color  = "#27ae60" if s['day_change'] >= 0 else "#e74c3c"
        pnl_color  = "#27ae60" if s['pnl_value']  >= 0 else "#e74c3c"
        day_arrow  = "&#9650;" if s['day_change'] >= 0 else "&#9660;"
        pnl_arrow  = "&#9650;" if s['pnl_value']  >= 0 else "&#9660;"
        total_pnl += s['pnl_value']
        portfolio_html += f"""
        <tr style='border-bottom:1px solid #eee'>
            <td><b>{s['name']}</b><br><small style='color:#888'>{s['ticker']}</small></td>
            <td align='center'>&#8377;{s['current_price']}</td>
            <td align='center' style='color:{day_color}'>{day_arrow} {s['day_change']}%</td>
            <td align='center'>&#8377;{s['buy_price']}</td>
            <td align='center'>{s['qty']}</td>
            <td align='center' style='color:{pnl_color}'>{pnl_arrow} {s['pnl_pct']}%</td>
            <td align='center' style='color:{pnl_color}'><b>&#8377;{s['pnl_value']:,.0f}</b></td>
            <td align='center'><small>{s['week52_low']} / {s['week52_high']}</small></td>
        </tr>"""
    total_color = "#27ae60" if total_pnl >= 0 else "#e74c3c"

    # ---- THEMES SECTION ----
    themes_html = ""
    for theme, data in theme_analysis.items():
        signal  = data.get("signal",  "")
        summary = data.get("summary", "")
        watch   = data.get("watch",   "")
        themes_html += f"""
        <div style='background:#f8f9fa;border-left:4px solid #3498db;
                    padding:12px;margin:8px 0;border-radius:4px'>
            <b>{signal} {theme.upper()}</b><br>
            <span style='color:#555'>{summary}</span><br>
            <small style='color:#3498db'>Watch: <b>{watch}</b></small>
        </div>"""

    # ---- STOCK NEWS SECTION ----
    news_html = ""
    for ticker, articles in stock_news.items():
        if articles:
            news_html += f"<p><b>{ticker}</b></p><ul>"
            for a in articles:
                title = a.get('title', '')
                url   = a.get('url', '#')
                if title:
                    news_html += f"<li><a href='{url}' style='color:#2980b9'>{title}</a></li>"
            news_html += "</ul>"

    # ---- FULL EMAIL HTML ----
    html = f"""
    <html><body style='font-family:Arial,sans-serif;max-width:950px;margin:auto;color:#333'>
    <div style='background:linear-gradient(135deg,#1a1a2e,#16213e);
                color:white;padding:25px;border-radius:10px;margin-bottom:20px'>
        <h1 style='margin:0'>Daily Market Agent Report</h1>
        <p style='margin:5px 0 0;opacity:0.8'>{date_str} | Powered by yfinance + Marketaux + Gemini AI</p>
    </div>
    <div style='background:white;border:1px solid #e0e0e0;border-radius:8px;padding:20px;margin-bottom:20px'>
        <h2 style='color:#1a1a2e;border-bottom:2px solid #3498db;padding-bottom:8px'>My Portfolio Update</h2>
        <table width='100%' cellpadding='8' cellspacing='0' style='border-collapse:collapse;font-size:13px'>
            <thead>
                <tr style='background:#1a1a2e;color:white'>
                    <th align='left'>Stock</th>
                    <th>CMP (&#8377;)</th>
                    <th>Day Change</th>
                    <th>Buy Price</th>
                    <th>Qty</th>
                    <th>P&amp;L %</th>
                    <th>P&amp;L (&#8377;)</th>
                    <th>52W Low / High</th>
                </tr>
            </thead>
            <tbody>{portfolio_html}</tbody>
            <tfoot>
                <tr style='background:#f0f0f0;font-weight:bold'>
                    <td colspan='6' align='right'>Total Portfolio P&amp;L:</td>
                    <td style='color:{total_color}'>&#8377;{total_pnl:,.0f}</td>
                    <td></td>
                </tr>
            </tfoot>
        </table>
    </div>
    <div style='background:white;border:1px solid #e0e0e0;border-radius:8px;padding:20px;margin-bottom:20px'>
        <h2 style='color:#1a1a2e;border-bottom:2px solid #e67e22;padding-bottom:8px'>Hot Market Themes Today (AI Analysis)</h2>
        {themes_html}
    </div>
    <div style='background:white;border:1px solid #e0e0e0;border-radius:8px;padding:20px;margin-bottom:20px'>
        <h2 style='color:#1a1a2e;border-bottom:2px solid #27ae60;padding-bottom:8px'>Latest News - My Portfolio Stocks</h2>
        {news_html}
    </div>
    <div style='text-align:center;color:#aaa;font-size:11px;padding:15px'>
        Generated by Your Free AI Stock Agent | &#8377;0 Cost
    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Daily Market Report - {date_str}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
    print(f"Email sent to {RECEIVER_EMAIL}")
