
"""yahoofinacescraping_commented_en.py
======================================

Python script generated from *yahoofinacescraping.ipynb* **with detailed English comments**.  
Core logic is unchanged; only syntax fixes (f‑string quotes) and removal of real API keys.

Important:
    • Store your real keys in a `.env` file or environment variables (see below).  
    • Install dependencies with: `pip install -r requirements.txt`

© 2024 – feel free to adapt.
"""


# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------
import os
from datetime import datetime
import textwrap

import pandas as pd
import yfinance as yf

# If you want to use Gemini or OpenAI,
# install the packages: `pip install google-generativeai openai`
import google.generativeai as genai
from openai import OpenAI  # currently unused but prepared for later


# ------------------------------------------------------------
# Example: fetch basic information about one ticker
# ------------------------------------------------------------
# Tip: always use descriptive variable names – here `apple` instead of `NVDA`
apple = yf.Ticker("AAPL")
apple_info = apple.info            # dict with all available fields
apple_earnings = apple.earnings_dates  # upcoming & past earnings dates


# ------------------------------------------------------------
# Helper function: latest news as a DataFrame
# ------------------------------------------------------------
def get_news(ticker: str) -> pd.DataFrame:
    """Return news articles for *ticker* as a DataFrame.

    Columns:
        • Ticker   – symbol (e.g. AAPL)  
        • Title    – headline  
        • Summary  – wrapped summary (50 characters per line)  
        • Date     – publication datetime
    """
    stock = yf.Ticker(ticker)
    raw_news = stock.news

    df_news = pd.DataFrame()

    for entry in raw_news:
        # Wrap the summary so console output stays readable
        summary_wrapped = textwrap.fill(entry["content"]["summary"], width=50)

        # Convert ISO timestamp to datetime
        pub_date = datetime.strptime(entry["content"]["pubDate"], "%Y-%m-%dT%H:%M:%SZ")

        new_row = pd.DataFrame(
            {
                "Ticker": ticker,
                "Title": entry["content"]["title"],
                "Summary": summary_wrapped,
                "Date": pub_date,
            },
            index=[0],
        )
        df_news = pd.concat([df_news, new_row], ignore_index=True)

    return df_news


# ------------------------------------------------------------
# Helper function: news as a formatted text block
# ------------------------------------------------------------
def get_info(ticker: str) -> str:
    """Format the news from *get_news* as plain text."""
    df = get_news(ticker)
    data = ""

    for i in range(len(df)):
        data += (
            f"News {i + 1} of {df['Date'][i]}:\n"
            f"Title: {df['Title'][i]}\n"
            f"Summary: {df['Summary'][i]}\n\n"
        )

    return data


# ------------------------------------------------------------
# Helper function: fundamentals & key metrics
# ------------------------------------------------------------
def get_add_infos(ticker: str) -> dict:
    """Return a dictionary with selected metrics for *ticker*."""
    stock_info = yf.Ticker(ticker).info

    return {
        "Industry": stock_info.get("industry", "N/A"),
        "Sector": stock_info.get("sector", "N/A"),
        "Business Summary": textwrap.fill(
            stock_info.get("longBusinessSummary", "N/A"), width=50
        ),
        "Market Cap": stock_info.get("marketCap", "N/A"),
        "52-Week Low": stock_info.get("fiftyTwoWeekLow", "N/A"),
        "52-Week High": stock_info.get("fiftyTwoWeekHigh", "N/A"),
        "Price-to-Sales": stock_info.get("priceToSalesTrailing12Months", "N/A"),
        "50-Day Average": stock_info.get("fiftyDayAverage", "N/A"),
        "200-Day Average": stock_info.get("twoHundredDayAverage", "N/A"),
        "Enterprise Value": stock_info.get("enterpriseValue", "N/A"),
        "Profit Margins": stock_info.get("profitMargins", "N/A"),
        "Shares Outstanding": stock_info.get("sharesOutstanding", "N/A"),
        "Shares Short": stock_info.get("sharesShort", "N/A"),
        "Book Value": stock_info.get("bookValue", "N/A"),
        "Price-to-Book": stock_info.get("priceToBook", "N/A"),
    }


# ------------------------------------------------------------
# Prompt generator for Gemini / OpenAI
# ------------------------------------------------------------
def get_prompt(ticker: str) -> str:
    """Create a detailed prompt for LLM analysis."""
    stock_data = get_add_infos(ticker)
    infos = get_info(ticker)

    prompt = f"""

    I am a short-term investor (day trading) assessing the potential of {ticker}.
    Please analyse the stock using the latest news and data.

    Fundamental data:
    {stock_data}

    News articles/posts:
    {infos}

    As a stock market expert, please provide ONLY a JSON answer:

    {{
        "Conclusion": "...",
        "Recommendation": "Buy/Sell/Neutral"
    }}
    """
    return prompt


# ------------------------------------------------------------
# Request analysis from LLM
# ------------------------------------------------------------
def get_analysis(ticker: str) -> str:
    """Send the prompt to Gemini 1.5 Flash and return the answer."""
    # NEVER hardcode your API keys – read them from environment variables
    gemini_key = os.getenv("GEMINI_API_KEY")  # set via .env or your shell
    if not gemini_key:
        raise EnvironmentError("Please set GEMINI_API_KEY as an environment variable")

    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(get_prompt(ticker))
    return response.text


# ------------------------------------------------------------
# Example run
# ------------------------------------------------------------
if __name__ == "__main__":
    result = get_analysis("BABA")  # Alibaba
    print(textwrap.fill(result, 50))
