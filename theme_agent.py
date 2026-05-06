import google.genai as genai
from config import GEMINI_API_KEY
from news_agent import get_theme_news

def analyze_themes():
    analysis  = {}
    theme_news = get_theme_news()

    if not GEMINI_API_KEY:
        analysis["Config"] = {"signal": "⚠️", "summary": "No Gemini API key provided", "watch": "N/A"}
        return analysis

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        news_text = ""
        for theme, articles in theme_news.items():
            news_text += f"\n\n### THEME: {theme}\n"
            for a in articles:
                news_text += f"- {a.get('title', '')}: {a.get('description', '')}\n"

        if not news_text.strip():
            analysis["News"] = {"signal": "⚠️", "summary": "No news fetched from Marketaux", "watch": "N/A"}
            return analysis

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
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw_text = response.text
        print(f"Gemini responded with {len(raw_text)} chars")

        blocks = raw_text.split("---")
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
                        if "HOT"   in raw_sig: block_data["signal"] = "🔥 HOT"
                        elif "POS" in raw_sig: block_data["signal"] = "✅ POSITIVE"
                        elif "NEG" in raw_sig: block_data["signal"] = "🔴 NEGATIVE"
                        else:                   block_data["signal"] = "⚠️ NEUTRAL"
                    elif line.startswith("SUMMARY:"):
                        block_data["summary"] = line.replace("SUMMARY:", "").strip()
                    elif line.startswith("WATCH:"):
                        block_data["watch"]   = line.replace("WATCH:", "").strip()
                if theme_key:
                    analysis[theme_key] = block_data

    except Exception as e:
        print(f"Gemini error details: {type(e).__name__}: {e}")
        analysis["Error"] = {"signal": "⚠️", "summary": f"{type(e).__name__}: {str(e)[:80]}", "watch": "N/A"}

    return analysis
