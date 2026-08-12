"""Retrain the outfield + goalkeeper models WITHOUT tensorflow-probability.

This is the executable, validated core of the nb6 TFP removal: it reproduces
nb6's training cells (X/y construction from database_entries, the two-head
SinhArcsinh outfield model and the three-head GK model) but replaces every TFP
object with fantabeto_dist:
  * SinhArcsinh negative-log-likelihood loss  -> fantabeto_dist.sinharcsinh_nll_tf
  * distribution sampling (for r2 reporting)  -> fantabeto_dist.sample_sinharcsinh_np
  * GK clean-sheet Bernoulli                  -> plain sigmoid + binary_crossentropy

The network outputs the RAW 4-vector [loc, raw_scale, skewness, raw_tail] per
target (constraints applied inside the loss / by constrain_params_np), exactly
as nb6 now does. Weights + scalers are written to saves/ and consumed by nb6's
prediction cells and nb7.

Run: uv run python data_tools/train_models.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import fantabeto_dist as fd

tf.keras.backend.set_floatx("float32")
tfk = tf.keras

MID = "mid_outputs"
SAVES = "saves"
TAIL_MIN, TAIL_RANGE_OF, TAIL_RANGE_GK = 0.5, 1.2, 0.8


def _read_seasons(fname):
    """Concat a database_entries file across TRAIN_SEASONS (+ current if built)."""
    frames = []
    for s in config.TRAIN_SEASONS:
        p = f"{MID}/season{s}/{fname}" if s != config.CURRENT_SEASON else f"{MID}/{fname}"
        if os.path.exists(p):
            frames.append(pd.read_excel(p, index_col=0))
        else:
            print(f"  (skip missing {p})")
    return pd.concat(frames, ignore_index=True)


def _nll(tail_range):
    return lambda yt, yp: fd.sinharcsinh_nll_tf(yt, yp, tail_min=TAIL_MIN, tail_range=tail_range)


def train_outfield():
    db = _read_seasons("database_entries.xlsx")
    npdb = np.array(db)
    y = npdb[:, [5, 9]].astype("float32")          # vote, fantavote
    f_start = 14
    X = npdb[:, f_start:].astype("float32")
    toadd = np.zeros((X.shape[0], 4), dtype="float32")
    toadd[:, 0] = npdb[:, 4]                        # home
    toadd[:, 1] = npdb[:, 10] == "D"
    toadd[:, 2] = npdb[:, 10] == "C"
    toadd[:, 3] = npdb[:, 10] == "A"
    X = np.concatenate((X, toadd), axis=1).astype("float32")

    scaler = StandardScaler().fit(X)
    Xtr_, Xte_, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=12)
    Xtr, Xte = scaler.transform(Xtr_), scaler.transform(Xte_)

    inp = tfk.layers.Input(shape=(Xtr.shape[1],), name="input")
    h = tfk.layers.Dropout(0.2)(inp)
    h = tfk.layers.Dense(16, activation="relu")(h)
    h = tfk.layers.Dropout(0.2)(h)
    h = tfk.layers.Dense(16, activation="relu")(h)
    x1 = tfk.layers.Dense(8, activation="sigmoid")(h)
    out1 = tfk.layers.Dense(4, activation="linear")(x1)   # raw SinhArcsinh params (vote)
    x2 = tfk.layers.Dense(8, activation="sigmoid")(h)
    out2 = tfk.layers.Dense(4, activation="linear")(x2)   # raw SinhArcsinh params (fantavote)
    model = tfk.Model(inp, [out1, out2])
    model.compile(optimizer=tfk.optimizers.Nadam(learning_rate=0.001),
                  loss=[_nll(TAIL_RANGE_OF), _nll(TAIL_RANGE_OF)])
    cb = tfk.callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True)
    model.fit(Xtr, [ytr[:, 0], ytr[:, 1]], validation_split=0.15,
              epochs=1000, batch_size=256, callbacks=[cb], verbose=0)

    os.makedirs(SAVES, exist_ok=True)
    pickle.dump(scaler, open(f"{SAVES}/scaler.pkl", "wb"))
    model.save_weights(f"{SAVES}/modelb.weights.h5")
    _report("OUTFIELD", model, Xte, yte, TAIL_RANGE_OF, n_targets=2)
    return model


def train_gk():
    db = _read_seasons("database_entries_gk.xlsx")
    npdb = np.array(db)
    y = npdb[:, [5, 9, 6]].astype("float32")       # vote, fantavote, goals
    y[:, 2] = (y[:, 2] == 0) * 1.0                  # clean sheet
    f_start = 13
    X = npdb[:, f_start:].astype("float32")
    toadd = np.zeros((X.shape[0], 1), dtype="float32")
    toadd[:, 0] = npdb[:, 4]                        # home
    X = np.concatenate((X, toadd), axis=1).astype("float32")

    scaler = StandardScaler().fit(X)
    Xtr_, Xte_, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=18)
    Xtr, Xte = scaler.transform(Xtr_), scaler.transform(Xte_)

    inp = tfk.layers.Input(shape=(Xtr.shape[1],), name="input")
    h = tfk.layers.Dense(16, activation="relu")(inp)
    h = tfk.layers.Dropout(0.3)(h)
    h = tfk.layers.Dense(16, activation="relu")(h)
    x1 = tfk.layers.Dense(16, activation="sigmoid")(h)
    x1 = tfk.layers.Dropout(0.2)(x1)
    out1 = tfk.layers.Dense(4, activation="linear")(x1)
    x2 = tfk.layers.Dense(16, activation="sigmoid")(h)
    out2 = tfk.layers.Dense(4, activation="linear")(x2)
    x3 = tfk.layers.Dense(8, activation="sigmoid")(h)
    x3 = tfk.layers.Dropout(0.2)(x3)
    out3 = tfk.layers.Dense(1, activation="sigmoid")(x3)   # clean-sheet probability
    model = tfk.Model(inp, [out1, out2, out3])
    model.compile(optimizer=tfk.optimizers.Nadam(learning_rate=0.001),
                  loss=[_nll(TAIL_RANGE_GK), _nll(TAIL_RANGE_GK), "binary_crossentropy"])
    cb = tfk.callbacks.EarlyStopping(monitor="val_loss", patience=50, restore_best_weights=True)
    model.fit(Xtr, [ytr[:, 0], ytr[:, 1], ytr[:, 2]], validation_split=0.15,
              epochs=2500, batch_size=128, callbacks=[cb], verbose=0)

    pickle.dump(scaler, open(f"{SAVES}/scaler_gk.pkl", "wb"))
    model.save_weights(f"{SAVES}/modelb_gk.weights.h5")
    _report("GK", model, Xte, yte, TAIL_RANGE_GK, n_targets=2, clean_sheet=yte[:, 2])
    return model


def _sample_mean(raw, tail_range):
    """Mean of the SinhArcsinh predicted by raw params (per row)."""
    out = np.zeros(len(raw))
    for i, r in enumerate(raw):
        mu, sig, eps, dl = fd.constrain_params_np(r[0], r[1], r[2], r[3],
                                                  tail_min=TAIL_MIN, tail_range=tail_range)
        out[i] = fd.sample_sinharcsinh_np(mu, sig, eps, dl, 400).mean()
    return out


def _report(tag, model, Xte, yte, tail_range, n_targets, clean_sheet=None):
    preds = model.predict(Xte, verbose=0)
    for t in range(n_targets):
        m = _sample_mean(preds[t], tail_range)
        finite = np.isfinite(m).all()
        print(f"  [{tag}] target {t}: r2={r2_score(yte[:, t], m):.3f} "
              f"pred_mean[{m.min():.2f},{m.max():.2f}] finite={finite}")
    if clean_sheet is not None:
        p = preds[2].ravel()
        from sklearn.metrics import roc_auc_score
        print(f"  [{tag}] clean-sheet: p[{p.min():.2f},{p.max():.2f}] "
              f"AUC={roc_auc_score(clean_sheet, p):.3f} base_rate={clean_sheet.mean():.2f}")


if __name__ == "__main__":
    print("Training outfield model (TFP-free)...")
    train_outfield()
    print("Training goalkeeper model (TFP-free)...")
    train_gk()
    print("Done. Weights + scalers written to saves/.")
