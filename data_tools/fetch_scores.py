"""Fetch per-match Serie A final scores and emit per-team goals-for/against.

Source: OpenFootball football.json (free, no key, scriptable, exact FT scores).
Understat no longer serves match-level data (only per-player season aggregates),
so this replaces the originally-planned Understat scores channel for the same
purpose: supplying the goalkeeper clean-sheet target (goals conceded == 0).

Output per season: fantacalcio/season<SS>/match_scores.csv
    columns: matchday, team, oppteam, home, goals_for, goals_against
    one row per team per match (760 rows/season), team names in the
    fantacalcio/fbref short-name convention used by voti_scraped.csv & fixtures.csv.
"""
import json
import re
import sys

import pandas as pd
import requests

# OpenFootball full name -> fantacalcio short name (union across 2425 + 2526).
TEAM_MAP = {
    "AC Milan": "Milan",
    "AC Monza": "Monza",
    "ACF Fiorentina": "Fiorentina",
    "AS Roma": "Roma",
    "Atalanta BC": "Atalanta",
    "Bologna FC 1909": "Bologna",
    "Cagliari Calcio": "Cagliari",
    "Como 1907": "Como",
    "Empoli FC": "Empoli",
    "FC Internazionale Milano": "Inter",
    "Genoa CFC": "Genoa",
    "Hellas Verona FC": "Hellas Verona",
    "Juventus FC": "Juventus",
    "Parma Calcio 1913": "Parma",
    "SS Lazio": "Lazio",
    "SSC Napoli": "Napoli",
    "Torino FC": "Torino",
    "US Lecce": "Lecce",
    "Udinese Calcio": "Udinese",
    "Venezia FC": "Venezia",
    "AC Pisa 1909": "Pisa",
    "US Cremonese": "Cremonese",
    "US Sassuolo Calcio": "Sassuolo",
}

SEASONS = {"2425": "2024-25", "2526": "2025-26"}
BASE = "https://raw.githubusercontent.com/openfootball/football.json/master/{yr}/it.1.json"


def _ft(score):
    """Full-time [home, away] from either {'ft': [...]} or a plain [h, a] list."""
    if isinstance(score, dict):
        return score.get("ft")
    return score


def build_season(ss, yr):
    data = json.loads(requests.get(BASE.format(yr=yr), headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text)
    rows = []
    unmapped = set()
    for m in data["matches"]:
        ft = _ft(m.get("score"))
        if not ft:  # unplayed
            continue
        md = int(re.search(r"(\d+)", m["round"]).group(1))
        t1, t2 = m["team1"], m["team2"]
        for t in (t1, t2):
            if t not in TEAM_MAP:
                unmapped.add(t)
        if unmapped:
            continue
        h, a = TEAM_MAP[t1], TEAM_MAP[t2]
        gh, ga = int(ft[0]), int(ft[1])
        rows.append([md, h, a, 1, gh, ga])  # home team
        rows.append([md, a, h, 0, ga, gh])  # away team
    if unmapped:
        raise SystemExit(f"[{ss}] unmapped OpenFootball teams: {sorted(unmapped)}")
    df = pd.DataFrame(rows, columns=["matchday", "team", "oppteam", "home", "goals_for", "goals_against"])
    df = df.sort_values(["matchday", "team"]).reset_index(drop=True)
    out = f"fantacalcio/season{ss}/match_scores.csv"
    df.to_csv(out, index=False)
    print(f"[{ss}] {len(df)} rows, matchdays {df.matchday.min()}-{df.matchday.max()}, "
          f"{df.team.nunique()} teams -> {out}")
    return df


if __name__ == "__main__":
    which = sys.argv[1:] or SEASONS.keys()
    for ss in which:
        build_season(ss, SEASONS[ss])
