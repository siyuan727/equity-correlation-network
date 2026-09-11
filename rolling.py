# Rolling MST tree length as a systemic-risk series, plus validation against
# VIX. The idea: when the market is stressed, correlations rise, Mantegna
# distances shrink, and the spanning tree gets shorter. So tree length should
# move opposite to VIX. This module builds that series and measures the link.

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.stats import pearsonr, spearmanr
import config


def _window_tree_length(ret_window, min_tickers):
    """Tree length + mean correlation for one window of log returns."""
    r = ret_window.dropna(axis=1, how="any")
    # Drop anything that didn't move all window (halts, etc.) or corrcoef
    # returns NaNs for it.
    r = r.loc[:, r.std(axis=0) > 0]
    n = r.shape[1]
    if n < min_tickers:
        return np.nan, np.nan, n

    c = np.corrcoef(r.to_numpy(), rowvar=False)
    iu = np.triu_indices(n, 1)
    mean_corr = float(c[iu].mean())

    d = np.sqrt(2.0 * (1.0 - c))
    np.fill_diagonal(d, 0.0)
    # scipy treats zero entries as "no edge"; only the diagonal is zero here,
    # off-diagonal distances are strictly positive for distinct names.
    mst = minimum_spanning_tree(d)
    return float(mst.sum() / (n - 1)), mean_corr, n


def build_series(prices, window=None, step=None, min_tickers=None):
    window = window or config.ROLL_WINDOW
    step = step or config.ROLL_STEP
    min_tickers = min_tickers or config.ROLL_MIN_TICKERS

    logret = np.log(prices / prices.shift(1))
    idx = prices.index
    out = []
    for end in range(window, len(idx), step):
        tl, mc, n = _window_tree_length(logret.iloc[end - window:end], min_tickers)
        out.append((idx[end - 1], tl, mc, n))

    df = pd.DataFrame(out, columns=["date", "tree_length", "mean_corr",
                                    "n_tickers"]).set_index("date")
    return df.dropna(subset=["tree_length"])


def validate(series, vix, window=None, step=None):
    """
    Correlate the network signal with VIX three ways, because the naive
    correlation on overlapping windows overstates significance badly.

    Windows are ROLL_WINDOW days long stepped ROLL_STEP days apart, so
    neighbouring points share most of their data and are nowhere near
    independent. n on the overlapping series is therefore not a real sample
    size. We report:

      1. overlapping levels   - point estimate is fine, p-value is not.
      2. non-overlapping levels - one window every ceil(window/step) points,
                                  so sampled windows share no days. This is
                                  the honest sample size and p-value.
      3. changes (first diffs) - correlate week-to-week moves, which strips
                                  the shared trend and persistence. Usually
                                  the smallest and most defensible number.
    """
    window = window or config.ROLL_WINDOW
    step = step or config.ROLL_STEP

    v = vix.reindex(series.index, method="ffill")
    m = series.join(v.rename("vix")).dropna()

    # 1. Overlapping levels.
    ov_r, ov_p = pearsonr(m["tree_length"], m["vix"])
    ov_sr, _ = spearmanr(m["tree_length"], m["vix"])
    mc_r, _ = pearsonr(m["mean_corr"], m["vix"])

    # 2. Non-overlapping levels.
    stride = int(np.ceil(window / step))
    nonov = m.iloc[::stride]
    no_r, no_p = pearsonr(nonov["tree_length"], nonov["vix"])

    # 3. Changes.
    d = m[["tree_length", "vix"]].diff().dropna()
    ch_r, ch_p = pearsonr(d["tree_length"], d["vix"])

    stats = {
        "n_overlap": len(m),
        "overlap_r": ov_r, "overlap_p": ov_p, "overlap_spearman": ov_sr,
        "meancorr_r": mc_r,
        "stride": stride, "n_nonoverlap": len(nonov),
        "nonoverlap_r": no_r, "nonoverlap_p": no_p,
        "n_changes": len(d),
        "change_r": ch_r, "change_p": ch_p,
    }
    return m, stats


def print_validation(stats):
    line = "=" * 70
    print("\n" + line)
    print("ROLLING NETWORK SIGNAL vs VIX")
    print(line)
    print("Overlapping windows share most of their data, so treat the first")
    print("row's p-value as meaningless. The non-overlapping and change-based")
    print("rows are the honest tests.")
    print("-" * 70)
    print(f"1. overlapping levels    r = {stats['overlap_r']:+.3f}   "
          f"n = {stats['n_overlap']:>4}   p = {stats['overlap_p']:.1e}  "
          f"(p inflated)")
    print(f"2. non-overlapping levels r = {stats['nonoverlap_r']:+.3f}   "
          f"n = {stats['n_nonoverlap']:>4}   p = {stats['nonoverlap_p']:.1e}  "
          f"(1 window / {stats['stride']} steps)")
    print(f"3. weekly changes        r = {stats['change_r']:+.3f}   "
          f"n = {stats['n_changes']:>4}   p = {stats['change_p']:.1e}  "
          f"(trend removed)")
    print("-" * 70)
    print(f"mean correlation vs VIX  r = {stats['meancorr_r']:+.3f}  (levels, "
          f"expected positive)")
    print(line + "\n")


def detect_events(series, vix, pct=10, merge_gap_days=45):
    """
    Flag stress episodes as dates where tree length falls into its lowest
    `pct` percent, then merge nearby flags into episodes. For each episode
    report the trough date, the minimum tree length, the peak VIX, and
    whether the trough lands inside a labelled crisis span or is out of
    sample.

    Note: the percentile threshold uses the whole sample, so this is a
    descriptive detector, not a real-time signal. A live version would set
    the threshold on a trailing basis only.
    """
    thr = float(np.percentile(series["tree_length"], pct))
    flags = series.index[series["tree_length"] <= thr]
    v = vix.reindex(series.index, method="ffill")

    cols = ["start", "end", "trough", "min_tree_length", "peak_vix", "label"]
    if len(flags) == 0:
        return pd.DataFrame(columns=cols), thr

    groups = [[flags[0]]]
    for dt in flags[1:]:
        if (dt - groups[-1][-1]).days > merge_gap_days:
            groups.append([dt])
        else:
            groups[-1].append(dt)

    rows = []
    for g in groups:
        span = series.loc[g[0]:g[-1]]
        trough = span["tree_length"].idxmin()
        rows.append({
            "start": g[0].date(),
            "end": g[-1].date(),
            "trough": trough.date(),
            "min_tree_length": round(float(span["tree_length"].min()), 3),
            "peak_vix": round(float(v.loc[g[0]:g[-1]].max()), 1),
            "label": _match_label(trough),
        })
    return pd.DataFrame(rows, columns=cols), thr


def _match_label(dt):
    for start, end, name in config.CRISIS_SPANS:
        if pd.Timestamp(start) <= dt <= pd.Timestamp(end):
            return name
    return "(out of sample)"


def print_events(events, thr):
    line = "=" * 70
    print(line)
    print(f"STRESS EPISODES  (tree length in bottom decile, threshold = {thr:.3f})")
    print(line)
    if events.empty:
        print("no episodes flagged")
    else:
        print(events.to_string(index=False))
        extra = events[events["label"] == "(out of sample)"]
        n_extra = len(extra)
        print("-" * 70)
        print(f"{len(events)} episodes flagged; {n_extra} fall outside the "
              f"shaded crisis spans.")
        if n_extra:
            print("Out-of-sample flags (the indicator caught these without "
                  "being told):")
            for _, r in extra.iterrows():
                print(f"  {r['trough']}  tree length {r['min_tree_length']}, "
                      f"peak VIX {r['peak_vix']}")
    print(line + "\n")


def detect_events_realtime(series, vix, pct=10, burn_in=52, lookback=None,
                           merge_gap_days=45):
    """
    Real-time version of the stress detector. At each date the threshold is the
    bottom-`pct` percentile of tree length computed from PAST data only, then
    shifted one step so the current point is never in its own threshold. A flag
    fires when tree length drops at or below that past-derived line.

    Because the threshold never sees the future, every flag here is one the
    detector would have produced live, on the day it fired. first_flag is that
    day.

    burn_in: observations of history required before any signal is emitted, so
             the early sample (before enough history exists) is left unflagged.
    lookback: None uses an expanding window (all history so far). Pass an int
              to use a trailing window of that many observations instead, which
              re-sensitises after a big crisis instead of letting it raise the
              bar permanently.
    """
    tl = series["tree_length"]
    roll = (tl.expanding(min_periods=burn_in) if lookback is None
            else tl.rolling(window=lookback, min_periods=burn_in))
    thr = roll.quantile(pct / 100.0).shift(1)

    v = vix.reindex(series.index, method="ffill")
    flags = series.index[(tl <= thr) & thr.notna()]

    cols = ["first_flag", "end", "trough", "min_tree_length", "peak_vix", "label"]
    if len(flags) == 0:
        return pd.DataFrame(columns=cols), thr

    groups = [[flags[0]]]
    for dt in flags[1:]:
        if (dt - groups[-1][-1]).days > merge_gap_days:
            groups.append([dt])
        else:
            groups[-1].append(dt)

    rows = []
    for g in groups:
        span = series.loc[g[0]:g[-1]]
        trough = span["tree_length"].idxmin()
        rows.append({
            "first_flag": g[0].date(),
            "end": g[-1].date(),
            "trough": trough.date(),
            "min_tree_length": round(float(span["tree_length"].min()), 3),
            "peak_vix": round(float(v.loc[g[0]:g[-1]].max()), 1),
            "label": _match_label(trough),
        })
    return pd.DataFrame(rows, columns=cols), thr


def print_events_realtime(events, burn_in):
    line = "=" * 70
    print(line)
    print("REAL-TIME STRESS DETECTOR")
    print(f"(trailing bottom-decile threshold, {burn_in}-week burn-in, "
          f"past data only)")
    print(line)
    if events.empty:
        print("no episodes flagged")
    else:
        print(events.to_string(index=False))
        print("-" * 70)
        print("first_flag is the day the signal first fired using only data")
        print("available then. The threshold never looks ahead, so these are")
        print("flags the detector would have produced live.")
        first = events.iloc[0]["first_flag"]
        print(f"Earliest possible signal after burn-in; first flag at {first}.")
    print(line + "\n")
