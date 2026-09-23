# Method notes

The two measures, the corrections in the order they mattered, and what an assist
cannot tell you.

## Why an assist at all

It is the only passing event in the public record. Touches, passes, potential
assists and time of possession all exist in the league's tracking data and none
of it is public for most of this sample. So the honest framing of this project is
not "here is how much the Spurs passed" — it is "here is the most that can be
said about passing from a file that only records the last one".

That constraint drives two choices.

**The unit is a made field goal, not a possession.** An assist is only recorded
when the shot goes in, so the denominator has to be made shots. A team that
passed beautifully into a missed layup is invisible here, and a team whose
shooters converted a lot of ordinary passes looks generous. Nothing in this data
separates the two.

**Free throws are excluded.** They are scoring plays and are never assisted, so
leaving them in makes the denominator move with the whistle rather than with the
passing. Removing them costs nothing: no information about passing is contained
in a free throw.

## Pricing the shot mix

The obvious objection is that a three is assisted 81-87% of the time and a two
about half the time, so a team that shoots more threes collects assists it did
not earn. Each team's expected assisted rate is therefore

    expected = league_ast3(season) x three_share + league_ast2(season) x (1 - three_share)

and `above_mix` is the difference. The league rates are re-estimated every
season, so the twenty-year drift in three-point volume never enters a comparison.

**Then the correction turns out to be small**, and that is the useful finding.
`output/mix_check.csv`:

| | |
|---|---|
| Within-season correlation, three-point share vs assisted rate | **+0.056** |
| Assisted rate per unit of three-point share | +0.106 |
| Mean rank change when the mix is priced | **2.4 places** |
| Largest rank change | 14 places |

The mechanism is real and the magnitude is not, because the two halves cancel:
the teams that take the most threes are also the teams that assist least on their
twos — isolation-heavy offenses that generate their threes off drives and their
twos off nothing. Anyone building this measure should still price the mix, and
should not expect it to change their mind.

## The concentration measure, and the one that did not work

The headline is the share of a team's assists made by its top two passers. Two
alternatives were tried first.

**The inverse Herfindahl over all assisters.** I built this one first because it is
the standard measure. It is wrong here. It
counts the tail, so a team that used twenty-seven players in a season scores as
egalitarian for reasons that have nothing to do with how it played. Under that
measure the five most distributed offenses of the last twenty years are the
2021-22 Trail Blazers, the 2020-21 Magic, the 2018-19 Knicks, the 2021-22 Pacers
and the 2014-15 Knicks — five teams with a combined point differential of −40 a
game and enormous roster churn. It is carried in `output/team_seasons.csv` as
`eff_assisters` so the comparison is visible rather than asserted.

**The leading passer's share alone.** Cleaner, but it treats a two-guard offense
as concentrated only if one of the two guards dominates. Two is the number that
matches the claim being tested, which is about the ball not stopping in a
particular pair of hands.

Neither the top-two share nor the Herfindahl is affected by the assist-tag
denominator problem above, because both are shares of a team's own assists.

## The correction that mattered

Concentration is not independent of quality. Across 599 team-seasons it
correlates **+0.31** with point differential: good teams have somebody good
enough to run the offense through, and bad teams do not. Read unadjusted, "most
distributed offense" is a leaderboard of bad basketball.

Two ways of handling it are reported, deliberately, because they answer slightly
different questions.

**Condition on quality.** Restrict to the 86 team-seasons at +5 points a game or
better and rank within that. This is the version to quote, because "good teams
that also did this" is the claim being made about San Antonio.

**Adjust for quality.** Regress within-season standardized concentration on
within-season standardized point differential and read the residual. Slope +0.33
SD per SD. This ranks all 599 and puts the 2013-14 Spurs 2nd, but it also lets a
mediocre team score highly for being unusually distributed *for a mediocre team*,
which is not the same claim.

The two agree about San Antonio, which is the reason to trust either.

## Persistence

A team-season counts as "near the top" when it finished in its own season's top
ten both for passing above its shot mix and for spreading the creation around.
San Antonio has nine of twenty; Chicago and Minnesota have six.

The cutoff at ten is arbitrary and `output/persistence_cutoffs.csv` varies it,
with an honest result: at fifteen it is San Antonio 13 against a seven-way tie at
8, and at ten it is 9 against 6. At **five** it falls apart — the Clippers lead
with three and San Antonio has two — because requiring a top-five finish on two
different measures in the same season admits so few team-seasons that nobody
accumulates any.

So the claim is specifically about a sustained pattern near the top, not about
peaks, and a cutoff tight enough to be about peaks cannot see it. That is a real
limitation of the statistic and not a reason to pick the cutoff that flatters
it: the peaks are reported separately, above, and San Antonio does not own
them.

## Where this is weakest

**No possessions, no misses, no passes.** Everything is per made field goal. A
team that generated wide-open looks and missed them is not distinguishable from
one that did not generate them.

**An assist is a scorer's judgment.** Different scorekeepers have different
thresholds for what counts as "directly leading to" a basket, and this project
takes twenty seasons of that judgment at face value. The stability of the league
rate across the sample is reassuring about drift over time; it says nothing about
consistency between buildings on a given night.

**Roster churn moves the concentration measure**, which is why the top-two share
rather than the Herfindahl is the headline. It is reduced, not removed: a team
that lost its point guard in November will look distributed for the year.

**Team quality is measured as point differential per game**, taken from the final
score on the last event of each game. It is a control, not a finding, and it does
not need to be more precise than that.

**Regular season only, 2003-04 to 2022-23.** The phrase was coined about a
postseason. Nothing here is about the playoffs, where the sample is fifty times
smaller and the opposition is not the league.
