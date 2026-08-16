"""Asta budget calculator: total credits -> per-role budget + target squad.

Splits the budget attack-heavy (goals drive fantacalcio points), then fills each
role with a barbell:
  * ANCHORS  — the studs you build around. Picked by fantacalcio FVM/price
    (market consensus), because the cold-start model's projections are compressed
    and do NOT rank the expensive elites — so we let the market flag them and the
    model flag the bargains.
  * VALUES   — cheap, underpriced starters from the model's value/must-have tiers.

Reference prices are the fantacalcio QI; real bids run higher, so leftover =
your bidding room. Run: uv run python data_tools/asta_plan.py [TOTAL] (default 500)
"""
import sys

import pandas as pd

BOARD = "fantacalcio/asta_board_2627.xlsx"

# roster + strategy (Classic 3-8-8-6). Edit if your league differs.
ROLE_PCT = {"A": 0.58, "C": 0.24, "D": 0.12, "P": 0.06}
ROLE_SLOTS = {"A": 6, "C": 8, "D": 8, "P": 3}
ROLE_ANCHORS = {"A": 2, "C": 2, "D": 1, "P": 1}
ROLE_NAME = {"P": "GOALKEEPERS", "D": "DEFENDERS", "C": "MIDFIELDERS", "A": "ATTACKERS"}
TAIL_RESERVE = 0.05


def fill_role(df, n_slots, n_anchor):
    anchors = df.sort_values("fvm", ascending=False)                  # studs by market
    values = df[(df.source == "model") & (df.tier.isin(["value", "must-have"]))] \
        .sort_values("value", ascending=False)                       # model bargains
    cheap = df.sort_values("price")
    picks, taken = [], set()

    def take(row, kind):
        if row["name"] not in taken and len(picks) < n_slots:
            picks.append((kind, row)); taken.add(row["name"])

    for _, r in anchors.iterrows():
        if len([p for p in picks if p[0] == "anchor"]) >= n_anchor:
            break
        take(r, "anchor")
    for _, r in values.iterrows():
        take(r, "value")
    for _, r in cheap.iterrows():                                     # top up to n_slots
        take(r, "filler")
    return picks


def plan(total=500):
    board = pd.read_excel(BOARD, sheet_name="board")
    usable = round(total * (1 - TAIL_RESERVE))
    print(f"\nTOTAL {total} credits  ({usable} to allocate, {total - usable} held for bid wars)\n")
    grand = 0
    for r in ["A", "C", "D", "P"]:
        budget = round(ROLE_PCT[r] * usable)
        picks = fill_role(board[board.r == r], ROLE_SLOTS[r], ROLE_ANCHORS[r])
        spent = sum(p[1]["price"] for p in picks)
        grand += spent
        print(f"=== {ROLE_NAME[r]}  ({ROLE_SLOTS[r]} slots · budget ~{budget} · targets sum {spent:.0f}) ===")
        for kind, p in picks:
            cs = f"  cs {p['clean_sheet_pct']:.0f}%" if r == "P" and pd.notna(p["clean_sheet_pct"]) else ""
            src = "" if p["source"] == "model" else "  (unrated)"
            print(f"   {kind:<6} {p['name']:<18} {p['team']:<11} {int(p['price']):>3}cr  proj {p['proj_pts']:>3.0f}  fvm {int(p['fvm']):>3}{cs}{src}")
        print()
    print(f"target-price sum {grand:.0f} / {total}.  Anchors will be bid up — that's what the "
          f"{total - grand:.0f} headroom + {total - usable} reserve are for.")
    print("Anchors are market studs (incl. new signings the model can't score); values are model bargains.")


if __name__ == "__main__":
    plan(int(sys.argv[1]) if len(sys.argv) > 1 else 500)
