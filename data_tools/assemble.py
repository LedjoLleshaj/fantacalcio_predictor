import json, io, os, sys
import pandas as pd

SP = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(SP, "fbref_raw")
REPO = "/Users/ledjolleshaj/projects/fantacalcio_predictor"
NAMECOLS = {'player','nationality','position','team','age','birth_year'}
OUTFIELD = ['stats','shooting','passing','passing_types','gca','defense','possession','misc']
ALLCATS = OUTFIELD + ['keepers','keepersadv']

def load(season, cat, which):
    d = json.load(open(os.path.join(RAW, f"{season}__{cat}.json")))
    csv = d.get(which) or ""
    if not csv.strip(): return None
    return pd.read_csv(io.StringIO(csv))

def dedup_cols(df):
    return df.loc[:, ~df.columns.duplicated()]

def target_cols(fname):
    d = pd.read_csv(os.path.join(REPO, "fbref_data/season2223", fname), nrows=0)
    return list(d.columns)

def finalize(df, target, keycols):
    df = dedup_cols(df)
    df = df.reindex(columns=target)          # exact schema, missing->NaN, extras dropped
    statcols = [c for c in df.columns if c not in NAMECOLS and c not in keycols]
    df[statcols] = df[statcols].fillna(0)
    return df

def build_season(season, outdir):
    os.makedirs(outdir, exist_ok=True)
    # OUTFIELD players: positional concat (order verified identical)
    frames=[load(season,c,'player') for c in OUTFIELD]
    of = pd.concat(frames, axis=1)
    of = finalize(of, target_cols("outfield_players.csv"), {})
    of.to_csv(os.path.join(outdir,"outfield_players.csv"), index=False)
    # KEEPERS: merge keepers+keepersadv on player+team
    k1=load(season,'keepers','player'); k2=load(season,'keepersadv','player')
    kp = pd.concat([k1,k2],axis=1)
    kp = finalize(kp, target_cols("keepers_players.csv"), {})
    kp.to_csv(os.path.join(outdir,"keepers_players.csv"), index=False)
    # TEAMS for / vs: merge all 10 categories' squad tables on 'team'
    for which,fname in [('squad_for','teams.csv'),('squad_against','teams_vs.csv')]:
        merged=None
        for c in ALLCATS:
            s=load(season,c,which)
            if s is None: continue
            s=dedup_cols(s)
            merged = s if merged is None else merged.merge(s, on='team', how='outer', suffixes=('',f'_{c}'))
        merged = finalize(merged, target_cols(fname), {'team'})
        merged.to_csv(os.path.join(outdir,fname), index=False)
    return of.shape, kp.shape

for season, sub in [("2425","season2425"),("2526","season2526")]:
    outdir=os.path.join(REPO,"fbref_data",sub)
    of,kp=build_season(season,outdir)
    print(f"{season}: outfield {of}, keepers {kp} -> {outdir}")
