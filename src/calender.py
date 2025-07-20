"""
calender_commented_en.py
========================

Purpose
-------
Fetch upcoming earnings dates (and related EPS surprise metrics) for a list
of tickers.  Tickers are read from every `.txt` file inside the *Tickers/*
directory.  Data are queried via the Yahoo Finance API provided by the
*yfinance* library.

The script creates three main helper functions:

* ``get_stock_data``  – download the earnings calendar for a single ticker
* ``get_tickers``     – collect all ticker symbols from *.txt files
* ``get_earning_data``– assemble a DataFrame with the next future earnings
                        per ticker

Usage
-----
Run the script directly:

    $ python calender_commented_en.py

By default it expects a folder structure::

    .
    ├── calender_commented_en.py
    └── Tickers/
        ├── Cac40.txt
        └── NASDAQ.txt

Each *.txt file contains one ticker symbol per line (optionally separated by
whitespace).

Dependencies
------------
* pandas   –  ``pip install pandas``
* yfinance –  ``pip install yfinance``

Created automatically from *calender.ipynb* on
2025-06-18T10:24:57.500053 UTC
"""

# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------
import pandas as pd
import os 
import yfinance as yf
import textwrap
from datetime import datetime
import json

# ------------------------------------------------------------
# Helper: fetch earnings calendar for *one* ticker
# ------------------------------------------------------------
# The function returns a DataFrame with the following columns:
#     Ticker         – symbol, e.g. "AAPL"
#     Earnings Date  – date of the earnings event (YYYY‑MM‑DD)
#     Earnings Time  – time of day (if available)
#     Country        – head‑quarter country, taken from ticker.info
#     EPS Estimate   – analyst EPS estimate prior to earnings
#     Reported EPS   – reported EPS
#     Surprise(%)    – earnings surprise in percent

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    
    #company = stock.info['longName']
    
    
    coloumns = ['Ticker','Earnings Date','Earnings Time','Country',"Reported EPS","Surprise(%)"]
    df = pd.DataFrame(columns = coloumns)
    
    try:
       
        earning = stock.earnings_dates
    except Exception as e:
        #print(f"Error processing {ticker}: {e}")
        return df
    
    
    try:
        earning_key = earning.keys()
    except Exception as e:
        #print(f"Error processing {ticker}: {e}")
        return df
    
    #earning = earning[['Reported EPS','Surprise(%)']]
    
    try:
        company_country = stock.info.get('country', None)
        for i in range(len(earning)):
            
            earning_date = earning.index[i].strftime('%Y-%m-%d')
            
            earning_time =earning.index[i].strftime('%H:%M:%S')
    
            
            # Use .get() to safely retrieve values and avoid KeyErrors
            eps_estimate = earning.iloc[i].get('EPS Estimate', None)
            reported_eps = earning.iloc[i].get('Reported EPS', None)
            surprise = earning.iloc[i].get('Surprise(%)', None)
            new_row = [ticker,earning_date,earning_time,company_country,eps_estimate,reported_eps,surprise]
            #new_row = [ticker,earning_date,earning_time,company_country,reported_eps,surprise]
            df.loc[i] = new_row
    except Exception as e:
        #print(f"Error processing {ticker}: {e}")  # Print error message for debugging
        pass
    return df



# ------------------------------------------------------------
# Helper: read all ticker symbols from ./Tickers/*.txt
# ------------------------------------------------------------
# Each line may contain additional text; only the first
# whitespace‑separated token is treated as the ticker.
def get_tickers(pfad):
    tickers = []
    for file in os.listdir(pfad):
        if file.endswith(".txt"):
            with open(pfad + file) as f:
                for line in f:
                    tickers.append(line.strip().split()[0])
    return tickers


# ------------------------------------------------------------
# Orchestrator: build earnings DataFrame for **all** tickers
# ------------------------------------------------------------
# The DataFrame includes only *future* earnings events (compared to today),
# ignoring entries that are already in the past.
#
# Additionally the function updates (or creates) a JSON cache file
# at "./Tickers/data.json" so downstream tools (e.g. dashboards) can use
# the pre‑computed information instantly without calling the API again.

def get_earning_data(pfad):
    
    coloumns = ['Ticker','Earnings Date','Earnings Time','Country',"EPS Estimate","Reported EPS","Surprise(%)"]
    #coloumns = ['Ticker','Earnings Date','Earnings Time','Country',"Reported EPS","Surprise(%)"]
    df = pd.DataFrame(columns = coloumns)
    date = datetime.today().strftime('%Y-%m-%d')
    tickers = get_tickers(pfad)
    
    with open("./Tickers/data.json") as json_file:
        data = json.load(json_file)
    
    # get data for all ticker
    for ticker in tickers:
        stock = get_stock_data(ticker)
        if stock.empty:
            continue
        else:
            for i in range(len(stock)):
                if date < stock['Earnings Date'].iloc[i]:
                    df = pd.concat([df,stock.iloc[[i]]])
                    data[ticker] = stock.iloc[[i]].to_dict()
            
    return df

# ------------------------------------------------------------
# Entrypoint – run a quick demo when executed directly
# ------------------------------------------------------------
if __name__ == "__main__":
    # Folder that contains your *.txt files with tickers
    tickers_folder = "./../Tickers/"
    
    # Fetch the next earnings events for all tickers
    earnings_df = get_earning_data(tickers_folder)
    
    # Display the result (at most 10 lines) in the console
    with pd.option_context("display.max_rows", 10):
        print(earnings_df)
