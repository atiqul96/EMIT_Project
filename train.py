"""Train one profile per CMU subject and save to profiles/cmu_<subject>.joblib
Usage: python train.py [kind]     kind = hold | digraph | tri (default tri)
"""
import sys
import joblib
import pandas as pd
from features import build_features
from model import fit_profile, GAMMA_OFFLINE

kind = sys.argv[1] if len(sys.argv) > 1 else "tri"
df = pd.read_csv("data/DSL-StrongPasswordData.csv")
X = build_features(df, kind)

for s in sorted(df.subject.unique()):
    idx = df[(df.subject == s) & (df.sessionIndex <= 4)].index     # early sessions only
    p = fit_profile(X.loc[idx], gamma=GAMMA_OFFLINE)
    joblib.dump(p, f"profiles/cmu_{s}.joblib")
print("trained", df.subject.nunique(), "profiles, features:", kind)
