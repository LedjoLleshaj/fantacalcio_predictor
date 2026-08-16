"""Scrape fantacalcio.it round-1 probabili formazioni -> live starter status.

Server-rendered, plain requests. Each team's probable XI is a `ul.team-lineup`;
doubtful/injured/suspended players live in their own lists. This gives real
2026/27 starter confirmation (vs the board's last-season role proxy).

-> fantacalcio/probabili_2627.csv  columns: name, team, r1
   r1 in {STARTER, DOUBT, INJURED, SUSPENDED}  (team = fbref last-word key)
"""
import re
import sys

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
# list class -> status. Order matters: later (worse) availability overrides.
LISTS = [("team-lineup", "STARTER"), ("doubts-list", "DOUBT"),
         ("suspendeds-list", "SUSPENDED"), ("injured-list", "INJURED")]
PRIORITY = {"STARTER": 0, "DOUBT": 1, "SUSPENDED": 2, "INJURED": 3}


def _team(href):
    m = re.search(r"/squadre/([a-z-]+)/", href or "")
    return m.group(1).split("-")[-1].capitalize() if m else ""


def fetch(out="fantacalcio/probabili_2627.csv"):
    soup = BeautifulSoup(requests.get(URL, headers=UA, timeout=30).text, "lxml")
    md = soup.find(string=re.compile(r"Giornata\s*\d+"))
    status = {}                                    # name -> (r1, team), worst wins
    for cls, tag in LISTS:
        for ul in soup.select(f"ul.{cls}"):
            for a in ul.select("a.player-name, a.player-link"):
                name = a.get_text(strip=True)
                if not name:
                    continue
                cur = status.get(name)
                if cur is None or PRIORITY[tag] > PRIORITY[cur[0]]:
                    status[name] = (tag, _team(a.get("href")))
    df = pd.DataFrame([[n, t, r1] for n, (r1, t) in status.items()],
                      columns=["name", "team", "r1"])
    df.to_csv(out, index=False)
    print(f"{(md or 'round ?').strip()}: {len(df)} players -> {out}")
    print(df.r1.value_counts().to_dict())
    return df


if __name__ == "__main__":
    fetch(*(sys.argv[1:] or []))
