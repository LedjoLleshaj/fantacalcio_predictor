"""Asta budget plan for OUR league (rules encoded below).

League rules that drive the strategy:
  * Budget 1000, roster 3P/8D/8C/6A = 25, bench 2P/3D/3C/3A.
  * MODIFICATORE DIFESA **ON** — needs >=4 defenders fielded, computed on VOTO
    (no bonus/malus) of the best 3 defenders + the goalkeeper:
      >=6 -> +1 | >=6.5 -> +2 | >=7 -> +4 | >=7.5 -> +6
    A defensive block from a high-clean-sheet team spikes all four at once.
  * Porta inviolata +1, gol subito -1  -> clean-sheet% is doubly valuable for GK.
  * NO fattore capitano -> no premium for a "captain" stud; maximize the total.
  * Unlimited substitutions but TRADITIONAL (same role only, no module change)
    -> real bench cover needed in EVERY role; riserva d'ufficio is a disaster
    (voto 3 outfield / 2 GK), so never leave a role uncovered.
  * Goal thresholds 66 then +1 goal per 6 pts; F1 competition table rewards
    winning the matchday -> upside matters, not just the average.

Prices on the board are fantacalcio QI, calibrated to a 500 budget, so with
1000 credits expect the market to clear near 2x QI. Targets below are scaled.

Run: uv run python data_tools/asta_plan.py [TOTAL]   (default 1000)
"""
import sys

import pandas as pd

BOARD = "fantacalcio/asta_board_2627.xlsx"
QI_BASE = 500                      # budget the QI price list is calibrated to

# Defense-weighted split (modificatore difesa is ON and includes the GK).
ROLE_PCT = {"A": 0.45, "C": 0.23, "D": 0.22, "P": 0.10}
ROLE_SLOTS = {"A": 6, "C": 8, "D": 8, "P": 3}
ROLE_ANCHORS = {"A": 2, "C": 2, "D": 2, "P": 1}
ROLE_NAME = {"P": "GOALKEEPERS", "D": "DEFENDERS", "C": "MIDFIELDERS", "A": "ATTACKERS"}
TAIL_RESERVE = 0.06
MOD_MIN_CS = 45.0                  # team clean-sheet% that makes a block worth it


def load():
    b = pd.read_excel(BOARD, sheet_name="board")
    cs = (b[(b.r == "P") & b.clean_sheet_pct.notna()]
          .groupby("team").clean_sheet_pct.max())
    b["team_cs"] = b.team.map(cs)          # team defensive strength for every player
    return b, cs.sort_values(ascending=False)


def defensive_block(b, cs, n_def=3):
    """GK + defenders from the best-clean-sheet team: correlated modificatore upside."""
    for team in cs.index:
        gk = b[(b.team == team) & (b.r == "P") & (b.role_lock == "nailed")]
        de = b[(b.team == team) & (b.r == "D") & b.role_lock.isin(["nailed", "likely"])]
        if len(gk) and len(de) >= n_def:
            return team, gk.nlargest(1, "exp_MV"), de.nlargest(n_def, "exp_MV")
    return None, None, None


def pick(df, n, by, exclude):
    d = df[~df.name.isin(exclude)]
    return d.nlargest(n, by)


def plan(total=1000):
    b, cs = load()
    scale = total / QI_BASE
    usable = round(total * (1 - TAIL_RESERVE))
    print(f"\n{'='*74}\nASTA PLAN — {total} credits   (allocate {usable}, hold {total-usable} for bid wars)")
    print(f"Market clears near {scale:.0f}x QI at this budget — 'target' columns are scaled.\n{'='*74}")

    team, gkb, deb = defensive_block(b, cs)
    taken = []
    if team:
        blk = pd.concat([gkb, deb])
        cost = blk.price.sum() * scale
        print(f"\n### DEFENSIVE BLOCK — {team} (clean sheet {cs[team]:.0f}%)  ~{cost:.0f} cr")
        print("    Modificatore difesa is scored on these four at once: one clean sheet")
        print("    lifts every voto together and spikes the bonus to +4/+6.")
        for _, p in blk.iterrows():
            print(f"    {p['r']}  {p['name']:<18} {p['team']:<11} QI {int(p['price']):>2} -> target {p['price']*scale:>5.0f}  voto {p['exp_MV']:.2f}")
        taken = list(blk.name)

    grand = blk.price.sum() * scale if team else 0
    for r in ["A", "C", "D", "P"]:
        budget = round(ROLE_PCT[r] * usable)
        pool = b[(b.r == r) & (b.source == "model") & (~b.r1.isin(["INJURED", "SUSPENDED"]))]
        starters = pool[pool.role_lock.isin(["nailed", "likely"])]
        # block members already fill slots in their role (never double-buy a premium GK)
        n_block = int((blk.r == r).sum()) if team else 0
        n_anchor = max(0, ROLE_ANCHORS[r] - n_block)
        anc = pick(starters, n_anchor, "fvm", taken)
        n_val = max(0, ROLE_SLOTS[r] - ROLE_ANCHORS[r] - (1 if r != "P" else 0) - max(0, n_block - ROLE_ANCHORS[r]))
        val = pick(starters[starters.tier.isin(["value", "must-have"])],
                   n_val, "value", taken + list(anc.name))
        sel = pd.concat([anc.assign(kind="anchor"), val.assign(kind="value")])
        spent = sel.price.sum() * scale
        grand += spent
        note = f"; {n_block} filled by the block" if n_block else ""
        print(f"\n=== {ROLE_NAME[r]} — budget ~{budget} cr ({ROLE_SLOTS[r]} slots{note}, targets ~{spent:.0f}) ===")
        for _, p in sel.iterrows():
            extra = f"  cs {p['clean_sheet_pct']:.0f}%" if r == "P" and pd.notna(p["clean_sheet_pct"]) else ""
            mark = "  <block>" if p["name"] in taken else ""
            print(f"   {p['kind']:<6} {p['name']:<18} {p['team']:<11} QI {int(p['price']):>2} -> target {p['price']*scale:>5.0f}"
                  f"  voto {p['exp_MV']:.2f} fv {p['exp_FV']:.2f}{extra}{mark}")
        taken += list(sel.name)

    print(f"\n{'-'*74}")
    print(f"targets total ~{grand:.0f} / {total}. The rest is bidding headroom — anchors go above QI.")
    print("Fill the last slots with EUR1-3 same-role bench cover: substitutions are")
    print("Traditional (same role only) and riserva d'ufficio scores 3 (2 for GK).")


if __name__ == "__main__":
    plan(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
