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

## STILL NEEDED
- Quotazioni_Fantacalcio.xlsx (player prices/list) for current season.
- seriea_calendar.xlsx (fixtures -> oppteam/home) for 2024-25, 2025-26, 2026-27.
- Integration: adapt nb2/nb3/nb4 to consume voti_scraped.csv + the assembled
  fbref/Understat CSVs (the old nb2 parses fantacalcio's Excel export layout).
