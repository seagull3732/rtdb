#!/usr/bin/env python3
"""
ideas.py — Roblox Trend Database (rtdb), game idea agent v0.1

Turns the opportunity scoreboard, the knowledge base and this week's radar into original game concepts,
each with a declared trait profile the scoring agent can check against the lift tables.

  python ideas.py generate [--archetypes 3] [--per 3] [--brief "text"] [--dry-run] [--model ID]
      For each of the top N archetypes, propose PER concepts. --brief adds your constraints or a theme,
      e.g. --brief "co-op only, under 5 weeks, Halloween launch". Stores concepts (status 'proposed'),
      writes reports/concepts-<date>.md and refreshes reports/concepts_log.md.
  python ideas.py list [--status proposed|approved|rejected|all]
  python ideas.py show ID
  python ideas.py approve ID [--note "..."]        human gate: ready for the scoring agent / supervisor
  python ideas.py reject ID --reason "..."         stored, and the reason becomes a lesson the agent reads next time
  python ideas.py lesson add --pattern "..." [--evidence "..."] [--owner idea|scoring|supervisor|lead_dev|team|all]
                             [--archetype "core_loop / Category"] [--confidence 0.7]
  python ideas.py lesson list

Settings: DATABASE_URL, ANTHROPIC_API_KEY, RTDB_LLM_MODEL (default claude-sonnet-5-5). About 10-15 cents per archetype.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timezone

import psycopg

import collector as C
import code_features as F
import opportunity as O
from radar import q, jsonable

log = logging.getLogger("rtdb.ideas")
DEFAULT_MODEL = os.environ.get("RTDB_LLM_MODEL", "claude-sonnet-5-5")

PROFILE_KEYS = ["core_loop", "play_mode", "session_shape", "progression_type", "social_asymmetry", "can_lose_progress",
                "has_base_defense", "offline_accrual", "has_timers_or_fomo", "borrows_meme_or_ip", "title_pattern",
                "icon_has_face", "icon_has_text", "desc_has_codes", "pass_has_boost", "pass_has_vip"]
PROFILE_NUMS = ["server_size", "pass_count", "pass_min_price", "pass_median_price", "ttfr_target_seconds",
                "first_purchase_prompt_min", "round_length_s"]

SYSTEM_PROMPT = """You are the game idea agent of a small Roblox studio that designs from data. You receive one archetype's measured
profile (how its games perform, which traits its hits share versus the control group, named leaders and recent entrants,
estimated cost), the studio's lessons, this week's radar context, concepts already proposed, and an optional brief.
Propose ORIGINAL concepts for this archetype. Rules:
- Original means a new theme and a new hook, not a renamed leader. Name leaders only to explain the gap you are filling.
- Never use protected characters, franchises, brands or memes, even where the data shows borrowed IP lifts hits.
- Ground constraints in the profile's numbers; label anything else as design judgement.
- Every concept declares its trait profile using EXACTLY the allowed vocabulary given, so it can be scored mechanically.
- Respect the lessons and the brief. Do not repeat the already-proposed concepts (different hook, different theme).
- Be concrete: a 10-year-old on a phone should understand the hook in one sentence.
Return ONE JSON object: {"concepts": [ {
 "title": "<= 8 words", "hook": "one sentence", "elevator_pitch": "3-4 sentences",
 "the_gap": "which measured gap this fills, with numbers",
 "core_loop": "4-6 sentences of what the player does minute to minute",
 "first_60_seconds": "what happens, second by second in broad strokes",
 "features": ["6-10 concrete features, each tagged (measured) or (judgement)"],
 "rewards": {"first_minute": "...", "first_session": "...", "first_week": "...", "progression": "...", "retention_hooks": ["day 2", "day 8"]},
 "social_mechanic": "...", "monetization": {"passes": [{"name": "...", "price_robux": 0, "what": "..."}], "first_prompt_minute": 0.0, "notes": "..."},
 "content_cadence": "...", "differentiation_vs_leaders": "name the leaders and say what is different",
 "declared_profile": {"core_loop": "...", "play_mode": ["..."], "session_shape": "...", "progression_type": ["..."],
   "social_asymmetry": "...", "can_lose_progress": true, "has_base_defense": false, "offline_accrual": false,
   "has_timers_or_fomo": false, "borrows_meme_or_ip": "none", "title_pattern": "...", "icon_has_face": true,
   "icon_has_text": false, "desc_has_codes": false, "pass_has_boost": false, "pass_has_vip": false,
   "server_size": 0, "pass_count": 0, "pass_min_price": 0, "pass_median_price": 0, "ttfr_target_seconds": 0,
   "first_purchase_prompt_min": 0.0, "round_length_s": null},
 "scope": {"estimated_weeks": 0, "team": "...", "biggest_risk": "..."},
 "kill_early_if": "the earliest sign in week 1 that this concept is not working",
 "confidence": 0.0 } ] }"""


def allowed_vocab(conn) -> dict:
    cb = F.load_codebook(conn)
    return {k: v["allowed"] for k, v in cb.items() if v.get("allowed")}


def lessons_for(conn, archetype: str) -> list[dict]:
    return jsonable(q(conn, """SELECT created_at::date AS date, source, owner_agent, archetype, pattern, evidence, confidence
                                FROM lesson WHERE status = 'active' AND owner_agent IN ('idea','all')
                                  AND (archetype IS NULL OR archetype = %s)
                                ORDER BY created_at DESC LIMIT 40""", (archetype,)))


def radar_context(conn, core_loop: str) -> list[dict]:
    return jsonable(q(conn, """
        SELECT r.report_date, e.name, r.report->>'verdict' AS verdict, r.report->>'headline' AS headline,
               (r.dossier->'game'->>'ccu_24h') AS ccu_24h
        FROM radar_report r JOIN experience e USING (universe_id)
        LEFT JOIN v_category c USING (universe_id)
        WHERE r.report_date > current_date - 7 AND (c.core_loop = %s OR r.heat > 20)
        ORDER BY r.report_date DESC, r.heat DESC LIMIT 12""", (core_loop,)))


def already_proposed(conn, archetype: str) -> list[dict]:
    return jsonable(q(conn, """SELECT id, title, hook, status FROM concept WHERE archetype = %s ORDER BY id DESC LIMIT 30""", (archetype,)))


def validate_profile(prof: dict, vocab: dict) -> list[str]:
    problems = []
    for k in PROFILE_KEYS:
        v = prof.get(k)
        if v is None:
            problems.append(f"{k}: missing"); continue
        allowed = vocab.get(k)
        if k in ("can_lose_progress", "has_base_defense", "offline_accrual", "has_timers_or_fomo", "icon_has_face", "icon_has_text", "desc_has_codes", "pass_has_boost", "pass_has_vip"):
            if not isinstance(v, bool):
                problems.append(f"{k}: expected true/false")
        elif allowed:
            vals = v if isinstance(v, list) else [v]
            bad = [x for x in vals if x not in allowed]
            if bad:
                problems.append(f"{k}: {bad} not in allowed values")
    if prof.get("borrows_meme_or_ip") not in (None, "none"):
        problems.append("borrows_meme_or_ip must be 'none' (no protected IP)")
    return problems


def render_concept(cid: int | None, archetype: str, c: dict) -> str:
    prof, mon, sc, rw = c.get("declared_profile") or {}, c.get("monetization") or {}, c.get("scope") or {}, c.get("rewards") or {}
    lines = [f"### {'#' + str(cid) + ' · ' if cid else ''}{c.get('title', '')}  —  {archetype}",
             f"*{c.get('hook', '')}*", "",
             f"**Pitch.** {c.get('elevator_pitch', '')}", "", f"**The gap.** {c.get('the_gap', '')}", "",
             f"**Core loop.** {c.get('core_loop', '')}", "", f"**First 60 seconds.** {c.get('first_60_seconds', '')}", ""]
    if c.get("features"):
        lines.append("**Features**")
        lines += [f"- {x}" for x in c["features"]]
        lines.append("")
    lines += ["**Rewards and retention**", f"- First minute: {rw.get('first_minute', '')}", f"- First session: {rw.get('first_session', '')}",
              f"- First week: {rw.get('first_week', '')}", f"- Progression: {rw.get('progression', '')}"]
    lines += [f"- Retention hook: {h}" for h in rw.get("retention_hooks") or []]
    lines += ["", f"**Social mechanic.** {c.get('social_mechanic', '')}", ""]
    passes = ", ".join(f"{p.get('name')} ({p.get('price_robux')} R$: {p.get('what')})" for p in mon.get("passes") or [])
    lines += [f"**Monetization.** {passes}. First prompt at minute {mon.get('first_prompt_minute')}. {mon.get('notes', '')}", "",
              f"**Content cadence.** {c.get('content_cadence', '')}", "",
              f"**Versus the leaders.** {c.get('differentiation_vs_leaders', '')}", "",
              "**Declared trait profile** (what the scoring agent checks): " + ", ".join(f"{k}={prof.get(k)}" for k in PROFILE_KEYS + PROFILE_NUMS if prof.get(k) is not None), "",
              f"**Scope.** ~{sc.get('estimated_weeks')} weeks · {sc.get('team', '')} · biggest risk: {sc.get('biggest_risk', '')}", "",
              f"**Kill early if.** {c.get('kill_early_if', '')}", "",
              f"*Agent confidence {c.get('confidence')}*"]
    return "\n".join(lines)


def job_generate(conn, n_arch: int, per: int, brief: str | None, dry_run: bool, model: str, day: date) -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY is not set"); return 0
    vocab = allowed_vocab(conn)
    rows = [r for r in O.scoreboard(conn) if (r["metrics"].get("games") or 0) >= O.MIN_GAMES_FOR_BRIEF][:n_arch]
    if not rows:
        log.info("no archetypes with enough games yet"); return 0
    http = C.Http()
    tin = tout = 0
    saved, md_all = [], []
    for r in rows:
        arch, core_loop = r["archetype"], r["metrics"]["core_loop"]
        payload = {
            "archetype_profile": {k: r[k] for k in ("archetype", "metrics", "traits", "numeric_traits", "games", "cost", "adjusted", "confidence", "components", "history_days")},
            "allowed_vocabulary": {k: vocab.get(k) for k in PROFILE_KEYS if vocab.get(k)},
            "lessons": lessons_for(conn, arch),
            "radar_last_7_days": radar_context(conn, core_loop),
            "already_proposed": already_proposed(conn, arch),
            "brief_from_the_studio": brief or "none",
            "how_many_concepts": per,
            "notes": ["staying power = share of peak kept on days 8-28 (retention proxy)",
                      "lift = share among hits / share among controls; archetype shares are small-n",
                      "declared_profile values must come from allowed_vocabulary; booleans are true/false; play_mode and progression_type are lists"],
        }
        try:
            obj, usage = F.ask_json(http, api_key, model, "INPUT (JSON):\n" + json.dumps(payload, default=str), None, system=SYSTEM_PROMPT, max_tokens=16000)
        except Exception as e:
            log.warning("idea agent failed for %s: %s", arch, e); conn.rollback(); continue
        tin += int(usage.get("input_tokens", 0)); tout += int(usage.get("output_tokens", 0))
        concepts = obj.get("concepts") or []
        for c in concepts[:per]:
            problems = validate_profile(c.get("declared_profile") or {}, vocab)
            c["profile_problems"] = problems
            if dry_run:
                print(render_concept(None, arch, c)); print("\nprofile problems:", problems or "none"); print("\n" + "=" * 78)
                continue
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO concept (run_date, archetype, title, hook, body, markdown, model)
                               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                            (day, arch, (c.get("title") or "untitled")[:120], (c.get("hook") or "")[:400], json.dumps(c), "", model))
                cid = cur.fetchone()[0]
                md = render_concept(cid, arch, c)
                cur.execute("UPDATE concept SET markdown = %s WHERE id = %s", (md, cid))
            conn.commit()
            saved.append((cid, arch, c)); md_all.append(md)
            log.info("concept #%d  %-32s %s%s", cid, arch[:32], c.get("title", ""), f"  [profile issues: {len(problems)}]" if problems else "")
        if dry_run:
            return 0
    if saved:
        os.makedirs(os.path.join(C.BASE_DIR, "reports"), exist_ok=True)
        path = os.path.join(C.BASE_DIR, "reports", f"concepts-{day.isoformat()}.md")
        head = [f"# Concepts — {day.isoformat()}", "",
                f"{len(saved)} concepts across {len({a for _, a, _ in saved})} archetypes" + (f" · brief: {brief}" if brief else ""),
                "Status: proposed. Approve with `python ideas.py approve ID`, reject with `python ideas.py reject ID --reason \"...\"`.", "",
                "| # | Archetype | Concept | Hook | Weeks | Confidence |", "|---|---|---|---|---|---|"]
        for cid, arch, c in saved:
            head.append(f"| {cid} | {arch} | {c.get('title', '')} | {(c.get('hook') or '').replace('|', '/')} | {(c.get('scope') or {}).get('estimated_weeks')} | {c.get('confidence')} |")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(head) + "\n\n" + "\n\n---\n\n".join(md_all) + "\n")
        write_concepts_log(conn)
    cost = tin / 1e6 * 2 + tout / 1e6 * 10
    log.info("idea agent: %d concepts saved (%d in / %d out tokens, about $%.2f)", len(saved), tin, tout, cost)
    return len(saved)


def write_concepts_log(conn) -> str:
    rows = q(conn, "SELECT id, run_date, archetype, title, hook, status, status_note, body FROM concept ORDER BY id DESC")
    lines = ["# Concepts log — every concept the idea agent has proposed", "", "Newest first. Status changes via `python ideas.py approve|reject ID`.", "",
             "| # | Date | Archetype | Concept | Hook | Weeks | Status |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        weeks = ((r["body"] or {}).get("scope") or {}).get("estimated_weeks")
        st = r["status"] + (f" ({r['status_note']})" if r["status_note"] else "")
        lines.append(f"| {r['id']} | [{r['run_date']}](concepts-{r['run_date']}.md) | {r['archetype']} | {r['title']} | {(r['hook'] or '').replace('|', '/')} | {weeks} | {st} |")
    os.makedirs(os.path.join(C.BASE_DIR, "reports"), exist_ok=True)
    path = os.path.join(C.BASE_DIR, "reports", "concepts_log.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def job_list(conn, status: str) -> int:
    where = "" if status == "all" else "WHERE status = %s"
    rows = q(conn, f"SELECT id, run_date, archetype, title, status, body->'scope'->>'estimated_weeks' AS weeks, body->>'confidence' AS conf FROM concept {where} ORDER BY id DESC", () if status == "all" else (status,))
    if not rows:
        print(f"no concepts with status {status}"); return 0
    print(f"{'#':>4} {'date':10} {'archetype':28} {'status':12} {'wks':>4} {'conf':>5}  title")
    for r in rows:
        print(f"{r['id']:>4} {str(r['run_date']):10} {r['archetype'][:28]:28} {r['status']:12} {str(r['weeks'] or ''):>4} {str(r['conf'] or ''):>5}  {r['title']}")
    return len(rows)


def job_show(conn, cid: int) -> int:
    rows = q(conn, "SELECT markdown, status, status_note, score FROM concept WHERE id = %s", (cid,))
    if not rows:
        print(f"no concept #{cid}"); return 0
    print(rows[0]["markdown"])
    print(f"\nStatus: {rows[0]['status']}" + (f" — {rows[0]['status_note']}" if rows[0]["status_note"] else ""))
    if rows[0]["score"]:
        print("Score:", json.dumps(rows[0]["score"], indent=1))
    return 1


def set_status(conn, cid: int, status: str, note: str | None, lesson_from_rejection: bool = False) -> int:
    rows = q(conn, "SELECT archetype, title FROM concept WHERE id = %s", (cid,))
    if not rows:
        print(f"no concept #{cid}"); return 0
    with conn.cursor() as cur:
        cur.execute("UPDATE concept SET status = %s, status_note = %s, status_at = now() WHERE id = %s", (status, note, cid))
        if lesson_from_rejection and note:
            cur.execute("""INSERT INTO lesson (source, archetype, owner_agent, pattern, evidence, confidence)
                           VALUES ('human', %s, 'idea', %s, %s, 0.8)""",
                        (rows[0]["archetype"], f"Rejected concept '{rows[0]['title']}': {note}", f"concept #{cid}"))
    conn.commit()
    write_concepts_log(conn)
    print(f"concept #{cid} → {status}" + (f" ({note})" if note else ""))
    return 1


def lesson_add(conn, pattern: str, evidence: str | None, owner: str, archetype: str | None, confidence: float) -> int:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO lesson (source, archetype, owner_agent, pattern, evidence, confidence) VALUES ('human', %s, %s, %s, %s, %s) RETURNING id",
                    (archetype, owner, pattern, evidence, confidence))
        lid = cur.fetchone()[0]
    conn.commit(); print(f"lesson #{lid} added for {owner}"); return 1


def lesson_list(conn) -> int:
    rows = q(conn, "SELECT id, created_at::date AS d, source, owner_agent, archetype, pattern, confidence, status FROM lesson ORDER BY id DESC LIMIT 100")
    if not rows:
        print("no lessons yet"); return 0
    for r in rows:
        print(f"#{r['id']} {r['d']} [{r['owner_agent']}] {r['archetype'] or 'general'} ({r['source']}, {r['confidence']}, {r['status']}): {r['pattern']}")
    return len(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["generate", "list", "show", "approve", "reject", "lesson"])
    ap.add_argument("arg", nargs="?", help="concept id, or 'add'/'list' for lesson")
    ap.add_argument("--archetypes", type=int, default=3); ap.add_argument("--per", type=int, default=3)
    ap.add_argument("--brief", default=None); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL); ap.add_argument("--date", default=None)
    ap.add_argument("--status", default="proposed"); ap.add_argument("--note", default=None); ap.add_argument("--reason", default=None)
    ap.add_argument("--pattern", default=None); ap.add_argument("--evidence", default=None); ap.add_argument("--owner", default="all")
    ap.add_argument("--archetype", default=None); ap.add_argument("--confidence", type=float, default=0.7)
    args = ap.parse_args(argv)
    day = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    log_dir = os.path.join(C.BASE_DIR, "logs"); os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"ideas-{day.isoformat()}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); logging.getLogger().addHandler(fh)
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr); return 2
    db = F.Db(dsn)
    missing = [t for t in ("lesson", "concept")
               if db.conn.execute("SELECT to_regclass(%s)", (f"public.{t}",)).fetchone()[0] is None]
    if missing:
        print(f"The database is missing table(s) {', '.join(missing)}. Replace schema.sql with the latest version, "
              f"then run:  python collector.py init", file=sys.stderr)
        db.close(); return 2
    try:
        if args.job == "generate":
            db.retry(job_generate, args.archetypes, args.per, args.brief, args.dry_run, args.model, day)
        elif args.job == "list":
            db.retry(job_list, args.status)
        elif args.job == "show":
            db.retry(job_show, int(args.arg))
        elif args.job == "approve":
            db.retry(set_status, int(args.arg), "approved", args.note)
        elif args.job == "reject":
            if not args.reason:
                print("reject needs --reason \"...\" (it becomes a lesson)", file=sys.stderr); return 2
            db.retry(set_status, int(args.arg), "rejected", args.reason, True)
        elif args.job == "lesson":
            if args.arg == "add":
                if not args.pattern:
                    print("lesson add needs --pattern \"...\"", file=sys.stderr); return 2
                db.retry(lesson_add, args.pattern, args.evidence, args.owner, args.archetype, args.confidence)
            else:
                db.retry(lesson_list)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
