# Calm-vs-crisis snapshot comparison and CSV output.
# Console output stays ASCII: the Windows console is cp1252 and chokes on
# characters like the square-root sign, which throws UnicodeEncodeError.

import pandas as pd
import config


def compare(calm, crisis):
    c, x = calm["metrics"], crisis["metrics"]
    rows = [
        ("Tickers in network", c["n_tickers"], x["n_tickers"]),
        ("Trading days", c["n_days"], x["n_days"]),
        ("Mean pairwise corr", round(c["mean_corr"], 3), round(x["mean_corr"], 3)),
        ("MST tree length", round(c["tree_length"], 3), round(x["tree_length"], 3)),
        ("Max MST degree", c["max_degree"], x["max_degree"]),
        ("Central hub", c["hub"], x["hub"]),
        ("Hub sector", c["hub_sector"], x["hub_sector"]),
        ("Top eigenvector node", c["top_eigen"], x["top_eigen"]),
    ]
    return pd.DataFrame(rows, columns=["metric", c["label"], x["label"]])


def print_report(calm, crisis, table):
    c, x = calm["metrics"], crisis["metrics"]
    line = "=" * 68
    print("\n" + line)
    print("EQUITY CORRELATION NETWORK: CALM vs CRISIS")
    print(line)
    print(table.to_string(index=False))
    print(line)
    print(f"Mean correlation moved {x['mean_corr'] - c['mean_corr']:+.3f} into the crisis.")
    dd = x["max_degree"] - c["max_degree"]
    if dd > 0:
        deg = (f"max degree rose from {c['max_degree']} to {x['max_degree']}, "
               f"a more hub-dominated tree.")
    elif dd < 0:
        deg = f"max degree fell from {c['max_degree']} to {x['max_degree']}."
    else:
        deg = (f"max degree was unchanged at {c['max_degree']}, so the "
               f"hub-collapse effect is weak in this window.")
    print(f"Tree length fell {c['tree_length'] - x['tree_length']:.3f}. {deg}")
    print(line + "\n")


def save_outputs(calm, crisis, table):
    table.to_csv(config.OUTPUT_DIR / "regime_comparison.csv", index=False)
    calm["centrality"].to_csv(config.OUTPUT_DIR / "centrality_calm.csv")
    crisis["centrality"].to_csv(config.OUTPUT_DIR / "centrality_crisis.csv")
    print(f"[analysis] wrote comparison and centrality CSVs to {config.OUTPUT_DIR.name}/")
