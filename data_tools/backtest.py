"""Smoke backtest: predict known past matchdays with the retrained (TFP-free)
models and compare to the actual recorded votes.

Not a rigorous evaluation (season-aggregate features include the target
matchday) -- a 'not broken' gate per the design: correlation > 0 and vote MAE
roughly < 1.5. Rigorous backtesting is a Phase-2 study.

Uses the already-built database_entries (features + actual vote/fantavote per
player-match), the same X construction as data_tools/train_models.py, and the
saved weights. Run: uv run python data_tools/backtest.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fantabeto_dist as fd

tfk = tf.keras
MID = "mid_outputs"


def _build_of():
    inp = tfk.layers.Input((112,)); x = tfk.layers.Dropout(0.2)(inp)
    x = tfk.layers.Dense(16, "relu")(x); x = tfk.layers.Dropout(0.2)(x); x = tfk.layers.Dense(16, "relu")(x)
    o1 = tfk.layers.Dense(4)(tfk.layers.Dense(8, "sigmoid")(x))
    o2 = tfk.layers.Dense(4)(tfk.layers.Dense(8, "sigmoid")(x))
    m = tfk.Model(inp, [o1, o2]); m.load_weights("saves/modelb.weights.h5"); return m


def _build_gk():
    inp = tfk.layers.Input((90,)); x = tfk.layers.Dense(16, "relu")(inp)
    x = tfk.layers.Dropout(0.3)(x); x = tfk.layers.Dense(16, "relu")(x)
    g1 = tfk.layers.Dense(4)(tfk.layers.Dropout(0.2)(tfk.layers.Dense(16, "sigmoid")(x)))
    g2 = tfk.layers.Dense(4)(tfk.layers.Dense(16, "sigmoid")(x))
    g3 = tfk.layers.Dense(1, "sigmoid")(tfk.layers.Dropout(0.2)(tfk.layers.Dense(8, "sigmoid")(x)))
    m = tfk.Model(inp, [g1, g2, g3]); m.load_weights("saves/modelb_gk.weights.h5"); return m


def _mean(raw, tail_range):
    out = np.zeros(len(raw))
    for i, r in enumerate(raw):
        p = fd.constrain_params_np(*r, tail_min=0.5, tail_range=tail_range)
        out[i] = fd.sample_sinharcsinh_np(*p, 400).mean()
    return out


def backtest_outfield(ss, md):
    db = pd.read_excel(f"{MID}/season{ss}/database_entries.xlsx", index_col=0)
    sub = db[db["matchday"] == md]
    if not len(sub):
        return None
    npdb = np.array(sub)
    X = npdb[:, 14:].astype("float32")
    add = np.zeros((len(sub), 4), "float32")
    add[:, 0] = npdb[:, 4]; add[:, 1] = npdb[:, 10] == "D"; add[:, 2] = npdb[:, 10] == "C"; add[:, 3] = npdb[:, 10] == "A"
    X = np.concatenate((X, add), axis=1)
    scaler = pickle.load(open("saves/scaler.pkl", "rb"))
    raw = _build_of().predict(scaler.transform(X), verbose=0)
    mv, fv = _mean(np.array(raw[0]), 1.2), _mean(np.array(raw[1]), 1.2)
    av, af = npdb[:, 5].astype(float), npdb[:, 9].astype(float)
    return dict(n=len(sub), corr_v=np.corrcoef(mv, av)[0, 1], mae_v=np.abs(mv - av).mean(),
                corr_f=np.corrcoef(fv, af)[0, 1], mae_f=np.abs(fv - af).mean())


def backtest_gk(ss, md):
    db = pd.read_excel(f"{MID}/season{ss}/database_entries_gk.xlsx", index_col=0)
    sub = db[db["matchday"] == md]
    if not len(sub):
        return None
    npdb = np.array(sub)
    X = npdb[:, 13:].astype("float32")
    add = np.zeros((len(sub), 1), "float32"); add[:, 0] = npdb[:, 4]
    X = np.concatenate((X, add), axis=1)
    scaler = pickle.load(open("saves/scaler_gk.pkl", "rb"))
    raw = _build_gk().predict(scaler.transform(X), verbose=0)
    cs_pred = np.array(raw[2]).ravel()
    cs_true = (npdb[:, 6].astype(float) == 0) * 1
    from sklearn.metrics import roc_auc_score
    auc = roc_auc_score(cs_true, cs_pred) if len(set(cs_true)) > 1 else float("nan")
    return dict(n=len(sub), cs_auc=auc, cs_base=cs_true.mean())


if __name__ == "__main__":
    for ss in ["2425", "2526"]:
        for md in [10, 25]:
            r = backtest_outfield(ss, md)
            g = backtest_gk(ss, md)
            if r:
                print(f"[{ss} md{md}] OF n={r['n']}  vote: corr={r['corr_v']:.2f} MAE={r['mae_v']:.2f}  "
                      f"fantavote: corr={r['corr_f']:.2f} MAE={r['mae_f']:.2f}")
            if g:
                print(f"            GK n={g['n']}  clean-sheet AUC={g['cs_auc']:.2f} (base {g['cs_base']:.2f})")
