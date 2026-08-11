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
