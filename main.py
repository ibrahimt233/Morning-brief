import os
import requests
import yfinance as yf
from google import genai

# ---- Edit this list to your own watchlist ----
WATCHLIST = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "TSLA"]

# Tried in order; the first one that works is used.
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


def get_market_data():
    lines = []
    for symbol in WATCHLIST:
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="5d")
            if len(hist) < 2:
                continue
            last, prev = hist["Close"].iloc[-1], hist["Close"].iloc[-2]
            change = (last - prev) / prev * 100
            week = (last - hist["Close"].iloc[0]) / hist["Close"].iloc[0] * 100

            headlines = []
            for item in (t.news or [])[:3]:
                title = item.get("title") or item.get("content", {}).get("title")
                if title:
                    headlines.append(title)

            lines.append(
                f"{symbol}: ${last:.2f} | 1d {change:+.2f}% | 5d {week:+.2f}% | "
                f"News: {'; '.join(headlines) or 'none'}"
            )
        except Exception as e:
            lines.append(f"{symbol}: data unavailable ({e})")
    return "\n".join(lines)


def summarize(data):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""Here is this morning's market data for my watchlist:

{data}

Write a short morning brief (under 250 words) for a beginner investor:
1. Biggest movers and the likely reason, based only on the data above.
2. Which 2-3 stocks look most interesting to research further, and why.
3. Key risks or things to watch today.

Do not give buy/sell orders or price predictions. Be clear about uncertainty.
Plain text only, no markdown."""

    for model in MODELS:
        try:
            return client.models.generate_content(model=model, contents=prompt).text
        except Exception as e:
            print(f"{model} failed: {e}")
    raise RuntimeError("All models failed")


def send_telegram(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4000]},
        timeout=30,
    )
    r.raise_for_status()


if __name__ == "__main__":
    data = get_market_data()
    brief = summarize(data)
    send_telegram("Morning brief\n\n" + brief + "\n\nNot financial advice.")
