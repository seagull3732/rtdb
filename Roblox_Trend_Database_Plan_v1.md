# Roblox Trend Database — Plan v1

*Prepared 29 September 2026, updated the same day after the first live runs (collector v0.4). Companion files: `schema.sql`, `collector.py`, `code_features.py`, `archive.py`, `radar.py`, `backfill.py`, `opportunity.py`, `ideas.py`, `ask.py`, `sql.py`, `collector.yml` (GitHub Actions schedule), `run.ps1`, `test_offline.py`, `requirements.txt`.*

**Goal.** Build a database of trending Roblox experiences, find what separates games that succeed from games that don't, and use that to design games with a higher base rate of success.

---

## 0. Two facts that shape everything below

### 0.1 The target moved in June 2026

Roblox now tells creators what its home-page algorithm rewards. On 15 June 2026 it expanded *Recommended For You* (RFY) from a 7-day window to a 28-day window that measures long-term retention directly, and published the full list of ranking signals with their relative importance. The new signals cover day 1, days 2–7 and days 8–28, and the old "qualified play-through" signal was split so that play-through behaviour, session quality and spend are measured separately. Roblox's stated reason: over-valuing short-term engagement had let games with attention-grabbing thumbnails but little lasting value displace games players valued long term. On 20 August 2026 Roblox announced it is testing a further update in the same direction (games players choose to return to over time).

**Consequence.** The question "what do trending games have in common?" splits in two:

1. *What player behaviours does the platform reward?* — now largely public (retention windows, play-through, session quality, co-play, spend).
2. *Which design choices produce those behaviours?* — this is what the database has to answer, and it is a more durable question than "what is on this month's chart."

### 0.2 A database of only winners cannot tell you what causes winning

If 80% of top games have "Verb a Noun" titles, that is only meaningful if far fewer failed games do. Every phase below collects losers alongside winners, and every finding is expressed as a *lift* over a base rate, never as a bare prevalence.

---

## Phase 0 — Define success before collecting anything (week 1)

### 0.a Outcome variables (use several)

| Variable | Why |
|---|---|
| **Peak CCU** | How big the spike got |
| **Sustained CCU** — median daily CCU over days 8–28 after peak | Mirrors RFY's long-retention window; separates franchises from flashes |
| **Decay half-life** — days from peak until daily CCU falls below 50% of peak | Same purpose, different lens |
| **Visit velocity, like ratio, favourites per visit** | Quality and satisfaction proxies |
| **Chart presence** — days on each sort, best position | Note what each sort measures: Roblox's *Top Trending* is defined as the games players have spent more time in over the past two weeks — an engagement-growth sort, not raw CCU |
| **Revenue proxy** — rank on the Top Earning sort | You cannot see other studios' revenue directly |

### 0.b Fixed tiers (do not move them mid-study)

- **Breakout** ≥ 100,000 peak CCU
- **Hit** 20,000–100,000
- **Mid** 2,000–20,000
- **Tail** < 2,000

(Implemented in `v_tier` in `schema.sql`. Change the thresholds there, once, if you must.)

### 0.c Three populations tracked from day one

1. **Charts** — everything reaching the top 200 of any front-page sort.
2. **Launch cohort** — anything created within 60 days of first being seen that crosses 500 CCU. This is where breakouts and flops appear side by side; it is the only population that lets you predict rather than describe.
3. **Controls** — a random sample of ~300 games sitting at 200–2,000 CCU. This is the base rate.

Unit of analysis: the **universe** (experience), snapshotted over time. Features are time-stamped and versioned because games change.

---

## Phase 1 — Data sources (weeks 1–2)

### 1.a Roblox public web endpoints (no key)

Third-party trackers are built on these. Live player counts, lifetime visits, favourites, votes and metadata are available per universe.

| Endpoint | Gives you |
|---|---|
| `games.roblox.com/v1/games?universeIds=` | playing, visits, favourites, maxPlayers, created/updated, genre taxonomy (L1/L2), creator |
| `games.roblox.com/v1/games/votes` | up/down votes |
| `games.roblox.com/v1/games/{universeId}/game-passes` | passes and prices |
| `thumbnails.roblox.com/v1/games/icons` and `/multiget/thumbnails` | icon and thumbnail image URLs |
| `apis.roblox.com/explore-api/v1/get-sorts` and `get-sort-content` | the Charts sorts themselves, paginated |
| `groups.roblox.com/v1/groups/{id}`, `users.roblox.com/v1/users/{id}` | creator size and track record |

These are undocumented and occasionally move. `collector.py probe` prints the live structure of the charts payload so you can confirm field names on day one.

### 1.b Historical backfill

Your own collection starts with zero history, and history is the scarce asset. RoMonitor Stats exposes an API returning half-hourly CCU with data back to 2020; check its terms and pricing, then backfill peak/decay curves for the last 2–3 years for every game you care about. Do **not** build on Rotrends — it was deprecated on 31 August 2026.

### 1.c Roblox's published discovery framework

Use the June 2026 signal list as the spine of the feature taxonomy: retention windows (D1, D2–7, D8–28), play-through, session quality, co-play, spend. For your *own* games, Creator Analytics has a Home Recommendations tab that reports performance against the algorithm's signals. Roblox also notes that play-through, playtime and retention naturally differ by acquisition source — so always separate Sponsored traffic from organic when you test.

### 1.d External virality signals

Most Roblox breakouts ignite outside Roblox and are then amplified by the algorithm. Capture both timestamps:

- YouTube Data API — weekly count of videos and total views mentioning each game
- TikTok — weekly manual sample or a social-listening tool
- Discord — invite-page member counts
- Roblox group member counts (collected automatically by `collector.py daily`)

### 1.e Etiquette and terms

Public endpoints only; one request at a time; a User-Agent with a contact address; no authenticated scraping of other people's data. Read Roblox's Terms of Use before running against the live platform.

Observed on day one: `games.roblox.com` (the stats endpoint) returns 429 at roughly two requests per second and stays throttled for the better part of a minute. The collector therefore paces that host at one call every 3 s by default (`RTDB_GAMES_INTERVAL_S`), doubles the interval each time it is throttled, waits 20–120 s between retries, and skips a batch rather than abort a run if it still can't get through. The charts (explore) API was not throttled at all. Expect `sorts` to take 3–5 minutes and `daily` about an hour; both are fine for background jobs.

---

## Phase 2 — Schema (week 2) — see `schema.sql`

Postgres (Supabase's free tier will last a year; any Postgres works). Sixteen tables, ten analysis views.

**Entities and time series**

| Table | Purpose |
|---|---|
| `experience` | one row per universe: metadata, `population`, `launch_cohort`, `tracking_tier` |
| `snapshot` | playing / visits / favourites / votes per game per run |
| `sort_catalog`, `chart_position` | which sorts exist; every game's position on every sort, every run |

**Change logs** (update cadence, title and thumbnail experiments fall out of these for free)

| Table | Key |
|---|---|
| `name_history` | (universe, name) |
| `description_history` | (universe, hash of description) |
| `thumbnail_history` | (universe, kind, image URL) |

**Monetization, creators, context**

| Table | Purpose |
|---|---|
| `gamepass`, `gamepass_price_history` | the monetization scaffold and how it changes |
| `creator` | groups/users with member counts and track record |
| `external_signal` | YouTube / TikTok / Discord / group-size time series |
| `regime_event` | platform events to split analyses pre/post — pre-seeded with the Dec 2025, Jun 2026 and Aug 2026 algorithm changes |

**Features and your own games**

| Table | Purpose |
|---|---|
| `codebook` | feature definitions, pre-seeded with codebook v1 (Phase 4) |
| `feature` | one row per coding event; latest wins, history kept |
| `own_experiment` | your games' Creator Analytics exports (retention by source, play-through, bounce, play days, co-play, spend) |
| `collector_run` | job log, so you notice when something stops running |

**Views** — `v_daily_ccu`, `v_peak`, `v_decay` (half-life), `v_sustained` (median CCU days 8–28 after peak), `v_tier`, `v_chart_summary`, `v_feature_latest`, `v_feature_lift`, `v_feature_numeric`, `v_growth_alerts` (breakout detector), `v_archetype_entrants_weekly` (wave analysis), `v_coding_progress`, `v_recode_candidates`, and from the partner round `v_category`, `v_category_summary`, `v_velocity`, `v_retention_proxy`, `v_cohort_monthly`, `v_cohort_curve`, `v_thumbnail_impact`, `v_thumbnail_churn`.

Volume is trivial: 2,000 games × 48 snapshots a day ≈ 100k rows/day. Turn `v_daily_ccu` into a materialized view when `snapshot` passes ~50M rows.

---

## Phase 3 — Collection pipeline (weeks 2–3) — see `collector.py`

**Start collecting the day the schema exists**, before any analysis. Every week you wait is history you can only partly recover.

| Job | Cadence | What it does |
|---|---|---|
| `sorts` | hourly | Snapshots every front-page sort (position per game, deep pages for the big sorts), registers the games, snapshots their stats |
| `stats` | every 30 min | Snapshots playing / visits / favourites / votes for the *intensive* tier |
| `promote` | hourly, after `sorts` | Applies the watchlist rules and launch-cohort labelling |
| `daily` | daily | Refreshes metadata, change logs, thumbnails, game passes, creators |
| `sample-controls` | once, then top-ups | Picks N random games in a CCU band as the control population |

**Watchlist (promotion) rules**, in order:

1. Top 200 on a **major** sort in the last 24 h → `population = 'charts'` (never overrides control/own). Major sorts default to Top Trending, Up-and-Coming, Top Playing Now, Top Earning, Top Revisited, Most Popular and Fun with Friends (`RTDB_MAJOR_SORTS`); the small "Trending in [genre]" lists are recorded but don't define the population, so their mid-sized games stay eligible as controls.
2. Created within 60 days of first sighting and crossed 500 CCU → `launch_cohort = TRUE`.
3. Promote to *intensive* if: control/own; top 200 on a major sort or any Up-and-Coming/Rising sort in the last 24 h; a growth alert (daily CCU ≥ 1.5× yesterday and ≥ 300); or a launch-cohort game first seen within 60 days.
4. Demote to *daily* if absent from every sort for 14 days and max CCU < 200 over 14 days (controls/own never demote).

`v_growth_alerts` doubles as your daily "what just ignited" list. Within a few weeks you will be catching new hits within 24 hours of ignition — the most informative moment to study them.

**Data-quality flags to add in month 2:** CCU-to-visits anomalies, sudden like-ratio jumps, unnaturally flat CCU plateaus (bot signatures), universe/place deduplication.

---

## Phase 4 — Codebook v1: turning games into features (weeks 3–5)

Pre-seeded in the `codebook` table. Two families.

### 4.a Machine-extractable (write once, runs forever)

| Feature | Type | Definition |
|---|---|---|
| `title_pattern` | enum | verb_a_noun · x_simulator · x_tycoon · x_rng · x_rp · obby · named_ip · descriptive · other |
| `title_len_chars`, `title_emoji_count` | number | length and emoji count of the current title |
| `title_has_update_tag` | bool | bracketed or emoji-flagged update/event tag |
| `title_is_sequel` | bool | "2", "II", "Remastered", etc. |
| `desc_len_chars`, `desc_has_discord`, `desc_has_codes` | number/bool | description length; Discord link; redeemable codes |
| `icon_has_face`, `icon_has_text`, `icon_has_arrow`, `icon_character_count` | bool/number | tagged by a vision model at scale |
| `pass_count`, `pass_min_price`, `pass_median_price` | number | on-sale passes and price distribution |
| `pass_has_boost`, `pass_has_vip` | bool | luck / 2× / speed / auto-collect passes; VIP bundle |
| `server_size`, `age_rating`, `genre_l1`, `genre_l2` | number/enum | from the API |
| `update_freq_per_week` | number | change events per week over the trailing 28 days |
| `creator_is_group`, `creator_prior_peak_ccu`, `creator_group_members` | bool/number | creator track record |

### 4.b Requires play (expensive, and where the real signal lives)

| Feature | Type | Definition |
|---|---|---|
| `core_loop` | enum | collect · grow · steal · tycoon · obby · horror · round_pvp · roleplay · idle · rng · sports · shooter · other |
| `ttfr_seconds` | number | time to first reward |
| `ttfc_seconds` | number | time to first meaningful choice |
| `session_shape`, `round_length_s` | enum/number | persistent · rounds · hybrid; round length |
| `progression_type` | multi | numbers_go_up · rebirth_prestige · rarity_collection · levels · cosmetic_only · none |
| `social_asymmetry` | enum | none · take · help · trade · mixed — can players take from, help, or trade with each other? |
| `can_lose_progress`, `has_base_defense` | bool | risk and defence |
| `offline_accrual`, `has_timers_or_fomo` | bool | idle accrual; limited-time items, timers, events |
| `first_purchase_prompt_min`, `first_purchase_price` | number | when the first purchase is offered and at what price |
| `mobile_one_thumb`, `lowend_fps_ok` | bool | mobile ergonomics and performance |
| `borrows_meme_or_ip` | enum | none · meme · anime · other_game · brand |

### 4.c Process (automated with `code_features.py`)

- `python code_features.py auto` computes the 25 machine-extractable traits for every tracked game in seconds and re-runs weekly (only changed values are written).
- `python code_features.py llm` asks Claude to infer nine design traits (core loop, session shape, progression, social mechanics, risk, base defence, offline accrual, timers/FOMO, borrowed IP) plus the four icon traits from the icon image, for every game not yet coded. Each answer carries a confidence and a one-line rationale; answers marked "unknown" or below 0.3 confidence are left blank, and anything below 0.6 is flagged for a second look. Runs weekly on the cloud runner if an `ANTHROPIC_API_KEY` secret is set; roughly $5–10 for the first 900 games at Claude Sonnet 5.5 prices, cents per week after that.
- `python code_features.py queue` writes `coding_queue.csv`: the games that still need the seven play-required traits, prioritised by tier, with the LLM's answers alongside for verification. Fill it in Excel (a gameplay video and a stopwatch cover most of it), then `python code_features.py import coding_queue.csv --coder XX`. Human values override the LLM, which overrides auto.
- Code the **top 300 + 300 controls + every launch-cohort game that crosses 2k CCU** by hand this way; `v_coding_progress` shows how far along each feature is, and `v_recode_candidates` lists games whose page changed since they were coded.
- If two people code, overlap 15% and measure agreement. A feature coders cannot agree on is not measuring anything — fix the definition or drop it.
- Record `evidence` (screenshot path, video timestamp) for play features. You will want it when a finding looks too good.
- Bump `codebook.version` whenever a definition changes; never silently redefine.

---

## Phase 5 — Analysis (weeks 5–8, then monthly)

1. **Lift tables — the core deliverable.** For every feature: prevalence among Hits + Breakouts vs Controls, lift ratio, Wilson confidence interval. Point estimates come from `v_feature_lift`; compute intervals in Python. Anything near 100% in both groups is table stakes, not a driver. *Illustrative:* "Verb-a-Noun titles: 62% of breakouts vs 18% of controls, 3.4× lift."
2. **Longevity vs flash.** Same features; outcomes are `half_life_days` (`v_decay`) and `sustained_ccu_d8_28` / `sustain_ratio` (`v_sustained`). After the June change this is the analysis that matters most. Features that only predict a launch spike are the ones Roblox has just stopped rewarding.
3. **Launch-cohort prediction.** For every `launch_cohort` game, predict "reaches 10k CCU within 30 days" from features knowable at launch. Logistic regression first (interpretable), gradient boosting second. Split train/test **by time**, never randomly. Report AUC *and* calibration. Expect modest signal and small N — say so in the write-up.
4. **Wave-saturation curves.** `v_archetype_entrants_weekly` counts entrants per week per core loop with their outcomes; plot performance by entry order. The "Steal a X" wave shows why: Steal An Egg released 25 July 2026 and reached roughly 3 million active players and 3.1 billion visits within two months — more than a year after Steal a Brainrot. Waves can outlast intuition; the curve tells you when late entrants stop getting paid.
5. **Archetype discovery.** Embed titles + descriptions + coded features, cluster, and track which clusters gain share month over month.
6. **Structured deep-dives.** Play the top 20 and the 20 most surprising failures with the Phase 4 rubric. Data tells you where to look; it cannot tell you what felt good.

**Tooling.** pandas, statsmodels, scikit-learn in notebooks; Metabase or Streamlit on the views for a dashboard (Power BI works equally well). Write a one-page findings memo every month — stating results with numbers exposes weak ones fast.

**Analytic hygiene.** Always run each analysis pre/post each `regime_event`. Report N alongside every percentage. Treat any lift below ~1.5× as noise until it survives a second month of data.

---

## Phase 6 — From findings to games (week 8 onward)

### 6.a Design constraints, not templates

Translate findings into constraints such as: first reward within 30 seconds; one social-asymmetry mechanic; a defendable base; a first purchase under 99 Robux offered after the first loss; one content update a week. Constraints combine into original games; templates produce clone #14.

### 6.b The experiment protocol

The database can only raise your base rate — it cannot bless a single game. So:

1. Build **3–6 small prototypes** (2–4 weeks each) against the constraints.
2. Launch each with an **identical, fixed Sponsored budget**.
3. Write **kill/scale criteria before launch** and put them in `experience.notes`. Example: *kill* if D1 retention is below the genre median in Creator Analytics after 1,000 organic players; *scale* if D7 is above the 75th percentile.
4. Give every test **at least 28 days** — that is now the algorithm's window.
5. Instrument exactly the published signals: first-play bounce, play-through, play days per user, co-play, spend. Roblox has said creators whose games deliver long-term value through retention, co-play and spend will get more opportunity to build an audience.
6. Export Creator Analytics into `own_experiment`, split by acquisition source, and set `population = 'own'` on your universes. Your prototypes — especially the failures — become training data.

---

## Phase 7 — Keep it alive

- Weekly: check `collector_run` for failures; skim `v_growth_alerts`.
- Monthly: re-run lift tables and the longevity analysis; findings memo.
- Quarterly: retrain the launch-cohort model; re-code the top 100 (games change).
- Whenever Roblox announces a discovery change: add a `regime_event` row and re-run everything pre/post.

The Roblox meta turns over roughly every 6–12 months. A model trained on 2025's charts is a model of 2025.

---

## Limitations (put these in your own memo too)

- **Survivorship and feedback loops.** Charts *cause* growth as well as reflect it. Controls help; they do not fully fix it.
- **Small N at the top.** Fifty breakouts a year is a small sample. Widen to Hits and Mids for statistical power.
- **Unmeasured execution.** Polish, feel, a bug-free launch, thumbnail craft — the features you cannot code often decide between two games with identical feature vectors.
- **Bots and inflated metrics.** Build the quality flags in month 2 and exclude flagged windows.
- **IP and cloning risk.** "Borrows a viral meme" may show high lift and still be a legal or moderation liability.
- **Regime change.** Everything before 15 June 2026 was measured under a different algorithm. Treat it as a separate era.

---

## Timeline and effort

| Weeks | Milestone |
|---|---|
| 1 | Success metrics, tiers, populations; `probe` run; endpoints verified |
| 2 | Schema live; collector on cron; RoMonitor backfill started |
| 3–5 | Codebook v1 applied; ~600 games coded (LLM-assisted) |
| 5–8 | Lift tables, longevity analysis, first cohort model; findings memo #1 |
| 8–12 | Design constraints written; prototypes 1–3 built |
| 12–20 | Launch tests on 28-day windows; kill/scale decisions; memo #2 |
| Ongoing | Monthly re-analysis, quarterly retrain |

One person comfortable with Python and SQL can run the whole pipeline. Coding 600 games is the single biggest time sink — budget 40–60 hours even with LLM pre-fill.

---

## Addendum (30 Sep 2026) — partner feedback, what changed

**Added (schema v0.4, `archive.py`, workflow update):**

- `play_mode` trait (pve · pvp · coop · social · party · trading · roleplay · creative, multi-select) coded by the Claude pass; `v_category` rolls every game up to one primary category and `v_category_summary` shows games, hits, 30-day entrants, median 7-day growth, surging count, staying power, half-life and like ratio per category.
- `v_velocity`: 1-, 7- and 28-day player growth per game, Top Trending rank movement, and a label (surging / growing / flat / declining / collapsing).
- `v_retention_proxy`: staying power on days 8–28, half-life, like ratio, favourites per 1k visits. These are proxies: Roblox publishes true retention only to a game's owner, so D1/D7/D30 exist in this database only for your own games (`own_experiment`).
- `v_cohort_monthly` (games by launch month: share reaching 2k / 20k / 100k, median peak, half-life, staying power, pre/post the June 2026 algorithm change) and `v_cohort_curve` (median trajectory by days since launch).
- `v_thumbnail_impact` (players 7 days before vs after each icon/banner change) and `v_thumbnail_churn` (how often each tier changes thumbnails).
- Backups: `archive.py weekly` exports every table (big time series month-to-date) each Sunday; `archive.py monthly` writes last month's `snapshot` and `chart_position` as immutable files on the 1st. Both attach to a GitHub release named `backups`, gpg-encrypted with the `BACKUP_PASSPHRASE` secret. `archive.py restore FILE` loads any of them back. Nothing in the system deletes data; this makes the full-resolution history survive the live database.

**History sources (1 Oct).** RoMonitor Stats has no public per-game history API; its public `count` endpoint is Roblox-wide concurrent users (half-hourly since 2020), which the collector now loads daily into `platform_ccu` so every growth figure can be read against the platform (`v_platform_context`, included in radar dossiers). Per-game history is available legitimately from RTrack's paid API on RapidAPI (free tier: 10 requests/month to test); `backfill.py import-csv FILE --source rtrack` loads any per-game history CSV into `snapshot` tagged by source, resolving place ids and registering unknown games. Backfilled rows never overwrite the collector's own samples, and the radar's "first time" triggers automatically use real history once it exists. A direct data-licence request to RoMonitor (owned by Gamefam) is the other route.

**Storage decision needed within the month.** The Supabase free tier holds 500 MB; at ~55k snapshot and ~39k chart rows a day the live database grows roughly 350 MB a month. Options: Supabase Pro ($25/month, 8 GB ≈ two years of raw data) or a small server with a large disk. Either way the monthly archives are the permanent copy.

**Explosive radar (built 30 Sep, `radar.py`).** `v_radar_candidates` flags games that tripped any of: a growth alert, first appearance on a major chart, a 20-place climb on Top Trending, doubling in 7 days, or crossing 2k / 10k / 50k players for the first time, and ranks them by a heat score. For the top N (default 12) the radar assembles a dossier from the database (velocity, chart entries incl. sponsored slots, 21-day player curve, name/description/icon/pass changes in the last 14 days, all coded traits, which of those traits are over-represented among hits, wave context for the same core loop, the creator's other games, the cohort baseline for its age) and has Claude write an evidence-weighted brief: headline, what it is, what's happening, distinct traits, ranked reasons each tied to evidence with a confidence, wave context, confounders, what to watch. Stored in `radar_report`, rendered to `reports/radar-<date>.md` (committed to the repo daily at 14:00 UTC), optionally posted to Discord via `RTDB_DISCORD_WEBHOOK`. Cost: cents per day.

**Opportunity engine (built 1 Oct, `opportunity.py`).** `v_archetype_metrics` measures every archetype (core loop × primary category): games, hits, hit rate, median peak, longevity (median staying power and half-life, with the n behind each), saturation (entrants in 30/90 days, how many reached 2k/20k, acceleration vs the previous 90 days), behaviour proxies (like ratio, favourites, server size), trend (median 7-day growth, Top Trending slots). `opportunity.py scoreboard` scores archetypes on longevity 25% · room 25% · mechanics 20% · trend 20% · cost 10%, each with a data-sufficiency weight that becomes a confidence figure; cost is a published rubric in solo-dev weeks (`COST_RUBRIC`) overridable per archetype via `cost_overrides.csv`. `opportunity.py run --top 5` has Claude write a design brief per top archetype: the gap with numbers, measured constraints with lift, traits to avoid, an original concept, scope, risks, and kill/scale thresholds for the 28-day test; briefs are marked PROVISIONAL until 28 days of history exist. Stored in `opportunity_report`, committed to `reports/` on the 1st of each month.

**Question-and-answer tool (built 1 Oct, `ask.py`).** `python ask.py "question"` or interactive. Claude translates the question into one read-only SQL query against the views (it is given a guide to what each view means plus the live column list), the tool validates it (SELECT/WITH only, no write keywords, LIMIT enforced), runs it in a read-only transaction with a 25-second timeout, retries up to twice on errors, and Claude answers from the results with the query and first rows shown so the work can be checked. Follow-up questions keep the last three exchanges as context. "Why did X spike?" reads the stored radar brief. About 2–3 cents a question.

**Game idea agent (built 2 Oct, `ideas.py`).** Weekly on Mondays after the opportunities: for the top archetypes it reads the archetype profile, the knowledge base (`lesson` table), the last seven days of radar verdicts and the concepts already proposed, plus an optional brief, and proposes several original concepts per archetype — hook, pitch, gap with numbers, loop, first 60 seconds, features, rewards and retention hooks, social mechanic, pass ladder, differentiation from named leaders, scope, kill-early signal — each with a **declared trait profile** in the codebook vocabulary (validated; borrowed IP refused) so the scoring agent can check it against the lift tables mechanically. Stored in `concept` with a status workflow: `python ideas.py approve ID` / `reject ID --reason` (rejections become lessons). Reports: `reports/concepts-<date>.md` and `reports/concepts_log.md`.

**Still to build:** (monthly archetype scoring on longevity, saturation, mechanics lift, behaviour proxies, trend and estimated cost → design briefs), and the question-and-answer tool over the views. All three read the Claude-coded traits, so the LLM pass runs first.

## Appendix A — Getting the pipeline running

Settings live in a file called `secrets.txt` next to `collector.py` (or in environment variables, which win if both are set). Put the Supabase **Session pooler** connection string on its own line, plus any other settings as `KEY=VALUE`:

```
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
RTDB_CONTACT=you@example.com
```

Then, from a terminal opened in that folder (Windows PowerShell shown; Mac/Linux is the same without `python -m`):

```
python -m pip install -r requirements.txt
python collector.py init            # creates 16 tables and 10 views; safe to re-run
python collector.py probe           # walks the charts API; prints every sort, its id, and whether it paginates
python collector.py sorts           # first real collection: chart positions, then stats (3–5 minutes)
python collector.py promote         # watchlist rules; prints tiers and populations
python collector.py stats           # 30-minute snapshot of the intensive tier
python collector.py sample-controls --n 300 --lo 200 --hi 2000
python collector.py daily           # change logs, thumbnails, game passes, creators (15–30 minutes)

python code_features.py auto        # 25 automatic design traits for every game; seconds; free
python code_features.py llm --dry-run   # preview one LLM coding prompt/answer (needs ANTHROPIC_API_KEY in secrets.txt)
python code_features.py llm --limit 300 # code up to 300 uncoded games with Claude
python code_features.py queue --n 50    # spreadsheet of games needing the play-required traits
python code_features.py import coding_queue.csv --coder XX   # load what you filled in
```

`test_offline.py` exercises every job against fake payloads; run it only against a scratch database, because it inserts fake games.

Schedule. On Windows, `run.ps1` is the single entry point: Task Scheduler runs it every 30 minutes and it decides what is due (`stats` every run; `sorts` + `promote` on the top-of-hour run; `daily` on the 3 AM run). Task action: `powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "<folder>\run.ps1"`, set to run whether the user is logged on or not, "do not start a new instance" if already running, and "run as soon as possible after a missed start". The PC must stay on and awake (Power settings → sleep: Never). On Mac/Linux, cron (UTC):

```
*/30 * * * *   python collector.py stats
5    * * * *   python collector.py sorts
15   * * * *   python collector.py promote
20   3 * * *   python collector.py daily
```

Each job takes a lock file (`.lock_<job>`) so a slow run is never stacked on top of itself, and appends to `logs/<job>-<date>.log`. `daily` takes 15–30 minutes: game passes refresh weekly (daily for games created in the last 14 days) and creators every 14 days, at most 150 per run, because `groups.roblox.com` throttles at anything faster than one call per 10 s.

Environment knobs: `RTDB_GAMES_INTERVAL_S` (default 3), `RTDB_CREATOR_INTERVAL_S` (default 10), `RTDB_CREATOR_BUDGET` (default 150), `RTDB_MAX_ATTEMPTS` (default 8), `RTDB_SORT_DEPTH` (pages per sort, default 4), `RTDB_DEEP_SORT_DEPTH` (default 20, applied to sorts whose names match `RTDB_DEEP_SORT_KEYWORDS`, default `popular,playing`), `RTDB_MAJOR_SORTS` (which sorts define the charts population), `RTDB_HASH_IMAGES=1` to download and hash icons.

**First-week checks**

- `select job, ok, rows_written, http_requests, started_at from collector_run order by id desc limit 20;`
- `select tracking_tier, population, count(*) from experience group by 1,2;`
- `select * from v_growth_alerts order by growth desc;`
- After a few days: `select * from v_decay where half_life_days is not null order by peak_avg_ccu desc limit 20;`

**Not yet built (month 2):** YouTube/TikTok/Discord collectors into `external_signal`; LLM pre-coding script into `feature`; bot-signature flags; RoMonitor backfill loader; Wilson intervals and the cohort model notebook.

---

## Appendix B — Sources

- Roblox Newsroom, *Optimizing Discovery: How Great Games Reach Millions of Players on Roblox* (15 Jun 2026) — https://about.roblox.com/newsroom/2026/06/optimizing-discovery-great-games-reach-millions-players-roblox
- Roblox DevForum, *Recommended For You Algorithm Improvements That Better Value Long-Term Retention* (15 Jun 2026) — https://devforum.roblox.com/t/recommended-for-you-algorithm-improvements-that-better-value-long-term-retention/4684575
- Roblox DevForum, *Boost Your Discovery by Building Games People Want to Play* (20 Aug 2026 update) — https://devforum.roblox.com/t/boost-your-discovery-by-building-games-people-want-to-play/4779042
- Roblox DevForum, *Improved Recommended For You Algorithm and Analytics for Creators* (11 Dec 2025 update) — https://devforum.roblox.com/t/boost-your-discovery-with-the-improved-recommended-for-you-algorithm-and-analytics-for-creators/3587441
- Roblox Creator Hub, *Discovery* documentation — https://create.roblox.com/docs/discovery
- Roblox Charts, *Top Trending* (sort definition) — https://www.roblox.com/charts/top-trending
- RoMonitor Stats — https://romonitorstats.com (API with half-hourly CCU history; see also the open-source fetcher at https://github.com/CG821/romonitor-fetch)
- Rotrends deprecation notice (31 Aug 2026) — https://rotrends.com/top-roblox-games
- Sportskeeda, *Best Roblox games to play right now (September 2026)* — Steal An Egg figures — https://www.sportskeeda.com/roblox-news/best-roblox-games-to-play-right-now
