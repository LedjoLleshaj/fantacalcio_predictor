"""Central run configuration for the fantabeto pipeline.

Edit these values to run a new matchday / season, instead of editing
hardcoded notebook cells.
"""

# --- Season selection ---
CURRENT_SEASON = "2627"                 # season being predicted, YYMM (Serie A 2026/27)
TRAIN_SEASONS = ["2223", "2425", "2526"]  # seasons whose datasets feed training
MATCHDAY_OUT = 1                        # upcoming matchday to predict

# --- Model load / retrain flags ---
LOAD_MODEL_OF = False   # outfield: load saved weights?
REFIT_MODEL_OF = True   # outfield: (re)train?
LOAD_MODEL_GK = False   # goalkeeper: load saved weights?
REFIT_MODEL_GK = True   # goalkeeper: (re)train?

# --- Data directories (relative to repo root) ---
FBREF_DATA = "fbref_data"
MID_OUTPUTS = "mid_outputs"
OUTPUTS = "outputs"
SAVES = "saves"
FANTACALCIO = "fantacalcio"


def season_dir(base: str, season: str) -> str:
    """Path for a season's data under `base`.

    Current season lives directly in `base`; past seasons under `season<YYMM>/`.
    """
    if season == CURRENT_SEASON:
        return base
    return f"{base}/season{season}"
