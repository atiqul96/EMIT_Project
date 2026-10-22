"""Feature engineering: hold, digraph (DD/UD) and trigraph timing.

Same formulas are used for the CMU CSV (offline) and for live keystrokes,
so a model trained on one kind of data is scored with identical features.
"""
import pandas as pd


def build_features(df, kind="tri"):
    """CMU dataframe -> feature table.
    kind: 'hold' | 'digraph' | 'tri' (hold + digraph + trigraph)
    """
    H = [c for c in df.columns if c.startswith("H.")]
    DD = [c for c in df.columns if c.startswith("DD.")]
    UD = [c for c in df.columns if c.startswith("UD.")]
    if kind == "hold":
        return df[H].copy()
    X = df[H + DD + UD].copy()
    if kind == "tri":
        for i in range(len(DD) - 1):
            # trigraph = time from key i going down to key i+2 going down
            X[f"TRI{i}"] = df[DD[i]] + df[DD[i + 1]]
    return X


def events_to_features(events):
    """Live keystrokes -> one feature row (seconds).
    events: list of {"k": key code, "d": keydown ms, "u": keyup ms}
    Order: H (n) + DD (n-1) + UD (n-1) + TRI (n-2)
    """
    ev = sorted(events, key=lambda e: e["d"])
    d = [e["d"] / 1000.0 for e in ev]
    u = [e["u"] / 1000.0 for e in ev]
    n = len(ev)
    H = [u[i] - d[i] for i in range(n)]
    DD = [d[i + 1] - d[i] for i in range(n - 1)]
    UD = [d[i + 1] - u[i] for i in range(n - 1)]
    TRI = [DD[i] + DD[i + 1] for i in range(n - 2)]
    return H + DD + UD + TRI
