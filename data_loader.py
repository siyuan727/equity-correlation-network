# Price data via yfinance, cached to CSV so we only download once.

import sys
import pandas as pd
import config


def _try_yf():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        sys.exit("yfinance missing. Run: pip install yfinance")


def load_prices(tickers=None, start=None, end=None, force=False):
    """Wide frame of adjusted closes: index=dates, columns=tickers."""
    tickers = tickers or config.TICKERS
    start = start or config.FULL_START
    end = end or config.FULL_END
    cache = config.DATA_DIR / f"prices_{start}_{end}.csv"

    if cache.exists() and not force:
        print(f"[data] using cached {cache.name}")
        px = pd.read_csv(cache, index_col=0, parse_dates=True)
        keep = [t for t in tickers if t in px.columns]
        return px[keep].sort_index()

    print(f"[data] downloading {len(tickers)} tickers {start}..{end}")
    yf = _try_yf()
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False, group_by="column")
    if raw.empty:
        sys.exit("[data] empty download - check connection or tickers")

    # auto_adjust puts the adjusted price in 'Close'. Multiple tickers come
    # back with a (field, ticker) column index.
    px = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    px = px.dropna(axis=1, how="all").dropna(how="all").sort_index()

    missing = sorted(set(tickers) - set(px.columns))
    if missing:
        print(f"[data] no data for {len(missing)}: {', '.join(missing)}")

    px.to_csv(cache)
    return px


def load_series(symbol, start=None, end=None, force=False, name=None):
    """Single close-price series (used for ^VIX and ^GSPC)."""
    start = start or config.FULL_START
    end = end or config.FULL_END
    safe = symbol.replace("^", "").replace("/", "_")
    cache = config.DATA_DIR / f"{safe}_{start}_{end}.csv"

    if cache.exists() and not force:
        print(f"[data] using cached {cache.name}")
        s = pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = name or safe
        return s

    print(f"[data] downloading {symbol} {start}..{end}")
    yf = _try_yf()
    raw = yf.download(symbol, start=start, end=end, auto_adjust=True,
                      progress=False)
    if raw.empty:
        sys.exit(f"[data] empty download for {symbol}")

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
        close = close.iloc[:, 0]
    else:
        close = raw["Close"]

    close = close.dropna().sort_index()
    close.name = name or safe
    close.to_frame().to_csv(cache)
    return close


if __name__ == "__main__":
    px = load_prices()
    print(px.tail())
    print(f"{px.shape[0]} days x {px.shape[1]} tickers")
