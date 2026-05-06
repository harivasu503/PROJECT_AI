import google.generativeai as genai
from config import GEMINI_API_KEY
from news_agent import get_theme_news

genai.configure(api_key=GEMINI_API_KEY)

def analyze_themes():
    theme_news = get_theme_news()
    model      = genai.GenerativeModel("gemini-1.5-flash")
    analysis   = {}

    news_text = ""
    for theme, articles in theme_news.items():
        news_text += f"\n\n### THEME: {theme}\n"
        for a in articles:
            news_text += f"- {a.get('title', '')}: {a.get('description', '')}\n"

    prompt = f"""You are an expert Indian stock market analyst.

Below is today's news grouped by market themes. For each theme:
1. Rate its market strength: HOT / POSITIVE / NEUTRAL / NEGATIVE
2. Give a 2-line summary of what is happening
3. Mention 1-2 Indian stocks that could benefit (NSE tickers)

Keep each theme analysis under 60 words. Be direct and actionable.

NEWS DATA:
{news_text}

Format your response exactly like this for each theme:

THEME: [theme name]
SIGNAL: [HOT/POSITIVE/NEUTRAL/NEGATIVE]
SUMMARY: [2-line summary]
WATCH: [stock1, stock2]
---
"""

    try:
        response = model.generate_content(prompt)
        raw_text = response.text
        blocks   = raw_text.split("---")
        for block in blocks:
            if "THEME:" in block:
                lines      = block.strip().split("\n")
                theme_key  = ""
                block_data = {}
                for line in lines:
                    if line.startswith("THEME:"):
                        theme_key = line.replace("THEME:", "").strip()
                    elif line.startswith("SIGNAL:"):
                        raw_sig = line.replace("SIGNAL:", "").strip().upper()
                        if "HOT"      in raw_sig: block_data["signal"] = "🔥 HOT"
                        elif "POS"    in raw_sig: block_data["signal"] = "✅ POSITIVE"
                        elif "NEG"    in raw_sig: block_data["signal"] = "🔴 NEGATIVE"
                        else:                      block_data["signal"] = "⚠️ NEUTRAL"
                    elif line.startswith("SUMMARY:"):
                        block_data["summary"] = line.replace("SUMMARY:", "").strip()
                    elif line.startswith("WATCH:"):
                        block_data["watch"]   = line.replace("WATCH:", "").strip()
                if theme_key:
                    analysis[theme_key] = block_data
    except Exception as e:
        analysis["Error"] = {"signal": "⚠️", "summary": str(e), "watch": "N/A"}

    return analysis
