"""
a==========

Console-oriented application that orchestrates two helper modules:

* ``getstock_earning_calender.py`` – retrieves upcoming earnings dates.
* ``yahoofinacescraping_stock_resume.py`` – pulls fundamentals & recent news,
  then lets a Large Language Model create a human‑readable summary.

Workflow
--------
1. **Reddit ingestion**  
   For a curated list of subreddits the script fetches fresh posts, downloads
   every top‑level comment (plus nested replies for smaller threads) and stores
   them as plain ``.txt`` files in *./Comments/Short/* or *./Comments/Long/*,
   depending on the comment count.

2. **Sentiment extraction**  
   Each ``.txt`` file is sent to an LLM (e.g. Gemini 1.5 Flash) which returns a
   JSON document summarising bullish / bearish sentiment and counts of option
   mentions (calls / puts).

3. **Aggregation**  
   Individual JSON payloads are merged into *./Comments/JSON/Data.json* so the
   overall sentiment per ticker can be queried later by other tools.

"""

import os
import json
import asyncio
import nest_asyncio
from typing import List

import pandas as pd
import requests
import asyncpraw

from dotenv import load_dotenv
load_dotenv()  # reads .env in current working dir
# ---------------------------------------------------------------------------
# Helper – fetch newest posts for one subreddit
# ---------------------------------------------------------------------------
def get_data(sub: str, headers: dict, params: dict) -> pd.DataFrame:
    """Return a DataFrame with the latest posts from *sub*. """
    res = requests.get(f'https://oauth.reddit.com/r/{sub}/new',
                       headers=headers, params=params)
    posts = res.json()['data']['children']

    rows = []
    for post in posts:
        pdata = post['data']
        rows.append(
            {
                "Subreddit": pdata['subreddit'],
                "Title": pdata['title'],
                "Selftext": pdata['selftext'],
                "Id": pdata['id'],
                "Comments": pdata['num_comments'],
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Async helpers – save comments to disk
# ---------------------------------------------------------------------------
async def fetch_reddit_comments_long(post_id: str, client_key: str, secret_key: str):
    """Save top‑level comments only into ./Comments/Long/. """
    reddit = asyncpraw.Reddit(client_id=client_key,
                              client_secret=secret_key,
                              user_agent='MyAPI/0.0.1')
    submission = await reddit.submission(id=post_id)

    save_path = "./Comments/Long/"
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, f"reddit_comments_{post_id}.txt")

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(f"Post Title: {submission.title}\n")
        file.write(f"Post Text: {submission.selftext}\n\nComments:\n")

        i = 1
        for top_level_comment in submission.comments:
            if isinstance(top_level_comment, asyncpraw.models.Comment):
                file.write(f"User_{i}: {top_level_comment.body}\n")
                i += 1


async def fetch_reddit_comments(post_id: str, client_key: str, secret_key: str):
    """Save all comments & replies into ./Comments/Short/. """
    async with asyncpraw.Reddit(client_id=client_key,
                                client_secret=secret_key,
                                user_agent='MyAPI/0.0.1') as reddit:
        submission = await reddit.submission(id=post_id)
        await submission.comments.replace_more(limit=None)

        save_path = "./Comments/Short/"
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, f"reddit_comments_{post_id}.txt")

        async def process_comment(comment, fh, level=1):
            indent = "    " * level
            fh.write(f"{indent}Reply: {comment.author}: {comment.body}\n")
            tasks = [process_comment(rep, fh, level + 1) for rep in comment.replies]
            await asyncio.gather(*tasks)

        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(f"Post Title: {submission.title}\n")
            fh.write(f"Post Text: {submission.selftext}\n\nComments:\n")

            tasks = []
            i = 1
            for top_comment in submission.comments:
                fh.write(f"User_{i}: {top_comment.body}\n")
                i += 1
                tasks.append(process_comment(top_comment, fh))
            await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
def get_prompt(txt: str) -> str:
    """Return the LLM prompt for sentiment extraction."""
    return (
        "You are an expert in sentiment analysis using AI. "
        "Analyze the following text and return a JSON object per ticker "
        "with counts for positive, negative, and neutral comments."
        "\n\n" + txt
    )


def get_json_from_llm(file_path: str) -> dict:
    """Send *file_path* content to Gemini and parse the JSON reply."""
    import google.generativeai as genai

    with open(file_path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    prompt = get_prompt(raw)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY", "DUMMY_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    txt = response.text.replace("```", "").replace("json", "")
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        print(f"[WARN] could not parse JSON from {file_path}")
        return {}


def list_text_files(base_path: str) -> List[str]:
    """Return all .txt files inside Short/ and Long/ folders."""
    out = []
    for variant in ("Short", "Long"):
        for root, _, fnames in os.walk(os.path.join(base_path, variant)):
            for fname in fnames:
                if fname.endswith(".txt"):
                    out.append(os.path.join(root, fname))
    return out


# ---------------------------------------------------------------------------
# Main workflows
# ---------------------------------------------------------------------------
def aggregate_sentiment():
    """Merge individual JSON snippets into Comments/JSON/Data.json."""
    os.makedirs("./Comments/JSON", exist_ok=True)
    target = "./Comments/JSON/Data.json"
    agg = {}
    if os.path.exists(target):
        with open(target, "r", encoding="utf-8") as fh:
            agg = json.load(fh)

    for txt in list_text_files("./Comments"):
        print(f"Processing {txt}")
        snippet = get_json_from_llm(txt)
        for ticker, content in snippet.items():
            agg.setdefault(ticker, []).append(content)

        with open(target, "w", encoding="utf-8") as fh:
            json.dump(agg, fh, indent=2)

    print("Sentiment data updated.")


def popular_tickers(min_posts: int = 10) -> pd.DataFrame:
    """Return DataFrame with tickers mentioned at least *min_posts* times."""
    with open("./Comments/JSON/Data.json", "r", encoding="utf-8") as fh:
        data = json.load(fh)

    df = pd.DataFrame(
        [{"Ticker": t, "Mentions": len(v)} for t, v in data.items()]
    )
    return df[df["Mentions"] >= min_posts].sort_values("Mentions", ascending=False)


# ---------------------------------------------------------------------------
# __main__ entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Uncomment `harvest_reddit()` to refresh comment files (may hit API limits)
    # harvest_reddit()

    aggregate_sentiment()

    print("\nMost‑mentioned tickers (≥10 posts):")
    print(popular_tickers().to_string(index=False))
