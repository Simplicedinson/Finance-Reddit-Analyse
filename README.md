# Finance-Analyse 📈🧠
> Mining Reddit sentiment + Yahoo Finance fundamentals to find timely trade ideas.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What it does
1. **Reddit crawler** – pulls fresh posts from configurable sub-reddits, dumps  
   the full comment trees to `./Comments/Short/` and `./Comments/Long/`.
2. **Sentiment engine** – sends each `.txt` file to an LLM (Gemini 1.5 Flash)  
   to extract _bullish / bearish / neutral_ counts per ticker.
3. **Earnings calendar** – fetches next earnings dates (and EPS surprise) for  
   every ticker in `./Tickers/*.txt`.
4. **Stock résumé** – mixes fundamentals, latest news & the Reddit sentiment to  
   generate a concise _“buy / sell / neutral”_ recommendation.

Everything is orchestrated via **`src/app_cli.py`** (command-line) or the more
granular helper scripts in `src/`.

---

## Folder layout
```text
FINANZ-ANALYSE/
├── Comments/
│   ├── JSON/                 ← aggregated sentiment → Data.json
│   ├── Long/                 ← >1 500-comment threads
│   └── Short/                ← smaller threads
├── Tickers/                  ← one TXT per watch-list (comma: “SYM,Company”)
│   ├── Cac40.txt
│   ├── NASDAQ.txt
│   └── NYSE.txt
├── src/
│   ├── app_cli.py            ← main entry point (CLI)
│   ├── calender.py           ← earnings crawler (yfinance)
│   ├── getstock_earning_calender.py
│   ├── yahoofinacescraping_stock_resume.py
│   └── App_commented_en_v2.py (legacy notebook export)
└── .env                      ← **never commit; holds your API keys**
```
## Typical workflows

| Task | Command |
|------|---------|
| Pull new Reddit comments <br><span style="font-size:0.9em;">*(can be rate-limited)*</span> | `python -m src.app_cli harvest` |
| Aggregate sentiment JSON only <br><span style="font-size:0.9em;">*(default)*</span> | `python -m src.app_cli` |
| Get upcoming earnings for **CAC 40** | `python -m src.calender Tickers/Cac40.txt` |




## Requirements

* **Python 3.10+**  
* Generate your lock-file:  

  ```bash
  pip freeze > requirements.txt

## Disclaimer
This repository is for research & educational purposes only and does not
constitute financial advice. Trade at your own risk.
