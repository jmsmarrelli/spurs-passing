"""Stage 2 - price the passing, control it, and see where San Antonio lands.

    python src/run_02_beautiful.py

Writes output/team_seasons.csv, output/league_path.csv, output/league_summary.csv,
output/mix_check.csv, output/spurs_path.csv, output/among_the_good.csv,
output/persistence.csv, output/persistence_cutoffs.csv, output/spurs_passers.csv
and figures 01-05.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import FIG, MIN_MADE_FG, OUT, PROC, SUBJECT_SEASON, TEAM  # noqa: E402
import labels as L  # noqa: E402
import passing as P  # noqa: E402
import style as S  # noqa: E402

S.apply()

GOOD_MARGIN = 5.0     # what counts as a good team for the conditional comparison
TOP_N = 10            # how deep "near the top" goes in the persistence count


def season_label(season: int) -> str:
    return f"{season - 1}-{str(season)[2:]}"


def concentration(assists: pd.DataFrame) -> pd.DataFrame:
    """How much of a team-season's creation ran through its leading passers.

    The headline is the share held by the top two. The inverse-Herfindahl
    version is carried alongside it because it is the more standard measure and
    because it behaves badly here in a way worth showing: it counts the tail, so
    a team that used twenty-seven players scores as egalitarian for reasons that
    have nothing to do with how it played.
    """
    rows = []
    for (season, team), block in assists.groupby(["season", "team"], observed=True):
        n = np.sort(block["assists"].to_numpy().astype(float))[::-1]
        total = n.sum()
        if total <= 0:
            continue
        share = n / total
        rows.append({
            "season": season, "team": team, "assists": int(total),
            "assisters": int(len(n)),
            "top1": float(share[0]),
            "top2": float(share[:2].sum()),
            "eff_assisters": float(1.0 / np.square(share).sum()),
        })
    return pd.DataFrame(rows)


def top_passers(assists: pd.DataFrame, season: int, team: str, n: int = 3) -> str:
    b = assists[(assists["season"] == season) & (assists["team"] == team)]
    b = b.nlargest(n, "assists")
    total = assists.loc[(assists["season"] == season)
                        & (assists["team"] == team), "assists"].sum()
    return ", ".join(f"{r.player} {100 * r.assists / total:.1f}%" for r in b.itertuples())


def build(totals: pd.DataFrame, assists: pd.DataFrame,
          strength: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rates = P.league_rates(totals)
    d = P.price_shot_mix(totals, rates)
    d = d.merge(concentration(assists), on=["season", "team"], how="inner")
    d = d.merge(strength, on=["season", "team"], how="inner")
    d = d[d["made_fg"] >= MIN_MADE_FG].reset_index(drop=True)

    d["rank_above"] = P.rank_within_season(d, "above_mix")
    d["rank_rate"] = P.rank_within_season(d, "assisted_rate")
    d["rank_top2"] = P.rank_within_season(d, "top2", ascending=True)

    # Concentration is not independent of quality: good teams have somebody good
    # enough to run the offence through. Take that out before asking who was
    # unusually distributed, so the answer is not just a list of bad teams.
    z = lambda c: d.groupby("season")[c].transform(lambda x: (x - x.mean()) / x.std())
    d["z_top2"], d["z_margin"] = z("top2"), z("margin")
    d["z_above"] = z("above_mix")
    slope, intercept = np.polyfit(d["z_margin"], d["z_top2"], 1)
    d["top2_resid"] = d["z_top2"] - (slope * d["z_margin"] + intercept)
    d.attrs["quality_slope"] = float(slope)
    d.attrs["quality_r"] = float(np.corrcoef(d["margin"], d["top2"])[0, 1])
    return d, rates


def mix_check(d: pd.DataFrame) -> pd.DataFrame:
    """How much does pricing the shot mix actually change?

    The objection that the raw assisted rate is really a shot-location statistic
    is the obvious one, so it gets tested rather than assumed. It turns out to be
    a small effect in the cross-section, for a reason worth knowing: the teams
    that take the most threes also assist least on their twos, and the two
    roughly cancel.
    """
    z = lambda c: d.groupby("season")[c].transform(lambda x: (x - x.mean()) / x.std())
    slope = np.polyfit(d["three_share"], d["assisted_rate"], 1)[0]
    moved = (d.groupby("season")["assisted_rate"].rank(ascending=False)
             - d.groupby("season")["above_mix"].rank(ascending=False)).abs()
    return pd.DataFrame([{
        "within_season_r_three_vs_assisted": float(np.corrcoef(z("three_share"),
                                                               z("assisted_rate"))[0, 1]),
        "assisted_rate_per_unit_three_share": float(slope),
        "mean_three_share_sd_within_season": float(d.groupby("season")["three_share"].std().mean()),
        "mean_rank_change_when_priced": float(moved.mean()),
        "max_rank_change_when_priced": float(moved.max()),
    }])


def fig_contamination(rates: pd.DataFrame, league: pd.DataFrame, check: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 4.3))
    x = rates["season"]
    ax1.plot(x, 100 * rates["league_ast3"], color=S.SERIES[0], lw=2, zorder=3,
             label="on threes")
    ax1.plot(x, 100 * rates["league_ast2"], color=S.SERIES[1], lw=2, zorder=3,
             label="on twos")
    ax1.plot(x, 100 * rates["league_assisted"], color=S.INK, lw=2.2,
             ls=(0, (4, 2.5)), zorder=4, label="all field goals")
    for y, txt, col in ((100 * rates["league_ast3"].iloc[-1], "on threes", S.SERIES[0]),
                        (100 * rates["league_ast2"].iloc[-1], "on twos", S.SERIES[1]),
                        (100 * rates["league_assisted"].iloc[-1], "all", S.INK)):
        ax1.annotate(txt, (x.iloc[-1], y), xytext=(7, 0), textcoords="offset points",
                     va="center", fontsize=9, color=col, fontweight="semibold")
    ax1.set_xlim(x.min() - 0.4, x.max() + 5.6)
    ax1.set_ylim(0, 95)
    ax1.set_ylabel("Assisted share of made field goals")
    ax1.set_yticks(range(0, 91, 20), [f"{v}%" for v in range(0, 91, 20)])
    ax1.set_xticks(range(2005, 2024, 6), [season_label(s) for s in range(2005, 2024, 6)])
    ax1.tick_params(axis="x", labelsize=8.8)
    ax1.set_title("A three is assisted; a two often is not", loc="left", fontsize=11)
    S.strip(ax1)

    ax2.plot(x, 100 * league["three_share"], color=S.SERIES[0], lw=2, zorder=3)
    ax2.set_ylabel("Three-point share of made field goals")
    ax2.set_ylim(0, 35)
    ax2.set_yticks(range(0, 31, 10), [f"{v}%" for v in range(0, 31, 10)])
    ax2.set_xticks(range(2005, 2024, 6), [season_label(s) for s in range(2005, 2024, 6)])
    ax2.tick_params(axis="x", labelsize=8.8)
    ax2.set_xlim(x.min() - 0.4, x.max() + 0.4)
    ax2.set_title("And the league doubled its threes", loc="left", fontsize=11)
    S.strip(ax2)

    c = check.iloc[0]
    S.caption(fig, "The obvious objection to a raw assisted rate: a team that moved its attempts "
                   "to the arc collects assists it did not earn by passing more. So every "
                   "measure here prices it out first - each team is given the assisted rate its "
                   "own two-three split predicts at the league's rates for that season. It turns "
                   f"out to matter less than it looks. Within a season the correlation between "
                   f"three-point share and assisted rate is only "
                   f"{c['within_season_r_three_vs_assisted']:+.2f}, and pricing the mix moves a "
                   f"team about {c['mean_rank_change_when_priced']:.1f} places in the ranking: "
                   "the teams that shoot the most threes are also the ones that assist least on "
                   "their twos.")
    fig.tight_layout()
    fig.savefig(FIG / "01_contamination.png")
    plt.close(fig)


def fig_spurs_path(d: pd.DataFrame) -> None:
    s = d[d["team"] == TEAM].sort_values("season")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.6, 6.4), sharex=True)

    ax1.axhline(0, color=S.INK_3, lw=0.9, zorder=2)
    ax1.bar(s["season"], 100 * s["above_mix"], width=0.66, zorder=3,
            color=[S.SPURS if v > 0 else S.SILVER for v in s["above_mix"]])
    ax1.set_ylabel("Assisted rate above what\ntheir shot mix predicts")
    ax1.set_yticks([-2, 0, 2, 4, 6], ["-2 pp", "0", "+2 pp", "+4 pp", "+6 pp"])
    ax1.set_title("Passing volume, priced for shot selection", loc="left", fontsize=11)
    S.strip(ax1)

    ax2.plot(s["season"], 100 * s["top2"], color=S.SPURS, lw=2, zorder=4)
    ax2.scatter(s["season"], 100 * s["top2"], s=26, color=S.SPURS, zorder=5,
                edgecolors=S.SURFACE, lw=1.2)
    league_top2 = d.groupby("season")["top2"].mean()
    ax2.plot(league_top2.index, 100 * league_top2, color=S.SILVER, lw=2, zorder=3)
    ax2.annotate("league average", (league_top2.index[-1], 100 * league_top2.iloc[-1]),
                 xytext=(7, 0), textcoords="offset points", va="center",
                 fontsize=9, color=S.INK_3, fontweight="semibold")
    lo = s[s["season"] == SUBJECT_SEASON]
    ax2.annotate(f"{season_label(SUBJECT_SEASON)}\n{100 * lo['top2'].iloc[0]:.0f}%",
                 (SUBJECT_SEASON, 100 * lo["top2"].iloc[0]), xytext=(0, -30),
                 textcoords="offset points", ha="center", fontsize=9,
                 color=S.INK, fontweight="semibold")
    ax2.set_ylabel("Share of assists made by\nthe team's top two passers")
    ax2.set_ylim(20, 58)
    ax2.set_yticks([25, 35, 45, 55], ["25%", "35%", "45%", "55%"])
    ax2.set_xticks(range(2004, 2024, 3), [season_label(v) for v in range(2004, 2024, 3)])
    ax2.tick_params(axis="x", labelsize=8.8)
    ax2.set_xlim(2003.3, 2027.2)
    ax2.set_title("And who was doing it", loc="left", fontsize=11)
    S.strip(ax2)

    S.caption(fig, "Two different things happened to San Antonio's offense. It started passing "
                   "slightly more than its shot chart called for around 2012-13, and it kept "
                   "that up for six seasons. Underneath, the creation spread out for a decade "
                   "and then snapped back when Kawhi Leonard's last season ended the era.")
    fig.tight_layout()
    fig.savefig(FIG / "02_spurs_path.png")
    plt.close(fig)


def fig_quality(d: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    others = d[d["team"] != TEAM]
    ax.scatter(others["margin"], 100 * others["top2"], s=15, color=S.NEUTRAL,
               alpha=0.75, linewidths=0, zorder=2)
    sa = d[d["team"] == TEAM]
    ax.scatter(sa["margin"], 100 * sa["top2"], s=34, color=S.SPURS, zorder=4,
               edgecolors=S.SURFACE, lw=1.1)

    xs = np.linspace(d["margin"].min(), d["margin"].max(), 50)
    b = np.polyfit(d["margin"], 100 * d["top2"], 1)
    ax.plot(xs, np.polyval(b, xs), color=S.SERIES[1], lw=2, zorder=3)
    ax.annotate("better teams run more of it\nthrough one or two players",
                (xs[-1], np.polyval(b, xs[-1])), xytext=(-6, 26),
                textcoords="offset points", ha="right", fontsize=9,
                color=S.SERIES[1], fontweight="semibold")

    mark = d[(d["team"] == TEAM) & (d["season"].isin([SUBJECT_SEASON, 2017, 2023]))]
    L.place(ax, mark["margin"].to_numpy(), (100 * mark["top2"]).to_numpy(),
            [season_label(int(v)) for v in mark["season"]],
            fontsize=9, colour=S.INK)

    ax.axvline(GOOD_MARGIN, color=S.INK_3, lw=1.0, ls=(0, (3, 3)), zorder=2)
    ax.annotate(f"+{GOOD_MARGIN:.0f} points a game", (GOOD_MARGIN, 24),
                xytext=(7, 0), textcoords="offset points", fontsize=8.8,
                color=S.INK_3, zorder=5,
                bbox=dict(facecolor=S.SURFACE, edgecolor="none", pad=1.5))
    ax.set_xlabel("Point differential per game")
    ax.set_ylabel("Share of assists made by the team's top two passers")
    ax.set_yticks([25, 35, 45, 55], ["25%", "35%", "45%", "55%"])
    ax.set_title("Distributed creation is mostly a symptom of having nobody to feed",
                 loc="left")
    S.strip(ax)
    S.caption(fig, f"All {len(d)} team-seasons, 2003-04 to 2022-23; San Antonio in black. The "
                   f"correlation between team quality and concentration is "
                   f"+{d.attrs['quality_r']:.2f}. The 2022-23 Spurs lost 60 games and spread "
                   f"the ball around more than the 2013-14 team did, which is the whole problem "
                   f"with quoting this measure unadjusted.")
    fig.tight_layout()
    fig.savefig(FIG / "03_quality_confound.png")
    plt.close(fig)


def fig_among_good(good: pd.DataFrame) -> None:
    d = good.nsmallest(20, "top2").sort_values("top2", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.2, 6.6))
    colours = [S.SPURS if t == TEAM else S.SILVER for t in d["team"]]
    ax.barh(d.index, 100 * d["top2"], color=colours, height=0.64, zorder=2)
    for i, r in d.iterrows():
        ax.text(100 * r["top2"] + 0.4, i, f"{100 * r['top2']:.1f}%", va="center",
                fontsize=8.6, color=S.INK if r["team"] == TEAM else S.INK_2,
                fontweight="semibold" if r["team"] == TEAM else "normal")
    ax.set_yticks(d.index, [f"{r.team}  {season_label(int(r.season))}" for r in d.itertuples()])
    ax.set_ylim(-0.8, len(d) - 0.2)
    ax.set_xlim(0, 100 * d["top2"].max() * 1.12)
    ax.set_xticks(range(0, 41, 10), [f"{v}%" for v in range(0, 41, 10)])
    ax.grid(axis="y", visible=False)
    S.strip(ax, keep=("bottom",))
    ax.tick_params(axis="y", labelsize=8.8)
    ax.set_xlabel("Share of assists made by the team's top two passers")
    ax.set_title("The twenty most distributed offenses among teams that were actually good",
                 loc="left")
    n_sa = int((d["team"] == TEAM).sum())
    S.caption(fig, f"Restricted to the {len(good)} team-seasons in twenty years with a point "
                   f"differential of +{GOOD_MARGIN:.0f} or better. {n_sa} of the twenty are San "
                   f"Antonio, and they are four consecutive seasons.")
    fig.tight_layout()
    fig.savefig(FIG / "04_among_the_good.png")
    plt.close(fig)


def fig_persistence(pers: pd.DataFrame) -> None:
    d = pers.nlargest(12, "seasons").sort_values("seasons").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    colours = [S.SPURS if t == TEAM else S.SILVER for t in d["team"]]
    ax.barh(d.index, d["seasons"], color=colours, height=0.62, zorder=2)
    for i, r in d.iterrows():
        ax.text(r["seasons"] + 0.08, i, str(int(r["seasons"])), va="center",
                fontsize=9, color=S.INK if r["team"] == TEAM else S.INK_2,
                fontweight="semibold" if r["team"] == TEAM else "normal")
    ax.set_yticks(d.index, d["team"])
    ax.set_ylim(-0.75, len(d) - 0.25)
    ax.set_xlim(0, d["seasons"].max() * 1.14)
    ax.grid(axis="y", visible=False)
    S.strip(ax, keep=("bottom",))
    ax.set_xlabel(f"Seasons in the league's top {TOP_N} on both measures")
    ax.set_title("Nobody peaked higher. Nobody stayed up there as long.", loc="left")
    S.caption(fig, f"A season counts when the team finished in its own season's top {TOP_N} both "
                   f"for passing above its shot mix and for spreading the creation around. Out "
                   f"of twenty seasons.")
    fig.tight_layout()
    fig.savefig(FIG / "05_persistence.png")
    plt.close(fig)


def main() -> None:
    totals = pd.read_csv(PROC / "team_totals.csv")
    assists = pd.read_csv(PROC / "assists.csv")
    strength = pd.read_csv(PROC / "team_strength.csv")

    d, rates = build(totals, assists, strength)
    league = (d.groupby("season")
              .apply(lambda g: pd.Series({
                  "three_share": np.average(g["three_share"], weights=g["made_fg"]),
                  "top2": g["top2"].mean(),
                  "margin_sd": g["margin"].std()}), include_groups=False)
              .reset_index())
    d.round(5).to_csv(OUT / "team_seasons.csv", index=False)
    rates.round(5).to_csv(OUT / "league_path.csv", index=False)
    league.round(5).to_csv(OUT / "league_summary.csv", index=False)

    sas = d[d["team"] == TEAM].sort_values("season")
    sas.round(5).to_csv(OUT / "spurs_path.csv", index=False)

    good = d[d["margin"] >= GOOD_MARGIN].copy()
    good.nsmallest(len(good), "top2").round(5).to_csv(OUT / "among_the_good.csv", index=False)

    # The two sentences in the README that name players need a source in
    # output/ like everything else does.
    quoted = []
    for season in (SUBJECT_SEASON, 2018):
        block = assists[(assists["season"] == season) & (assists["team"] == TEAM)]
        total = block["assists"].sum()
        for r in block.nlargest(4, "assists").itertuples():
            quoted.append({"season": season, "player": r.player, "assists": int(r.assists),
                           "share": r.assists / total})
    pd.DataFrame(quoted).round(5).to_csv(OUT / "spurs_passers.csv", index=False)

    d["near_top"] = ((d["rank_above"] <= TOP_N) & (d["rank_top2"] <= TOP_N)).astype(int)
    pers = (d.groupby("team")["near_top"].sum().rename("seasons").reset_index()
            .sort_values("seasons", ascending=False))
    pers.to_csv(OUT / "persistence.csv", index=False)

    # The depth of "near the top" is a choice, so it is varied rather than
    # defended. Only the ordering is claimed.
    cuts = []
    for cut in (5, 10, 15):
        flag = ((d["rank_above"] <= cut) & (d["rank_top2"] <= cut)).astype(int)
        by_team = flag.groupby(d["team"]).sum().sort_values(ascending=False)
        runner_up = int(by_team.iloc[1])
        cuts.append({"cutoff": cut,
                     "leader": by_team.index[0], "leader_seasons": int(by_team.iloc[0]),
                     "runner_up_seasons": runner_up,
                     "teams_tied_at_runner_up": int((by_team == runner_up).sum()),
                     "runners_up": ", ".join(sorted(by_team.index[by_team == runner_up]))})
    cuts = pd.DataFrame(cuts)
    cuts.to_csv(OUT / "persistence_cutoffs.csv", index=False)

    check = mix_check(d)
    check.round(5).to_csv(OUT / "mix_check.csv", index=False)
    fig_contamination(rates, league, check)
    fig_spurs_path(d)
    fig_quality(d)
    fig_among_good(good)
    fig_persistence(pers)

    subj = d[(d["team"] == TEAM) & (d["season"] == SUBJECT_SEASON)].iloc[0]
    print(f"{len(d)} team-seasons, {d['season'].min()}-{d['season'].max()}\n")
    print("--- the league's own rates ---")
    print(rates.round(4).to_string(index=False))

    print("\n--- does pricing the shot mix change anything? ---")
    print(check.round(4).T.to_string(header=False))

    print(f"\n--- {season_label(SUBJECT_SEASON)} San Antonio ---")
    print(f"assisted rate           {subj['assisted_rate']:.4f}  "
          f"(rank {int(subj['rank_rate'])} of 30)")
    print(f"their shot mix predicts {subj['expected']:.4f}")
    print(f"above the mix           {subj['above_mix']:+.4f}  "
          f"(rank {int(subj['rank_above'])} of 30)")
    print(f"top-two assist share    {subj['top2']:.4f}  "
          f"(rank {int(subj['rank_top2'])} of 30, lower is more distributed)")
    print(f"quality-adjusted        {subj['top2_resid']:+.2f} SD  "
          f"(rank {int((d['top2_resid'] < subj['top2_resid']).sum()) + 1} of {len(d)})")

    print(f"margin, worst in the league that season: "
          f"{d[d['season'] == 2023].nsmallest(1, 'margin')['team'].iloc[0]} "
          f"{d[d['season'] == 2023]['margin'].min():.2f}")
    print(f"who was passing: {top_passers(assists, SUBJECT_SEASON, TEAM)}")
    print(f"        2017-18: {top_passers(assists, 2018, TEAM)}")

    print(f"\nconcentration against team quality: r = {d.attrs['quality_r']:+.3f}, "
          f"slope {d.attrs['quality_slope']:+.3f} SD per SD")

    print(f"\n--- most distributed among the {len(good)} team-seasons at "
          f"+{GOOD_MARGIN:.0f} or better ---")
    print(good.nsmallest(8, "top2")[["season", "team", "margin", "top2", "top1",
                                     "above_mix"]]
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print("\n--- most distributed once team quality is taken out ---")
    print(d.nsmallest(8, "top2_resid")[["season", "team", "margin", "top2", "top2_resid"]]
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print(f"\n--- seasons in the top {TOP_N} on both measures ---")
    print(pers.head(8).to_string(index=False))
    print("\nunder other cutoffs:")
    print(cuts.to_string(index=False))

    print(f"\n--- San Antonio, season by season ---")
    print(sas[["season", "assisted_rate", "expected", "above_mix", "rank_above",
               "top1", "top2", "rank_top2", "top2_resid", "margin"]]
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print("\n--- what the inverse-Herfindahl version does instead ---")
    print(d.nlargest(5, "eff_assisters")[["season", "team", "eff_assisters", "assisters",
                                          "top2", "margin"]]
          .to_string(index=False, float_format=lambda v: f"{v:.2f}"))


if __name__ == "__main__":
    main()
