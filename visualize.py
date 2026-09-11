# Plots: the calm-vs-crisis MST pair, and the rolling tree length vs VIX.
# Figures are saved before plt.show() so they survive a non-interactive
# backend (which is what PyCharm sometimes uses).

import matplotlib.pyplot as plt
import pandas as pd
import networkx as nx
import config


def _draw_mst(ax, result):
    mst, m = result["mst"], result["metrics"]
    try:
        pos = nx.kamada_kawai_layout(mst)
    except Exception:
        pos = nx.spring_layout(mst, seed=42, k=0.5, iterations=200)

    deg = dict(mst.degree())
    sizes = [120 + 90 * deg[n] for n in mst.nodes()]
    colors = [mst.nodes[n]["color"] for n in mst.nodes()]

    nx.draw_networkx_edges(mst, pos, ax=ax, edge_color="#BBBBBB", width=1.2)
    nx.draw_networkx_nodes(mst, pos, ax=ax, node_size=sizes, node_color=colors,
                           edgecolors="white", linewidths=0.8)
    nx.draw_networkx_labels(mst, pos, ax=ax, font_size=7)
    ax.set_title(f"{m['label']}\nmean corr {m['mean_corr']:.2f}, "
                 f"tree length {m['tree_length']:.2f}, "
                 f"hub {m['hub']} (deg {m['max_degree']})", fontsize=10)
    ax.axis("off")


def plot_snapshot(calm, crisis, show=True):
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    _draw_mst(axes[0], calm)
    _draw_mst(axes[1], crisis)
    handles = [plt.Line2D([0], [0], marker="o", linestyle="", markersize=8,
                          markerfacecolor=col, markeredgecolor="white", label=sec)
               for sec, col in config.SECTOR_COLORS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Minimum spanning trees, node size = degree, color = sector",
                 fontsize=13, y=0.98)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    path = config.OUTPUT_DIR / "mst_comparison.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"[viz] saved {path.name}")
    if show:
        try:
            plt.show()
        except Exception:
            pass
    plt.close(fig)


def _shade(ax):
    for start, end, label in config.CRISIS_SPANS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end),
                   color="#C44E52", alpha=0.12)


def plot_rolling(series, vix, stats, events=None, threshold=None, show=True):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                   height_ratios=[1, 1])

    ax1.plot(series.index, series["tree_length"], color="#4C72B0", lw=1.1,
             label="MST tree length")
    if threshold is not None:
        ax1.plot(threshold.index, threshold.values, color="#888888", lw=0.9,
                 ls="--", label="trailing bottom-decile threshold")
    ax1.set_ylabel("MST tree length")
    ax1.set_title(f"Rolling network compression vs VIX  "
                  f"(non-overlapping r = {stats['nonoverlap_r']:+.2f}, "
                  f"n = {stats['n_nonoverlap']}; "
                  f"weekly-change r = {stats['change_r']:+.2f})", fontsize=12)
    _shade(ax1)

    # Mark where the real-time detector first fired for each episode. A triangle
    # at the first-flag date, with the date on out-of-sample catches.
    if events is not None and not events.empty:
        for _, r in events.iterrows():
            fd = pd.Timestamp(r["first_flag"])
            y = series["tree_length"].get(fd, r["min_tree_length"])
            ax1.scatter([fd], [y], marker="v", color="#C44E52", zorder=5, s=45)
            if r["label"] == "(out of sample)":
                ax1.annotate(str(r["first_flag"]), (fd, y),
                             textcoords="offset points", xytext=(0, -14),
                             fontsize=7, ha="center", color="#7A2E31")
    ax1.legend(loc="lower right", fontsize=8, frameon=False)

    vplot = vix.loc[series.index.min():series.index.max()]
    ax2.plot(vplot.index, vplot.values, color="#C44E52", lw=0.9)
    ax2.set_ylabel("VIX")
    ax2.set_xlabel("")
    _shade(ax2)

    # One label per shaded span, placed along the top of the lower panel.
    ymax = ax2.get_ylim()[1]
    for start, end, label in config.CRISIS_SPANS:
        mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
        if series.index.min() <= mid <= series.index.max():
            ax2.text(mid, ymax * 0.92, label, fontsize=8, ha="center",
                     color="#7A2E31")

    fig.tight_layout()
    path = config.OUTPUT_DIR / "rolling_vs_vix.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"[viz] saved {path.name}")
    if show:
        try:
            plt.show()
        except Exception:
            pass
    plt.close(fig)
