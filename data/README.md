# Data

One file per season at `data/raw/pbp/play_by_play_<season>.csv.gz`, where
`<season>` is the year the season ended: `play_by_play_2014.csv.gz` is 2013-14.

## Getting the files

From [sportsdataverse/hoopR-data](https://github.com/sportsdataverse/hoopR-data),
a mirror of ESPN's public feeds.

```bash
git clone --filter=blob:none --no-checkout --depth 1 \
  https://github.com/sportsdataverse/hoopR-data.git /tmp/hoopR-data
cd /tmp/hoopR-data
git sparse-checkout set --no-cone "nba/pbp/csv/*"
git checkout
cd -
mkdir -p data/raw/pbp
cp /tmp/hoopR-data/nba/pbp/csv/play_by_play_20*.csv.gz data/raw/pbp/
```

About 470 MB. `data/raw/` and `data/processed/` are gitignored; everything the
analysis cites is written to `output/` and committed.

## Why the sample starts at 2003-04

The mirror carries 2001-02 and 2002-03 as well, at 457 and 967 games against a
full season's 1,189. Partial coverage is fine for a question asked one game at a
time and is not fine for a team-season average, so the sample begins at 2003-04,
where the feed carries 1,174 of 1,189 games, and ends at 2022-23, where the
mirror currently stops.

## Where the assist comes from

`athlete_id_2` on a scoring play. The event text carries the same information —
"Tony Parker assists" in the modern files, "Assisted by Tony Parker" in the older
ones — but the sentence was reworded partway through the sample and the
structured column was not, so the column is what the pipeline reads.

That distinction matters more than it sounds. Two other things in these files
*were* re-recorded mid-sample and are unusable across it: the action-type
vocabulary (pull-up, floater and step-back do not exist before 2007-08) and the
shot coordinates (before 2010-11 most attempts at the rim carry the rim's own
coordinate). Nothing in this project touches either one. The assist tag is
stable: the league's assisted share of made field goals sits between 56.3% and
60.9% in every season of the sample, with no step at any boundary.

## Columns used

| Column | Used for |
|---|---|
| `game_id`, `season`, `season_type` | joining, and the regular-season filter |
| `scoring_play`, `type_text` | made field goals, with free throws removed |
| `score_value` | whether the basket was worth three |
| `team_id`, `home_team_id`, `away_team_id`, `home_team_abbrev`, `away_team_abbrev` | which team, under which abbreviation |
| `athlete_id_2` | who assisted |
| `athlete_id_1`, `text` | who scored, and the assister's name recovered from the sentence |
| `home_score`, `away_score` | the final score, for the team-quality control |

## Filters applied in stage 1, and what they cost

| Filter | Rows dropped |
|---|---|
| Regular season only (`season_type == 2`) | the postseason |
| A team on the row | 22 in twenty seasons |
| Worth two or three points | 245, all from 2012-13 on, recorded as worth zero |
| A real franchise | 2,900 |

The last one is not a formality. The mirror files the **All-Star Game** under the
same season type as the regular season, so without it the tables acquire teams
called EAST, WEST, LEB, GIA, DUR, STE, USA and WORLD — and an exhibition in which
nobody plays defense is the most generous passing team ever recorded.
