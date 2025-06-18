
"""getstock.py
========================

Purpose
-------
*   Read a list of ticker symbols from one or more ``*.txt`` files stored in
    the *Tickers/* directory (the example uses **Cac40.txt** containing the
    CAC 40 constituents).
*   Query Yahoo Finance for **up‑coming earnings dates** plus EPS surprise
    metrics for each ticker via the `yfinance` package.
*   Keep a **persistent JSON cache** (``Cac40.json``) so the script can be
    re‑run quickly without losing previously fetched data.
*   Produce a Pandas ``DataFrame`` ``df1`` that holds only *future* earnings
    events and print a concise, chronologically‑sorted table to *stdout*.

Created automatically from the original *getstock.ipynb* on
2025-06-18T10:38:54.799635 UTC

Dependencies
------------
::

    pip install pandas yfinance

Folder layout expected
----------------------
::

    .
    ├── getstock_commented_en.py      # <–– this file
    └── Tickers/
        ├── Cac40.txt                # each line: "<TICKER>,<COMPANY NAME>"
        └── Cac40.json               # cache file (will be created / updated)

Feel free to tweak path constants, variable names and logging behaviour.
"""


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import os
from datetime import datetime
import json

import pandas as pd
import yfinance as yf


# ---------------------------------------------------------------------------
# Helper: build a DataFrame with tickers + company names
# ---------------------------------------------------------------------------
def load_ticker_list(txt_path: str) -> pd.DataFrame:
    """Read ``<symbol>,<company name>`` pairs from *txt_path*.

    Each line in the file must contain a comma‑separated ticker symbol and
    company name, e.g. ::

        AAPL,Apple Inc.
        MSFT,Microsoft Corporation

    For Euronext Paris stocks the function automatically appends the suffix
    ``.PA`` because Yahoo Finance expects that format.

    Returns
    -------
    pandas.DataFrame
        Columns ``['Ticker', 'Name']``.
    """
    df = pd.DataFrame(columns=['Ticker', 'Name'])

    with open(txt_path, 'r', encoding='utf-8') as fh:
        for raw in fh.read().splitlines():
            symbol, name = raw.split(',', 1)
            yfin_symbol = f'{symbol}.PA'  # e.g. "AI.PA" for Air Liquide
            df = pd.concat(
                [df, pd.DataFrame({'Ticker': [yfin_symbol], 'Name': [name]})],
                ignore_index=True,
            )

    return df


# ---------------------------------------------------------------------------
# Helper: fetch the *entire* earnings calendar for ONE ticker
# ---------------------------------------------------------------------------
def get_stock_data(ticker: str) -> pd.DataFrame:
    """Download the full earnings calendar for *ticker* via yfinance."""
    stock = yf.Ticker(ticker)

    cols = ['Ticker', 'Earnings Date', 'Earnings Time', 'Country',
            'Reported EPS', 'Surprise(%)']
    df = pd.DataFrame(columns=cols)

    earnings_df = stock.earnings_dates

    try:
        company_country = stock.info.get('country', None)

        # Iterate over each earnings entry (past & future)
        for idx in range(len(earnings_df)):
            earning_date = earnings_df.index[idx].strftime('%Y-%m-%d')
            earning_time = earnings_df.index[idx].strftime('%H:%M:%S')

            reported_eps = earnings_df.iloc[idx].get('Reported EPS', None)
            surprise_pct = earnings_df.iloc[idx].get('Surprise(%)', None)

            new_row = pd.DataFrame(
                {'Ticker': [ticker],
                 'Earnings Date': [earning_date],
                 'Earnings Time': [earning_time],
                 'Country': [company_country],
                 'Reported EPS': [reported_eps],
                 'Surprise(%)': [surprise_pct]}
            )
            df = pd.concat([df, new_row], ignore_index=True)

    except Exception:
        # One failing ticker shouldn't crash the script; consider logging.
        pass

    return df


# ---------------------------------------------------------------------------
# Orchestrator: collect *future* earnings for **all** tickers
# ---------------------------------------------------------------------------
def build_earnings_table(ticker_df: pd.DataFrame, cache_path: str) -> pd.DataFrame:
    """Return DataFrame with the next earnings event for each ticker."""
    cache_data = {}
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as fh:
            cache_data = json.load(fh)

    results = pd.DataFrame(
        columns=['Ticker', 'Earnings Date', 'Earnings Time', 'Country',
                 'Reported EPS', 'Surprise(%)']
    )

    today_str = datetime.today().strftime('%Y-%m-%d')

    for ticker in ticker_df['Ticker']:
        print(f'\\n---- Processing {ticker} ----')
        earnings = get_stock_data(ticker)

        future_events = earnings[earnings['Earnings Date'] > today_str]
        if not future_events.empty:
            first_event = future_events.iloc[[0]]
            results = pd.concat([results, first_event], ignore_index=True)
            cache_data[ticker] = first_event.to_dict(orient='records')[0]

        print(f'---- Done {ticker} ----')

    # Save updated cache
    with open(cache_path, 'w', encoding='utf-8') as fh:
        json.dump(cache_data, fh, indent=2)

    results['Earnings Date'] = pd.to_datetime(results['Earnings Date'])
    return results.sort_values(by='Earnings Date')


# ---------------------------------------------------------------------------
# Entrypoint – quick demo
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    TICKER_FILE = './Tickers/Cac40.txt'
    CACHE_FILE = './Tickers/Cac40.json'

    symbols_df = load_ticker_list(TICKER_FILE)
    upcoming_df = build_earnings_table(symbols_df, CACHE_FILE)

    with pd.option_context('display.max_rows', 10):
        print('\\nUpcoming earnings events:\\n')
        print(upcoming_df.to_string(index=False))
