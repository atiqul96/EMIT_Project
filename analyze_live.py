"""Summarise live hijack tests from the attempts table in Turso.
Usage: python analyze_live.py

Genuine attempts  -> live FRR (how often the real user was flagged) and false locks.
Impostor attempts -> detection rate, and how many attempts it took to LOCK each impostor
                     (one 'trial' = impostor attempts until the session locked).
"""
import pandas as pd

import db

df = pd.DataFrame(db.fetch_attempts(), columns=db.LOG_COLUMNS)
g = df[df.typist == "Genuine"]
i = df[df.typist == "Impostor"]

print(f"Genuine attempts : {len(g)}")
if len(g):
    print(f"  NORMAL         : {(g.tier == 'NORMAL').mean():.0%}")
    print(f"  live FRR       : {(g.tier != 'NORMAL').mean():.0%}  (flagged SUSPICIOUS or LOCKED)")
    print(f"  false locks    : {(g.tier == 'LOCKED').sum()}")

print(f"\nImpostor attempts: {len(i)}")
if len(i):
    print(f"  detected       : {(i.tier != 'NORMAL').mean():.0%}  (live FAR = {(i.tier == 'NORMAL').mean():.0%})")
    delays, run = [], 0
    for t in i.tier:
        run += 1
        if t == "LOCKED":
            delays.append(run)
            run = 0
    if delays:
        print(f"  trials locked  : {len(delays)}")
        print(f"  attempts to lock: mean {sum(delays)/len(delays):.1f}, max {max(delays)}  {delays}")
    if run:
        print(f"  {run} impostor attempt(s) at the end did not reach a lock")
    print("\nPer impostor:")
    print(i.groupby("tester").tier.value_counts().unstack(fill_value=0))
