# Settings for the whole project. Edit dates, windows, or the universe here.

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Full span to pull once and cache. Everything else slices out of this.
FULL_START = "2007-01-01"
FULL_END = "2024-12-31"

# Benchmarks used to validate the network signal.
VIX_SYMBOL = "^VIX"
INDEX_SYMBOL = "^GSPC"

# Rolling window for the systemic-risk series.
# 60 trading days is roughly a quarter of price history per correlation
# estimate; stepping 5 days gives one reading a week, which is enough
# resolution to catch selloffs without the series getting noisy.
ROLL_WINDOW = 60
ROLL_STEP = 5
ROLL_MIN_TICKERS = 20

# Two fixed windows for the calm-vs-crisis snapshot (the MST plots).
CALM_WINDOW = ("2021-04-01", "2021-12-31")
CRISIS_WINDOW = ("2020-02-01", "2020-04-30")
CALM_LABEL = "Calm (Apr-Dec 2021)"
CRISIS_LABEL = "Crisis (Feb-Apr 2020)"

# Ticker must have at least this many prices in a window to be used.
MIN_OBS = 30

# Stress periods to shade on the time-series plot. Dates are approximate
# start/end of each episode, not official recession dating.
CRISIS_SPANS = [
    ("2008-09-01", "2009-03-31", "GFC"),
    ("2011-08-01", "2011-10-31", "EU debt"),
    ("2015-08-01", "2016-02-15", "China/oil"),
    ("2018-10-01", "2018-12-31", "Q4 '18"),
    ("2020-02-20", "2020-04-30", "COVID"),
    ("2022-01-01", "2022-10-15", "'22 bear"),
]

# Universe: large caps with a sector tag. The sector map colors the network
# nodes. Names without price history back to FULL_START are dropped from the
# rolling series automatically (see rolling.py), so a few later IPOs are fine.
TICKER_SECTORS = {
    "AAPL": "Info Tech", "MSFT": "Info Tech", "NVDA": "Info Tech",
    "ORCL": "Info Tech", "CRM": "Info Tech", "ADBE": "Info Tech",
    "CSCO": "Info Tech",
    "GOOGL": "Comm Svcs", "NFLX": "Comm Svcs", "DIS": "Comm Svcs",
    "VZ": "Comm Svcs", "T": "Comm Svcs",
    "AMZN": "Cons Disc", "HD": "Cons Disc", "MCD": "Cons Disc",
    "NKE": "Cons Disc", "SBUX": "Cons Disc", "LOW": "Cons Disc",
    "PG": "Cons Staples", "KO": "Cons Staples", "PEP": "Cons Staples",
    "WMT": "Cons Staples", "COST": "Cons Staples",
    "JPM": "Financials", "BAC": "Financials", "WFC": "Financials",
    "GS": "Financials", "MS": "Financials", "BLK": "Financials",
    "AXP": "Financials",
    "JNJ": "Health Care", "UNH": "Health Care", "LLY": "Health Care",
    "PFE": "Health Care", "MRK": "Health Care",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    "BA": "Industrials", "CAT": "Industrials", "GE": "Industrials",
    "HON": "Industrials", "UPS": "Industrials",
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities",
}
TICKERS = sorted(TICKER_SECTORS)

SECTOR_COLORS = {
    "Info Tech": "#4C72B0", "Comm Svcs": "#DD8452", "Cons Disc": "#55A868",
    "Cons Staples": "#C44E52", "Financials": "#8172B3", "Health Care": "#937860",
    "Energy": "#DA8BC3", "Industrials": "#8C8C8C", "Utilities": "#CCB974",
}
