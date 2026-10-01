-- =============================================================================
--  Roblox Trend Database (rtdb) — schema v0.6  (re-running this file is safe)
--  Target: PostgreSQL 14+ (Supabase free tier is fine). Apply with:
--      psql "$DATABASE_URL" -f schema.sql        or        python collector.py init
--  Design rules:
--    * Every fact is time-stamped. Games change; features are versioned.
--    * Winners and losers live in the same tables. `population` says which
--      sampling frame a game came from; `tier` (a view) says how it performed.
--    * Nothing here is Roblox-specific beyond the API field names.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Core entities
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS experience (
    universe_id        BIGINT PRIMARY KEY,
    root_place_id      BIGINT,
    name               TEXT NOT NULL,
    creator_type       TEXT,                    -- 'User' | 'Group'
    creator_id         BIGINT,
    creator_name       TEXT,
    created_at         TIMESTAMPTZ,             -- Roblox "created"
    updated_at_roblox  TIMESTAMPTZ,             -- Roblox "updated" (last publish)
    genre              TEXT,                    -- legacy genre string
    genre_l1           TEXT,                    -- Roblox genre taxonomy, level 1
    genre_l2           TEXT,                    -- level 2 (sub-genre)
    max_players        INT,
    age_rating         TEXT,                    -- from explore/charts payload when present
    population         TEXT,                    -- 'charts' | 'control' | 'own' | NULL (=other/long tail)
    launch_cohort      BOOLEAN NOT NULL DEFAULT FALSE,  -- created <=60d before first seen AND crossed 500 CCU
    tracking_tier      TEXT NOT NULL DEFAULT 'daily',   -- 'intensive' (30 min) | 'daily' | 'paused'
    first_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at       TIMESTAMPTZ,
    notes              TEXT,
    CONSTRAINT experience_population_chk CHECK (population IS NULL OR population IN ('charts','control','own')),
    CONSTRAINT experience_tier_chk CHECK (tracking_tier IN ('intensive','daily','paused'))
);
CREATE INDEX IF NOT EXISTS experience_tier_idx ON experience (tracking_tier);
CREATE INDEX IF NOT EXISTS experience_population_idx ON experience (population);
CREATE INDEX IF NOT EXISTS experience_created_idx ON experience (created_at);

-- Time series of headline stats. One row per game per collector run.
CREATE TABLE IF NOT EXISTS snapshot (
    universe_id  BIGINT NOT NULL REFERENCES experience(universe_id),
    ts           TIMESTAMPTZ NOT NULL,
    playing      INT,
    visits       BIGINT,
    favorites    BIGINT,
    upvotes      BIGINT,
    downvotes    BIGINT,
    PRIMARY KEY (universe_id, ts)
);
CREATE INDEX IF NOT EXISTS snapshot_ts_idx ON snapshot (ts);

-- Which sorts exist (discovered from the explore API, not hard-coded).
CREATE TABLE IF NOT EXISTS sort_catalog (
    sort_id        TEXT PRIMARY KEY,
    sort_name      TEXT,
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL
);

-- Position of every game on every front-page sort, every run.
CREATE TABLE IF NOT EXISTS chart_position (
    ts           TIMESTAMPTZ NOT NULL,
    sort_id      TEXT NOT NULL,
    sort_name    TEXT,
    device       TEXT NOT NULL DEFAULT 'computer',
    country      TEXT NOT NULL DEFAULT 'all',
    universe_id  BIGINT NOT NULL,
    position     INT NOT NULL,
    is_sponsored BOOLEAN NOT NULL DEFAULT FALSE,   -- the feed marks paid placements; keep them, flag them
    PRIMARY KEY (ts, sort_id, device, country, universe_id)
);
ALTER TABLE chart_position ADD COLUMN IF NOT EXISTS is_sponsored BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS chart_position_universe_idx ON chart_position (universe_id, ts);
CREATE INDEX IF NOT EXISTS chart_position_sort_idx ON chart_position (sort_id, ts);

-- -----------------------------------------------------------------------------
-- 2. Change logs (update cadence, title/thumbnail experiments fall out of these)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS name_history (
    universe_id    BIGINT NOT NULL REFERENCES experience(universe_id),
    name           TEXT NOT NULL,
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (universe_id, name)
);

CREATE TABLE IF NOT EXISTS description_history (
    universe_id    BIGINT NOT NULL REFERENCES experience(universe_id),
    desc_hash      TEXT NOT NULL,               -- sha1 of the description text
    description    TEXT,
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (universe_id, desc_hash)
);

CREATE TABLE IF NOT EXISTS thumbnail_history (
    universe_id    BIGINT NOT NULL REFERENCES experience(universe_id),
    kind           TEXT NOT NULL,               -- 'icon' | 'thumbnail'
    image_url      TEXT NOT NULL,               -- CDN URL changes when the image changes
    image_hash     TEXT,                        -- optional: sha1 of downloaded bytes
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (universe_id, kind, image_url)
);

-- -----------------------------------------------------------------------------
-- 3. Monetization scaffold
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gamepass (
    pass_id        BIGINT PRIMARY KEY,
    universe_id    BIGINT NOT NULL REFERENCES experience(universe_id),
    name           TEXT,
    price_robux    INT,                         -- NULL = off sale
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS gamepass_universe_idx ON gamepass (universe_id);

CREATE TABLE IF NOT EXISTS gamepass_price_history (
    pass_id        BIGINT NOT NULL REFERENCES gamepass(pass_id),
    price_robux    INT,                         -- NULL = off sale
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (pass_id, first_seen_at)
);

-- -----------------------------------------------------------------------------
-- 4. Creators, external signals, regime events
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS creator (
    creator_type   TEXT NOT NULL,               -- 'User' | 'Group'
    creator_id     BIGINT NOT NULL,
    name           TEXT,
    member_count   BIGINT,                      -- groups only, latest value
    created_at     TIMESTAMPTZ,                 -- users only
    first_seen_at  TIMESTAMPTZ NOT NULL,
    last_seen_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (creator_type, creator_id)
);

-- Anything measured outside Roblox's game stats: YouTube, TikTok, Discord,
-- group member counts over time. One row per (game, source, metric, time).
CREATE TABLE IF NOT EXISTS external_signal (
    universe_id  BIGINT NOT NULL REFERENCES experience(universe_id),
    source       TEXT NOT NULL,                 -- 'youtube' | 'tiktok' | 'discord' | 'roblox_group' | ...
    metric       TEXT NOT NULL,                 -- 'videos_7d' | 'views_7d' | 'members' | ...
    value        NUMERIC,
    ts           TIMESTAMPTZ NOT NULL,
    url          TEXT,
    PRIMARY KEY (universe_id, source, metric, ts)
);

-- Platform-level events that can shift what "works". Every analysis should be
-- runnable pre/post a regime event.
CREATE TABLE IF NOT EXISTS regime_event (
    id           SERIAL PRIMARY KEY,
    event_date   DATE NOT NULL,
    kind         TEXT NOT NULL,                 -- 'algorithm' | 'policy' | 'platform' | 'other'
    description  TEXT NOT NULL,
    url          TEXT
);

INSERT INTO regime_event (event_date, kind, description, url)
SELECT v.* FROM (VALUES
 ('2025-12-11'::date,'algorithm','Improved Recommended For You algorithm released globally; Home Recommendations tab added to Creator Analytics.','https://devforum.roblox.com/t/boost-your-discovery-with-the-improved-recommended-for-you-algorithm-and-analytics-for-creators/3587441'),
 ('2026-06-15'::date,'algorithm','Recommended For You moved from a 7-day to a 28-day window measuring long-term retention (D1, D2-7, D8-28); play-through, session quality and spend measured separately; full signal list and weights published to creators.','https://about.roblox.com/newsroom/2026/06/optimizing-discovery-great-games-reach-millions-players-roblox'),
 ('2026-08-20'::date,'algorithm','Roblox announces testing of a further RFY update to better recognize long-term player value (games players return to over time).','https://devforum.roblox.com/t/boost-your-discovery-by-building-games-people-want-to-play/4779042')
) AS v(event_date, kind, description, url)
WHERE NOT EXISTS (SELECT 1 FROM regime_event r WHERE r.event_date = v.event_date AND r.description = v.description);

-- -----------------------------------------------------------------------------
-- 5. Features and the codebook
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS codebook (
    feature_key     TEXT PRIMARY KEY,
    family          TEXT NOT NULL,              -- 'auto' (machine-extractable) | 'play' (requires playing)
    value_type      TEXT NOT NULL,              -- 'bool' | 'enum' | 'multi' | 'number'
    definition      TEXT NOT NULL,
    allowed_values  TEXT,                       -- for enum/multi: pipe-separated
    version         TEXT NOT NULL DEFAULT 'v1'
);

-- One row per coding event. Latest per (universe, feature) is what analysis uses
-- (see v_feature_latest). Keep old rows: they show how a game changed.
CREATE TABLE IF NOT EXISTS feature (
    universe_id       BIGINT NOT NULL REFERENCES experience(universe_id),
    feature_key       TEXT NOT NULL REFERENCES codebook(feature_key),
    value_text        TEXT,                     -- bool ('true'/'false'), enum, multi ('a|b')
    value_num         NUMERIC,                  -- numbers
    coded_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    coder             TEXT NOT NULL,            -- 'auto' | 'llm' | initials of a human coder
    codebook_version  TEXT NOT NULL DEFAULT 'v1',
    evidence          TEXT,                     -- optional: why (screenshot path, timestamp in a video, quote)
    PRIMARY KEY (universe_id, feature_key, coded_at, coder)
);
CREATE INDEX IF NOT EXISTS feature_key_idx ON feature (feature_key);

-- Codebook v1. Edit freely; bump `version` when a definition changes.
INSERT INTO codebook (feature_key, family, value_type, definition, allowed_values) VALUES
 -- ---- auto: title / description --------------------------------------------
 ('title_pattern','auto','enum','Dominant naming template of the current title.','verb_a_noun|x_simulator|x_tycoon|x_rng|x_rp|obby|named_ip|descriptive|other'),
 ('title_len_chars','auto','number','Length of the current title in characters, emoji included.',NULL),
 ('title_emoji_count','auto','number','Count of emoji/pictographs in the current title.',NULL),
 ('title_has_update_tag','auto','bool','Title carries a bracketed or emoji-flagged update/event tag, e.g. [UPDATE], [NEW], 🎃 EVENT.',NULL),
 ('title_is_sequel','auto','bool','Title marks a sequel or numbered version (e.g. "2", "II", "Remastered").',NULL),
 ('desc_len_chars','auto','number','Length of the current description in characters.',NULL),
 ('desc_has_discord','auto','bool','Description links to or names a Discord server.',NULL),
 ('desc_has_codes','auto','bool','Description mentions redeemable codes.',NULL),
 -- ---- auto: icon / thumbnail (vision-model tagged) -----------------------------
 ('icon_has_face','auto','bool','Icon shows at least one face with a readable expression.',NULL),
 ('icon_has_text','auto','bool','Icon has overlaid text.',NULL),
 ('icon_has_arrow','auto','bool','Icon has an arrow, circle, or other pointing device.',NULL),
 ('icon_character_count','auto','number','Number of distinct characters/creatures visible in the icon.',NULL),
 -- ---- auto: monetization scaffold ---------------------------------------------
 ('pass_count','auto','number','Number of on-sale game passes.',NULL),
 ('pass_min_price','auto','number','Cheapest on-sale game pass in Robux.',NULL),
 ('pass_median_price','auto','number','Median on-sale game pass price in Robux.',NULL),
 ('pass_has_boost','auto','bool','Any pass sells luck, 2x, speed, auto-collect or similar progression boosts.',NULL),
 ('pass_has_vip','auto','bool','Any pass is a VIP/premium bundle.',NULL),
 -- ---- auto: structure / cadence / creator -------------------------------------
 ('server_size','auto','number','Max players per server (maxPlayers).',NULL),
 ('age_rating','auto','enum','Roblox age recommendation label.','all_ages|9plus|13plus|17plus|unrated'),
 ('genre_l1','auto','enum','Roblox genre taxonomy level 1, as returned by the API.',NULL),
 ('genre_l2','auto','enum','Roblox genre taxonomy level 2, as returned by the API.',NULL),
 ('update_freq_per_week','auto','number','Distinct description/name/thumbnail change events per week over the trailing 28 days.',NULL),
 ('creator_is_group','auto','bool','Owned by a group rather than an individual user.',NULL),
 ('creator_prior_peak_ccu','auto','number','Highest peak CCU of any earlier experience by the same creator.',NULL),
 ('creator_group_members','auto','number','Group member count at coding time (groups only).',NULL),
 -- ---- play: core loop and session ---------------------------------------------
 ('core_loop','play','enum','What the player mostly does, minute to minute.','collect|grow|steal|tycoon|obby|horror|round_pvp|roleplay|idle|rng|sports|shooter|other'),
 ('ttfr_seconds','play','number','Time to first reward: seconds from spawn until the first currency/item/progress feedback.',NULL),
 ('ttfc_seconds','play','number','Time to first meaningful choice: seconds until the player makes a decision that changes outcomes.',NULL),
 ('session_shape','play','enum','Persistent world vs discrete rounds.','persistent|rounds|hybrid'),
 ('round_length_s','play','number','Typical round length in seconds (rounds/hybrid only).',NULL),
 ('progression_type','play','multi','Progression systems present.','numbers_go_up|rebirth_prestige|rarity_collection|levels|cosmetic_only|none'),
 ('social_asymmetry','play','enum','Can players take from, help, or trade with each other?','none|take|help|trade|mixed'),
 ('can_lose_progress','play','bool','Players can lose accumulated progress (theft, death penalty, decay).',NULL),
 ('has_base_defense','play','bool','Players own a space they must defend or upgrade defensively.',NULL),
 ('offline_accrual','play','bool','Progress accrues while the player is offline.',NULL),
 ('has_timers_or_fomo','play','bool','Limited-time items, timers, rotating shops or events present.',NULL),
 ('first_purchase_prompt_min','play','number','Minutes into a fresh session before the first purchase prompt appears.',NULL),
 ('first_purchase_price','play','number','Robux price of the first purchase prompted.',NULL),
 ('mobile_one_thumb','play','bool','Core loop is playable one-handed on a phone.',NULL),
 ('lowend_fps_ok','play','bool','Holds a playable frame rate on a low-end phone.',NULL),
 ('borrows_meme_or_ip','play','enum','Leans on an internet trend or existing IP.','none|meme|anime|other_game|brand')
ON CONFLICT (feature_key) DO NOTHING;

-- -----------------------------------------------------------------------------
-- 6. Your own games' analytics, in the same database
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS own_experiment (
    universe_id          BIGINT NOT NULL REFERENCES experience(universe_id),
    metric_date          DATE NOT NULL,
    source               TEXT NOT NULL,         -- 'organic' | 'sponsored' | 'all'
    new_users            INT,
    d1_retention         NUMERIC,
    d7_retention         NUMERIC,
    d30_retention        NUMERIC,
    play_through_rate    NUMERIC,
    first_play_bounce    NUMERIC,
    play_days_per_user   NUMERIC,
    playtime_per_user_s  NUMERIC,
    coplay_days_per_user NUMERIC,
    spend_per_user       NUMERIC,
    notes                TEXT,
    PRIMARY KEY (universe_id, metric_date, source)
);

-- -----------------------------------------------------------------------------
-- 7. Collector bookkeeping (so you notice when a job stops running)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS collector_run (
    id            SERIAL PRIMARY KEY,
    job           TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL,
    finished_at   TIMESTAMPTZ,
    ok            BOOLEAN,
    rows_written  INT,
    http_requests INT,
    error         TEXT
);

-- =============================================================================
-- 8. Analysis views
-- =============================================================================

-- Daily roll-up of CCU. Turn into a MATERIALIZED VIEW once snapshot > ~50M rows.
CREATE OR REPLACE VIEW v_daily_ccu AS
SELECT universe_id,
       (ts AT TIME ZONE 'UTC')::date AS day,
       avg(playing)::numeric(12,1)   AS avg_ccu,
       max(playing)                  AS max_ccu,
       count(*)                      AS n_snapshots
FROM snapshot
WHERE playing IS NOT NULL
GROUP BY 1, 2;

-- Peak day per game (by daily average CCU).
CREATE OR REPLACE VIEW v_peak AS
SELECT DISTINCT ON (universe_id)
       universe_id, day AS peak_day, avg_ccu AS peak_avg_ccu, max_ccu AS peak_max_ccu
FROM v_daily_ccu
ORDER BY universe_id, avg_ccu DESC, day;

-- Decay half-life: days from peak until daily average first falls below 50% of peak.
-- NULL half_life_days = has not decayed yet (still within 50% of peak) or not enough data.
CREATE OR REPLACE VIEW v_decay AS
WITH half AS (
    SELECT p.universe_id, p.peak_day, p.peak_avg_ccu,
           min(d.day) AS half_day
    FROM v_peak p
    LEFT JOIN v_daily_ccu d
           ON d.universe_id = p.universe_id
          AND d.day > p.peak_day
          AND d.avg_ccu < 0.5 * p.peak_avg_ccu
    GROUP BY p.universe_id, p.peak_day, p.peak_avg_ccu
)
SELECT universe_id, peak_day, peak_avg_ccu, half_day,
       (half_day - peak_day) AS half_life_days
FROM half;

-- Sustained CCU: median daily-average CCU over days 8–28 after peak (mirrors RFY's D8–28 window).
CREATE OR REPLACE VIEW v_sustained AS
SELECT p.universe_id,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY d.avg_ccu) AS sustained_ccu_d8_28,
       count(*) AS days_observed,
       (percentile_cont(0.5) WITHIN GROUP (ORDER BY d.avg_ccu) / NULLIF(p.peak_avg_ccu, 0))::numeric(6,3) AS sustain_ratio
FROM v_peak p
JOIN v_daily_ccu d
  ON d.universe_id = p.universe_id
 AND d.day BETWEEN p.peak_day + 8 AND p.peak_day + 28
GROUP BY p.universe_id, p.peak_avg_ccu;

-- Outcome tiers. Thresholds are deliberate and fixed; change them here only.
CREATE OR REPLACE VIEW v_tier AS
SELECT e.universe_id, e.name, e.population, e.launch_cohort, e.created_at,
       p.peak_day, p.peak_max_ccu, p.peak_avg_ccu,
       CASE WHEN p.peak_max_ccu >= 100000 THEN 'breakout'
            WHEN p.peak_max_ccu >=  20000 THEN 'hit'
            WHEN p.peak_max_ccu >=   2000 THEN 'mid'
            WHEN p.peak_max_ccu IS NULL   THEN NULL
            ELSE 'tail' END AS tier
FROM experience e
LEFT JOIN v_peak p USING (universe_id);

-- Days on each sort and best organic position (sponsored placements are counted separately).
CREATE OR REPLACE VIEW v_chart_summary AS
SELECT universe_id, sort_id, max(sort_name) AS sort_name,
       count(DISTINCT (ts AT TIME ZONE 'UTC')::date) FILTER (WHERE NOT is_sponsored) AS days_on_chart,
       min(position) FILTER (WHERE NOT is_sponsored) AS best_position,
       min(ts) AS first_on, max(ts) AS last_on,
       count(DISTINCT (ts AT TIME ZONE 'UTC')::date) FILTER (WHERE is_sponsored) AS sponsored_days
FROM chart_position
GROUP BY universe_id, sort_id;

-- Latest coded value per (game, feature). Precedence: a human coder beats the LLM, which beats 'auto';
-- within the same coder class the newest row wins.
CREATE OR REPLACE VIEW v_feature_latest AS
SELECT DISTINCT ON (universe_id, feature_key)
       universe_id, feature_key, value_text, value_num, coded_at, coder, codebook_version, evidence
FROM feature
ORDER BY universe_id, feature_key,
         CASE WHEN coder = 'auto' THEN 2 WHEN coder = 'llm' THEN 1 ELSE 0 END,
         coded_at DESC;

-- Numeric features: median among hits vs among controls (the lift table only handles categories).
CREATE OR REPLACE VIEW v_feature_numeric AS
WITH f AS (
    SELECT fl.feature_key, fl.value_num, t.tier, t.population
    FROM v_feature_latest fl JOIN v_tier t USING (universe_id)
    WHERE fl.value_num IS NOT NULL
)
SELECT feature_key,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY value_num) FILTER (WHERE tier IN ('breakout','hit')) AS median_hits,
       count(*) FILTER (WHERE tier IN ('breakout','hit'))                                                 AS n_hits,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY value_num) FILTER (WHERE population = 'control')       AS median_control,
       count(*) FILTER (WHERE population = 'control')                                                     AS n_control
FROM f
GROUP BY feature_key
ORDER BY feature_key;

-- Games whose name, description or images changed after a human/LLM coded them: worth a second look.
CREATE OR REPLACE VIEW v_recode_candidates AS
WITH last_coded AS (
    SELECT universe_id, max(coded_at) AS coded_at FROM feature WHERE coder <> 'auto' GROUP BY universe_id
),
changes AS (
    SELECT universe_id, max(first_seen_at) AS changed_at FROM (
        SELECT universe_id, first_seen_at FROM name_history
        UNION ALL SELECT universe_id, first_seen_at FROM description_history
        UNION ALL SELECT universe_id, first_seen_at FROM thumbnail_history
    ) x GROUP BY universe_id
)
SELECT e.universe_id, e.name, lc.coded_at AS last_coded_at, ch.changed_at
FROM experience e
JOIN last_coded lc USING (universe_id)
JOIN changes ch USING (universe_id)
WHERE ch.changed_at > lc.coded_at + interval '1 hour'
ORDER BY ch.changed_at DESC;

-- How far the coding has got, per feature.
CREATE OR REPLACE VIEW v_coding_progress AS
SELECT c.family, c.feature_key,
       count(DISTINCT f.universe_id)                                            AS games_coded,
       count(DISTINCT f.universe_id) FILTER (WHERE f.coder = 'llm')             AS by_llm,
       count(DISTINCT f.universe_id) FILTER (WHERE f.coder NOT IN ('auto','llm')) AS by_humans
FROM codebook c
LEFT JOIN feature f USING (feature_key)
GROUP BY c.family, c.feature_key
ORDER BY c.family, c.feature_key;

-- Lift table for categorical/bool features: prevalence among hits+breakouts vs the control frame.
-- Compute confidence intervals in Python (Wilson); this view gives the point estimates.
CREATE OR REPLACE VIEW v_feature_lift AS
WITH f AS (
    SELECT fl.feature_key, fl.value_text, t.tier, t.population
    FROM v_feature_latest fl
    JOIN v_tier t USING (universe_id)
    WHERE fl.value_text IS NOT NULL
),
hit_with  AS (SELECT feature_key, value_text, count(*) AS n FROM f WHERE tier IN ('breakout','hit') GROUP BY 1,2),
hit_tot   AS (SELECT feature_key, count(*) AS n FROM f WHERE tier IN ('breakout','hit') GROUP BY 1),
ctrl_with AS (SELECT feature_key, value_text, count(*) AS n FROM f WHERE population = 'control' GROUP BY 1,2),
ctrl_tot  AS (SELECT feature_key, count(*) AS n FROM f WHERE population = 'control' GROUP BY 1)
SELECT hw.feature_key, hw.value_text,
       hw.n AS n_hits_with, ht.n AS n_hits,
       COALESCE(cw.n, 0) AS n_control_with, ct.n AS n_control,
       (hw.n::numeric / ht.n)::numeric(6,3) AS p_hits,
       (COALESCE(cw.n, 0)::numeric / NULLIF(ct.n, 0))::numeric(6,3) AS p_control,
       ((hw.n::numeric / ht.n) / NULLIF(COALESCE(cw.n, 0)::numeric / NULLIF(ct.n, 0), 0))::numeric(8,2) AS lift
FROM hit_with hw
JOIN hit_tot  ht USING (feature_key)
LEFT JOIN ctrl_with cw USING (feature_key, value_text)
LEFT JOIN ctrl_tot  ct USING (feature_key)
ORDER BY lift DESC NULLS LAST, p_hits DESC;

-- Breakout detector: games whose daily average CCU grew >=50% day-over-day to at least 300.
-- Used by the collector's `promote` job; also your daily "what just ignited" list.
CREATE OR REPLACE VIEW v_growth_alerts AS
WITH recent AS (                       -- only the last 3 days of snapshots: cheap even at scale
    SELECT universe_id, (ts AT TIME ZONE 'UTC')::date AS day, avg(playing)::numeric(12,1) AS avg_ccu
    FROM snapshot
    WHERE ts > now() - interval '3 days' AND playing IS NOT NULL
    GROUP BY 1, 2
),
d AS (
    SELECT universe_id, day, avg_ccu,
           lag(avg_ccu) OVER (PARTITION BY universe_id ORDER BY day) AS prev_avg
    FROM recent
)
SELECT d.universe_id, e.name, d.day, d.prev_avg, d.avg_ccu,
       (d.avg_ccu / NULLIF(d.prev_avg, 0))::numeric(8,2) AS growth,
       e.created_at
FROM d
JOIN experience e USING (universe_id)
WHERE d.day >= (now() AT TIME ZONE 'UTC')::date - 1
  AND d.avg_ccu >= 300
  AND d.prev_avg IS NOT NULL
  AND d.avg_ccu >= 1.5 * d.prev_avg;

-- Wave analysis: new entrants per ISO week for each core-loop archetype, with their outcome.
CREATE OR REPLACE VIEW v_archetype_entrants_weekly AS
SELECT fl.value_text AS core_loop,
       date_trunc('week', e.created_at)::date AS week,
       count(*) AS entrants,
       count(*) FILTER (WHERE t.tier IN ('breakout','hit')) AS hits,
       avg(t.peak_max_ccu)::numeric(12,0) AS avg_peak_ccu
FROM v_feature_latest fl
JOIN experience e USING (universe_id)
JOIN v_tier t USING (universe_id)
WHERE fl.feature_key = 'core_loop' AND e.created_at IS NOT NULL
GROUP BY 1, 2;

COMMIT;

-- =============================================================================
-- 9. Partner round: categories, velocity, retention proxies, cohorts, thumbnails
--    (schema v0.4 — appended; re-running the whole file is still safe)
-- =============================================================================

BEGIN;

-- play_mode: the explicit PvE / PvP / social / party / trading label, coded by the LLM pass.
INSERT INTO codebook (feature_key, family, value_type, definition, allowed_values) VALUES
 ('play_mode','play','multi','How players relate to the game and each other: all that apply.','pve|pvp|coop|social|party|trading|roleplay|creative')
ON CONFLICT (feature_key) DO NOTHING;

-- core_loop vocabulary v2: the first pass left 27% of games as 'other'; these cover the common Roblox loops.
UPDATE codebook SET allowed_values =
  'collect|grow|steal|tycoon|obby|horror|round_pvp|roleplay|idle|rng|sports|shooter|fighting|survival|tower_defense|vehicle_sim|sandbox_physics|build_craft|dress_up|rhythm|puzzle|hangout|racing|other',
  version = 'v2'
WHERE feature_key = 'core_loop' AND version <> 'v2';

-- One primary category per game, derived from play_mode, then core_loop, then Roblox's own genre.
CREATE OR REPLACE VIEW v_category AS
WITH f AS (
    SELECT universe_id,
           max(value_text) FILTER (WHERE feature_key = 'play_mode') AS play_mode,
           max(value_text) FILTER (WHERE feature_key = 'core_loop') AS core_loop
    FROM v_feature_latest
    WHERE feature_key IN ('play_mode', 'core_loop')
    GROUP BY universe_id
)
SELECT e.universe_id, e.name, e.genre_l1, e.genre_l2, f.play_mode, f.core_loop,
       CASE
         WHEN f.play_mode LIKE '%pvp%'      THEN 'PvP'
         WHEN f.play_mode LIKE '%coop%'     THEN 'Co-op PvE'
         WHEN f.play_mode LIKE '%trading%'  THEN 'Trading'
         WHEN f.play_mode LIKE '%party%'    THEN 'Party'
         WHEN f.play_mode LIKE '%social%'   THEN 'Social'
         WHEN f.play_mode LIKE '%roleplay%' THEN 'Roleplay'
         WHEN f.play_mode LIKE '%creative%' THEN 'Creative'
         WHEN f.play_mode LIKE '%pve%'      THEN 'PvE'
         WHEN f.core_loop IN ('round_pvp','shooter','sports','steal','fighting','racing') THEN 'PvP'
         WHEN f.core_loop IN ('roleplay','dress_up')                 THEN 'Roleplay'
         WHEN f.core_loop IN ('hangout')                             THEN 'Social'
         WHEN f.core_loop IN ('build_craft','sandbox_physics')       THEN 'Creative'
         WHEN f.core_loop IN ('collect','grow','tycoon','idle','rng','obby','horror','survival','tower_defense','vehicle_sim','rhythm','puzzle') THEN 'PvE'
         WHEN e.genre_l1 ILIKE '%roleplay%' OR e.genre_l1 ILIKE '%avatar%' THEN 'Roleplay'
         WHEN e.genre_l1 ILIKE '%party%'   THEN 'Party'
         WHEN e.genre_l1 ILIKE '%shooter%' OR e.genre_l1 ILIKE '%sports%' OR e.genre_l1 ILIKE '%action%' THEN 'PvP'
         WHEN e.genre_l1 IS NOT NULL THEN 'PvE'
         ELSE 'Uncategorised' END AS category
FROM experience e
LEFT JOIN f USING (universe_id);

-- Velocity: how fast each game is gaining or losing players, over three horizons, plus chart movement.
CREATE OR REPLACE VIEW v_velocity AS
WITH w AS (
    SELECT universe_id,
           avg(playing) FILTER (WHERE ts > now() - interval '24 hours')                                                   AS ccu_24h,
           avg(playing) FILTER (WHERE ts BETWEEN now() - interval '48 hours' AND now() - interval '24 hours')             AS ccu_prev_24h,
           avg(playing) FILTER (WHERE ts BETWEEN now() - interval '8 days'   AND now() - interval '7 days')               AS ccu_7d_ago,
           avg(playing) FILTER (WHERE ts BETWEEN now() - interval '29 days'  AND now() - interval '28 days')              AS ccu_28d_ago,
           max(playing) FILTER (WHERE ts > now() - interval '7 days')                                                     AS peak_7d,
           avg(playing) FILTER (WHERE ts > now() - interval '6 hours')                                                    AS ccu_6h
    FROM snapshot
    WHERE ts > now() - interval '29 days' AND playing IS NOT NULL
    GROUP BY universe_id
),
r AS (
    SELECT universe_id,
           min(position) FILTER (WHERE ts > now() - interval '24 hours' AND sort_id = 'top-trending' AND NOT is_sponsored)                              AS trending_rank_now,
           min(position) FILTER (WHERE ts BETWEEN now() - interval '8 days' AND now() - interval '7 days' AND sort_id = 'top-trending' AND NOT is_sponsored) AS trending_rank_7d_ago
    FROM chart_position
    WHERE ts > now() - interval '8 days'
    GROUP BY universe_id
)
SELECT e.universe_id, e.name,
       round(w.ccu_24h)::int                                             AS ccu_24h,
       (w.ccu_24h / NULLIF(w.ccu_prev_24h, 0) - 1)::numeric(8,3)          AS growth_1d,
       (w.ccu_24h / NULLIF(w.ccu_7d_ago, 0) - 1)::numeric(8,3)            AS growth_7d,
       (w.ccu_24h / NULLIF(w.ccu_28d_ago, 0) - 1)::numeric(8,3)           AS growth_28d,
       w.peak_7d,
       r.trending_rank_now, r.trending_rank_7d_ago,
       (r.trending_rank_7d_ago - r.trending_rank_now)                     AS trending_rank_climb,   -- positive = moved up
       CASE WHEN w.ccu_7d_ago IS NULL                       THEN 'new / no 7-day baseline'
            WHEN w.ccu_24h / NULLIF(w.ccu_7d_ago, 0) - 1 >  0.50 THEN 'surging'
            WHEN w.ccu_24h / NULLIF(w.ccu_7d_ago, 0) - 1 >  0.10 THEN 'growing'
            WHEN w.ccu_24h / NULLIF(w.ccu_7d_ago, 0) - 1 > -0.10 THEN 'flat'
            WHEN w.ccu_24h / NULLIF(w.ccu_7d_ago, 0) - 1 > -0.40 THEN 'declining'
            ELSE 'collapsing' END                                         AS velocity_label,
       round(w.ccu_6h)::int                                              AS ccu_6h,
       (w.ccu_6h / NULLIF(w.ccu_24h, 0))::numeric(6,2)                    AS momentum          -- <1 = fading within the day
FROM experience e
JOIN w USING (universe_id)
LEFT JOIN r USING (universe_id);

-- Retention PROXIES. Roblox does not publish retention for other studios' games; these are the closest public
-- stand-ins: how much of its peak a game keeps on days 8–28, how fast it decays, and how players rate it.
-- True D1/D7/D30 exists only for your own games (own_experiment).
CREATE OR REPLACE VIEW v_retention_proxy AS
WITH latest AS (
    SELECT DISTINCT ON (universe_id) universe_id, ts, playing, visits, favorites, upvotes, downvotes
    FROM snapshot ORDER BY universe_id, ts DESC
)
SELECT e.universe_id, e.name,
       s.sustain_ratio                                                     AS staying_power_d8_28,   -- 1.0 = still at peak
       d.half_life_days,
       (l.upvotes::numeric / NULLIF(l.upvotes + l.downvotes, 0))::numeric(5,3) AS like_ratio,
       (l.favorites::numeric * 1000 / NULLIF(l.visits, 0))::numeric(8,3)       AS favourites_per_1k_visits,
       l.visits, l.favorites, l.ts AS as_of
FROM experience e
JOIN latest l USING (universe_id)
LEFT JOIN v_sustained s USING (universe_id)
LEFT JOIN v_decay d USING (universe_id);

-- Cohorts by launch month. Note the frame: games we track are games that reached a front-page sort,
-- so these are "games that got noticed", not all games created that month.
CREATE OR REPLACE VIEW v_cohort_monthly AS
SELECT date_trunc('month', e.created_at)::date                             AS cohort_month,
       CASE WHEN e.created_at >= '2026-06-15' THEN 'post RFY 28-day' ELSE 'pre' END AS regime,
       count(*)                                                            AS games_tracked,
       count(*) FILTER (WHERE p.peak_max_ccu >= 2000)                       AS reached_2k,
       count(*) FILTER (WHERE p.peak_max_ccu >= 20000)                      AS reached_20k,
       count(*) FILTER (WHERE p.peak_max_ccu >= 100000)                     AS reached_100k,
       (count(*) FILTER (WHERE p.peak_max_ccu >= 20000))::numeric / NULLIF(count(*), 0) AS hit_rate,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY p.peak_max_ccu)         AS median_peak,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY d.half_life_days)       AS median_half_life_days,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY s.sustain_ratio)        AS median_staying_power
FROM experience e
LEFT JOIN v_peak p USING (universe_id)
LEFT JOIN v_decay d USING (universe_id)
LEFT JOIN v_sustained s USING (universe_id)
WHERE e.created_at >= '2024-01-01'
GROUP BY 1, 2
ORDER BY 1;

-- Median trajectory of launch-cohort games by days since creation, per cohort month.
CREATE OR REPLACE VIEW v_cohort_curve AS
SELECT date_trunc('month', e.created_at)::date                 AS cohort_month,
       (d.day - e.created_at::date)                            AS day_n,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY d.avg_ccu)  AS median_ccu,
       count(*)                                                AS games
FROM v_daily_ccu d
JOIN experience e USING (universe_id)
WHERE e.launch_cohort AND d.day >= e.created_at::date
GROUP BY 1, 2
ORDER BY 1, 2;

-- Category roll-up: everything the partner asked to see per category, side by side.
CREATE OR REPLACE VIEW v_category_summary AS
SELECT c.category,
       count(*)                                                                      AS games,
       count(*) FILTER (WHERE t.tier IN ('breakout','hit'))                           AS hits,
       count(*) FILTER (WHERE e.created_at > now() - interval '30 days')              AS entrants_30d,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY v.growth_7d)                       AS median_growth_7d,
       count(*) FILTER (WHERE v.velocity_label = 'surging')                           AS surging_now,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY r.staying_power_d8_28)             AS median_staying_power,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY r.half_life_days)                  AS median_half_life_days,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY r.like_ratio)                      AS median_like_ratio,
       sum(v.ccu_24h)                                                                 AS players_now
FROM v_category c
JOIN experience e USING (universe_id)
LEFT JOIN v_tier t USING (universe_id)
LEFT JOIN v_velocity v USING (universe_id)
LEFT JOIN v_retention_proxy r USING (universe_id)
GROUP BY c.category
ORDER BY players_now DESC NULLS LAST;

-- Thumbnail evaluation (observational): players in the 7 days before vs after each icon/banner change.
CREATE OR REPLACE VIEW v_thumbnail_impact AS
WITH changes AS (
    SELECT th.universe_id, th.kind, th.image_url, th.first_seen_at AS changed_at
    FROM thumbnail_history th
    JOIN experience e USING (universe_id)
    WHERE th.first_seen_at > e.first_seen_at + interval '1 hour'    -- a real change, not the first capture
)
SELECT c.universe_id, e.name, c.kind, c.changed_at, c.image_url,
       avg(s.playing) FILTER (WHERE s.ts >= c.changed_at - interval '7 days' AND s.ts <  c.changed_at)::numeric(12,1) AS ccu_before_7d,
       avg(s.playing) FILTER (WHERE s.ts >  c.changed_at AND s.ts <= c.changed_at + interval '7 days')::numeric(12,1) AS ccu_after_7d,
       (avg(s.playing) FILTER (WHERE s.ts >  c.changed_at AND s.ts <= c.changed_at + interval '7 days')
        / NULLIF(avg(s.playing) FILTER (WHERE s.ts >= c.changed_at - interval '7 days' AND s.ts < c.changed_at), 0) - 1)::numeric(8,3) AS change_pct
FROM changes c
JOIN experience e USING (universe_id)
LEFT JOIN snapshot s ON s.universe_id = c.universe_id
                    AND s.ts BETWEEN c.changed_at - interval '7 days' AND c.changed_at + interval '7 days'
GROUP BY c.universe_id, e.name, c.kind, c.changed_at, c.image_url
ORDER BY c.changed_at DESC;

-- How often games change their icon/banner, by tier: do hits refresh their thumbnails more?
CREATE OR REPLACE VIEW v_thumbnail_churn AS
SELECT t.tier,
       count(DISTINCT e.universe_id)                                                        AS games,
       count(th.*) FILTER (WHERE th.first_seen_at > e.first_seen_at + interval '1 hour')     AS changes_observed,
       (count(th.*) FILTER (WHERE th.first_seen_at > e.first_seen_at + interval '1 hour'))::numeric
         / NULLIF(count(DISTINCT e.universe_id), 0)                                         AS changes_per_game,
       min(e.first_seen_at)                                                                 AS observed_since
FROM experience e
LEFT JOIN v_tier t USING (universe_id)
LEFT JOIN thumbnail_history th ON th.universe_id = e.universe_id
GROUP BY t.tier
ORDER BY t.tier;

COMMIT;


-- =============================================================================
-- 10. Explosive radar (schema v0.5)
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS radar_report (
    universe_id  BIGINT NOT NULL REFERENCES experience(universe_id),
    report_date  DATE NOT NULL,
    heat         NUMERIC,
    triggers     TEXT[],
    dossier      JSONB,                      -- everything the analyst was shown
    report       JSONB,                      -- the structured brief
    markdown     TEXT,                       -- the rendered brief
    model        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (universe_id, report_date)
);

-- Who is igniting right now, why they tripped the radar, and a heat score to rank them.
-- "First time" triggers only count for games we have watched for 7+ days, or genuinely new games (created < 60 days ago).
CREATE OR REPLACE VIEW v_radar_candidates AS
WITH first_major AS (
    SELECT universe_id, min(ts) AS first_on_major
    FROM chart_position
    WHERE sort_id IN ('top-trending','up-and-coming','top-playing-now') AND NOT is_sponsored AND position <= 100
    GROUP BY universe_id
),
milestones AS (
    SELECT universe_id,
           max(playing) FILTER (WHERE ts >  now() - interval '24 hours') AS max_24h,
           max(playing) FILTER (WHERE ts <= now() - interval '24 hours') AS max_before
    FROM snapshot GROUP BY universe_id
),
alerts AS (SELECT DISTINCT universe_id FROM v_growth_alerts),
base AS (
    SELECT e.universe_id, e.name, e.created_at, v.ccu_24h, v.growth_1d, v.growth_7d, v.growth_28d,
           v.trending_rank_now, v.trending_rank_climb, v.velocity_label, v.momentum,
           (e.first_seen_at < now() - interval '7 days' OR e.created_at > now() - interval '60 days') AS history_ok,
           (a.universe_id IS NOT NULL)                                                   AS t_alert,
           (f.first_on_major > now() - interval '24 hours'
              AND (e.first_seen_at < now() - interval '3 days' OR e.created_at > now() - interval '60 days')) AS t_chart,
           (v.trending_rank_climb >= 20)                                                 AS t_climb,
           (v.growth_7d >= 1.0 AND v.ccu_24h >= 1000)                                    AS t_double,
           CASE WHEN m.max_24h >= 50000 AND coalesce(m.max_before, 0) < 50000 THEN 50000
                WHEN m.max_24h >= 10000 AND coalesce(m.max_before, 0) < 10000 THEN 10000
                WHEN m.max_24h >=  2000 AND coalesce(m.max_before, 0) <  2000 THEN  2000 END AS milestone
    FROM experience e
    JOIN v_velocity v USING (universe_id)
    LEFT JOIN alerts a USING (universe_id)
    LEFT JOIN first_major f USING (universe_id)
    LEFT JOIN milestones m USING (universe_id)
    WHERE e.tracking_tier <> 'paused'
)
SELECT universe_id, name, created_at, ccu_24h, growth_1d, growth_7d, growth_28d, trending_rank_now, trending_rank_climb, velocity_label,
       array_remove(ARRAY[
           CASE WHEN t_alert                       THEN 'growth alert: daily players up 50%+ day-over-day' END,
           CASE WHEN t_chart                       THEN 'new to a major chart (top 100) in the last 24h' END,
           CASE WHEN t_climb                       THEN 'climbed 20+ places on Top Trending this week' END,
           CASE WHEN t_double                      THEN 'doubled players in 7 days' END,
           CASE WHEN history_ok AND milestone IS NOT NULL THEN 'crossed ' || (milestone / 1000) || 'k players for the first time' END
       ], NULL) AS triggers,
       (ln(greatest(coalesce(ccu_24h, 1), 1))
          * (1 + least(coalesce(greatest(growth_7d, 0), 0), 3) + 0.5 * least(coalesce(greatest(growth_1d, 0), 0), 3))
          * least(1.0, coalesce(momentum, 1) + 0.25)                       -- a spike that is already fading ranks lower
        + CASE WHEN t_chart THEN 3 ELSE 0 END
        + least(coalesce(greatest(trending_rank_climb, 0), 0), 50) / 10.0
        + CASE WHEN t_alert THEN 2 ELSE 0 END)::numeric(8,2) AS heat,
       momentum
FROM base
WHERE (t_alert OR t_chart OR t_climb OR t_double OR (history_ok AND milestone IS NOT NULL))
  AND coalesce(momentum, 1) >= 0.4                                        -- skip spikes that are already over
ORDER BY heat DESC;

COMMIT;
