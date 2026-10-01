#!/usr/bin/env python3
"""
radar.py — Roblox Trend Database (rtdb), explosive radar v0.1

Finds the games that are igniting, builds an evidence dossier for each from the database, and has
Claude write a short evidence-weighted brief: what it is, what is happening, which traits stand out,
the most likely reasons (ranked, each tied to evidence), wave context, confounders, what to watch.

  python radar.py run [--n 12] [--dry-run] [--model ID] [--date YYYY-MM-DD]
      Scores candidates (v_radar_candidates), briefs the top N, stores each brief in radar_report,
      writes reports/radar-<date>.md and, if RTDB_DISCORD_WEBHOOK is set, posts a short digest.
      --dry-run prints one dossier and brief without writing anything.
  python radar.py show [--date YYYY-MM-DD]
      Prints the digest for a day (default today) from radar_report.

Settings (secrets.txt / .env / environment): DATABASE_URL, ANTHROPIC_API_KEY, RTDB_LLM_MODEL,
RTDB_RADAR_N (default 12), RTDB_DISCORD_WEBHOOK (optional).

Honesty rules baked into the prompt: every reason must point at a number or trait in the dossier,
observed facts are separated from inferences, and reasons are hypotheses ranked by evidence —
this is correlational data about a platform whose algorithm amplifies whatever it already favours.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg

import collector as C
import code_features as F

log = logging.getLogger("rtdb.radar")
DEFAULT_MODEL = os.environ.get("RTDB_LLM_MODEL", "claude-sonnet-5-5")
RADAR_N = int(os.environ.get("RTDB_RADAR_N", "12"))

SYSTEM_PROMPT = """You are the analyst for a Roblox market-intelligence database. You receive a JSON dossier about one
experience that is gaining players, with comparison statistics from the same database.
Write an evidence-weighted brief. Rules:
- Every claim points at a specific number, trait or comparison in the dossier. No outside knowledge presented as fact;
  if you use general knowledge of Roblox or of this game, label it as such.
- Separate what is observed from what is inferred. Reasons are hypotheses: rank them by strength of evidence and
  give each a confidence from 0 to 1.
- Call out confounders when present: sponsored chart placements, a creator with a prior hit (audience carry-over),
  a platform event, a name/thumbnail change, or player counts that look bot-like (flat plateaus, visits inconsistent
  with concurrency).
- If the dossier cannot explain the surge, say so plainly instead of inventing a story.
- The dossier includes growth_same_hours (the last 6 hours vs the same 6 hours yesterday). Use it to separate a real
  rise from the daily cycle before anything else; verdict daily_cycle_or_artifact when that is the best explanation.
Return ONE JSON object and nothing else:
{"verdict": "one of: real_breakout | event_spike | daily_cycle_or_artifact | unclear",
 "headline": "<= 15 words", "what_it_is": "1-2 sentences", "whats_happening": "2-3 sentences with numbers",
 "distinct_traits": [{"trait": "...", "value": "...", "why_notable": "..."}],
 "likely_reasons": [{"reason": "...", "evidence": "...", "confidence": 0.0}],
 "wave_context": "first mover / fast follower / late entrant, with the numbers",
 "confounders": ["..."], "watch_next": ["..."], "overall_confidence": 0.0}"""


# ----------------------------------------------------------------------------
# Dossier
# ----------------------------------------------------------------------------
def q(conn, sql: str, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def jsonable(x):
    if isinstance(x, Decimal):
        return float(x)
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return x


def build_dossier(conn, uid: int, cand: dict, lift: dict) -> dict:
    head = q(conn, """
        SELECT e.universe_id, e.name, e.root_place_id, e.created_at, (now()::date - e.created_at::date) AS age_days,
               e.genre_l1, e.genre_l2, e.max_players, e.age_rating, e.creator_type, e.creator_name, c.member_count AS creator_group_members,
               e.first_seen_at, e.population, e.launch_cohort, t.tier, cat.category,
               v.ccu_24h, v.ccu_6h, v.momentum, v.growth_same_hours, v.ccu_cv_24h, v.growth_1d, v.growth_7d, v.growth_28d, v.peak_7d,
               v.trending_rank_now, v.trending_rank_climb, v.velocity_label,
               p.peak_max_ccu AS peak_so_far, p.peak_day, r.like_ratio, r.favourites_per_1k_visits, r.visits, r.staying_power_d8_28, r.half_life_days
        FROM experience e
        LEFT JOIN creator c ON c.creator_type = e.creator_type AND c.creator_id = e.creator_id
        LEFT JOIN v_velocity v USING (universe_id) LEFT JOIN v_peak p USING (universe_id)
        LEFT JOIN v_retention_proxy r USING (universe_id) LEFT JOIN v_tier t USING (universe_id)
        LEFT JOIN v_category cat USING (universe_id)
        WHERE e.universe_id = %s""", (uid,))[0]
    charts_now = q(conn, """SELECT sort_id, min(position) AS best_position, bool_or(is_sponsored) AS sponsored_slot
                            FROM chart_position WHERE universe_id = %s AND ts > now() - interval '24 hours'
                            GROUP BY sort_id ORDER BY best_position""", (uid,))
    chart_first = q(conn, """SELECT sort_id, min(ts) AS first_seen_on_sort FROM chart_position
                             WHERE universe_id = %s AND NOT is_sponsored GROUP BY sort_id ORDER BY 2""", (uid,))
    daily = q(conn, """SELECT day, avg_ccu, max_ccu, (day = (now() AT TIME ZONE 'UTC')::date) AS partial_day
                       FROM v_daily_ccu WHERE universe_id = %s AND day > current_date - 21 ORDER BY day""", (uid,))
    hourly = q(conn, """SELECT date_trunc('hour', ts) AS hour, round(avg(playing)) AS avg_players
                        FROM snapshot WHERE universe_id = %s AND ts > now() - interval '48 hours' GROUP BY 1 ORDER BY 1""", (uid,))
    changes = q(conn, """
        SELECT 'name' AS kind, n.name AS value, n.first_seen_at FROM name_history n JOIN experience e USING (universe_id)
         WHERE n.universe_id = %s AND n.first_seen_at > e.first_seen_at + interval '1 hour' AND n.first_seen_at > now() - interval '14 days'
        UNION ALL
        SELECT 'description', left(description, 160), d.first_seen_at FROM description_history d JOIN experience e USING (universe_id)
         WHERE d.universe_id = %s AND d.first_seen_at > e.first_seen_at + interval '1 hour' AND d.first_seen_at > now() - interval '14 days'
        UNION ALL
        SELECT 'image:' || kind, image_url, t.first_seen_at FROM thumbnail_history t JOIN experience e USING (universe_id)
         WHERE t.universe_id = %s AND t.first_seen_at > e.first_seen_at + interval '1 hour' AND t.first_seen_at > now() - interval '14 days'
        UNION ALL
        SELECT 'new game pass', g.name || ' — ' || coalesce(g.price_robux::text, 'off sale') || ' R$', g.first_seen_at
          FROM gamepass g JOIN experience e USING (universe_id)
         WHERE g.universe_id = %s AND g.first_seen_at > e.first_seen_at + interval '1 hour' AND g.first_seen_at > now() - interval '14 days'
        ORDER BY 3 DESC LIMIT 20""", (uid, uid, uid, uid))
    passes = q(conn, """SELECT name, price_robux FROM gamepass WHERE universe_id = %s AND price_robux > 0
                        AND last_seen_at > now() - interval '30 days' ORDER BY price_robux LIMIT 25""", (uid,))
    traits = q(conn, """SELECT feature_key, coalesce(value_text, value_num::text) AS value, coder, evidence
                        FROM v_feature_latest WHERE universe_id = %s ORDER BY feature_key""", (uid,))
    trait_map = {t["feature_key"]: t["value"] for t in traits}
    # which of this game's trait values are historically over-represented among hits
    notable = []
    for t in traits:
        row = lift.get((t["feature_key"], t["value"]))
        if row and row["n_hits"] >= 5 and row["n_control"] >= 10 and row["lift"] is not None and (row["lift"] >= 1.3 or row["lift"] <= 0.7):
            notable.append({"trait": t["feature_key"], "value": t["value"], "share_of_hits": row["p_hits"],
                            "share_of_controls": row["p_control"], "lift": row["lift"],
                            "direction": "over-represented among hits" if row["lift"] >= 1.3 else "under-represented among hits"})
    notable.sort(key=lambda r: -abs((r["lift"] or 1) - 1))
    core_loop = trait_map.get("core_loop")
    wave = {}
    if core_loop:
        wave = q(conn, """
            SELECT count(*) FILTER (WHERE e.created_at > now() - interval '90 days') AS entrants_90d,
                   count(*) FILTER (WHERE e.created_at > now() - interval '90 days' AND p.peak_max_ccu >= 20000) AS entrants_90d_reaching_20k,
                   count(*) AS games_with_this_loop
            FROM v_feature_latest f JOIN experience e USING (universe_id) LEFT JOIN v_peak p USING (universe_id)
            WHERE f.feature_key = 'core_loop' AND f.value_text = %s""", (core_loop,))[0]
        wave["biggest_games_with_this_loop"] = q(conn, """
            SELECT e.name, p.peak_max_ccu, e.created_at::date AS created
            FROM v_feature_latest f JOIN experience e USING (universe_id) LEFT JOIN v_peak p USING (universe_id)
            WHERE f.feature_key = 'core_loop' AND f.value_text = %s AND e.universe_id <> %s
            ORDER BY p.peak_max_ccu DESC NULLS LAST LIMIT 6""", (core_loop, uid))
    creator_other = q(conn, """
        SELECT o.name, p.peak_max_ccu, o.created_at::date AS created
        FROM experience o LEFT JOIN v_peak p USING (universe_id)
        WHERE o.creator_type = %s AND o.creator_id = (SELECT creator_id FROM experience WHERE universe_id = %s) AND o.universe_id <> %s
        ORDER BY p.peak_max_ccu DESC NULLS LAST LIMIT 6""", (head["creator_type"], uid, uid))
    bench = q(conn, """
        WITH pop AS (
            SELECT universe_id, like_ratio, favourites_per_1k_visits,
                   percent_rank() OVER (ORDER BY like_ratio)                AS like_pct,
                   percent_rank() OVER (ORDER BY favourites_per_1k_visits)  AS fav_pct
            FROM v_retention_proxy WHERE like_ratio IS NOT NULL
        )
        SELECT (SELECT count(*) FROM pop) AS games_compared,
               (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY like_ratio) FROM pop)               AS median_like_ratio,
               (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY favourites_per_1k_visits) FROM pop) AS median_favourites_per_1k_visits,
               p.like_pct AS this_game_like_ratio_percentile, p.fav_pct AS this_game_favourites_percentile
        FROM pop p WHERE p.universe_id = %s""", (uid,))
    cohort = q(conn, """
        SELECT median_ccu, games FROM v_cohort_curve
        WHERE cohort_month = date_trunc('month', %s::timestamptz)::date AND day_n = %s""",
               (head["created_at"], head["age_days"])) if head["created_at"] else []
    dossier = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "triggers": cand.get("triggers"), "heat": cand.get("heat"),
        "game": head, "charts_last_24h": charts_now, "first_appearance_per_chart": chart_first,
        "daily_players_last_21_days": daily, "hourly_players_last_48h": hourly,
        "changes_last_14_days": changes, "game_passes_on_sale": passes,
        "traits": {t["feature_key"]: {"value": t["value"], "coder": t["coder"], "note": (t["evidence"] or "")[:120]} for t in traits},
        "traits_with_meaningful_lift": notable[:10],
        "wave_context_same_core_loop": wave,
        "creators_other_games": creator_other,
        "cohort_baseline_same_age": (cohort[0] if cohort else "no cohort baseline yet (needs more history)"),
        "reception_benchmarks_all_tracked_games": (bench[0] if bench else None),
        "data_caveats": ["player counts are concurrent users sampled every 30-60 min; they can be inflated by bots",
                         "retention is a proxy (staying power), not measured retention",
                         "the charts both reflect and cause growth; a chart entry is not an independent signal",
                         "this database started collecting on 2026-09-29; 'first time' triggers are only used for games watched 7+ days or created < 60 days ago",
                         "a day marked partial_day covers only the hours elapsed so far today (UTC)",
                         "ccu_cv_24h is the spread of the last 24h of player samples relative to their mean; organic audiences with a daily cycle rarely sit below ~0.08, so a flat line (very low value) over a full day deserves suspicion"],
    }
    return jsonable(dossier)


# ----------------------------------------------------------------------------
# Brief
# ----------------------------------------------------------------------------
def render_markdown(d: dict, r: dict) -> str:
    g = d["game"]
    def pct(x):
        return "n/a" if x is None else f"{x * 100:+.0f}%"
    lines = [f"### {g['name']}  —  {r.get('headline', '')}",
             f"**Verdict: {str(r.get('verdict', 'unclear')).replace('_', ' ')}** (confidence {r.get('overall_confidence')})",
             f"*{g.get('category') or 'uncategorised'} · {g.get('genre_l1') or ''} · created {str(g.get('created_at') or '')[:10]} ({g.get('age_days')} days old) · "
             f"creator: {g.get('creator_name')} ({g.get('creator_type')})*",
             "",
             f"**Players now:** {g.get('ccu_24h')} avg last 24h · same hours vs yesterday {pct(g.get('growth_same_hours'))} · 1d {pct(g.get('growth_1d'))} · "
             f"7d {pct(g.get('growth_7d'))} · 28d {pct(g.get('growth_28d'))} · peak so far {g.get('peak_so_far')} · like ratio {g.get('like_ratio')}",
             f"**Why it tripped the radar:** {', '.join(d.get('triggers') or [])} (heat {d.get('heat')})",
             "",
             f"**What it is.** {r.get('what_it_is', '')}",
             "",
             f"**What's happening.** {r.get('whats_happening', '')}",
             ""]
    if r.get("distinct_traits"):
        lines.append("**Distinct traits**")
        for t in r["distinct_traits"]:
            lines.append(f"- {t.get('trait')} = {t.get('value')}: {t.get('why_notable')}")
        lines.append("")
    if r.get("likely_reasons"):
        lines.append("**Likely reasons (hypotheses, ranked)**")
        for i, x in enumerate(r["likely_reasons"], 1):
            lines.append(f"{i}. {x.get('reason')} — *evidence:* {x.get('evidence')} *(confidence {x.get('confidence')})*")
        lines.append("")
    if r.get("wave_context"):
        lines += [f"**Wave context.** {r['wave_context']}", ""]
    if r.get("confounders"):
        lines += ["**Confounders:** " + "; ".join(r["confounders"]), ""]
    if r.get("watch_next"):
        lines += ["**Watch next:** " + "; ".join(r["watch_next"]), ""]
    lines.append(f"*Overall confidence {r.get('overall_confidence')} · play: https://www.roblox.com/games/{g.get('root_place_id')}*")
    return "\n".join(lines)


def brief_one(http, api_key: str, model: str, dossier: dict) -> tuple[dict, dict]:
    prompt = "DOSSIER (JSON):\n" + json.dumps(dossier, ensure_ascii=False, default=str)
    # Sonnet 5.5 thinks before it answers and the thinking counts against this budget, so it is generous;
    # ask_json retries with double the budget if a reply still comes back truncated.
    return F.ask_json(http, api_key, model, prompt, None, system=SYSTEM_PROMPT, max_tokens=8000)


def post_discord(webhook: str, text: str) -> None:
    import httpx
    for chunk in [text[i:i + 1900] for i in range(0, len(text), 1900)][:3]:
        r = httpx.post(webhook, json={"content": chunk}, timeout=20)
        if r.status_code >= 300:
            log.warning("Discord webhook returned %s", r.status_code)
        time.sleep(0.5)


def digest_text(day: date, items: list[dict]) -> str:
    out = [f"# Explosive radar — {day.isoformat()}", "",
           f"{len(items)} game(s) tripped the radar. Ordered by heat. Reasons are evidence-ranked hypotheses, not proven causes.", ""]
    if items and all("report" in it for it in items):
        out += ["| # | Game | Verdict | Players (24h) | Same hours vs yesterday | Flatness | Heat | Headline |", "|---|---|---|---|---|---|---|---|"]
        for i, it in enumerate(items, 1):
            g, rep = it["dossier"]["game"], it["report"]
            gsh, cv = g.get("growth_same_hours"), g.get("ccu_cv_24h")
            flat = "n/a" if cv is None else ("FLAT" if cv < 0.08 else f"{cv:.2f}")
            out.append(f"| {i} | {g['name']} | {str(rep.get('verdict', 'unclear')).replace('_', ' ')} | {g.get('ccu_24h')} | "
                       f"{'n/a' if gsh is None else f'{gsh * 100:+.0f}%'} | {flat} | {it['dossier'].get('heat')} | {rep.get('headline', '')} |")
        out.append("")
    for it in items:
        out.append(it["markdown"])
        out.append("\n---\n")
    return "\n".join(out)


def short_digest(day: date, items: list[dict]) -> str:
    out = [f"**Explosive radar — {day.isoformat()}** ({len(items)} games)"]
    for it in items[:6]:
        g, r = it["dossier"]["game"], it["report"]
        top = (r.get("likely_reasons") or [{}])[0].get("reason", "")
        out.append(f"• **{g['name']}** [{str(r.get('verdict', 'unclear')).replace('_', ' ')}] — {g.get('ccu_24h')} players, same hours {g.get('growth_same_hours')} — {r.get('headline', '')} — top reason: {top}")
    out.append("Full briefs: reports/radar-" + day.isoformat() + ".md in the repo.")
    return "\n".join(out)


def job_run(conn, n: int, dry_run: bool, model: str, day: date) -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY is not set; the radar needs it to write briefs")
        return 0
    cands = q(conn, "SELECT * FROM v_radar_candidates LIMIT %s", (n,))
    if not cands:
        log.info("radar: nothing tripped the radar today")
        return 0
    lift_rows = q(conn, "SELECT feature_key, value_text, p_hits, p_control, lift, n_hits, n_control FROM v_feature_lift")
    lift = {(r["feature_key"], r["value_text"]): jsonable(r) for r in lift_rows}
    http = C.Http()
    items, tokens_in, tokens_out = [], 0, 0
    for i, cand in enumerate(cands, 1):
        uid = cand["universe_id"]
        cand = jsonable(cand)
        try:
            dossier = build_dossier(conn, uid, cand, lift)
            report, usage = brief_one(http, api_key, model, dossier)
        except Exception as e:
            log.warning("radar: %s (%s) failed: %s", cand.get("name"), uid, e)
            conn.rollback()
            continue
        tokens_in += int(usage.get("input_tokens", 0)); tokens_out += int(usage.get("output_tokens", 0))
        md = render_markdown(dossier, report)
        items.append({"uid": uid, "cand": cand, "dossier": dossier, "report": report, "markdown": md})
        log.info("radar %2d/%d %-40s heat %s — %s", i, len(cands), str(cand.get("name"))[:40], cand.get("heat"), report.get("headline", ""))
        if dry_run:
            print(json.dumps(dossier, indent=1, default=str)[:6000], "\n...\n", md)
            return 0
    with conn.cursor() as cur:
        cur.execute("DELETE FROM radar_report WHERE report_date = %s", (day,))   # a re-run replaces the day's digest
        for it in items:
            cur.execute("""INSERT INTO radar_report (universe_id, report_date, heat, triggers, dossier, report, markdown, model)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (universe_id, report_date) DO UPDATE
                             SET heat = EXCLUDED.heat, triggers = EXCLUDED.triggers, dossier = EXCLUDED.dossier,
                                 report = EXCLUDED.report, markdown = EXCLUDED.markdown, model = EXCLUDED.model, created_at = now()""",
                        (it["uid"], day, it["cand"].get("heat"), it["cand"].get("triggers"),
                         json.dumps(it["dossier"]), json.dumps(it["report"]), it["markdown"], model))
    conn.commit()
    os.makedirs(os.path.join(C.BASE_DIR, "reports"), exist_ok=True)
    path = os.path.join(C.BASE_DIR, "reports", f"radar-{day.isoformat()}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(digest_text(day, items))
    cost = tokens_in / 1e6 * 2 + tokens_out / 1e6 * 10
    log.info("radar: %d briefs written to %s (%d in / %d out tokens, about $%.2f)", len(items), path, tokens_in, tokens_out, cost)
    webhook = os.environ.get("RTDB_DISCORD_WEBHOOK")
    if webhook and items:
        post_discord(webhook, short_digest(day, items))
    return len(items)


def job_show(conn, day: date) -> int:
    rows = q(conn, "SELECT dossier, report, markdown FROM radar_report WHERE report_date = %s ORDER BY heat DESC", (day,))
    if not rows:
        print(f"no radar reports for {day}")
        return 0
    print(digest_text(day, [{"dossier": r["dossier"], "report": r["report"], "markdown": r["markdown"]} for r in rows]))
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["run", "show"])
    ap.add_argument("--n", type=int, default=RADAR_N)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default today, UTC)")
    args = ap.parse_args(argv)
    day = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()

    log_dir = os.path.join(C.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"radar-{day.isoformat()}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    db = F.Db(dsn)
    try:
        if args.job == "run":
            db.retry(job_run, args.n, args.dry_run, args.model, day)
        else:
            db.retry(job_show, day)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
