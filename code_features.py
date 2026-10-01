#!/usr/bin/env python3
"""
code_features.py — Roblox Trend Database (rtdb), feature coding v0.1  (Phase 4 automation)

Turns the raw data the collector gathers into codebook features, and organises the small
remainder that still needs a human.

  python code_features.py auto
      Deterministic traits for every non-paused game (title pattern, emoji, update tags, sequel
      markers, description traits, game-pass scaffold, server size, age rating, genre, update
      frequency, creator traits). Free, takes seconds, safe to re-run: only changed values are written.

  python code_features.py llm [--limit 200] [--recode] [--missing KEY] [--no-vision] [--dry-run] [--model ID]
      Asks Claude to infer the design traits that can be read from a game's page: core loop,
      session shape, progression, social mechanics, risk, timers, borrowed IP, and the icon traits
      (from the icon image). Each answer is stored with a confidence and a one-line rationale.
      Needs ANTHROPIC_API_KEY (in secrets.txt as ANTHROPIC_API_KEY=... or as an env var).
      Codes games that were never coded; --recode also refreshes games whose name/description/
      icon changed since they were last coded. --dry-run prints one prompt and answer, writes nothing.

  python code_features.py queue [--n 50] [--out coding_queue.csv]
      Writes a prioritised CSV of games that still need the play-required traits (time to first
      reward, round length, first purchase prompt, mobile checks), with the LLM's low-confidence
      answers flagged for a second look. Fill it in with Excel, then:

  python code_features.py import coding_queue.csv --coder NC
      Loads the filled columns into the feature table under the given coder initials. Humans
      override the LLM, which overrides auto (see v_feature_latest).

Settings come from secrets.txt / .env next to this script or from environment variables:
  DATABASE_URL, ANTHROPIC_API_KEY, RTDB_LLM_MODEL (default claude-sonnet-5-5)
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import logging
import os
import re
import statistics
import sys
import time
from datetime import datetime

import psycopg

import collector as C   # reuses settings loading, the paced HTTP client and BASE_DIR

log = logging.getLogger("rtdb.code")
CODEBOOK_VERSION = "v1"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("RTDB_LLM_MODEL", "claude-sonnet-5-5")

# ----------------------------------------------------------------------------
# Shared helpers
# ----------------------------------------------------------------------------
def load_codebook(conn) -> dict[str, dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT feature_key, family, value_type, allowed_values FROM codebook")
        return {k: {"family": f, "type": t, "allowed": (a.split("|") if a else None)} for k, f, t, a in cur.fetchall()}


def latest_values(conn, coder: str | None = None) -> dict[tuple[int, str], tuple]:
    """(universe_id, feature_key) -> (value_text, value_num) of the latest row, optionally for one coder."""
    sql = """SELECT DISTINCT ON (universe_id, feature_key) universe_id, feature_key, value_text, value_num
             FROM feature {where} ORDER BY universe_id, feature_key, coded_at DESC"""
    with conn.cursor() as cur:
        if coder:
            cur.execute(sql.format(where="WHERE coder = %s"), (coder,))
        else:
            cur.execute(sql.format(where=""))
        return {(u, k): (t, n) for u, k, t, n in cur.fetchall()}


def write_features(conn, rows: list[tuple], coder: str, only_if_changed: dict | None = None) -> int:
    """rows: (universe_id, feature_key, value_text, value_num, evidence). Returns rows written."""
    out = []
    for uid, key, vt, vn, ev in rows:
        if vt is None and vn is None:
            continue
        if only_if_changed is not None:
            prev = only_if_changed.get((uid, key))
            if prev is not None and prev[0] == vt and _num_eq(prev[1], vn):
                continue
        out.append((uid, key, vt, vn, coder, CODEBOOK_VERSION, (ev or "")[:500]))
    if not out:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO feature (universe_id, feature_key, value_text, value_num, coder, codebook_version, evidence)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            out,
        )
    conn.commit()
    return len(out)


def _num_eq(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


def bool_text(v: bool) -> str:
    return "true" if v else "false"


# ----------------------------------------------------------------------------
# AUTO: deterministic traits
# ----------------------------------------------------------------------------
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\U0001F1E6-\U0001F1FF]")
TAG_RE = re.compile(r"[\[\(【][^\]\)】]{1,40}[\]\)】]")
UPDATE_WORD_RE = re.compile(r"\b(UPDATE|UPD|NEW|EVENT|RELEASE|PART\s*\d+|SEASON\s*\d+|HALLOWEEN|CHRISTMAS|WINTER|SUMMER|EASTER|ANNIVERSARY|CODES?)\b")
SEQUEL_RE = re.compile(r"(\s(2|3|4|5|ii|iii|iv)\b|remaster|reborn|remake|revamp|reloaded|\b2\.0\b)")
VERBS = {
    "steal", "grow", "build", "catch", "hatch", "adopt", "raise", "find", "plant", "fish", "escape", "survive", "be",
    "become", "make", "eat", "feed", "collect", "craft", "wash", "buy", "sell", "cook", "drive", "fly", "dig", "mine",
    "hunt", "train", "rob", "save", "drop", "kick", "punch", "win", "beat", "open", "get", "touch", "pop", "mow", "milk",
    "climb", "race", "ride", "tap", "click", "press", "pet", "own", "flip", "throw", "shoot", "dodge", "paint", "draw",
    "guess", "spin", "roll", "pull", "push", "carry", "lift", "break", "crack", "smash", "hit", "slap", "protect",
    "defend", "farm", "harvest", "brew", "bake", "merge", "evolve", "summon", "hide", "seek", "rescue", "free", "unbox",
    "spawn", "trade", "steal", "sneak", "raid", "loot", "fight", "kill", "blow", "fill", "stack", "dress", "run", "jump",
}
BOOST_RE = re.compile(r"luck|lucky|2x|x2|3x|x3|double|triple|boost|speed|fast|auto|instant|infinite|unlimited|multiplier|\+\d+%|more (coins|cash|money|gems)|extra")
VIP_RE = re.compile(r"\bvip\b|premium|elite|deluxe|starter|bundle|\bpack\b|supporter|donat")

AUTO_SQL = """
WITH latest_desc AS (
    SELECT DISTINCT ON (universe_id) universe_id, description
    FROM description_history ORDER BY universe_id, last_seen_at DESC
),
passes AS (
    SELECT universe_id,
           count(*) FILTER (WHERE price_robux > 0)                                                    AS pass_count,
           min(price_robux) FILTER (WHERE price_robux > 0)                                            AS pass_min,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY price_robux) FILTER (WHERE price_robux > 0)    AS pass_median,
           string_agg(lower(coalesce(name, '')), ' | ')                                               AS pass_names
    FROM gamepass WHERE last_seen_at > now() - interval '30 days'
    GROUP BY universe_id
),
changes AS (
    SELECT e.universe_id,
           (SELECT count(*) FROM name_history n WHERE n.universe_id = e.universe_id
              AND n.first_seen_at > e.first_seen_at + interval '1 hour' AND n.first_seen_at > now() - interval '28 days')
         + (SELECT count(*) FROM description_history d WHERE d.universe_id = e.universe_id
              AND d.first_seen_at > e.first_seen_at + interval '1 hour' AND d.first_seen_at > now() - interval '28 days')
         + (SELECT count(*) FROM thumbnail_history t WHERE t.universe_id = e.universe_id
              AND t.first_seen_at > e.first_seen_at + interval '1 hour' AND t.first_seen_at > now() - interval '28 days') AS n_changes,
           LEAST(28.0, GREATEST(1.0, EXTRACT(EPOCH FROM (now() - e.first_seen_at)) / 86400.0)) AS days_observed
    FROM experience e
),
prior AS (
    SELECT e.universe_id, max(p.peak_max_ccu) AS prior_peak
    FROM experience e
    JOIN experience o ON o.creator_type = e.creator_type AND o.creator_id = e.creator_id
                     AND o.universe_id <> e.universe_id AND o.created_at < e.created_at
    JOIN v_peak p ON p.universe_id = o.universe_id
    GROUP BY e.universe_id
)
SELECT e.universe_id, e.name, ld.description, e.max_players, e.age_rating, e.genre_l1, e.genre_l2,
       e.creator_type, c.member_count,
       ps.pass_count, ps.pass_min, ps.pass_median, ps.pass_names,
       ch.n_changes, ch.days_observed, pr.prior_peak
FROM experience e
LEFT JOIN latest_desc ld USING (universe_id)
LEFT JOIN passes ps USING (universe_id)
LEFT JOIN changes ch USING (universe_id)
LEFT JOIN prior pr USING (universe_id)
LEFT JOIN creator c ON c.creator_type = e.creator_type AND c.creator_id = e.creator_id
WHERE e.tracking_tier <> 'paused'
ORDER BY e.universe_id
"""


def clean_title(name: str) -> str:
    t = TAG_RE.sub(" ", name or "")
    t = EMOJI_RE.sub(" ", t)
    t = re.sub(r"[^\w\s'&.-]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def title_pattern(name: str) -> str:
    t = clean_title(name)
    m = re.match(r"^([a-z]+)\s+(a|an|the|some|your|my)\s+\w", t)
    if m and m.group(1) in VERBS:
        return "verb_a_noun"
    if re.search(r"\bsimulator\b|\bsim\b", t):
        return "x_simulator"
    if "tycoon" in t:
        return "x_tycoon"
    if re.search(r"\brng\b", t):
        return "x_rng"
    if re.search(r"\brp\b|roleplay|role play", t):
        return "x_rp"
    if re.search(r"\bobby\b|tower of hell|parkour", t):
        return "obby"
    return "descriptive"


def age_enum(label: str | None) -> str:
    s = (label or "").lower()
    if not s:
        return "unrated"
    if "all" in s:
        return "all_ages"
    if "17" in s:
        return "17plus"
    if "13" in s:
        return "13plus"
    if "9" in s:
        return "9plus"
    return "unrated"


def auto_rows_for(r: tuple) -> list[tuple]:
    (uid, name, desc, max_players, age, g1, g2, ctype, members,
     pass_count, pass_min, pass_median, pass_names, n_changes, days_obs, prior_peak) = r
    name = name or ""
    desc_l = (desc or "").lower()
    rows = [
        (uid, "title_pattern", title_pattern(name), None, f"title={name[:80]!r}"),
        (uid, "title_len_chars", None, len(name), None),
        (uid, "title_emoji_count", None, len(EMOJI_RE.findall(name)), None),
        (uid, "title_has_update_tag", bool_text(bool(TAG_RE.search(name) or UPDATE_WORD_RE.search(name))), None, None),
        (uid, "title_is_sequel", bool_text(bool(SEQUEL_RE.search(clean_title(name)))), None, None),
        (uid, "desc_len_chars", None, len(desc or ""), None),
        (uid, "desc_has_discord", bool_text(bool(re.search(r"discord|dsc\.gg", desc_l))), None, None),
        (uid, "desc_has_codes", bool_text(bool(re.search(r"\bcodes?\b", desc_l))), None, None),
        (uid, "pass_count", None, int(pass_count or 0), None),
        (uid, "server_size", None, max_players, None),
        (uid, "age_rating", age_enum(age), None, f"label={age!r}"),
        (uid, "creator_is_group", bool_text(ctype == "Group"), None, None),
        (uid, "creator_prior_peak_ccu", None, int(prior_peak or 0), None if prior_peak else "no earlier experience by this creator in the database"),
    ]
    if pass_count:
        names = pass_names or ""
        rows += [
            (uid, "pass_min_price", None, int(pass_min), None),
            (uid, "pass_median_price", None, float(pass_median), None),
            (uid, "pass_has_boost", bool_text(bool(BOOST_RE.search(names))), None, None),
            (uid, "pass_has_vip", bool_text(bool(VIP_RE.search(names))), None, None),
        ]
    if g1:
        rows.append((uid, "genre_l1", g1, None, None))
    if g2:
        rows.append((uid, "genre_l2", g2, None, None))
    if days_obs:
        rows.append((uid, "update_freq_per_week", None, round(float(n_changes or 0) / (float(days_obs) / 7.0), 2),
                     f"{n_changes} change events over {float(days_obs):.0f} days"))
    if ctype == "Group" and members is not None:
        rows.append((uid, "creator_group_members", None, int(members), None))
    return rows


def job_auto(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(AUTO_SQL)
        games = cur.fetchall()
    prev = latest_values(conn, coder="auto")
    rows = []
    for r in games:
        rows.extend(auto_rows_for(r))
    n = write_features(conn, rows, coder="auto", only_if_changed=prev)
    log.info("auto: %d games examined, %d feature values written (unchanged values skipped)", len(games), n)
    return n


# ----------------------------------------------------------------------------
# LLM: inferred design traits
# ----------------------------------------------------------------------------
LLM_FIELDS = ["play_mode", "core_loop", "session_shape", "progression_type", "social_asymmetry", "can_lose_progress",
              "has_base_defense", "offline_accrual", "has_timers_or_fomo", "borrows_meme_or_ip"]
ICON_FIELDS = ["icon_has_face", "icon_has_text", "icon_has_arrow", "icon_character_count"]

SYSTEM_PROMPT = """You are a research assistant coding Roblox experiences against a fixed codebook for a study of what makes games succeed.
Use only the evidence provided (title, description, genre, server size, game passes, and the icon image if given).
Answer with ONE JSON object and nothing else: no prose, no markdown fences.
For every field return an object {"value": ..., "confidence": 0.0-1.0, "why": "<= 12 words pointing at the evidence"}.
If the evidence does not support an answer, set "value" to "unknown" and confidence below 0.3.
Booleans are true/false. progression_type and play_mode are lists of one or more allowed values."""

LLM_SQL = """
WITH latest_desc AS (
    SELECT DISTINCT ON (universe_id) universe_id, description FROM description_history ORDER BY universe_id, last_seen_at DESC
),
icon AS (
    SELECT DISTINCT ON (universe_id) universe_id, image_url FROM thumbnail_history WHERE kind = 'icon' ORDER BY universe_id, last_seen_at DESC
),
passes AS (
    SELECT universe_id, string_agg(coalesce(name,'') || ' — ' || coalesce(price_robux::text,'off sale') || ' R$', '; ' ORDER BY price_robux) AS pass_list
    FROM (SELECT * FROM gamepass WHERE last_seen_at > now() - interval '30 days' ORDER BY price_robux LIMIT 400) g GROUP BY universe_id
),
last_llm AS (
    SELECT universe_id, max(coded_at) AS coded_at FROM feature WHERE coder = 'llm' GROUP BY universe_id
),
changed AS (
    SELECT universe_id, max(first_seen_at) AS changed_at FROM (
        SELECT universe_id, first_seen_at FROM name_history
        UNION ALL SELECT universe_id, first_seen_at FROM description_history
        UNION ALL SELECT universe_id, first_seen_at FROM thumbnail_history) x GROUP BY universe_id
)
SELECT e.universe_id, e.name, ld.description, e.genre_l1, e.genre_l2, e.max_players, e.age_rating, e.created_at,
       ps.pass_list, ic.image_url, t.tier, ll.coded_at, ch.changed_at
FROM experience e
JOIN v_tier t USING (universe_id)
LEFT JOIN latest_desc ld USING (universe_id)
LEFT JOIN icon ic USING (universe_id)
LEFT JOIN passes ps USING (universe_id)
LEFT JOIN last_llm ll USING (universe_id)
LEFT JOIN changed ch USING (universe_id)
WHERE e.tracking_tier <> 'paused'
  AND (ll.coded_at IS NULL
       OR (%(recode)s AND ch.changed_at > ll.coded_at + interval '1 hour')
       OR (%(missing)s::text IS NOT NULL AND NOT EXISTS (SELECT 1 FROM feature f WHERE f.universe_id = e.universe_id AND f.feature_key = %(missing)s::text)))
ORDER BY CASE t.tier WHEN 'breakout' THEN 0 WHEN 'hit' THEN 1 WHEN 'mid' THEN 2 ELSE 3 END,
         CASE WHEN e.population = 'control' THEN 0 ELSE 1 END,
         t.peak_max_ccu DESC NULLS LAST
LIMIT %(limit)s
"""


def field_spec(codebook: dict, fields: list[str]) -> str:
    lines = []
    for f in fields:
        cb = codebook.get(f, {})
        allowed = cb.get("allowed")
        typ = cb.get("type")
        if typ == "bool":
            lines.append(f'- {f}: true or false')
        elif typ == "number":
            lines.append(f'- {f}: integer')
        elif allowed:
            lines.append(f'- {f}: one of {" | ".join(allowed)}' + (" (list)" if typ == "multi" else ""))
        else:
            lines.append(f"- {f}: free text")
    return "\n".join(lines)


def build_prompt(codebook: dict, g: tuple, with_icon: bool) -> str:
    (uid, name, desc, g1, g2, max_players, age, created, pass_list, _icon, tier, _lc, _ch) = g
    desc = (desc or "").strip()
    if len(desc) > 2500:
        desc = desc[:2500] + " …[truncated]"
    fields = LLM_FIELDS + (ICON_FIELDS if with_icon else [])
    return (
        f"GAME\nTitle: {name}\nCreated: {created.date() if created else 'unknown'}\n"
        f"Genre: {g1 or 'unknown'} / {g2 or 'unknown'}\nServer size: {max_players or 'unknown'}\nAge label: {age or 'unknown'}\n\n"
        f"DESCRIPTION\n{desc or '(empty)'}\n\n"
        f"GAME PASSES (name — price)\n{pass_list or '(none on sale)'}\n\n"
        f"FIELDS TO CODE\n{field_spec(codebook, fields)}\n\n"
        f"Definitions: play_mode = how players relate to the game and each other, all that apply (pve = against the game, "
        f"pvp = against each other, coop = together against the game, social = hangout/chat, party = short minigames, "
        f"trading = player-to-player economy, roleplay, creative = building/designing); core_loop = what the player mostly "
        f"does minute to minute; social_asymmetry = whether players can "
        f"take from (take), help (help), or trade with (trade) each other, mixed if several, none if solo/parallel play; "
        f"has_base_defense = the player owns a space they must defend or upgrade defensively; offline_accrual = progress "
        f"accrues while logged out; has_timers_or_fomo = limited-time items, timers, rotating shops or events; "
        f"borrows_meme_or_ip = leans on an internet meme, an anime, another game's hook, or a brand."
        + ("\nIcon fields describe the attached icon image only." if with_icon else "")
    )


def fetch_icon_b64(http: C.Http, url: str | None) -> tuple[str, str] | None:
    if not url:
        return None
    try:
        data = http.get_bytes(url)
    except Exception as e:  # network hiccup: just code without the icon
        log.warning("icon fetch failed (%s); coding without image", e)
        return None
    if not data or len(data) > 4_000_000:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        mt = "image/png"
    elif data[:3] == b"\xff\xd8\xff":
        mt = "image/jpeg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mt = "image/webp"
    else:
        return None
    return mt, base64.b64encode(data).decode("ascii")


def call_claude(http: C.Http, api_key: str, model: str, prompt: str, icon: tuple[str, str] | None) -> tuple[str, dict]:
    content: list[dict] = []
    if icon:
        content.append({"type": "image", "source": {"type": "base64", "media_type": icon[0], "data": icon[1]}})
    content.append({"type": "text", "text": prompt})
    body = {"model": model, "max_tokens": 1200, "system": SYSTEM_PROMPT, "messages": [{"role": "user", "content": content}]}
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for attempt in range(6):
        r = http.client.post(ANTHROPIC_URL, headers=headers, json=body, timeout=120)
        if r.status_code == 200:
            data = r.json()
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            return text, data.get("usage", {})
        if r.status_code in (429, 500, 502, 503, 529):
            delay = min(60, 5 * 2**attempt)
            log.warning("Anthropic API %s; retrying in %ds", r.status_code, delay)
            time.sleep(delay)
            continue
        raise RuntimeError(f"Anthropic API {r.status_code}: {r.text[:300]}")
    raise RuntimeError("Anthropic API: gave up after retries")


def parse_answer(text: str, codebook: dict, fields: list[str]) -> tuple[list[tuple], list[str]]:
    """Returns (rows without universe_id: (feature_key, value_text, value_num, evidence), low_confidence_fields)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    obj = json.loads(cleaned[start:end + 1])
    rows, low = [], []
    for f in fields:
        item = obj.get(f)
        if not isinstance(item, dict):
            continue
        val, conf, why = item.get("value"), item.get("confidence"), item.get("why", "")
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.0
        ev = f"conf={conf:.2f}; {why}"
        cb = codebook.get(f, {})
        typ, allowed = cb.get("type"), cb.get("allowed")
        if val in (None, "unknown", "") or conf < 0.3:
            low.append(f)
            continue
        if typ == "bool":
            b = str(val).strip().lower() in ("true", "yes", "1")
            rows.append((f, bool_text(b), None, ev))
        elif typ == "number":
            try:
                rows.append((f, None, float(val), ev))
            except (TypeError, ValueError):
                low.append(f)
        elif typ == "multi":
            vals = val if isinstance(val, list) else str(val).split("|")
            keep = [v.strip() for v in vals if allowed is None or v.strip() in allowed]
            if keep:
                rows.append((f, "|".join(keep), None, ev))
            else:
                low.append(f)
        else:
            v = str(val).strip()
            if allowed is None or v in allowed:
                rows.append((f, v, None, ev))
            else:
                low.append(f)
        if conf < 0.6 and f not in low:
            low.append(f)
    return rows, low


def job_llm(conn, limit: int, recode: bool, vision: bool, dry_run: bool, model: str, missing: str | None = None) -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY is not set (add ANTHROPIC_API_KEY=... to secrets.txt); skipping the LLM pass")
        return 0
    codebook = load_codebook(conn)
    with conn.cursor() as cur:
        cur.execute(LLM_SQL, {"recode": recode, "limit": limit, "missing": missing})
        games = cur.fetchall()
    if not games:
        log.info("llm: nothing to code (every game is already coded; use --recode to refresh changed games)")
        return 0
    http = C.Http()
    written = coded = 0
    tokens_in = tokens_out = 0
    for i, g in enumerate(games, 1):
        uid, name = g[0], g[1]
        icon = fetch_icon_b64(http, g[9]) if vision else None
        fields = LLM_FIELDS + (ICON_FIELDS if icon else [])
        prompt = build_prompt(codebook, g, with_icon=bool(icon))
        try:
            text, usage = call_claude(http, api_key, model, prompt, icon)
            rows, low = parse_answer(text, codebook, fields)
        except Exception as e:
            log.warning("llm: %s (%s) failed: %s", name, uid, e)
            continue
        tokens_in += int(usage.get("input_tokens", 0))
        tokens_out += int(usage.get("output_tokens", 0))
        if dry_run:
            print("=" * 78, f"\nPROMPT for {name} ({uid}):\n{prompt}\n", "-" * 78, f"\nANSWER:\n{text}\n", "-" * 78,
                  f"\nPARSED ({len(rows)} values, low confidence: {low}):")
            for r in rows:
                print("  ", r)
            return 0
        n = write_features(conn, [(uid, k, vt, vn, f"model={model}; {ev}") for k, vt, vn, ev in rows], coder="llm")
        written += n
        coded += 1
        log.info("llm %3d/%d %-40s %2d values%s", i, len(games), name[:40], n, f", second look: {', '.join(low)}" if low else "")
        time.sleep(0.3)
    cost = tokens_in / 1e6 * 2 + tokens_out / 1e6 * 10   # Sonnet 5.5 list prices; Haiku is cheaper
    log.info("llm: %d games coded, %d values written, %d input / %d output tokens (about $%.2f at Sonnet 5.5 prices)",
             coded, written, tokens_in, tokens_out, cost)
    return written


# ----------------------------------------------------------------------------
# QUEUE / IMPORT: the human part, as a spreadsheet round-trip
# ----------------------------------------------------------------------------
HUMAN_FIELDS = ["ttfr_seconds", "ttfc_seconds", "round_length_s", "first_purchase_prompt_min",
                "first_purchase_price", "mobile_one_thumb", "lowend_fps_ok"]
REVIEW_FIELDS = LLM_FIELDS   # LLM answers a human may overwrite in the same sheet

QUEUE_SQL = """
SELECT e.universe_id, e.name, e.root_place_id, t.tier, e.population, e.launch_cohort, t.peak_max_ccu
FROM experience e JOIN v_tier t USING (universe_id)
WHERE e.tracking_tier <> 'paused'
  AND (t.tier IN ('breakout','hit','mid') OR e.population = 'control' OR e.launch_cohort)
  AND NOT EXISTS (SELECT 1 FROM feature f WHERE f.universe_id = e.universe_id
                    AND f.feature_key = 'ttfr_seconds' AND f.coder NOT IN ('auto','llm'))
ORDER BY CASE t.tier WHEN 'breakout' THEN 0 WHEN 'hit' THEN 1 WHEN 'mid' THEN 2 ELSE 3 END,
         CASE WHEN e.population = 'control' THEN 0 ELSE 1 END,
         t.peak_max_ccu DESC NULLS LAST
LIMIT %s
"""


def job_queue(conn, n: int, out_path: str) -> int:
    with conn.cursor() as cur:
        cur.execute(QUEUE_SQL, (n,))
        games = cur.fetchall()
        cur.execute("""SELECT universe_id, feature_key, value_text, value_num, evidence FROM v_feature_latest
                       WHERE coder = 'llm'""")
        llm = {}
        for uid, key, vt, vn, ev in cur.fetchall():
            llm.setdefault(uid, {})[key] = (vt if vt is not None else vn, ev or "")
    header = (["universe_id", "name", "tier", "population", "play_url"]
              + [f"llm_{f}" for f in REVIEW_FIELDS] + ["second_look"]
              + HUMAN_FIELDS + [f"override_{f}" for f in REVIEW_FIELDS] + ["notes"])
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for uid, name, place, tier, pop, cohort, peak in games:
            answers = llm.get(uid, {})
            low = [k for k, (_v, ev) in answers.items() if k in REVIEW_FIELDS and re.search(r"conf=0\.[0-5]", ev)]
            w.writerow([uid, name, tier or "", (pop or "") + (" +launch" if cohort else ""),
                        f"https://www.roblox.com/games/{place}" if place else ""]
                       + [answers.get(k, ("", ""))[0] for k in REVIEW_FIELDS] + ["; ".join(low)]
                       + [""] * len(HUMAN_FIELDS) + [""] * len(REVIEW_FIELDS) + [""])
    log.info("queue: %d games written to %s (fill the blank columns, then: python code_features.py import %s --coder XX)",
             len(games), out_path, os.path.basename(out_path))
    return len(games)


def parse_human_value(codebook: dict, key: str, raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    cb = codebook.get(key, {})
    typ, allowed = cb.get("type"), cb.get("allowed")
    if typ == "bool":
        s = raw.lower()
        if s in ("true", "yes", "y", "1"):
            return ("true", None)
        if s in ("false", "no", "n", "0"):
            return ("false", None)
        raise ValueError(f"{key}: expected yes/no, got {raw!r}")
    if typ == "number":
        return (None, float(raw.replace(",", "")))
    if typ == "multi":
        vals = [v.strip() for v in re.split(r"[|,;]", raw) if v.strip()]
        bad = [v for v in vals if allowed and v not in allowed]
        if bad:
            raise ValueError(f"{key}: {bad} not in {allowed}")
        return ("|".join(vals), None)
    if allowed and raw not in allowed:
        raise ValueError(f"{key}: {raw!r} not in {allowed}")
    return (raw, None)


def job_import(conn, path: str, coder: str) -> int:
    codebook = load_codebook(conn)
    rows, errors = [], []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for line_no, rec in enumerate(csv.DictReader(f), start=2):
            try:
                uid = int(rec["universe_id"])
            except (KeyError, ValueError):
                errors.append(f"line {line_no}: missing universe_id")
                continue
            notes = (rec.get("notes") or "").strip()
            for col, raw in rec.items():
                key = col[len("override_"):] if col and col.startswith("override_") else col
                if key not in codebook or not raw or not raw.strip():
                    continue
                try:
                    parsed = parse_human_value(codebook, key, raw)
                except ValueError as e:
                    errors.append(f"line {line_no}: {e}")
                    continue
                if parsed:
                    rows.append((uid, key, parsed[0], parsed[1], notes))
    n = write_features(conn, rows, coder=coder)
    log.info("import: %d values written by coder %s from %s", n, coder, path)
    for e in errors[:50]:
        log.warning("import: %s", e)
    if len(errors) > 50:
        log.warning("import: %d more problems not shown", len(errors) - 50)
    return n


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["auto", "llm", "queue", "import"])
    ap.add_argument("path", nargs="?", help="import: CSV file to load")
    ap.add_argument("--coder", default=None, help="import: your initials, e.g. NC")
    ap.add_argument("--limit", type=int, default=200, help="llm: max games per run")
    ap.add_argument("--recode", action="store_true", help="llm: also refresh games whose page changed since coding")
    ap.add_argument("--missing", default=None, help="llm: also code games that lack this trait, e.g. --missing play_mode")
    ap.add_argument("--no-vision", action="store_true", help="llm: skip the icon image")
    ap.add_argument("--dry-run", action="store_true", help="llm: print one prompt and answer, write nothing")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"llm: model id (default {DEFAULT_MODEL})")
    ap.add_argument("--n", type=int, default=50, help="queue: how many games")
    ap.add_argument("--out", default=os.path.join(C.BASE_DIR, "coding_queue.csv"), help="queue: output CSV")
    args = ap.parse_args(argv)

    log_dir = os.path.join(C.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"code-{args.job}-{datetime.now().strftime('%Y-%m-%d')}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set (put the connection string in secrets.txt next to this script)", file=sys.stderr)
        return 2
    if args.job == "import" and (not args.path or not args.coder):
        print("usage: python code_features.py import FILE.csv --coder XX", file=sys.stderr)
        return 2

    with psycopg.connect(dsn) as conn:
        if args.job == "auto":
            job_auto(conn)
        elif args.job == "llm":
            job_llm(conn, args.limit, args.recode, not args.no_vision, args.dry_run, args.model, args.missing)
        elif args.job == "queue":
            job_queue(conn, args.n, args.out)
        else:
            job_import(conn, args.path, args.coder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
