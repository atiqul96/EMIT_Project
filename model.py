"""One-Class SVM profile: fit, calibrate thresholds, score, risk tier."""
import numpy as np
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

NU = 0.1
GAMMA = 0.001   # LIVE enrolment (5-15 samples): small gamma works best
GAMMA_OFFLINE = "scale"   # CMU (200 training rows per user)


def _held_out_scores(Z, nu, gamma, max_folds=10):
    """Honest scores: every sample is scored by a model that never saw it.
    (Scores on the training data itself are too optimistic to set thresholds.)"""
    n = len(Z)
    folds = min(n, max_folds)
    scores = np.zeros(n)
    for tr, te in KFold(folds, shuffle=True, random_state=0).split(Z):
        m = OneClassSVM(nu=nu, gamma=gamma).fit(Z[tr])
        scores[te] = m.decision_function(Z[te])
    return scores


def fit_profile(X, nu=NU, gamma=GAMMA):
    """X: 2-D array/DataFrame of feature rows for ONE user -> profile dict."""
    X = np.asarray(X, dtype=float)
    scaler = StandardScaler().fit(X)
    Z = scaler.transform(X)
    model = OneClassSVM(nu=nu, gamma=gamma).fit(Z)
    s = _held_out_scores(Z, nu, gamma)
    sd = s.std() if s.std() > 1e-9 else 1e-3
    t_susp = float(s.mean() - 2.0 * sd)      # below this -> SUSPICIOUS
    t_lock = float(t_susp - 3.0 * sd)        # below this -> LOCKED immediately
    return {"scaler": scaler, "model": model, "t_susp": t_susp, "t_lock": t_lock,
            "n_features": X.shape[1], "n_train": len(X)}


def score(profile, feats):
    """Higher = more like the enrolled user. Negative/low = anomaly."""
    z = profile["scaler"].transform(np.asarray(feats, dtype=float).reshape(1, -1))
    return float(profile["model"].decision_function(z)[0])


def tier(s, profile):
    if s >= profile["t_susp"]:
        return "NORMAL"
    if s >= profile["t_lock"]:
        return "SUSPICIOUS"
    return "LOCKED"
