"""Scrape the fantacalcio.it Classic quotazioni (roster + role + prices).

The quotazioni page is server-rendered (plain requests, no login) — the Excel
export API is premium-gated, but the table carries everything we need:
role (Classic), player name, team, QI (initial/asta price), QA (current price),
FVM (fantacalcio's own value metric).

-> fantacalcio/quotazioni_2627.csv  columns: id, r, name, team, price, fvm
   (team in the fbref last-word key: Inter, Milan, Verona, ...)
"""
import re
import sys

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.fantacalcio.it/quotazioni-fantacalcio"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


def team_key(slug):
    # href .../squadre/<slug>/...  ; 'hellas-verona' -> 'Verona', 'inter' -> 'Inter'
    return slug.split("-")[-1].capitalize()


def fetch(out="fantacalcio/quotazioni_2627.csv"):
    soup = BeautifulSoup(requests.get(URL, headers=UA, timeout=30).text, "lxml")
    rows = []
    for tr in soup.select("tbody tr.player-row"):
        role = tr.get("data-filter-role-classic", "").upper()
        a = tr.select_one("a.player-name")
        if not a or not role:
            continue
        name = a.get_text(strip=True)
        m = re.search(r"/squadre/([a-z-]+)/", a.get("href", ""))
        team = team_key(m.group(1)) if m else ""
        pid = tr.get("data-filter-team-id", "")

        def num(key):
            td = tr.select_one(f'td[data-col-key="{key}"]')
            try:
                return float(td.get_text(strip=True)) if td and td.get_text(strip=True) else 0
            except ValueError:
                return 0

        rows.append([pid, role, name, team, num("c_qi"), num("c_fvm")])
    df = pd.DataFrame(rows, columns=["id", "r", "name", "team", "price", "fvm"])
    df.to_csv(out, index=False)
    print(f"{len(df)} players -> {out}")
    print("roles:", df.r.value_counts().to_dict(), "| teams:", df.team.nunique(),
          "| price[%g,%g]" % (df.price.min(), df.price.max()))
    return df


if __name__ == "__main__":
    fetch(*(sys.argv[1:] or []))
