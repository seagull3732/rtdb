#!/usr/bin/env python3
"""
backfill.py — Roblox Trend Database (rtdb), history importer v0.1

Loads per-game player-count history from a CSV into the snapshot table, tagged with a source, so that
peaks, half-lives, cohort curves and the radar's "first time" logic use real history instead of
"since the day we started collecting". Rows never overwrite our own samples (same game + same
timestamp = ours wins), and re-running an import is harmless.

  python backfill.py import-csv FILE.csv --source rtrack
      [--id-col universe_id|place_id] [--time-col ts] [--players-col playing]
      [--visits-col visits] [--favorites-col favorites] [--upvotes-col upvotes] [--downvotes-col downvotes]
      [--dry-run]

  Column names are matched case-insensitively; the defaults also accept common variants
  (universeId / placeId / gameId, time / timestamp / date, players / ccu / playing / player_count).
  Place ids are resolved to universe ids via the database first, then Roblox's public lookup.
  Games not yet in the database are registered (metadata fetched from the games API) with
  population NULL and tracking_tier 'daily', so they join the ongoing collection.

  python backfill.py summary
      Rows per source, date range per source, and how many games have 28+ days of history.

Settings: DATABASE_URL (secrets.txt / .env / environment).
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timezone

import psycopg

import collector as C

log = logging.getLogger("rtdb.backfill")

ID_ALIASES = {"universe_id": ("universe_id", "universeid", "universe"), "place_id": ("place_id", "placeid", "game_id", "gameid", "rootplaceid", "root_place_id")}
TIME_ALIASES = ("ts", "time", "timestamp", "date", "datetime", "recorded_at")
PLAYERS_ALIASES = ("playing", "players", "ccu", "player_count", "playercount", "concurrent", "active")
UNIVERSE_LOOKUP = "https://apis.roblox.com/universes/v1/places/{pid}/universe"


def find_col(header: list[str], wanted: str | None, aliases: tuple[str, ...]) -> str | None:
    low = {h.lower().strip(): h for h in header}
    if wanted:
        return low.get(wanted.lower().strip())
    for a in aliases:
        if a in low:
            return low[a]
    return None


def parse_time(v: str) -> datetime | None:
    v = (v or "").strip()
    if not v:
        return None
    if v.isdigit():  # unix seconds or milliseconds
        n = int(v)
        return datetime.fromtimestamp(n / 1000 if n > 10_000_000_000 else n, tz=timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            d = datetime.strptime(v.replace("Z", "+0000") if fmt.endswith("%z") else v, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def to_int(v) -> int | None:
    try:
        s = str(v).replace(",", "").strip()
        return int(float(s)) if s not in ("", "None", "null", "NaN") else None
    except (TypeError, ValueError):
        return None


def resolve_universes(conn, http: C.Http, place_ids: set[int]) -> dict[int, int]:
    """place_id -> universe_id, from the database first, then Roblox's lookup."""
    out: dict[int, int] = {}
    if not place_ids:
        return out
    with conn.cursor() as cur:
        cur.execute("SELECT root_place_id, universe_id FROM experience WHERE root_place_id = ANY(%s)", (list(place_ids),))
        out.update({p: u for p, u in cur.fetchall()})
    missing = [p for p in place_ids if p not in out]
    for i, pid in enumerate(missing, 1):
        try:
            data = http.get_json(UNIVERSE_LOOKUP.format(pid=pid))
            uid = C.as_int((data or {}).get("universeId"))
            if uid:
                out[pid] = uid
        except Exception as e:
            log.warning("universe lookup failed for place %s: %s", pid, e)
        if i % 50 == 0:
            log.info("resolving place ids: %d/%d", i, len(missing))
    return out


def ensure_experiences(conn, http: C.Http, universe_ids: set[int]) -> int:
    """Register games we have never seen, with metadata from the games API."""
    with conn.cursor() as cur:
        cur.execute("SELECT universe_id FROM experience WHERE universe_id = ANY(%s)", (list(universe_ids),))
        known = {r[0] for r in cur.fetchall()}
    new_ids = [u for u in universe_ids if u not in known]
    if not new_ids:
        return 0
    games = C.fetch_games(http, new_ids)
    ts = C.run_ts()
    n = C.upsert_experiences(conn, games, ts)
    conn.commit()
    missing = len(new_ids) - len(games)
    if missing:
        log.warning("%d games could not be fetched from Roblox (deleted or private); their rows are skipped", missing)
    return n


def job_import(conn, path: str, source: str, args) -> int:
    if source == "rtdb":
        raise ValueError("source 'rtdb' is reserved for the live collector; name the real origin (rtrack, romonitor, csv...)")
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        id_col = find_col(header, args.id_col, ID_ALIASES["universe_id"]) if args.id_col != "place_id" else None
        id_kind = "universe"
        if not id_col:
            id_col = find_col(header, None if args.id_col in (None, "place_id", "universe_id") else args.id_col, ID_ALIASES["place_id"])
            id_kind = "place"
        time_col = find_col(header, args.time_col, TIME_ALIASES)
        players_col = find_col(header, args.players_col, PLAYERS_ALIASES)
        extra = {k: find_col(header, getattr(args, f"{k}_col"), (k,)) for k in ("visits", "favorites", "upvotes", "downvotes")}
        if not (id_col and time_col and players_col):
            raise ValueError(f"could not find the id/time/players columns in {header}; use --id-col/--time-col/--players-col")
        log.info("columns: id=%s (%s), time=%s, players=%s, extra=%s", id_col, id_kind, time_col, players_col, {k: v for k, v in extra.items() if v})
        rows = []
        for rec in reader:
            gid, t, p = to_int(rec.get(id_col)), parse_time(rec.get(time_col, "")), to_int(rec.get(players_col))
            if gid is None or t is None or p is None:
                continue
            rows.append((gid, t, p, *(to_int(rec.get(extra[k])) if extra[k] else None for k in ("visits", "favorites", "upvotes", "downvotes"))))
    log.info("%d usable rows read from %s", len(rows), path)
    if not rows:
        return 0
    http = C.Http()
    if id_kind == "place":
        mapping = resolve_universes(conn, http, {r[0] for r in rows})
        rows = [(mapping[r[0]], *r[1:]) for r in rows if r[0] in mapping]
        log.info("%d rows after resolving place ids (%d places matched)", len(rows), len(mapping))
    uids = {r[0] for r in rows}
    if args.dry_run:
        log.info("dry run: would import %d rows for %d games, %s → %s", len(rows), len(uids), min(r[1] for r in rows), max(r[1] for r in rows))
        return 0
    ensure_experiences(conn, http, uids)
    with conn.cursor() as cur:
        cur.execute("SELECT universe_id FROM experience WHERE universe_id = ANY(%s)", (list(uids),))
        registered = {r[0] for r in cur.fetchall()}
        batch = [(u, t, p, v, fav, up, dn, source) for u, t, p, v, fav, up, dn in rows if u in registered]
        cur.execute("SELECT count(*) FROM snapshot WHERE source = %s AND universe_id = ANY(%s)", (source, list(registered)))
        before = cur.fetchone()[0]
        cur.executemany(
            """INSERT INTO snapshot (universe_id, ts, playing, visits, favorites, upvotes, downvotes, source)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (universe_id, ts) DO NOTHING""",
            batch,
        )
        cur.execute("SELECT count(*) FROM snapshot WHERE source = %s AND universe_id = ANY(%s)", (source, list(registered)))
        written = cur.fetchone()[0] - before
    conn.commit()
    log.info("import: %d rows written for %d games from source %r (duplicates of existing timestamps skipped)", written, len(registered), source)
    return written


def job_summary(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("""SELECT source, count(*), min(ts)::date, max(ts)::date, count(DISTINCT universe_id)
                       FROM snapshot GROUP BY source ORDER BY source""")
        print(f"{'source':12} {'rows':>10} {'from':>12} {'to':>12} {'games':>7}")
        for s, n, a, b, g in cur.fetchall():
            print(f"{s:12} {n:10} {str(a):>12} {str(b):>12} {g:7}")
        cur.execute("""SELECT count(*) FROM (SELECT universe_id FROM snapshot GROUP BY universe_id
                       HAVING max(ts) - min(ts) >= interval '28 days') x""")
        print(f"games with 28+ days of history: {cur.fetchone()[0]}")
        cur.execute("SELECT count(*), min(ts)::date, max(ts)::date FROM platform_ccu")
        n, a, b = cur.fetchone()
        print(f"platform-wide points: {n} ({a} → {b})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["import-csv", "summary"])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--source", default=None, help="import-csv: where the data came from, e.g. rtrack")
    ap.add_argument("--id-col", default=None); ap.add_argument("--time-col", default=None); ap.add_argument("--players-col", default=None)
    for k in ("visits", "favorites", "upvotes", "downvotes"):
        ap.add_argument(f"--{k}-col", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    log_dir = os.path.join(C.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"backfill-{datetime.now().strftime('%Y-%m-%d')}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    if args.job == "import-csv" and (not args.path or not args.source):
        print("usage: python backfill.py import-csv FILE.csv --source NAME", file=sys.stderr)
        return 2
    with psycopg.connect(dsn, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5) as conn:
        if args.job == "import-csv":
            job_import(conn, args.path, args.source, args)
        else:
            job_summary(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
