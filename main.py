# Run the whole thing: python main.py (or the Run button in PyCharm).

import config
import data_loader
import network_builder as nb
import rolling
import analysis
import visualize


def main(show_plots=False):  # False: save PNGs and exit, no blocking windows
    prices = data_loader.load_prices()
    vix = data_loader.load_series(config.VIX_SYMBOL, name="vix")
    print(f"[main] prices {prices.shape[0]} days x {prices.shape[1]} tickers, "
          f"VIX {len(vix)} days\n")

    # 1. Rolling systemic-risk series and its link to VIX.
    series = rolling.build_series(prices)
    merged, stats = rolling.validate(series, vix)
    rolling.print_validation(stats)

    # Descriptive detector (full-sample threshold) and the real-time detector
    # (trailing threshold, past data only). The real-time one is the headline;
    # the descriptive one is kept for contrast.
    events, threshold = rolling.detect_events(series, vix)
    rolling.print_events(events, threshold)

    burn_in = 52
    events_rt, thr_series = rolling.detect_events_realtime(series, vix,
                                                           burn_in=burn_in)
    rolling.print_events_realtime(events_rt, burn_in)

    series.to_csv(config.OUTPUT_DIR / "rolling_tree_length.csv")
    events.to_csv(config.OUTPUT_DIR / "stress_episodes_fullsample.csv", index=False)
    events_rt.to_csv(config.OUTPUT_DIR / "stress_episodes_realtime.csv", index=False)
    visualize.plot_rolling(series, vix, stats, events=events_rt,
                           threshold=thr_series, show=show_plots)

    # 2. Calm-vs-crisis snapshot networks.
    calm = nb.summarize(prices, *config.CALM_WINDOW, config.CALM_LABEL)
    crisis = nb.summarize(prices, *config.CRISIS_WINDOW, config.CRISIS_LABEL)
    table = analysis.compare(calm, crisis)
    analysis.print_report(calm, crisis, table)
    analysis.save_outputs(calm, crisis, table)
    visualize.plot_snapshot(calm, crisis, show=show_plots)

    print("[main] done")


if __name__ == "__main__":
    main()
