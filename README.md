# fantabeto

**Fantacalcio Bayesian Estimated Team's Outcome** — a machine-learning system that predicts Serie A player performances for *Fantacalcio* (Italian fantasy football) and turns those predictions into the two decisions that win a league: **who to buy at the auction** and **who to field each week**.

> Original write-up: [How I won at Italian fantasy football using machine learning](https://pub.towardsai.net/how-i-won-at-italian-fantasy-football-fantacalcio-using-machine-learning-ce8fc3fdcaef)

It predicts two quantities per player per match, as **probability distributions** (not point estimates):

- **voto** — the match rating.
- **fantavoto** — voto plus bonus/malus from goals, assists, cards. This is what scores your team.

Data comes from [fantacalcio.it](https://www.fantacalcio.it) (votes, prices, probable line-ups), [fbref.com](https://fbref.com) (player/team stats) and [Understat](https://understat.com) (expected-goals). Trained on Serie A **2022/23 + 2024/25 + 2025/26**, predicting **2026/27**.

![team predictions](README_files/team_predictions.png)

---

## How the machine learning works

Two neural networks — one for **outfield players**, one for **goalkeepers** — take a player's season profile plus his team's and the opponent's context, and output the **parameters of a skewed `SinhArcsinh` distribution** for voto and fantavoto. The skew matters: a striker's fantavoto has a fat right tail (the goal games), and the model captures that asymmetry instead of collapsing it to an average.

- **Training loss** is the SinhArcsinh negative log-likelihood — the network learns the whole distribution, not just the mean.
- **Goalkeepers** get a third output: a **clean-sheet probability** (sigmoid head, trained with binary cross-entropy), which feeds the defense modifier and clean-sheet bonus.
- All the distribution math lives in [`fantabeto_dist.py`](fantabeto_dist.py) (pdf, log-likelihood loss, sampler, quantiles). *2026 revive note:* this replaced `tensorflow-probability`, which is deprecated on Python 3.12 — the model architecture is unchanged.

Because the outputs are distributions, a **Monte-Carlo lineup simulator** ([notebook 7](7_lineup_simulation.ipynb)) samples every player thousands of times to produce a whole team's **points distribution** — expected total, upside, and the effect of the Modificatore Difesa and clean sheets.

![lineup prediction](README_files/lineup_prediction.png)

---

## How to use it to win

Fantacalcio is won in two moments. The tools map to each.

### 1. The Asta (auction / draft) — build the best possible squad

The model gives each player an **expected fantavoto**. Multiplied by his **expected appearances**, that's a **projected season points** total. Divided by his **price**, that's **value**. The goal of the draft is to maximize total projected points within your budget and roster — so you want the players whose production is *underpriced*, and you want to avoid paying a name-tax.

The `data_tools/` scripts do exactly this:

```bash
uv run python data_tools/fetch_quotazioni.py   # scrape official 2026/27 prices + roles
uv run python data_tools/fetch_probabili.py    # scrape round-1 probable line-ups (live starter status)
uv run python data_tools/asta_board.py         # -> fantacalcio/asta_board_2627.xlsx
uv run python data_tools/asta_plan.py 500      # per-role budget + target squad (any budget)
```

**`asta_board_2627.xlsx`** ranks all ~500 players and tiers them:

| Tier | Meaning |
|------|---------|
| **must-have** | top season producers — anchor the roster on these |
| **value** | underpriced confirmed starters — your edge over rivals |
| **sleeper** | cheap upside / breakout bets |
| **unrated** | new signings / promoted squads the model can't score — lean on price |
| **avoid** | premium price, weak production |

Two columns tell you **whether a player will actually play** — the single most important thing:

- **`role_lock`** — season-long role from last year's appearances (`nailed` / `likely` / `rotation` / `bench`).
- **`r1`** — live from round-1 *probabili formazioni* (`STARTER` / `DOUBT` / `INJURED` / `SUSPENDED`).

`value`/`must-have` picks exclude benchwarmers, and the build **warns** on top picks flagged hurt or suspended. `asta_plan.py` then splits the budget attack-heavy (goals drive points) and fills each role with a barbell: a couple of studs + cheap value starters.

There's a printable **[asta cheat sheet](https://claude.ai/code/artifact/7d9f2eeb-49f0-43c0-851d-045b689e243a)** (scoring, point→goal table, budget split, auction playbook) to keep open on draft day.

### 2. Weekly — field the best XI

Once the season is live, each matchday: predict every player's fantavoto ([notebook 6](6_neural_network_training_and_prediction.ipynb)), then run the lineup simulator ([notebook 7](7_lineup_simulation.ipynb)) to pick the **XI that maximizes simulated team points**, choose a **captain** (highest expected fantavoto with upside), and decide whether to chase the **defense modifier**.

---

## Pipeline

Notebooks run in numeric order; each stage writes files consumed by the next (see [`CLAUDE.md`](CLAUDE.md) for the full map).

1. **`1_scraping_fbref`** — team & player stats from fbref.
2. **`2_votes_dataset_creation`** — the votes dataset (target variable).
3. **`3` / `3b`** — per-player season stats (current / past seasons).
4. **`4` / `4b`** — join into per-player-per-match training rows.
5. **`5_scraping_match_probable_players`** — probable line-ups for the upcoming matchday.
6. **`6_neural_network_training_and_prediction`** — train the two models, predict a matchday.
7. **`7_lineup_simulation`** — Monte-Carlo team-score distribution + optimal lineup.

The data-build logic (notebooks 2/3/4) is factored into [`data_tools/build_lib.py`](data_tools/build_lib.py) so it is testable and the notebooks stay thin. Run knobs (season, matchday, model flags) live in [`config.py`](config.py).

## Setup

```bash
uv sync                 # Python 3.12 environment (no tensorflow-probability)
uv run jupyter lab      # run the notebooks
uv run pytest           # tests for fantabeto_dist
```

## Current state & honest limits

- Target season **2026/27**; models retrained on 2022/23 + 2024/25 + 2025/26.
- **Cold start:** before the season plays, asta predictions lean on each player's 2025/26 profile — transfers and role changes aren't fully captured (the `r1` probabili overlay covers round-1 reality).
- **Degraded features:** fbref no longer serves ~73 advanced Serie A stats (passing/possession/GCA); the model leans on goals/assists/xG/minutes/cards. Predictions are directionally sound (backtest: positive vote correlation, GK clean-sheet AUC ≈ 0.73), not razor-sharp.

## Credits

- [Fantacalcio.it](https://www.fantacalcio.it) — the game, and a lot of the data (votes, prices, probable line-ups).
- [FBref.com](https://fbref.com) — player and team statistics.
- [Understat](https://understat.com) — expected-goals data.
- [amiles2233/ff_prob](https://github.com/amiles2233/ff_prob) — inspiration for distributional / Bayesian modelling of fantasy scores.
- [parth1902/Scrape-FBref-data](https://github.com/parth1902/Scrape-FBref-data) — FBref scraping.

`#fantacalcio #fantasy-football #serie-a #machine-learning #neural-networks`
