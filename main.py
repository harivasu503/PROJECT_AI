import os
from stock_data  import get_portfolio_data
from theme_agent import analyze_themes
from news_agent  import get_stock_news
from email_agent import send_daily_report
from config      import PORTFOLIO, MARKETAUX_API_KEY, GEMINI_API_KEY, SENDER_EMAIL
import traceback

def validate_config():
    missing = []
    if not MARKETAUX_API_KEY: missing.append("MARKETAUX_API_KEY")
    if not GEMINI_API_KEY:    missing.append("GEMINI_API_KEY")
    if not SENDER_EMAIL:      missing.append("SENDER_EMAIL")
    if missing:
        raise ValueError(f"Missing required secrets: {', '.join(missing)}")

def run_agent():
    print("=" * 55)
    print("   DAILY STOCK AGENT - STARTING RUN")
    print("=" * 55)

    validate_config()

    print("\n[1/4] Fetching portfolio prices via yfinance...")
    portfolio_data = get_portfolio_data()
    for s in portfolio_data:
        if "error" not in s:
            arrow = "UP" if s['day_change'] >= 0 else "DOWN"
            print(f"   {s['name']:<25} Rs{s['current_price']:>8}  {arrow} {abs(s['day_change'])}%")

    print("\n[2/4] Analyzing market themes with Gemini AI...")
    theme_analysis = analyze_themes()
    for theme, data in theme_analysis.items():
        print(f"   {data.get('signal','?')} {theme[:45]}")

    print("\n[3/4] Fetching latest news for portfolio stocks...")
    tickers    = list(PORTFOLIO.keys())
    stock_news = get_stock_news(tickers)
    for ticker, articles in stock_news.items():
        print(f"   {ticker}: {len(articles)} articles fetched")

    print("\n[4/4] Composing and sending email report...")
    send_daily_report(portfolio_data, theme_analysis, stock_news)

    print("\n" + "=" * 55)
    print("   AGENT RUN COMPLETE - EMAIL SENT!")
    print("=" * 55)

if __name__ == "__main__":
    try:
        run_agent()
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        exit(1)
