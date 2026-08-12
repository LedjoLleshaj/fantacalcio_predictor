# data_tools — fbref + Understat data acquisition (2026 revive)

fbref.com blocks automated scraping (Cloudflare) AND currently serves Serie A
with advanced stats stripped (xG/passing/GCA/possession/adv-defense absent).
See memory `fbref-advanced-stats-missing`.

## Current working method
1. **fbref basic stats** — extracted via the user's Cloudflare-cleared Chrome
   (browser subagent), per category page, cached as JSON, then `assemble.py`
   builds the 4 pipeline CSVs (`outfield_players`, `keepers_players`, `teams`,
   `teams_vs`) per season, schema-matched to `fbref_data/season2223/`.
2. **Understat xG top-up** — `merge_understat.py` pulls per-player xG/npxG/xA/
   shots/key_passes from Understat's AJAX endpoint
   `POST https://understat.com/main/getPlayersStats/` (data={'league':'Serie A',
   'season':'<start-year>'}) — works from plain `requests`, no Cloudflare — and
   fills the xg-family columns (xg, npxg, xg_per90, npxg_per90, xg_net,
   npxg_net, npxg_per_shot, assisted_shots) by accent-normalized name match
   (~90%).

## Coverage after both steps (per outfield_players.csv, 115 cols)
- Populated: basic stats (goals/assists/cards/minutes/shots) + xG family (~42 cols).
- STILL EMPTY (~73 cols): passing detail, GCA/SCA, possession (touches/carries),
  advanced defense — fbref no longer serves these for Serie A.

## Seasons
- 2024-25 -> fbref_data/season2425/  (Understat season '2024')
- 2025-26 -> fbref_data/season2526/  (Understat season '2025')
- current 2026-27 -> not yet fetched (season starting).

## fantacalcio voti (TARGET variable)
Scraped from fantacalcio.it voti pages (server-rendered, works via plain `requests`
OR browser): `https://www.fantacalcio.it/voti-fantacalcio-serie-a/<YYYY-YY>/<matchday>`.
Values live in DOM attributes: `.player-grade[data-value]` (voto),
`.player-fanta-grade[data-value]` (fantavoto), `.role[data-value]`, name in
`.player-name`. Italian decimal comma. The Excel-export API
(`/api/v1/Excel/votes/<seasonId>/<md>`) is premium-gated — scrape the page instead.
Consolidated to `fantacalcio/season2425/voti_scraped.csv` and `season2526/`
(cols: matchday, team, player, role, vote, fantavote, +_raw). ~12.6k rows/season.

## match scores (GK clean-sheet target)
`fetch_scores.py` pulls per-match Serie A final scores from **OpenFootball**
`football.json` (free, no key, plain `requests`, exact FT scores) ->
`fantacalcio/season<SS>/match_scores.csv` (matchday, team, oppteam, home,
goals_for, goals_against). Understat no longer serves match-level data (only
per-player season aggregates), hence OpenFootball. 2024-25 (`2425`) has md1-37
only (OpenFootball hasn't filled the final round); `2526` is complete.

## dataset build + training (integration)
`build_lib.py` ports nb2/nb3b/nb4b to the normalized inputs (voti_scraped +
fixtures + match_scores + assembled fbref CSVs), replacing the old Excel-export +
Quotazioni layout. `features.py` holds the model feature lists (auto-extracted
from nb4b so build_lib and the notebooks share one definition). Notebooks 2/3/3b/
4/4b are thin, runnable wrappers over `build_lib` (season-aware via
`config.season_dir`; nb3/nb4 build the current season, guarded until its inputs
exist; nb3b/4b build the training seasons). Outputs land in
`mid_outputs/season<SS>/` and positionally schema-match golden `season2223`.

`train_models.py` is the executable, validated core of the nb6 TFP removal:
retrains the outfield + goalkeeper models with `fantabeto_dist` (SinhArcsinh NLL
loss + sigmoid/binary-crossentropy clean sheet) on 2223+2425+2526 and writes
`saves/*.weights.h5` + scalers. nb6/nb7 contain the same TFP-free logic.

## STILL NEEDED (current-season 2026/27 prediction)
- Current-season inputs (voti_scraped, fixtures, match_scores, fbref) + build via
  nb2/nb3/nb4 once the season starts.
- Quotazioni_Fantacalcio.xlsx (player prices, for display) for the current season.
- nb5 probable lineups, then nb6 prediction + nb7 simulation.
