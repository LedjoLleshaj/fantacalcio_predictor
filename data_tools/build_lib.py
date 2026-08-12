"""Dataset-build engine for the fantabeto pipeline (2026 revive).

Ports the logic of notebooks 2 / 3b / 4b to consume the NEW normalized inputs
(voti_scraped.csv + fixtures.csv + match_scores.csv + assembled fbref CSVs),
replacing the old fantacalcio Excel-export + Quotazioni layout. Notebooks 2, 3b
and 4b are thin wrappers over these functions so the logic is testable and the
notebooks stay runnable.

Key differences from the original notebooks (all verified against nb6 usage):
  * Roster / role / name backbone comes from voti_scraped (one entry per player:
    modal team + modal role), NOT Quotazioni_Fantacalcio.xlsx. 'r' is the only
    Quotazioni-derived feature nb6 uses, and voti carries it per season.
  * players_votes goals/assists/cards_malus are ZERO for outfield (nb6 features
    start at col 14; targets are cols 5,9 = vote,fantavote — the decomposition is
    carried but unused). For goalkeepers, 'goals' = net goals conceded (negative),
    sourced from match_scores.csv, because nb6 derives the clean-sheet target as
    (goals == 0).
  * All team names normalized to the fbref "last word" key (e.g. Hellas Verona ->
    Verona) so voti / fixtures / scores / team_data all join consistently — this
    is the key team_data is indexed by in nb4b.
  * keepers_ID is defined (= len(outfield_players)); it was referenced but never
    defined in nb3b (the golden season2223 stats were built via nb3).
"""
import unicodedata

import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(__file__))                       # for features
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root for config
import features as F
import config

MID = "mid_outputs"
FBREF = "fbref_data"
FC = "fantacalcio"


def _p(base, ss, fname):
    """Season-aware path: current season lives in <base>/, past seasons in
    <base>/season<ss>/ (via config.season_dir)."""
    return f"{config.season_dir(base, ss)}/{fname}"

# vote_avg padding defaults (from nb3b cell 18)
_MEAN_DEF, _STD_DEF = 6.0, 0.58
_MEAN_DEF_P, _STD_DEF_P = 6.22, 0.43
_MIN_VOTES = 6
_MIN_GK_GAMES = 6


def team_key(name):
    """fbref 'last word' team key: 'Hellas Verona' -> 'Verona', 'Inter' -> 'Inter'."""
    return str(name).split(" ")[-1]


def normalize_name(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("utf-8")


# ---------------------------------------------------------------- nb2: votes
def build_players_votes(ss):
    """-> mid_outputs/season<ss>/players_votes.xlsx

    Columns: matchday, player, team, oppteam, home, vote, goals, assists,
    cards_malus, fantavote. GK 'goals' = -goals_against (net conceded); outfield
    goals/assists/cards_malus = 0 (unused downstream).
    """
    voti = pd.read_csv(_p(FC, ss, "voti_scraped.csv"))
    # role 'all' = team-total rows; vote/fantavote 55 = fantacalcio 's.v.' (did not play)
    voti = voti[(voti["role"] != "all") & (voti["vote"] < 20)].copy()
    voti["team"] = voti["team"].map(team_key)

    fixtures = pd.read_csv(_p(FC, ss, "fixtures.csv"))
    opp = {}
    for _, r in fixtures.iterrows():
        h, a = team_key(r["home"]), team_key(r["away"])
        opp[(int(r["matchday"]), h)] = (a, 1)
        opp[(int(r["matchday"]), a)] = (h, 0)

    scores = pd.read_csv(_p(FC, ss, "match_scores.csv"))
    ga = {(int(r["matchday"]), team_key(r["team"])): int(r["goals_against"]) for _, r in scores.iterrows()}

    rows = []
    for _, r in voti.iterrows():
        key = (int(r["matchday"]), r["team"])
        if key not in opp:
            continue
        oppt, home = opp[key]
        role = str(r["role"]).upper()
        goals = 0
        if role == "P":
            if key not in ga:
                continue  # GK match with no score (e.g. 2425 md38) -> clean-sheet unknown, skip
            goals = -ga[key]
        rows.append([int(r["matchday"]), r["player"], r["team"], oppt, home,
                     float(r["vote"]), goals, 0, 0, float(r["fantavote"])])

    df = pd.DataFrame(rows, columns=["matchday", "player", "team", "oppteam", "home",
                                     "vote", "goals", "assists", "cards_malus", "fantavote"])
    df.to_excel(_p(MID, ss, "players_votes.xlsx"))
    return df


# --------------------------------------------------------- nb4b: team_data
def build_team_data(ss):
    """-> mid_outputs/season<ss>/team_data.xlsx (indexed by last-word team key)."""
    team = pd.read_csv(_p(FBREF, ss, "teams.csv"))
    vs = pd.read_csv(_p(FBREF, ss, "teams_vs.csv"))
    for i in range(1, team.shape[1]):
        team = team.rename(columns={team.columns[i]: "team_" + team.columns[i]})
    for i in range(1, vs.shape[1]):
        vs = vs.rename(columns={vs.columns[i]: "vs_team_" + vs.columns[i]})
    vs.pop("team")
    td = pd.concat([team, vs], axis=1)
    td["team_idx"] = td["team"].map(team_key)
    td = td.set_index("team_idx")
    td.to_excel(_p(MID, ss, "team_data.xlsx"))
    return td


# --------------------------------------------------------- nb3b: players_stats
def _roster_from_voti(ss):
    """Quotazioni-equivalent roster from voti_scraped: one row per player
    (modal team + modal role), columns [id, r, name, team]."""
    v = pd.read_csv(_p(FC, ss, "voti_scraped.csv"))
    v = v[(v["role"] != "all") & (v["vote"] < 20)].copy()
    v["team"] = v["team"].map(team_key)
    v["r"] = v["role"].str.upper()
    rows = []
    for name, g in v.groupby("player", sort=True):
        rows.append([name, g["r"].mode().iloc[0], g["team"].mode().iloc[0]])
    fc = pd.DataFrame(rows, columns=["name", "r", "team"])
    fc.insert(0, "id", range(1, len(fc) + 1))
    # match golden column order [id, r, name, team] — nb4b/nb6 read players_stats
    # with index_col=3 expecting 'name' at that position.
    return fc[["id", "r", "name", "team"]]


def build_players_stats(ss, seed=0):
    np.random.seed(seed)
    outfield_players = pd.read_csv(_p(FBREF, ss, "outfield_players.csv"))
    keeper_players = pd.read_csv(_p(FBREF, ss, "keepers_players.csv"))

    # fbref name backbone (outfield then keepers, continuous index)
    players = pd.concat([outfield_players[["player", "team"]], keeper_players[["player", "team"]]],
                        axis=0, ignore_index=True)
    keepers_ID = len(outfield_players)
    players["surname"] = players["player"]
    players["initial"] = players["player"]
    for i in range(players.shape[0]):
        players.loc[i, "surname"] = normalize_name(players.loc[i, "player"].split(" ")[-1]).replace("'", "")
        players.loc[i, "initial"] = players.loc[i, "player"][0]

    # name_fix: rewrite fbref surname FROM->TO so it matches the fantacalcio spelling
    name_fix = pd.read_csv("config/name_fix.txt")
    for i in range(name_fix.shape[0]):
        for j in range(players.shape[0]):
            if (players.loc[j, "surname"].lower() == str(name_fix.loc[i, "FROM"]).lower()
                    and team_key(players.loc[j, "team"]).lower() == team_key(name_fix.loc[i, "TEAM"]).lower()):
                players.loc[j, "surname"] = name_fix.loc[i, "TO"]

    # roster from voti (replaces Quotazioni)
    fc = _roster_from_voti(ss)
    fc["surname"] = fc["name"]
    fc["initial"] = fc["name"]
    for i in range(fc.shape[0]):
        spl = normalize_name(str(fc.loc[i, "name"]).replace("'", "")).split(" ")
        if "." in spl[-1]:
            fc.loc[i, "surname"] = spl[-2]
            fc.loc[i, "initial"] = spl[-1][0]
        else:
            fc.loc[i, "surname"] = spl[-1]
            fc.loc[i, "initial"] = ""

    # match fc -> fbref combined index (fb_ID), respecting GK/outfield split
    fc["fb_ID"] = -1
    for i in range(fc.shape[0]):
        for j in range(players.shape[0]):
            if team_key(fc.loc[i, "team"]).lower() in team_key(players.loc[j, "team"]).lower():
                if fc.loc[i, "surname"].lower() == players.loc[j, "surname"].lower():
                    if (fc.loc[i, "r"] == "P") == (j >= keepers_ID):
                        fc.loc[i, "fb_ID"] = j

    # copy outfield fbref stats (cols 4..) for non-GKs. Block-assign into an
    # object frame so string columns (fbref 'age' = "24-088") don't raise on
    # modern pandas; unmatched rows stay 0. These extra cols are carried, not
    # used as model features.
    cols_out = list(outfield_players.columns[4:])
    ofblock = pd.DataFrame(0, index=fc.index, columns=cols_out, dtype=object)
    sel = fc.index[(fc["fb_ID"] != -1) & (fc["r"] != "P")]
    if len(sel):
        ofblock.loc[sel, cols_out] = outfield_players.loc[fc.loc[sel, "fb_ID"].values, cols_out].values
    fc = pd.concat([fc, ofblock], axis=1)

    # copy keeper fbref stats (cols 4.., skipping age/birth_year, already added) for GKs
    delta_k = len(outfield_players)
    # keeper stats past age/birth_year, excluding cols already added from outfield
    # (e.g. minutes_90s) so no duplicate columns are created.
    cols_kp = [c for c in list(keeper_players.columns[4:])[2:] if c not in cols_out]
    kpblock = pd.DataFrame(0, index=fc.index, columns=cols_kp, dtype=object)
    selk = fc.index[(fc["fb_ID"] != -1) & (fc["r"] == "P") & (fc["fb_ID"] - delta_k >= 0)]
    if len(selk):
        kpblock.loc[selk, cols_kp] = keeper_players.loc[fc.loc[selk, "fb_ID"].values - delta_k, cols_kp].values
    fc = pd.concat([fc, kpblock], axis=1)

    # Numeric-coerce the fbref stat block; empty/absent -> 0 (the accepted decision
    # for the 73 advanced fbref cols fbref no longer serves, and for unmatched
    # players). 'age' ("24-088") is non-numeric and unused -> becomes 0.
    for c in cols_out + cols_kp:
        fc[c] = pd.to_numeric(fc[c], errors="coerce").fillna(0)

    # vote_avg / vote_std from players_votes (pad short samples with role default)
    votes = pd.read_excel(_p(MID, ss, "players_votes.xlsx"), index_col=0)
    vote_by_player = votes.groupby("player")["vote"].apply(lambda s: np.array(s, dtype=float))
    va, vs_ = [], []
    for i in range(fc.shape[0]):
        v = vote_by_player.get(fc.loc[i, "name"], np.array([]))
        mean_i, std_i = (_MEAN_DEF_P, _STD_DEF_P) if fc.loc[i, "r"] == "P" else (_MEAN_DEF, _STD_DEF)
        if v.shape[0] < _MIN_VOTES:
            v = np.append(v, np.random.normal(mean_i, std_i, _MIN_VOTES - v.shape[0]))
        va.append(np.mean(v))
        vs_.append(np.std(v))
    fc["vote_avg"] = va
    fc["vote_std"] = vs_

    # backfill thin-sample GKs toward a rostered team-mate GK
    gk_start = list(fc.columns).index("gk_games")
    cols_avg = fc.columns[gk_start:]
    fc[cols_avg] = fc[cols_avg].astype(float)  # weighted backfill produces floats
    fc_new = fc.copy()
    for i in range(fc.shape[0]):
        if fc.loc[i, "r"] == "P" and fc.loc[i, "gk_games"] < _MIN_GK_GAMES:
            j = None
            for k in range(fc.shape[0]):
                if fc.loc[i, "team"] == fc.loc[k, "team"] and fc.loc[k, "gk_games"] >= _MIN_GK_GAMES:
                    j = k
                    break
            if j is None:
                continue
            w = 1 - (_MIN_GK_GAMES - fc.loc[i, "gk_games"]) / _MIN_GK_GAMES
            fc_new.loc[i, cols_avg] = fc.loc[i, cols_avg] * w + (1 - w) * fc.loc[j, cols_avg]
    fc = fc_new

    fc.to_excel(_p(MID, ss, "players_stats.xlsx"))
    return fc


# --------------------------------------------------------- nb4b: database_entries
def build_database_entries(ss):
    """Vectorized equivalent of nb4b's row-by-row player_match_data join.

    For each votes row: player features from players_stats + team_/vs_team_ from
    the player's team + opp_* from the opponent, then features_rel scaled by
    minutes and features_rel_gamecorr by minutes/games/90 (same as ext/ext_gk).
    """
    players = pd.read_excel(_p(MID, ss, "players_stats.xlsx"), index_col=3)
    team_data = pd.read_excel(_p(MID, ss, "team_data.xlsx"), index_col=0)
    votes = pd.read_excel(_p(MID, ss, "players_votes.xlsx"), index_col=0)

    P = players.reindex(votes["player"].values); P.index = votes.index
    TM = team_data.reindex(votes["team"].values); TM.index = votes.index
    OP = team_data.reindex(votes["oppteam"].values).add_prefix("opp_"); OP.index = votes.index
    full = pd.concat([P, TM, OP], axis=1)
    minutes = pd.to_numeric(full["minutes"], errors="coerce").fillna(0)
    games = pd.to_numeric(full["games"], errors="coerce").fillna(0)

    def _scale(rel_cols, gamecorr=()):
        rel = full[rel_cols].astype(float).div(minutes.clip(lower=1), axis=0)
        if len(gamecorr):
            rel[list(gamecorr)] = rel[list(gamecorr)].mul(minutes / games.clip(lower=1) / 90, axis=0)
        return rel

    # outfield
    delta = pd.concat([full[F.features_abs], _scale(F.features_rel, F.features_rel_gamecorr)], axis=1)
    db = pd.concat([votes, delta], axis=1)
    db = db.drop(db[db.r == "P"].index)
    db = db.drop(db[db.r != db.r].index)          # NaN r = player not in players_stats
    db = db.drop(db[db.xg != db.xg].index)
    db.to_excel(_p(MID, ss, "database_entries.xlsx"))

    # goalkeepers
    delta_gk = pd.concat([full[F.features_abs_gk], _scale(F.features_rel_gk)], axis=1)
    db_gk = pd.concat([votes, delta_gk], axis=1)
    db_gk = db_gk.drop(db_gk[db_gk.gk_games != db_gk.gk_games].index)
    db_gk = db_gk.drop(db_gk[db_gk.gk_games <= 0].index)  # keep only real keepers
    db_gk.to_excel(_p(MID, ss, "database_entries_gk.xlsx"))
    return db, db_gk


def build_season(ss):
    build_players_votes(ss)
    build_team_data(ss)
    build_players_stats(ss)
    return build_database_entries(ss)
