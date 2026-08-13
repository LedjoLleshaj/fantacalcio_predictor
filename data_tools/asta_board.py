"""Build the 2026/27 asta value board.

Cold-start: 2627 has no games yet, so each player's expected performance is the
retrained model applied to their 2025/26 statistical profile, evaluated against
an average opponent (home + away averaged). Joined to the scraped 2627 Classic
prices to rank players by VALUE (expected fantavoto per credit).

Inputs (all already present):
  fantacalcio/quotazioni_2627.csv            (fetch_quotazioni.py)
  mid_outputs/season2526/players_stats.xlsx  (2025/26 player profiles)
  mid_outputs/season2526/team_data.xlsx      (2025/26 team context)
  saves/modelb.weights.h5, modelb_gk.weights.h5, scaler*.pkl (retrained models)

Output: fantacalcio/asta_board_2627.xlsx (+ console top-value lists).
Players with no 2025/26 profile (promoted-team squads, new signings, rookies)
are listed separately with the model prediction unavailable — use fantacalcio's
FVM as the fallback there.
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd
import tensorflow as tf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fantabeto_dist as fd
import features as F
from build_lib import team_key

tfk = tf.keras
PAST = "mid_outputs/season2526"


def _of_model():
    inp = tfk.layers.Input((112,)); x = tfk.layers.Dropout(0.2)(inp)
    x = tfk.layers.Dense(16, "relu")(x); x = tfk.layers.Dropout(0.2)(x); x = tfk.layers.Dense(16, "relu")(x)
    o1 = tfk.layers.Dense(4)(tfk.layers.Dense(8, "sigmoid")(x))
    o2 = tfk.layers.Dense(4)(tfk.layers.Dense(8, "sigmoid")(x))
    m = tfk.Model(inp, [o1, o2]); m.load_weights("saves/modelb.weights.h5"); return m


def _gk_model():
    inp = tfk.layers.Input((90,)); x = tfk.layers.Dense(16, "relu")(inp)
    x = tfk.layers.Dropout(0.3)(x); x = tfk.layers.Dense(16, "relu")(x)
    g1 = tfk.layers.Dense(4)(tfk.layers.Dropout(0.2)(tfk.layers.Dense(16, "sigmoid")(x)))
    g2 = tfk.layers.Dense(4)(tfk.layers.Dense(16, "sigmoid")(x))
    g3 = tfk.layers.Dense(1, "sigmoid")(tfk.layers.Dropout(0.2)(tfk.layers.Dense(8, "sigmoid")(x)))
    m = tfk.Model(inp, [g1, g2, g3]); m.load_weights("saves/modelb_gk.weights.h5"); return m


def _mean_fv(raw4, tail_range):
    p = fd.constrain_params_np(*raw4, tail_min=0.5, tail_range=tail_range)
    return fd.sample_sinharcsinh_np(*p, 500).mean()


def _feature_frame(names, teams, players, team_data):
    """Per-player joined stats vs an average opponent (mirrors build_lib join)."""
    P = players.reindex(names); P.index = range(len(names))
    tm_idx = [t if t in team_data.index else "Avg" for t in teams]
    TM = team_data.reindex(tm_idx); TM.index = range(len(names))
    OP = team_data.reindex(["Avg"] * len(names)).add_prefix("opp_"); OP.index = range(len(names))
    full = pd.concat([P, TM, OP], axis=1)
    mins = pd.to_numeric(full["minutes"], errors="coerce").fillna(0)
    games = pd.to_numeric(full["games"], errors="coerce").fillna(0)
    return full, mins, games


def build(out="fantacalcio/asta_board_2627.xlsx"):
    q = pd.read_csv("fantacalcio/quotazioni_2627.csv")
    players = pd.read_excel(f"{PAST}/players_stats.xlsx", index_col=3)
    team_data = pd.read_excel(f"{PAST}/team_data.xlsx", index_col=0)
    avg = pd.DataFrame([team_data.mean(numeric_only=True)], index=["Avg"])
    avg["team"] = "Avg"
    team_data = pd.concat([team_data, avg])

    have = q[q.name.isin(players.index)].copy()
    miss = q[~q.name.isin(players.index)].copy()
    of = have[have.r != "P"].reset_index(drop=True)
    gk = have[have.r == "P"].reset_index(drop=True)

    of_m, gk_m = _of_model(), _gk_model()
    sc_of = pickle.load(open("saves/scaler.pkl", "rb"))
    sc_gk = pickle.load(open("saves/scaler_gk.pkl", "rb"))

    # ---- outfield ----
    full, mins, games = _feature_frame(list(of.name), list(of.team), players, team_data)
    abs_part = full[F.features_abs[4:]].astype(float)                 # drop r,games,games_starts,minutes
    rel = full[F.features_rel].astype(float).div(mins.clip(lower=1), axis=0)
    rel[F.features_rel_gamecorr] = rel[F.features_rel_gamecorr].mul(mins / games.clip(lower=1) / 90, axis=0)
    base = pd.concat([abs_part, rel], axis=1).to_numpy("float32")
    fv = np.zeros(len(of))
    for home in (1, 0):
        add = np.zeros((len(of), 4), "float32"); add[:, 0] = home
        add[:, 1] = (of.r == "D"); add[:, 2] = (of.r == "C"); add[:, 3] = (of.r == "A")
        raw = of_m.predict(sc_of.transform(np.concatenate([base, add], axis=1)), verbose=0)
        fv += np.array([_mean_fv(r, 1.2) for r in np.array(raw[1])]) / 2
    of["exp_FV"] = fv
    of["apps25"] = pd.to_numeric(players.reindex(of.name)["games"].values, errors="coerce")

    # ---- goalkeepers ----
    fullg, minsg, _ = _feature_frame(list(gk.name), list(gk.team), players, team_data)
    absg = fullg[F.features_abs_gk[3:]].astype(float)                 # drop gk_games,gk_games_starts,gk_minutes
    relg = fullg[F.features_rel_gk].astype(float).div(minsg.clip(lower=1), axis=0)
    baseg = pd.concat([absg, relg], axis=1).to_numpy("float32")
    fvg = np.zeros(len(gk)); csg = np.zeros(len(gk))
    for home in (1, 0):
        add = np.zeros((len(gk), 1), "float32"); add[:, 0] = home
        raw = gk_m.predict(sc_gk.transform(np.concatenate([baseg, add], axis=1)), verbose=0)
        fvg += np.array([_mean_fv(r, 0.8) for r in np.array(raw[1])]) / 2
        csg += np.array(raw[2]).ravel() / 2
    gk["exp_FV"] = fvg; gk["clean_sheet_pct"] = (csg * 100).round(1)
    gk["apps25"] = pd.to_numeric(players.reindex(gk.name)["gk_games"].values, errors="coerce")

    board = pd.concat([of, gk], ignore_index=True)
    # Season projection = per-match FV x expected appearances (2025/26 games, a
    # playing-time proxy). This is what wins fantacalcio and it kills the
    # "buy a EUR1 backup" trap that raw exp_FV/price falls into.
    board["apps25"] = board["apps25"].fillna(0).clip(upper=38)
    board["proj_pts"] = (board["exp_FV"] * board["apps25"]).round(0)
    board["value"] = (board["proj_pts"] / board["price"].clip(lower=1)).round(1)
    board["exp_FV"] = board["exp_FV"].round(2)
    # nailed starter = played >= 25 last season
    board["starter"] = board["apps25"] >= 25

    board["source"] = "model"

    # ---- score the 149 without a 2025/26 profile via FVM calibration ----
    # affine_players.txt is empty, so map FVM -> projected points per role with a
    # per-role linear fit (slope+intercept) on the model-scored players, clamped to
    # a sane season range. Lower confidence (FVM correlates ~0.4) -> source="fvm".
    fit = {}
    for r in ["P", "D", "C", "A"]:
        s = board[(board.r == r) & (board.fvm > 0)]
        fit[r] = np.polyfit(s.fvm, s.proj_pts, 1) if len(s) > 2 else (0.0, 150.0)
    miss = miss.copy()
    miss["exp_FV"] = np.nan; miss["clean_sheet_pct"] = np.nan; miss["apps25"] = np.nan
    miss["proj_pts"] = miss.apply(
        lambda x: round(float(np.clip(fit[x.r][0] * x.fvm + fit[x.r][1], 90, 260))), axis=1)
    miss["value"] = (miss.proj_pts / miss.price.clip(lower=1)).round(1)
    miss["starter"] = False
    miss["source"] = "fvm"

    full = pd.concat([board, miss], ignore_index=True)
    full = _assign_tiers(full)

    order = {"must-have": 0, "value": 1, "sleeper": 2, "unrated": 3, "filler": 4, "avoid": 5}
    full["_t"] = full.tier.map(order)
    full = full.sort_values(["r", "_t", "value"], ascending=[True, True, False]).drop(columns="_t")
    cols = ["name", "team", "r", "tier", "price", "apps25", "exp_FV", "proj_pts", "value",
            "clean_sheet_pct", "fvm", "source"]
    full = full[cols]

    with pd.ExcelWriter(out) as w:
        full.to_excel(w, sheet_name="board", index=False)
        for t in ["must-have", "value", "sleeper", "unrated", "avoid"]:
            full[full.tier == t].to_excel(w, sheet_name=t, index=False)
    print(f"board -> {out}  ({len(board)} model-scored + {len(miss)} FVM-estimated = {len(full)})")
    print("\ntier counts by role:")
    print(pd.crosstab(full.r, full.tier).to_string())
    for role, label in [("P", "GK"), ("D", "DEF"), ("C", "MID"), ("A", "ATT")]:
        print(f"\n=== {label} — MUST-HAVE + top VALUE ===")
        sub = full[(full.r == role) & (full.tier.isin(["must-have", "value"]))].head(14)
        c = ["name", "team", "tier", "price", "apps25", "proj_pts", "value", "source"] + (["clean_sheet_pct"] if role == "P" else [])
        print(sub[c].to_string(index=False))
    return full


def _assign_tiers(full):
    """Per-role tiers. Priority (high->low): must-have, avoid, value, sleeper, filler."""
    full = full.copy()
    full["tier"] = "filler"
    for r in full.r.unique():
        sub = full[full.r == r]
        pproj = sub.proj_pts.rank(pct=True)
        pval = sub.value.rank(pct=True)
        price_hi = sub.price.quantile(0.60)
        med_proj = sub.proj_pts.median()
        # FVM-estimated players have no real playing-time signal; only let them
        # into the top tiers when the price itself implies a starter (>= 6).
        credible = (sub.source == "model") | (sub.price >= 6)
        t = pd.Series("filler", index=sub.index)
        # cheap + upside/uncertain (rookies, rotation, FVM-scored) with a real floor
        t[(sub.price <= 6) & ((~sub.starter) | (sub.source == "fvm")) & (pproj >= 0.45)] = "sleeper"
        # underpriced real production
        t[(pval >= 0.70) & (sub.proj_pts >= med_proj) & credible] = "value"
        # premium price, weak value
        t[(sub.price >= price_hi) & (pval <= 0.30)] = "avoid"
        # top producers you build the roster around
        t[(pproj >= 0.85) & credible] = "must-have"
        # the model can't judge FVM-only players (new to Serie A / promoted squads);
        # never call them 'avoid'/'filler' -> 'unrated' (lean on price + your read).
        t[(sub.source == "fvm") & t.isin(["avoid", "filler"])] = "unrated"
        full.loc[sub.index, "tier"] = t
    return full


if __name__ == "__main__":
    build()
