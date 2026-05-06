import yfinance as yf
from config import PORTFOLIO

def get_portfolio_data():
    results = []
    for ticker, info in PORTFOLIO.items():
        try:
            stock = yf.Ticker(ticker)
            hist  = stock.history(period="2d")
            fast  = stock.fast_info

            current_price = round(hist['Close'].iloc[-1], 2)
            prev_price    = round(hist['Close'].iloc[-2], 2)
            day_change    = round(((current_price - prev_price) / prev_price) * 100, 2)

            buy_price  = info['buy_price']
            pnl_pct    = round(((current_price - buy_price) / buy_price) * 100, 2)
            pnl_value  = round((current_price - buy_price) * info['qty'], 2)

            try:
                week52_high = round(fast.year_high, 2)
                week52_low  = round(fast.year_low,  2)
            except:
                week52_high = "N/A"
                week52_low  = "N/A"

            results.append({
                "name":          info['name'],
                "ticker":        ticker,
                "current_price": current_price,
                "day_change":    day_change,
                "buy_price":     buy_price,
                "qty":           info['qty'],
                "pnl_pct":       pnl_pct,
                "pnl_value":     pnl_value,
                "week52_high":   week52_high,
                "week52_low":    week52_low,
            })
        except Exception as e:
            results.append({"name": info['name'], "ticker": ticker, "error": str(e)})
    return results
