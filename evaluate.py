"""Offline evaluation on CMU: FAR / FRR / ROC / AUC / EER.
Train: sessions 1-4 of a subject.  Genuine test: sessions 5-8 of that subject.
Impostor test: first 5 reps of every other subject.
Usage: python evaluate.py          (compares hold vs digraph vs tri, saves roc.png)
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, roc_auc_score
from features import build_features
from model import fit_profile, score, GAMMA_OFFLINE

df = pd.read_csv("data/DSL-StrongPasswordData.csv")


def evaluate(kind, subjects=None):
    X = build_features(df, kind)
    subjects = subjects or sorted(df.subject.unique())
    aucs, eers, curves = [], [], []
    for s in subjects:
        tr = df[(df.subject == s) & (df.sessionIndex <= 4)].index
        te = df[(df.subject == s) & (df.sessionIndex > 4)].index
        imp = df[df.subject != s].groupby("subject").head(5).index
        p = fit_profile(X.loc[tr], gamma=GAMMA_OFFLINE)
        g = [score(p, X.loc[i].values) for i in te]
        f = [score(p, X.loc[i].values) for i in imp]
        y = np.r_[np.ones(len(g)), np.zeros(len(f))]
        sc = np.r_[g, f]
        fpr, tpr, _ = roc_curve(y, sc)          # fpr = FAR, 1 - tpr = FRR
        eers.append(fpr[np.argmin(np.abs((1 - tpr) - fpr))])
        aucs.append(roc_auc_score(y, sc))
        curves.append((fpr, tpr))
    return np.mean(aucs), np.mean(eers), curves


if __name__ == "__main__":
    subs = sorted(df.subject.unique())[:20]      # remove [:20] for all 51 (slower)
    grid = np.linspace(0, 1, 101)
    plt.figure(figsize=(5, 5))
    print(f"{'features':10s} {'mean AUC':>9s} {'mean EER':>9s}")
    for kind in ("hold", "digraph", "tri"):
        auc, eer, curves = evaluate(kind, subs)
        print(f"{kind:10s} {auc:9.3f} {eer:9.3f}")
        mean_tpr = np.mean([np.interp(grid, f, t) for f, t in curves], axis=0)
        plt.plot(grid, mean_tpr, label=f"{kind} (AUC {auc:.2f})")
    plt.plot([0, 1], [0, 1], "k--", lw=0.8)
    plt.xlabel("FAR (false acceptance rate)")
    plt.ylabel("1 - FRR (true acceptance)")
    plt.title("Mean ROC over subjects")
    plt.legend()
    plt.tight_layout()
    plt.savefig("roc.png", dpi=150)
    print("saved roc.png")
