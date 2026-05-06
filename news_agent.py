import requests
import yfinance as yf
from config import MARKETAUX_API_KEY, THEMES

def get_theme_news():
    base_url   = "https://api.marketaux.com/v1/news/all"
    theme_news = {}
    for theme in THEMES:
        try:
            params = {
                "api_token": MARKETAUX_API_KEY,
                "search":    theme,
                "language":  "en",
                "limit":     3,
                "sort":      "published_desc",
            }
            response = requests.get(base_url, params=params, timeout=10)
            data     = response.json()
            articles = []
            if "data" in data:
                for article in data["data"]:
                    sentiment = 0
                    if article.get("entities"):
                        sentiment = article["entities"][0].get("sentiment_score", 0)
                    articles.append({
                        "title":       article.get("title", ""),
                        "description": article.get("description", "")[:200],
                        "url":         article.get("url", ""),
                        "published":   article.get("published_at", ""),
                        "sentiment":   sentiment,
                    })
            theme_news[theme] = articles
        except Exception as e:
            theme_news[theme] = [{"title": f"Error: {e}"}]
    return theme_news


def get_stock_news(tickers: list):
    stock_news = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            news  = stock.news[:3]
            stock_news[ticker] = [
                {
                    "title": item.get("content", {}).get("title", ""),
                    "url":   item.get("content", {}).get("canonicalUrl", {}).get("url", "")
                }
                for item in news
            ]
        except:
            stock_news[ticker] = []
    return stock_news
