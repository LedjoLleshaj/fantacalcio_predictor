# ASTA GUIDE — Serie A 2026/27

Everything you need, in reading order. Budget **1000 credits**, roster **3P / 8D / 8C / 6A = 25**.

---

## 1. How the game works

You manage a fantasy team of real Serie A players. Each matchday you field **11 starters** in an allowed
formation. Every player who actually plays gets a **voto** (journalist rating, ~6 = average). Bonus and
malus for what he did in the real match are added on top — that total is his **fantavoto**.

Your **team score = sum of your 11 starters' fantavoti** (+ the defence modifier, below). That total is
converted into **goals**, and you're matched against one rival each round. More goals wins.

If a starter doesn't play, he gets **SV (no vote)** and your bench replaces him — **same role only** in our
league. If nobody covers the role, the *riserva d'ufficio* gives you a **3** (2 for a keeper), which is a
disaster. So: never leave a role uncovered on the bench.

---

## 2. Our league's exact rules

### Bonus / malus

| Bonus | | Malus | |
|---|---|---|---|
| Gol segnato | **+3** | Rigore sbagliato | **−3** |
| Rigore segnato | **+3** | Autogol | **−2** |
| Rigore parato (GK) | **+3** | Espulsione | **−1** |
| Assist standard / gold | **+1** | Gol subito (GK, each) | **−1** |
| Porta inviolata (GK) | **+1** | Ammonizione | **−0.5** |
| Assist soft | 0 | Gol pareggio / vittoria | 0 |

### Points → goals

Threshold **66 = 1 goal**, then **+1 goal every 6 points**:
66 → 1 · 72 → 2 · 78 → 3 · 84 → 4 · 90 → 5 · 96 → 6 · 102 → 7 · 108 → 8

The **F1 competition** pays by matchday rank: **25 / 18 / 12 / 10 / 8 / 6 / 4 / 3 / 2 / 1**.
Winning a round is worth far more than placing — so **upside matters**, not just a safe average.

### Modificatore difesa — ON (this is the big one)

Requires **at least 4 defenders fielded**. Computed on **voto only** (no bonus/malus), averaging the
**best 3 defenders + the goalkeeper** (the GK *is* included):

| Avg voto | Bonus |
|---|---|
| < 6 | 0 |
| ≥ 6.00 | **+1** |
| ≥ 6.50 | **+2** |
| ≥ 7.00 | **+4** |
| ≥ 7.50 | **+6** |

Worth roughly **+1.6 per matchday ≈ 60 points a season ≈ 10 extra goals**.

### Other settings that change strategy

- **No fattore capitano** — no captain multiplier. Never pay a premium for "captain material".
- **Substitutions unlimited but Traditional** — same role only, no formation change.
- **Riserva d'ufficio** — voto 3 outfield / 2 goalkeeper. Cover every role.
- **Disponibilità singola** — each player belongs to one roster only.
- **Bench** — 2P / 3D / 3C / 3A. **Formations hidden**, 5-minute lineup timeout.

---

## 3. How the tool picks players

Two neural networks (one outfield, one goalkeeper) predict each player's **voto** and **fantavoto** — not as
a single number, but as a **probability distribution**, so a striker's "he might haul" upside is modelled
rather than averaged away. The goalkeeper model also outputs a **clean-sheet probability**.

From those the board computes:

- **exp_FV** — expected fantavoto per match.
- **exp_MV** — expected **voto** per match → this is what the defence modifier is scored on.
- **proj_pts** — exp_FV × expected appearances = projected season points.
- **value** — proj_pts ÷ price. **This is the draft edge**: production the market has underpriced.

Two columns tell you whether he'll actually play:

- **role_lock** — from last season's appearances: `nailed` / `likely` / `rotation` / `bench`.
- **r1** — live from round-1 probabili formazioni: `STARTER` / `DOUBT` / `INJURED` / `SUSPENDED`.

### Tiers

| Tier | Meaning |
|---|---|
| **must-have** | Top season producers — anchor the roster on these |
| **value** | Underpriced confirmed starters — where you beat your friends |
| **sleeper** | Cheap upside / breakout bets |
| **unrated** | New signings & promoted squads the model can't score — judge by price |
| **avoid** | Premium price, weak production — let someone else overpay |

**Important:** prices on the board are fantacalcio **QI**, calibrated to a 500 budget. With 1000 credits
expect the market to clear near **2× QI**.

---

## 4. The strategy

**Buy a defensive BLOCK.** Because the modificatore averages your best 3 defenders **plus** your keeper,
buying all four from the *same strong defence* means a single clean sheet lifts every one of them together
and spikes the bonus to +4 or +6. This is the single highest-leverage move in our ruleset.

Best blocks available:

| Team | Clean sheet | Block | ~Cost (2× QI) |
|---|---|---|---|
| **Milan** | 58% | Maignan + Pavlovic, Gila, Bartesaghi | ~98 |
| **Como** | 57% | Butez + Ramon, Kempf, Valle | ~74 |
| **Bologna** | 55% | Skorupski + Miranda J., Zortea, Vitik | ~58 |
| **Roma** | 54% | Svilar + Mancini, Wesley, Hermoso | ~120 |
| **Juventus** | 53% | Perin + Bremer, Celik, Kalulu | ~84 |
| **Inter** | 50% | Provedel + Dimarco, Bisseck, Akanji | ~122 |

Then: **2 attacker anchors + 2 midfield anchors**, and fill everything else from the **value** tier.
Budget split, defence-weighted because the modificatore is on: **ATT 45% · MID 23% · DEF 22% · GK 10%**.

---

## 5. Your plan at 1000 credits

```
==========================================================================
ASTA PLAN — 1000 credits   (allocate 940, hold 60 for bid wars)
Market clears near 2x QI at this budget — 'target' columns are scaled.
==========================================================================

### DEFENSIVE BLOCK — Milan (clean sheet 58%)  ~98 cr
    Modificatore difesa is scored on these four at once: one clean sheet
    lifts every voto together and spikes the bonus to +4/+6.
    P  Maignan            Milan       QI 15 -> target    30  voto 6.22
    D  Pavlovic           Milan       QI 14 -> target    28  voto 6.19
    D  Gila               Milan       QI 12 -> target    24  voto 6.00
    D  Bartesaghi         Milan       QI  8 -> target    16  voto 5.98

=== ATTACKERS — budget ~423 cr (6 slots, targets ~156) ===
   anchor Martinez L.        Inter       QI 35 -> target    70  voto 6.32 fv 7.38
   anchor Malen              Roma        QI 34 -> target    68  voto 6.30 fv 7.52
   value  Buksa              Udinese     QI  2 -> target     4  voto 5.96 fv 6.34
   value  N'Dri              Lecce       QI  3 -> target     6  voto 5.85 fv 5.96
   value  Borrelli           Cagliari    QI  4 -> target     8  voto 6.00 fv 6.62

=== MIDFIELDERS — budget ~216 cr (8 slots, targets ~140) ===
   anchor Paz N.             Como        QI 30 -> target    60  voto 6.31 fv 7.45
   anchor McTominay          Napoli      QI 28 -> target    56  voto 6.35 fv 7.29
   value  Fadera             Como        QI  2 -> target     4  voto 5.96 fv 6.28
   value  Masini             Frosinone   QI  2 -> target     4  voto 5.93 fv 5.97
   value  Ordonez C.         Parma       QI  2 -> target     4  voto 5.85 fv 5.96
   value  Lipani             Sassuolo    QI  2 -> target     4  voto 5.89 fv 5.93
   value  De Roon            Atalanta    QI  4 -> target     8  voto 5.96 fv 6.12

=== DEFENDERS — budget ~207 cr (8 slots; 3 filled by the block, targets ~26) ===
   value  Ranieri L.         Fiorentina  QI  3 -> target     6  voto 5.88 fv 5.93
   value  Athekame           Milan       QI  3 -> target     6  voto 5.96 fv 6.23
   value  De Winter          Milan       QI  3 -> target     6  voto 5.79 fv 5.96
   value  Pongracic          Fiorentina  QI  4 -> target     8  voto 5.82 fv 5.84

=== GOALKEEPERS — budget ~94 cr (3 slots; 1 filled by the block, targets ~4) ===
   value  Sportiello         Atalanta    QI  1 -> target     2  voto 6.27 fv 5.27  cs 38%
   value  Christensen O.     Fiorentina  QI  1 -> target     2  voto 6.34 fv 5.13  cs 20%

--------------------------------------------------------------------------
targets total ~424 / 1000. The rest is bidding headroom — anchors go above QI.
Fill the last slots with EUR1-3 same-role bench cover: substitutions are
Traditional (same role only) and riserva d'ufficio scores 3 (2 for GK).
```

---

## 6. Formations — ranked for our rules

| # | Module | When to use it |
|---|---|---|
| **1** | **4-3-3** | Default. Modificatore active + 3 attackers (goals are the biggest lever). |
| **2** | **4-4-2** | Third striker has a bad fixture, or your midfield is the strong suit. |
| **3** | **5-3-2** | Your defensive block faces weak opponents — maximise clean-sheet exposure. |

Allowed: 3-4-3 · 3-5-2 · 4-3-3 · 4-4-2 · 4-5-1 · 5-3-2 · 5-4-1.

**Never 3-4-3 or 3-5-2.** Swapping a defender for a midfielder gains about **+0.35** fantavoto but forfeits
about **1.6** of modificatore — a **net −1.2 per matchday**. Only if injuries leave you unable to field
four defenders.

---

## 7. Draft-day checklist

### 15 minutes before

- [ ] Refresh the data (prices and probabili move daily):
  ```bash
  uv run python data_tools/fetch_quotazioni.py && uv run python data_tools/fetch_probabili.py && uv run python data_tools/asta_board.py
  ```
- [ ] Run the plan: `uv run python data_tools/asta_plan.py 1000`
- [ ] Open `fantacalcio/asta_board_2627.xlsx` — sheets: `must-have`, `value`, `sleeper`, `unrated`
- [ ] Write **hard max bids** for your block + your 3–4 anchors, decided cold
- [ ] Baseline: 1000 ÷ 25 = **40 credits average per slot**

### During the auction

- [ ] Every ~5 picks check **credits left ÷ slots left ≥ 5**. Falling toward 2 = you overspent.
- [ ] Secure the **defensive block early** — GK + 3 defenders from one strong team.
- [ ] Anchors: chase to your written max, then **walk away instantly**.
- [ ] Fill from the **value** tier — that's the underpriced production.
- [ ] Cover **every role** on the bench (same-role subs only).
- [ ] Nominate players you *don't* want, to drain rivals' credits.
- [ ] Last slots: make sure you can field a legal XI first, upside second.

### The 5-second call (first "no" ends it)

1. Do I still need this role? Full → pass.
2. Is he a starter (`role_lock` / `r1`)? No → pass, unless a €1 flyer.
3. Tier? must-have / value → bid. avoid → pass. unrated → price + your own read.
4. Over my written max? → drop it now.

### Don'ts

- Don't blow 80% of the budget early — you'll be left with €1 non-players.
- Don't buy three keepers who don't play.
- Don't panic-buy the next name after losing a target.
- Don't bid on a `value` player you haven't confirmed will start.
- Don't field fewer than 4 defenders.

---

## 8. Watch-outs before you bid

### Flagged for round 1 (temporary — fine to own, don't overpay)

| Player | Team | Role | Status |
|---|---|---|---|
| Ekhator | Juventus | A | INJURED |
| Konè I. | Sassuolo | C | INJURED |
| Cataldi | Lazio | C | DOUBT |
| Mkhitaryan | Inter | C | SUSPENDED |
| Pellegrini Lu. | Lazio | D | INJURED |
| Britschgi | Parma | D | SUSPENDED |
| Kabasele | Udinese | D | SUSPENDED |
| Idrissi R. | Cagliari | D | INJURED |

### Top `unrated` — model is blind here, judge on price

New signings and promoted squads with no Serie A history for the model to learn from.

| Player | Team | Role | QI | ~Market |
|---|---|---|---|---|
| Ramos G. | Milan | A | 27 | 54 |
| Kolo Muani | Juventus | A | 26 | 52 |
| Mastantuono | Fiorentina | C | 12 | 24 |
| Alajbegovic | Juventus | C | 12 | 24 |
| Adams A. | Venezia | A | 12 | 24 |
| Kevin Carlos | Cagliari | A | 13 | 26 |
| Tourè E. | Parma | A | 11 | 22 |
| Spence | Inter | D | 12 | 24 |

### Honest limits

- **Cold start** — the model scores players on their **2025/26** form. Transfers and new roles aren't
  captured; the `r1` column is your correction for round-1 reality.
- **Degraded stats** — fbref stopped publishing ~73 advanced Serie A metrics, so the model leans on
  goals, assists, xG, appearances and cards. Directionally sound, not razor-sharp.
- **Verify the block** against the actual 2026/27 squads before bidding — the scraped roster contains
  transfers I couldn't independently confirm.

---

## 9. After the asta — the weekly routine

Once matchdays are played, each week:

```bash
# 1. refresh data + probable lineups   2. predict the matchday   3. simulate your lineup
uv run python data_tools/fetch_probabili.py
# notebooks 2-4 (build), 6 (predict -> outputs/pred_matchday_N.xlsx), 7 (lineup simulation)
```

Then field the XI with the highest simulated total, keeping 4+ defenders whenever your block has a
reasonable fixture. There's no captain to pick in our league — just maximise the sum.

---

*Printable one-page version: https://claude.ai/code/artifact/7d9f2eeb-49f0-43c0-851d-045b689e243a*
