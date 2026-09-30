-- =============================================================================
--  Roblox Trend Database (rtdb) — schema v0.2  (re-running this file is safe)
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

-- Latest coded value per (game, feature).
CREATE OR REPLACE VIEW v_feature_latest AS
SELECT DISTINCT ON (universe_id, feature_key)
       universe_id, feature_key, value_text, value_num, coded_at, coder, codebook_version
FROM feature
ORDER BY universe_id, feature_key, coded_at DESC;

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
