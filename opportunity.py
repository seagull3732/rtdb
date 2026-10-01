#!/usr/bin/env python3
"""
opportunity.py — Roblox Trend Database (rtdb), opportunity engine v0.1

Scores every archetype (core loop x primary category) on longevity, saturation, mechanics, player-behaviour
proxies, trend and estimated development cost, then has Claude write design briefs for the best gaps.

  python opportunity.py run [--top 5] [--dry-run] [--model ID] [--date YYYY-MM-DD]
      Computes v_archetype_metrics, scores archetypes, briefs the top N, stores them in opportunity_report,
      writes reports/opportunities-<date>.md. --dry-run prints the scoreboard and one brief, writes nothing.
  python opportunity.py scoreboard
      Prints the scored archetypes with every component, no LLM call, no cost.
  python opportunity.py show [--date YYYY-MM-DD]

Cost rubric: development cost is the one input the database cannot observe, so it is a scope rubric
(COST_RUBRIC below) expressed in estimated solo-developer weeks. Override any archetype by putting a
cost_overrides.csv next to this script with columns: archetype, weeks, notes.

Honesty rules: every component is reported with the number of games it rests on; components with too
little data are down-weighted and the brief is marked provisional until the database has 28+ days of history.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sys
from datetime import date, datetime, timezone

import psycopg

import collector as C
import code_features as F
from radar import q, jsonable

log = logging.getLogger("rtdb.opportunity")
DEFAULT_MODEL = os.environ.get("RTDB_LLM_MODEL", "claude-sonnet-5-5")

# Estimated solo-developer weeks to reach a testable v1 of a typical game in each loop. A rubric, not data.
COST_RUBRIC = {
    "obby": 2, "idle": 2, "rng": 2, "rhythm": 3, "puzzle": 3, "hangout": 3, "horror": 4, "collect": 4, "grow": 4,
    "tycoon": 5, "dress_up": 5, "steal": 6, "survival": 6, "tower_defense": 6, "round_pvp": 6, "sports": 6, "racing": 6,
    "sandbox_physics": 7, "shooter": 8, "fighting": 8, "vehicle_sim": 8, "roleplay": 10, "build_craft": 10, "other": 6, "uncoded": 6,
}
COST_MODIFIERS = {   # trait value -> extra weeks when common (>= 40%) among the archetype's hits
    ("social_asymmetry", "trade"): 2, ("play_mode_has", "trading"): 2, ("has_base_defense", "true"): 1,
    ("session_shape", "persistent"): 1, ("offline_accrual", "true"): 1,
}
WEIGHTS = {"longevity": 0.25, "room": 0.25, "mechanics": 0.20, "trend": 0.20, "cost": 0.10}
MIN_GAMES_FOR_BRIEF = int(os.environ.get("RTDB_OPP_MIN_GAMES", "5"))
LONGEVITY_MIN_HISTORY_DAYS = 14   # before this, half-lives only exist for games that crashed: a biased sample

SYSTEM_PROMPT = """You are a game-design strategist working from a Roblox market database. You receive one archetype's measured
profile (JSON): how its games perform, how crowded it is, which traits its hits share versus the control group, player
behaviour proxies, trend, and an estimated build cost. Write a design brief for an ORIGINAL game in this space.
Rules:
- Ground every claim in a number from the profile; label anything else as general knowledge.
- Constraints must be measured traits with their lift, not taste. Say which traits to avoid and why.
- Propose a concept that is original in theme and hook, not a renamed copy of the archetype's leader. Name the leader(s)
  only to explain the gap.
- State the kill / scale thresholds for a 28-day launch test in terms the database can measure.
- If data is thin (small n, missing longevity), say the brief is provisional and what would change your mind.
Return ONE JSON object and nothing else:
{"title": "<= 10 words", "the_gap": "2-3 sentences with numbers", "why_now": "1-2 sentences on trend/saturation",
 "constraints": [{"trait": "...", "target": "...", "evidence": "..."}], "avoid": [{"trait": "...", "why": "..."}],
 "concept": {"name": "...", "hook": "one sentence", "core_loop": "3-5 sentences", "first_60_seconds": "...",
             "social_mechanic": "...", "monetization": "...", "content_cadence": "..."},
 "features": ["5-8 concrete in-game features, each tied to a measured trait where possible"],
 "rewards": {"first_minute": "what the player earns and when", "first_session": "...", "first_week": "...",
             "progression_system": "the measured progression type and how rarity/numbers/levels interact",
             "retention_hooks": ["what brings a player back on day 2 and on day 8, tied to traits with lift"]},
 "scope": {"estimated_weeks": 0, "team": "...", "biggest_risk": "..."},
 "launch_test": {"kill_if": "...", "scale_if": "...", "watch": ["..."]},
 "provisional": true, "confidence": 0.0}"""


def load_overrides() -> dict[str, tuple[float, str]]:
    path = os.path.join(C.BASE_DIR, "cost_overrides.csv")
    out: dict[str, tuple[float, str]] = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8-sig") as f:
            for rec in csv.DictReader(f):
                try:
                    out[rec["archetype"].strip()] = (float(rec["weeks"]), rec.get("notes", ""))
                except (KeyError, ValueError):
                    continue
    return out


def archetype_traits(conn, archetype: str) -> dict:
    """Trait prevalence among this archetype's hits vs its non-hits, plus the global lift for the same values."""
    rows = q(conn, """
        WITH members AS (
            SELECT e.universe_id, (t.tier IN ('breakout','hit')) AS is_hit
            FROM experience e JOIN v_category c USING (universe_id) LEFT JOIN v_tier t USING (universe_id)
            WHERE coalesce(c.core_loop, 'uncoded') || ' / ' || c.category = %s AND e.tracking_tier <> 'paused'
        ),
        vals AS (
            SELECT m.is_hit, f.feature_key, f.value_text FROM members m JOIN v_feature_latest f USING (universe_id)
            WHERE f.value_text IS NOT NULL
              AND f.feature_key IN ('play_mode','session_shape','progression_type','social_asymmetry','can_lose_progress',
                                    'has_base_defense','offline_accrual','has_timers_or_fomo','borrows_meme_or_ip',
                                    'title_pattern','pass_has_boost','pass_has_vip','icon_has_face','icon_has_text','desc_has_codes','genre_l2')
        )
        SELECT v.feature_key, v.value_text,
               count(*) FILTER (WHERE v.is_hit)      AS hits_with,
               (SELECT count(*) FROM members WHERE is_hit)     AS hits_total,
               count(*) FILTER (WHERE NOT v.is_hit)  AS others_with,
               (SELECT count(*) FROM members WHERE NOT is_hit) AS others_total,
               l.lift AS global_lift, l.p_hits AS global_p_hits, l.p_control AS global_p_control
        FROM vals v
        LEFT JOIN v_feature_lift l ON l.feature_key = v.feature_key AND l.value_text = v.value_text
        GROUP BY v.feature_key, v.value_text, l.lift, l.p_hits, l.p_control
        HAVING count(*) FILTER (WHERE v.is_hit) > 0 OR count(*) FILTER (WHERE NOT v.is_hit) >= 3
        ORDER BY count(*) FILTER (WHERE v.is_hit) DESC, count(*) DESC""", (archetype,))
    out = []
    for r in rows:
        ht, ot = r["hits_total"] or 0, r["others_total"] or 0
        out.append({"trait": r["feature_key"], "value": r["value_text"],
                    "share_of_this_archetypes_hits": round(r["hits_with"] / ht, 2) if ht else None, "hits_n": ht,
                    "share_of_its_other_games": round(r["others_with"] / ot, 2) if ot else None, "others_n": ot,
                    "global_lift_vs_controls": r["global_lift"],
                    "evidence_strength": ("weak: fewer than 3 hits carry this value" if (r["hits_with"] or 0) < 3
                                          else "moderate" if (r["hits_with"] or 0) < 6 else "solid")})
    return {"rows": out[:40]}


def archetype_games(conn, archetype: str) -> dict:
    """Named leaders and recent entrants, so the brief can state the gap against real games."""
    leaders = q(conn, """
        SELECT e.name, e.created_at::date AS created, t.peak_max_ccu AS peak, v.ccu_24h AS players_now, r.like_ratio
        FROM experience e JOIN v_category c USING (universe_id) LEFT JOIN v_tier t USING (universe_id)
        LEFT JOIN v_velocity v USING (universe_id) LEFT JOIN v_retention_proxy r USING (universe_id)
        WHERE coalesce(c.core_loop, 'uncoded') || ' / ' || c.category = %s AND e.tracking_tier <> 'paused'
        ORDER BY t.peak_max_ccu DESC NULLS LAST LIMIT 6""", (archetype,))
    entrants = q(conn, """
        SELECT e.name, e.created_at::date AS created, t.peak_max_ccu AS peak, v.ccu_24h AS players_now
        FROM experience e JOIN v_category c USING (universe_id) LEFT JOIN v_tier t USING (universe_id)
        LEFT JOIN v_velocity v USING (universe_id)
        WHERE coalesce(c.core_loop, 'uncoded') || ' / ' || c.category = %s AND e.tracking_tier <> 'paused'
          AND e.created_at > now() - interval '90 days'
        ORDER BY e.created_at DESC LIMIT 12""", (archetype,))
    return {"leaders_by_peak": jsonable(leaders), "entrants_last_90_days": jsonable(entrants)}


def numeric_traits(conn, archetype: str) -> list[dict]:
    return q(conn, """
        WITH members AS (
            SELECT e.universe_id, (t.tier IN ('breakout','hit')) AS is_hit
            FROM experience e JOIN v_category c USING (universe_id) LEFT JOIN v_tier t USING (universe_id)
            WHERE coalesce(c.core_loop, 'uncoded') || ' / ' || c.category = %s AND e.tracking_tier <> 'paused'
        )
        SELECT f.feature_key,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY f.value_num) FILTER (WHERE m.is_hit)     AS median_among_hits,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY f.value_num) FILTER (WHERE NOT m.is_hit) AS median_among_others
        FROM members m JOIN v_feature_latest f USING (universe_id)
        WHERE f.value_num IS NOT NULL AND f.feature_key IN ('server_size','pass_count','pass_min_price','pass_median_price',
              'update_freq_per_week','title_len_chars','ttfr_seconds','first_purchase_prompt_min','first_purchase_price')
        GROUP BY f.feature_key ORDER BY f.feature_key""", (archetype,))


def estimate_cost(core_loop: str, traits: dict, overrides: dict, archetype: str) -> dict:
    if archetype in overrides:
        w, notes = overrides[archetype]
        return {"estimated_solo_dev_weeks": w, "basis": f"override: {notes or 'cost_overrides.csv'}"}
    base = COST_RUBRIC.get(core_loop, 6)
    adds = []
    for r in traits.get("rows", []):
        share = r.get("share_of_this_archetypes_hits")
        if share is None or share < 0.4:
            continue
        key = (r["trait"], r["value"])
        if key in COST_MODIFIERS:
            adds.append((key, COST_MODIFIERS[key]))
        if r["trait"] == "play_mode" and "trading" in (r["value"] or ""):
            adds.append((("play_mode_has", "trading"), 2))
    seen, total = set(), base
    for key, w in adds:
        if key not in seen:
            seen.add(key); total += w
    return {"estimated_solo_dev_weeks": total, "basis": f"rubric: base {base} for {core_loop}" + (" + " + ", ".join(f"{k[0]}={k[1]} (+{w})" for k, w in adds if k in seen) if seen else "")}


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def score_archetype(m: dict, cost_weeks: float, history_days: float) -> dict:
    """Each component scored 0..1 with a data-sufficiency weight; missing data lowers confidence, not the score."""
    comps = {}
    # longevity: staying power (0..1 already) blended with half-life (days / 30, capped)
    sp, sp_n = m.get("median_staying_power"), m.get("staying_power_n") or 0
    hl, hl_n = m.get("median_half_life_days"), m.get("half_life_n") or 0
    if history_days < LONGEVITY_MIN_HISTORY_DAYS:
        comps["longevity"] = {"score": 0.5, "sufficiency": 0.0, "note": f"neutral: only {history_days:.0f} days of history; half-lives measured this early come only from games that crashed",
                              "staying_power": sp, "half_life_days": hl, "n": max(sp_n, hl_n)}
    elif sp is not None or hl is not None:
        val = clamp(((float(sp) if sp is not None else 0.0) + (clamp(float(hl) / 30.0) if hl is not None else 0.0)) / (2 if (sp is not None and hl is not None) else 1))
        comps["longevity"] = {"score": val, "sufficiency": clamp(max(sp_n, hl_n) / 10.0) * clamp(history_days / 28.0), "staying_power": sp, "half_life_days": hl, "n": max(sp_n, hl_n)}
    else:
        comps["longevity"] = {"score": 0.5, "sufficiency": 0.0, "note": "no longevity data for this archetype yet"}
    # room: hits per recent entrant (higher = entrants still succeed), penalised by crowding acceleration
    e90, e90h, e90_2k, eprev = m.get("entrants_90d") or 0, m.get("entrants_90d_hits") or 0, m.get("entrants_90d_2k") or 0, m.get("entrants_prev_90d") or 0
    if e90 >= 3:
        success = (e90h + 0.5 * e90_2k) / e90
        accel = (e90 / max(eprev, 1)) if eprev else 2.0
        val = clamp(0.6 * clamp(success * 2) + 0.4 * clamp(1.5 - accel / 2))
        comps["room"] = {"score": val, "sufficiency": clamp(e90 / 10.0), "entrants_90d": e90, "entrants_90d_reaching_20k": e90h, "entrants_90d_reaching_2k": e90_2k, "entrants_prev_90d": eprev}
    else:
        hr = float(m.get("hit_rate") or 0)
        comps["room"] = {"score": clamp(0.4 + hr), "sufficiency": clamp((m.get("games") or 0) / 20.0), "note": "few recent entrants; using overall hit rate", "hit_rate": hr, "games": m.get("games")}
    # mechanics: overall hit rate and median peak as a proxy for how reliably the loop produces big games
    hr, games, mp = float(m.get("hit_rate") or 0), m.get("games") or 0, float(m.get("median_peak") or 0)
    comps["mechanics"] = {"score": clamp(0.5 * clamp(hr * 4) + 0.5 * clamp(math.log10(max(mp, 1)) / 5)), "sufficiency": clamp(games / 15.0), "hit_rate": hr, "median_peak": mp, "games": games}
    # trend: median 7-day growth and share of Top Trending slots
    g7, g7n, slots = m.get("median_growth_7d"), m.get("growth_7d_n") or 0, m.get("trending_top100_slots") or 0
    if g7 is not None:
        comps["trend"] = {"score": clamp(0.5 + float(g7)) * 0.7 + clamp(slots / 10.0) * 0.3, "sufficiency": clamp(g7n / 8.0), "median_growth_7d": g7, "trending_top100_slots": slots}
    else:
        comps["trend"] = {"score": 0.5 + clamp(slots / 10.0) * 0.3, "sufficiency": clamp(history_days / 7.0) * 0.5, "note": "no 7-day growth yet", "trending_top100_slots": slots}
    # cost: cheaper is better (2 weeks -> 1.0, 14+ weeks -> 0)
    comps["cost"] = {"score": clamp(1 - (cost_weeks - 2) / 12.0), "sufficiency": 0.6, "estimated_solo_dev_weeks": cost_weeks}
    total = sum(WEIGHTS[k] * comps[k]["score"] for k in WEIGHTS)
    confidence = sum(WEIGHTS[k] * comps[k]["sufficiency"] for k in WEIGHTS)
    adjusted = 0.5 + (total - 0.5) * confidence          # shrink toward neutral by how much data the score rests on
    return {"score": round(total, 3), "confidence": round(confidence, 2), "adjusted": round(adjusted, 3), "components": comps}


def history_days(conn) -> float:
    r = q(conn, "SELECT EXTRACT(EPOCH FROM (max(ts) - min(ts))) / 86400 AS d FROM snapshot WHERE source = 'rtdb'")
    return float(r[0]["d"] or 0)


def scoreboard(conn) -> list[dict]:
    overrides = load_overrides()
    hd = history_days(conn)
    metrics = q(conn, "SELECT * FROM v_archetype_metrics WHERE games >= 3 AND core_loop <> 'uncoded'")
    out = []
    for m in metrics:
        m = jsonable(m)
        traits = archetype_traits(conn, m["archetype"])
        cost = estimate_cost(m["core_loop"], traits, overrides, m["archetype"])
        sc = score_archetype(m, cost["estimated_solo_dev_weeks"], hd)
        nums = jsonable(numeric_traits(conn, m["archetype"]))
        if hd < LONGEVITY_MIN_HISTORY_DAYS:   # update cadence is measured from our own change logs; meaningless this early
            nums = [n for n in nums if n["feature_key"] != "update_freq_per_week"]
        out.append({"archetype": m["archetype"], "metrics": m, "traits": traits, "numeric_traits": nums,
                    "games": archetype_games(conn, m["archetype"]),
                    "cost": cost, **sc, "history_days": round(hd, 1)})
    out.sort(key=lambda r: (-r["adjusted"], -r["score"]))
    return out


def print_scoreboard(rows: list[dict]) -> None:
    print(f"{'#':>2} {'archetype':34} {'adj':>5} {'raw':>5} {'conf':>4} {'long':>5} {'room':>5} {'mech':>5} {'trend':>5} {'cost':>5} {'games':>5} {'hits':>4} {'ent90':>5} {'weeks':>5}")
    for i, r in enumerate(rows, 1):
        c, m = r["components"], r["metrics"]
        print(f"{i:>2} {r['archetype'][:34]:34} {r['adjusted']:5.2f} {r['score']:5.2f} {r['confidence']:4.2f} {c['longevity']['score']:5.2f} {c['room']['score']:5.2f} "
              f"{c['mechanics']['score']:5.2f} {c['trend']['score']:5.2f} {c['cost']['score']:5.2f} {m.get('games', 0):5} {m.get('hits', 0):4} {m.get('entrants_90d', 0):5} {r['cost']['estimated_solo_dev_weeks']:5}")


def render_markdown(rank: int, r: dict, b: dict) -> str:
    m, c = r["metrics"], r["components"]
    lines = [f"### {rank}. {r['archetype']} — {b.get('title', '')}",
             f"*Adjusted score {r.get('adjusted', r['score'])} (raw {r['score']}) · confidence {r['confidence']} · {'PROVISIONAL' if b.get('provisional') else 'grounded'} · "
             f"{m.get('games')} games, {m.get('hits')} hits, {m.get('entrants_90d')} entrants in 90 days, "
             f"est. {r['cost']['estimated_solo_dev_weeks']} solo-dev weeks*", "",
             f"**The gap.** {b.get('the_gap', '')}", "", f"**Why now.** {b.get('why_now', '')}", ""]
    if b.get("constraints"):
        lines.append("**Build to these constraints**")
        for x in b["constraints"]:
            lines.append(f"- {x.get('trait')}: {x.get('target')} — *{x.get('evidence')}*")
        lines.append("")
    if b.get("avoid"):
        lines.append("**Avoid**")
        for x in b["avoid"]:
            lines.append(f"- {x.get('trait')}: {x.get('why')}")
        lines.append("")
    cpt = b.get("concept") or {}
    lines += [f"**Concept: {cpt.get('name', '')}** — {cpt.get('hook', '')}", "",
              f"- Core loop: {cpt.get('core_loop', '')}", f"- First 60 seconds: {cpt.get('first_60_seconds', '')}",
              f"- Social mechanic: {cpt.get('social_mechanic', '')}", f"- Monetization: {cpt.get('monetization', '')}",
              f"- Content cadence: {cpt.get('content_cadence', '')}", ""]
    if b.get("features"):
        lines.append("**Features**")
        for x in b["features"]:
            lines.append(f"- {x}")
        lines.append("")
    rw = b.get("rewards") or {}
    if rw:
        lines += ["**Rewards and retention**",
                  f"- First minute: {rw.get('first_minute', '')}", f"- First session: {rw.get('first_session', '')}",
                  f"- First week: {rw.get('first_week', '')}", f"- Progression system: {rw.get('progression_system', '')}"]
        for h in rw.get("retention_hooks") or []:
            lines.append(f"- Retention hook: {h}")
        lines.append("")
    sc = b.get("scope") or {}
    lines += [f"**Scope.** ~{sc.get('estimated_weeks')} weeks · {sc.get('team', '')} · biggest risk: {sc.get('biggest_risk', '')}", ""]
    lt = b.get("launch_test") or {}
    lines += [f"**28-day test.** Kill if: {lt.get('kill_if', '')} · Scale if: {lt.get('scale_if', '')} · Watch: {'; '.join(lt.get('watch') or [])}", "",
              f"*Components — longevity {c['longevity']['score']:.2f}, room {c['room']['score']:.2f}, mechanics {c['mechanics']['score']:.2f}, "
              f"trend {c['trend']['score']:.2f}, cost {c['cost']['score']:.2f}; cost basis: {r['cost']['basis']}*"]
    return "\n".join(lines)


def report_text(day: date, items: list[dict]) -> str:
    out = [f"# Opportunity engine — {day.isoformat()}", "",
           "Archetypes ranked by a weighted score (longevity 25%, room to enter 25%, mechanics 20%, trend 20%, cost 10%). "
           "Confidence reflects how much data each score rests on; briefs marked PROVISIONAL rest on less than 28 days of history.", "",
           "| # | Archetype | Adjusted | Raw | Confidence | Games | Hits | Entrants 90d | Est. weeks | Brief |", "|---|---|---|---|---|---|---|---|---|---|"]
    for it in items:
        r, b = it["row"], it["brief"]
        out.append(f"| {it['rank']} | {r['archetype']} | {r.get('adjusted', r['score'])} | {r['score']} | {r['confidence']} | {r['metrics'].get('games')} | {r['metrics'].get('hits')} | "
                   f"{r['metrics'].get('entrants_90d')} | {r['cost']['estimated_solo_dev_weeks']} | {b.get('title', '')} |")
    out.append("")
    for it in items:
        out.append(it["markdown"]); out.append("\n---\n")
    return "\n".join(out)


def job_run(conn, top: int, dry_run: bool, model: str, day: date) -> int:
    rows = scoreboard(conn)
    print_scoreboard(rows[:max(top, 15)])
    rows = [r for r in rows if (r["metrics"].get("games") or 0) >= MIN_GAMES_FOR_BRIEF]
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY is not set; scoreboard only"); return 0
    http = C.Http()
    items, tin, tout = [], 0, 0
    for rank, r in enumerate(rows[:top], 1):
        profile = {k: r[k] for k in ("archetype", "metrics", "traits", "numeric_traits", "games", "cost", "score", "adjusted", "confidence", "components", "history_days")}
        profile["notes"] = ["staying power = share of peak kept on days 8-28 (retention proxy; Roblox publishes true retention only to a game's owner)",
                            "games.leaders_by_peak and games.entrants_last_90_days are real games: name them when stating the gap, but the concept must not copy them",
                            "update cadence (update_freq_per_week) is omitted until the database has 14+ days of change-log history",
                            "lift = share among hits / share among controls across the whole database; archetype shares are small-n",
                            f"the database has {r['history_days']} days of its own history; longevity and trend inputs mature after 28 days"]
        try:
            brief, usage = F.ask_json(http, api_key, model, "ARCHETYPE PROFILE (JSON):\n" + json.dumps(profile, default=str), None, system=SYSTEM_PROMPT, max_tokens=8000)
        except Exception as e:
            log.warning("brief failed for %s: %s", r["archetype"], e); conn.rollback(); continue
        tin += int(usage.get("input_tokens", 0)); tout += int(usage.get("output_tokens", 0))
        md = render_markdown(rank, r, brief)
        items.append({"rank": rank, "row": r, "brief": brief, "markdown": md})
        log.info("opportunity %d/%d %-34s score %.2f — %s", rank, top, r["archetype"][:34], r["score"], brief.get("title", ""))
        if dry_run:
            print(md); return 0
    with conn.cursor() as cur:
        cur.execute("DELETE FROM opportunity_report WHERE run_date = %s", (day,))
        for it in items:
            cur.execute("""INSERT INTO opportunity_report (run_date, rank, archetype, score, components, brief, markdown, model)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (day, it["rank"], it["row"]["archetype"], it["row"]["score"],
                         json.dumps({"components": it["row"]["components"], "metrics": it["row"]["metrics"], "cost": it["row"]["cost"], "confidence": it["row"]["confidence"], "adjusted": it["row"]["adjusted"]}, default=str),
                         json.dumps(it["brief"]), it["markdown"], model))
    conn.commit()
    os.makedirs(os.path.join(C.BASE_DIR, "reports"), exist_ok=True)
    path = os.path.join(C.BASE_DIR, "reports", f"opportunities-{day.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text(day, items))
    log.info("opportunity: %d briefs written to %s (%d in / %d out tokens, about $%.2f)", len(items), path, tin, tout, tin / 1e6 * 2 + tout / 1e6 * 10)
    return len(items)


def job_show(conn, day: date) -> int:
    rows = q(conn, "SELECT rank, archetype, score, components, brief, markdown FROM opportunity_report WHERE run_date = %s ORDER BY rank", (day,))
    if not rows:
        print(f"no opportunity report for {day}"); return 0
    items = [{"rank": r["rank"], "brief": r["brief"], "markdown": r["markdown"],
              "row": {"archetype": r["archetype"], "score": r["score"], "confidence": r["components"].get("confidence"), "adjusted": r["components"].get("adjusted"),
                      "metrics": r["components"].get("metrics", {}), "cost": r["components"].get("cost", {})}} for r in rows]
    print(report_text(day, items))
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["run", "scoreboard", "show"])
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--date", default=None)
    args = ap.parse_args(argv)
    day = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()

    log_dir = os.path.join(C.BASE_DIR, "logs"); os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"opportunity-{day.isoformat()}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); logging.getLogger().addHandler(fh)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr); return 2
    db = F.Db(dsn)
    try:
        if args.job == "run":
            db.retry(job_run, args.top, args.dry_run, args.model, day)
        elif args.job == "scoreboard":
            db.retry(lambda conn: print_scoreboard(scoreboard(conn)[:25]))
        else:
            db.retry(job_show, day)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
