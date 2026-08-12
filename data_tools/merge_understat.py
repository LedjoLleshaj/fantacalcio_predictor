import json, os, unicodedata
import pandas as pd, numpy as np
SP=os.path.dirname(os.path.abspath(__file__))
REPO="/Users/ledjolleshaj/projects/fantacalcio_predictor"

def norm(s):
    s=str(s).strip().lower()
    s=''.join(c for c in unicodedata.normalize('NFKD',s) if not unicodedata.combining(c))
    return s

for tag in ['2425','2526']:
    us=pd.DataFrame(json.load(open(f'{SP}/understat_{tag}.json')))
    for c in ['xG','npxG','xA','shots','key_passes','goals','npg','time','games']:
        us[c]=pd.to_numeric(us[c],errors='coerce')
    us['k']=us['player_name'].map(norm)
    us=us.drop_duplicates('k')

    of=pd.read_csv(f'{REPO}/fbref_data/season{tag}/outfield_players.csv')
    of['k']=of['player'].map(norm)
    m=of.merge(us[['k','xG','npxG','xA','shots','key_passes','goals','npg','time']],on='k',how='left',suffixes=('','_us'))
    matched=m['xG'].notna().sum()

    nn=m['xG'].notna()
    n90=(m['time']/90).replace(0,np.nan)
    # fill xg-family target columns
    m.loc[nn,'xg']=m.loc[nn,'xG']
    m.loc[nn,'npxg']=m.loc[nn,'npxG']
    m.loc[nn,'xg_per90']=(m['xG']/n90)[nn]
    m.loc[nn,'npxg_per90']=(m['npxG']/n90)[nn]
    m.loc[nn,'xg_net']=(m['goals_us']-m['xG'])[nn] if 'goals_us' in m else (m['goals']-m['xG'])[nn]
    m.loc[nn,'npxg_net']=(m['npg']-m['npxG'])[nn]
    sh=m['shots'].replace(0,np.nan)
    m.loc[nn,'npxg_per_shot']=(m['npxG']/sh)[nn]
    m.loc[nn,'assisted_shots']=m.loc[nn,'key_passes']
    # drop helper cols
    m=m.drop(columns=[c for c in ['k','xG','npxG','xA','shots','key_passes','goals_us','npg','time'] if c in m.columns])
    m.to_csv(f'{REPO}/fbref_data/season{tag}/outfield_players.csv',index=False)
    print(f'{tag}: fbref {len(of)} players, understat {len(us)}, matched {matched} ({100*matched//len(of)}%)')
