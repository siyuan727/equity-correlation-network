# Correlation network core: returns -> correlation -> Mantegna distance -> MST.
# Distance is d = sqrt(2(1-rho)), so rho=1 maps to 0 and rho=-1 maps to 2.

import numpy as np
import pandas as pd
import networkx as nx
import config


def log_returns(prices):
    return np.log(prices / prices.shift(1)).dropna(how="all")


def clean_window(prices, start, end, min_obs=config.MIN_OBS):
    """Slice to [start, end], drop thin tickers, align remaining dates."""
    w = prices.loc[start:end].copy()
    enough = w.notna().sum() >= min_obs
    w = w.loc[:, enough[enough].index].dropna(axis=0, how="any")
    if w.shape[1] < 2:
        raise ValueError(f"{start}..{end}: fewer than 2 usable tickers")
    return w


def correlation_matrix(window):
    return log_returns(window).corr().clip(-1.0, 1.0)


def distance_matrix(corr):
    # DataFrame.values can be read-only in pandas 3, so work off a copy.
    d = np.sqrt(2.0 * (1.0 - corr.to_numpy()))
    np.fill_diagonal(d, 0.0)
    return pd.DataFrame(d, index=corr.index, columns=corr.columns)


def build_mst(dist):
    tickers = list(dist.columns)
    g = nx.Graph()
    g.add_nodes_from(tickers)
    n = len(tickers)
    for i in range(n):
        for j in range(i + 1, n):
            g.add_edge(tickers[i], tickers[j], distance=float(dist.iloc[i, j]))

    mst = nx.minimum_spanning_tree(g, weight="distance")
    for a, b, data in mst.edges(data=True):
        data["corr"] = 1.0 - data["distance"] ** 2 / 2.0
    for node in mst.nodes():
        sec = config.TICKER_SECTORS.get(node, "Other")
        mst.nodes[node]["sector"] = sec
        mst.nodes[node]["color"] = config.SECTOR_COLORS.get(sec, "#333333")
    return mst


def mean_offdiag_corr(corr):
    m = corr.to_numpy()
    iu = np.triu_indices_from(m, k=1)
    return float(m[iu].mean())


def tree_length(mst):
    d = [e["distance"] for *_, e in mst.edges(data=True)]
    return float(np.mean(d)) if d else float("nan")


def centrality_table(mst):
    deg = dict(mst.degree())
    betw = nx.betweenness_centrality(mst, weight="distance", normalized=True)
    try:
        eig = nx.eigenvector_centrality_numpy(mst)
    except Exception:
        eig = {n: float("nan") for n in mst.nodes()}
    t = pd.DataFrame({
        "sector": {n: mst.nodes[n]["sector"] for n in mst.nodes()},
        "degree": deg, "betweenness": betw, "eigenvector": eig,
    })
    return t.sort_values("degree", ascending=False)


def summarize(prices, start, end, label):
    """Full snapshot for one window: corr, distance, MST, headline metrics."""
    w = clean_window(prices, start, end)
    corr = correlation_matrix(w)
    dist = distance_matrix(corr)
    mst = build_mst(dist)
    cent = centrality_table(mst)
    deg = dict(mst.degree())
    hub = max(deg, key=deg.get)
    metrics = {
        "label": label, "n_tickers": w.shape[1], "n_days": w.shape[0],
        "mean_corr": mean_offdiag_corr(corr), "tree_length": tree_length(mst),
        "max_degree": max(deg.values()), "hub": hub,
        "hub_sector": mst.nodes[hub]["sector"],
        "top_eigen": cent["eigenvector"].idxmax(),
    }
    return {"corr": corr, "dist": dist, "mst": mst,
            "centrality": cent, "metrics": metrics}
