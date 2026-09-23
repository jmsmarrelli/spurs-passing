"""Paths, seasons and the handful of choices the pipeline exposes."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
FIG = ROOT / "figures"
OUT = ROOT / "output"

for d in (RAW, PROC, FIG, OUT):
    d.mkdir(parents=True, exist_ok=True)

# Season label is the year the season ends: 2014 == 2013-14.
#
# The play-by-play mirror carries 2001-02 and 2002-03 as well, at 38% and 81% of
# the games. Partial coverage is fine for a game-level question and is not fine
# for a team-season average, so the sample starts where the feed is essentially
# complete and ends where it stops.
FIRST_SEASON = 2004
LAST_SEASON = 2023
SEASONS = list(range(FIRST_SEASON, LAST_SEASON + 1))

TEAM = "SA"
TEAM_NAME = "San Antonio Spurs"
SUBJECT_SEASON = 2014          # 2013-14, the season the phrase was coined about

# A team-season needs this many made field goals to appear in the rankings. No
# season in the sample comes close to failing it; the floor is there so a future
# partial season cannot quietly enter the tables.
MIN_MADE_FG = 1500

SEED = 20240117
