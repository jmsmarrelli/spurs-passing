"""Measuring how a team's points got created.

An assist is the only piece of passing that the public play-by-play records. It
is a thin instrument - there is no touch count, no pass count, no secondary
assist, no time-of-possession - and the interesting part of the project is what
can honestly be built out of something that thin.

Two quantities do the work.

**How much of the scoring came off a pass.** The share of made field goals that
carry an assist. Simple, and immediately contaminated: a three is assisted about
83% of the time and a two about 51%, so any team that shoots more threes scores
as more generous without passing more. The fix is to price the shot mix first -
give each team the assisted rate its own two/three split would produce at league
rates for that season - and read the residual.

**How many people did the creating.** A team can run everything through one
point guard and still assist on two thirds of its baskets. The Spurs claim is
not about volume, it is about distribution, so the second measure is the
effective number of assisters: the inverse Herfindahl of a team-season's assists
across its players. Five players sharing the creation equally scores 5.0; one
player doing all of it scores 1.0.

Neither measure depends on an action-type label or a shot coordinate, which is
deliberate. Both of those were re-recorded mid-sample; the assist tag was not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Every abbreviation a real franchise appears under in this feed, 2003-04 to
# 2022-23. Seattle becomes Oklahoma City, New Jersey becomes Brooklyn, and
# Charlotte's two spells share a code.
#
# The list is not decoration. The mirror files the All-Star Game under the same
# season type as the regular season, so without it the rankings pick up rosters
# called EAST, WEST, LEB, GIA, DUR, STE, USA and WORLD - and an exhibition in
# which nobody plays defence is the most generous passing team ever recorded.
FRANCHISES = {
    "ATL", "BKN", "BOS", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GS",
    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NJ", "NO",
    "NY", "OKC", "ORL", "PHI", "PHX", "POR", "SA", "SAC", "SEA", "TOR",
    "UTAH", "WSH",
}


def team_totals(events: pd.DataFrame) -> pd.DataFrame:
    """Made field goals and assisted counts per team-season, split by shot value."""
    g = events.groupby(["season", "team"], observed=True)
    out = g.agg(
        made_fg=("assisted", "size"),
        assisted=("assisted", "sum"),
        made2=("is_three", lambda s: int((~s.astype(bool)).sum())),
        made3=("is_three", "sum"),
    ).reset_index()
    two = events[~events["is_three"].astype(bool)].groupby(["season", "team"], observed=True)
    three = events[events["is_three"].astype(bool)].groupby(["season", "team"], observed=True)
    out = out.merge(two["assisted"].sum().rename("ast2").reset_index(),
                    on=["season", "team"], how="left")
    out = out.merge(three["assisted"].sum().rename("ast3").reset_index(),
                    on=["season", "team"], how="left")
    return out.fillna({"ast2": 0, "ast3": 0})


def league_rates(totals: pd.DataFrame) -> pd.DataFrame:
    """The league's own assisted rate on twos and on threes, season by season."""
    g = totals.groupby("season")
    return pd.DataFrame({
        "league_ast2": g["ast2"].sum() / g["made2"].sum(),
        "league_ast3": g["ast3"].sum() / g["made3"].sum(),
        "league_assisted": g["assisted"].sum() / g["made_fg"].sum(),
    }).reset_index()


def price_shot_mix(totals: pd.DataFrame, rates: pd.DataFrame) -> pd.DataFrame:
    """Assisted rate, the rate the team's own shot mix predicts, and the gap.

    `expected` is what this team would have assisted on if it converted twos and
    threes in the proportion it actually did and drew assists at the league's
    rate for each. The residual is the part of the passing that the shot chart
    does not explain, which is the only part worth arguing about.
    """
    d = totals.merge(rates, on="season", how="left")
    d["assisted_rate"] = d["assisted"] / d["made_fg"]
    d["three_share"] = d["made3"] / d["made_fg"]
    d["expected"] = (d["league_ast3"] * d["three_share"]
                     + d["league_ast2"] * (1 - d["three_share"]))
    d["above_mix"] = d["assisted_rate"] - d["expected"]
    return d


def effective_assisters(assists: pd.DataFrame) -> pd.DataFrame:
    """Inverse Herfindahl of a team-season's assists across players.

    Reads as "how many players were really creating". It is a distribution
    measure, not a count: a sixth man with 4% of the assists moves it barely at
    all, and two guards splitting 60% of them move it a lot.
    """
    rows = []
    for (season, team), block in assists.groupby(["season", "team"], observed=True):
        n = block["assists"].to_numpy(dtype=float)
        total = n.sum()
        if total <= 0:
            continue
        share = n / total
        rows.append({"season": season, "team": team,
                     "assists": int(total),
                     "assisters": int((n > 0).sum()),
                     "eff_assisters": float(1.0 / np.square(share).sum()),
                     "top_share": float(share.max())})
    return pd.DataFrame(rows)


def rank_within_season(d: pd.DataFrame, col: str, ascending: bool = False) -> pd.Series:
    return d.groupby("season")[col].rank(ascending=ascending, method="min")
