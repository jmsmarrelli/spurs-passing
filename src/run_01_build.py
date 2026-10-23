"""Stage 1 - twenty seasons of play-by-play down to what this project needs.

    python src/run_01_build.py

Reads one season file at a time, keeps the made field goals, records who scored,
who assisted and whether it was worth three, and writes two small tables:

    data/processed/team_totals.csv    one row per team-season
    data/processed/assists.csv        one row per player per team-season
    data/processed/team_strength.csv  games and point differential per team-season
    output/coverage.csv               what the feed contains, and what was dropped
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import OUT, PROC, RAW, SEASONS  # noqa: E402
import passing as P  # noqa: E402

ASSIST_PATTERNS = [
    # The sentence was reworded partway through the sample; the id column was
    # not, so the id is what the analysis keys on and the name is decoration.
    re.compile(r"\(([^()]+?) assists?\)\s*$"),
    re.compile(r"Assisted by (.+?)\.\s*$"),
]

COLS = ["game_id", "season", "season_type", "type_text", "scoring_play", "text",
        "score_value", "team_id", "athlete_id_1", "athlete_id_2",
        "home_score", "away_score",
        "home_team_id", "home_team_abbrev", "away_team_id", "away_team_abbrev"]

# Regular season only. The mirror uses 2 for it and 3 for the postseason.
REGULAR = 2


def season_path(season: int) -> Path:
    return RAW / "pbp" / f"play_by_play_{season}.csv.gz"


def assister_names(text: pd.Series) -> pd.Series:
    """Pull the passer's name out of the event sentence, both eras of it."""
    out = pd.Series(pd.NA, index=text.index, dtype="object")
    t = text.fillna("")
    for pattern in ASSIST_PATTERNS:
        found = t.str.extract(pattern, expand=False)
        out = out.where(out.notna(), found)
    return out


def abbrev_map(pbp: pd.DataFrame) -> dict:
    """team_id -> abbreviation, taken from the schedule fields on every row."""
    home = pbp[["home_team_id", "home_team_abbrev"]].dropna().drop_duplicates()
    away = pbp[["away_team_id", "away_team_abbrev"]].dropna().drop_duplicates()
    home.columns = away.columns = ["team_id", "abbrev"]
    both = pd.concat([home, away], ignore_index=True).drop_duplicates("team_id")
    return dict(zip(both["team_id"].astype("int64"), both["abbrev"]))


def load_season(season: int) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    path = season_path(season)
    if not path.exists():
        raise SystemExit(f"missing {path}. See data/README.md.")
    pbp = pd.read_csv(path, usecols=COLS, low_memory=False)
    pbp = pbp[pbp["season_type"] == REGULAR]
    names = abbrev_map(pbp)
    strength = final_scores(pbp, names, season)

    made = pbp[pbp["scoring_play"].fillna(False).astype(bool)].copy()
    # Free throws are scoring plays and are never assisted. They would drag the
    # denominator around with the whistle rather than with the passing.
    ft = made["type_text"].fillna("").str.contains("Free Throw")
    made = made[~ft]

    # Two kinds of broken row, both rare and both dropped rather than guessed
    # at: a made field goal with no team on it (22 rows in twenty seasons) and
    # one recorded as worth zero points (245 rows, all from 2012-13 on). Counted
    # in output/coverage.csv so the drop is visible rather than silent.
    no_team = int(made["team_id"].isna().sum())
    made = made[made["team_id"].notna()]
    bad_value = int((~made["score_value"].isin([2, 3])).sum())
    made = made[made["score_value"].isin([2, 3])]

    made["team"] = made["team_id"].astype("int64").map(names)
    made["is_three"] = (made["score_value"] == 3).astype(int)
    made["assisted"] = made["athlete_id_2"].notna().astype(int)
    made["assister"] = assister_names(made["text"])
    made["season"] = season
    keep = ["season", "game_id", "team", "athlete_id_1", "athlete_id_2",
            "assister", "is_three", "assisted"]
    exhibition = int((~made["team"].isin(P.FRANCHISES)).sum())
    made = made[made["team"].isin(P.FRANCHISES)]

    audit = {"season": season, "dropped_no_team": no_team,
             "dropped_zero_value": bad_value,
             "dropped_exhibition": exhibition}
    return made[keep], audit, strength


def final_scores(pbp: pd.DataFrame, names: dict, season: int) -> pd.DataFrame:
    """One row per game: the two teams and the final score.

    The running score is on every event, so the last event of a game carries the
    result. It is used only as a control - the question is whether distributed
    passing is a property of good offences or of teams with nobody good enough
    to dominate the ball - so a point differential per game is precise enough
    and needs no possession count.
    """
    last = pbp.groupby("game_id").tail(1)
    g = pd.DataFrame({
        "season": season,
        "game_id": last["game_id"].to_numpy(),
        "home": last["home_team_id"].map(names).to_numpy(),
        "away": last["away_team_id"].map(names).to_numpy(),
        "home_score": last["home_score"].to_numpy(),
        "away_score": last["away_score"].to_numpy(),
    }).dropna()
    g = g[g["home"].isin(P.FRANCHISES) & g["away"].isin(P.FRANCHISES)]
    home = g.assign(team=g["home"], margin=g["home_score"] - g["away_score"])
    away = g.assign(team=g["away"], margin=g["away_score"] - g["home_score"])
    return pd.concat([home[["season", "game_id", "team", "margin"]],
                      away[["season", "game_id", "team", "margin"]]],
                     ignore_index=True)


def main() -> None:
    events, coverage, audit, strength = [], [], [], []
    for season in SEASONS:
        e, a, st = load_season(season)
        events.append(e)
        audit.append(a)
        strength.append(st)
        coverage.append({
            "season": season,
            "games": int(e["game_id"].nunique()),
            "made_fg": int(len(e)),
            "assisted_rate": float(e["assisted"].mean()),
            "three_share": float(e["is_three"].mean()),
        })
        print(f"  {season}: {coverage[-1]['games']:,} games, "
              f"{coverage[-1]['made_fg']:,} made field goals", flush=True)
    events = pd.concat(events, ignore_index=True)

    totals = P.team_totals(events)
    totals.to_csv(PROC / "team_totals.csv", index=False)

    made = events[events["assisted"] == 1]
    assists = (made.groupby(["season", "team", "athlete_id_2"], observed=True)
               .size().rename("assists").reset_index()
               .rename(columns={"athlete_id_2": "athlete_id"}))
    assists["athlete_id"] = assists["athlete_id"].astype("int64")
    # The most common spelling wins, so a single mangled row cannot rename a
    # player. Falls back to the id when no sentence parsed at all.
    names = (made.dropna(subset=["assister"])
             .groupby("athlete_id_2")["assister"]
             .agg(lambda s: s.value_counts().idxmax()))
    assists["player"] = assists["athlete_id"].map(names).fillna(
        assists["athlete_id"].astype(str))
    assists.to_csv(PROC / "assists.csv", index=False)
    unnamed = int(assists["player"].eq(assists["athlete_id"].astype(str)).sum())

    team_games = pd.concat(strength, ignore_index=True)
    quality = (team_games.groupby(["season", "team"], observed=True)["margin"]
               .agg(games="size", margin="mean").reset_index())
    quality.round(5).to_csv(PROC / "team_strength.csv", index=False)

    cov = pd.DataFrame(coverage).merge(pd.DataFrame(audit), on="season")
    cov.round(5).to_csv(OUT / "coverage.csv", index=False)

    print(f"\n{len(events):,} made field goals, {len(totals)} team-seasons")
    print(f"{len(assists):,} player-team-season assist rows, "
          f"{unnamed} without a name recovered from the event text")
    print()
    print(cov.to_string(index=False, float_format=lambda v: f"{v:.4f}"))


if __name__ == "__main__":
    main()
