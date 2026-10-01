#!/usr/bin/env python3
"""
archive.py — Roblox Trend Database (rtdb), backups and cold archive v0.1

The database is append-only by design; this makes the history survive anything that happens
to the live database (plan limits, an accident, a provider outage).

  python archive.py weekly  [--out backup_out]
      Full export of every table except the two big time series, plus the month-to-date part of
      snapshot and chart_position. Writes one <table>.csv.gz per table and a manifest.
      Run weekly; the uploaded set is replaced each time, so it is always the current state.

  python archive.py monthly [--out backup_out] [--month YYYY-MM]
      The previous month's snapshot and chart_position rows (or the month given), as
      snapshot-YYYY-MM.csv.gz and chart_position-YYYY-MM.csv.gz. These files never change once
      written: together they are the permanent full-resolution history.

  python archive.py restore FILE.csv.gz [FILE ...] [--table name]
      Loads rows back into the live database (ON CONFLICT DO NOTHING, so it is safe to re-run and
      safe on a database that already has some of the rows). The table is taken from the file name
      (snapshot-2026-09.csv.gz → snapshot) unless --table is given. Load experience before the
      tables that reference it (the restore order is handled for you when several files are given).

Settings: DATABASE_URL from secrets.txt / .env next to this script, or the environment.
The GitHub workflow encrypts the files with gpg (BACKUP_PASSPHRASE secret) and attaches them to a
release named "backups"; decrypt with:  gpg --decrypt file.csv.gz.gpg > file.csv.gz
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import re
import sys
from datetime import date, datetime, timezone

import psycopg

import collector as C  # settings loading and BASE_DIR

log = logging.getLogger("rtdb.archive")

BIG_TABLES = ("snapshot", "chart_position")
# Restore order respects foreign keys (experience first, then everything that points at it).
RESTORE_ORDER = ["codebook", "regime_event", "sort_catalog", "creator", "experience", "snapshot", "chart_position",
                 "name_history", "description_history", "thumbnail_history", "gamepass", "gamepass_price_history",
                 "external_signal", "feature", "own_experiment", "collector_run"]


def list_tables(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("""SELECT table_name FROM information_schema.tables
                       WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name""")
        return [r[0] for r in cur.fetchall()]


def export_query(conn, sql: str, path: str) -> tuple[int, str]:
    """COPY the result of `sql` to a gzipped CSV. Returns (rows, sha256)."""
    rows = 0
    h = hashlib.sha256()
    with conn.cursor() as cur, gzip.open(path, "wb", compresslevel=6) as f:
        with cur.copy(f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER)") as cp:
            first = True
            for chunk in cp:
                b = bytes(chunk)
                f.write(b)
                h.update(b)
                rows += b.count(b"\n")
            rows = max(0, rows - 1)  # header line
    return rows, h.hexdigest()


def month_bounds(ym: str) -> tuple[str, str]:
    y, m = int(ym[:4]), int(ym[5:7])
    start = date(y, m, 1)
    end = date(y + (m == 12), (m % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


def job_weekly(conn, out: str) -> int:
    os.makedirs(out, exist_ok=True)
    manifest = {"kind": "weekly", "created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    total = 0
    this_month = datetime.now(timezone.utc).strftime("%Y-%m")
    start, end = month_bounds(this_month)
    for t in list_tables(conn):
        if t in BIG_TABLES:
            path = os.path.join(out, f"{t}-{this_month}-to-date.csv.gz")
            n, digest = export_query(conn, f"SELECT * FROM {t} WHERE ts >= '{start}' AND ts < '{end}' ORDER BY ts", path)
        else:
            path = os.path.join(out, f"{t}.csv.gz")
            n, digest = export_query(conn, f"SELECT * FROM {t}", path)
        manifest["files"][os.path.basename(path)] = {"rows": n, "sha256": digest, "bytes": os.path.getsize(path)}
        total += n
        log.info("weekly: %-28s %9d rows  %7.1f KB", os.path.basename(path), n, os.path.getsize(path) / 1024)
    with open(os.path.join(out, "manifest-weekly.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    log.info("weekly: %d rows exported to %s", total, out)
    return total


def job_monthly(conn, out: str, month: str | None) -> int:
    os.makedirs(out, exist_ok=True)
    if not month:
        today = datetime.now(timezone.utc).date()
        prev = date(today.year - (today.month == 1), (today.month - 2) % 12 + 1, 1)
        month = prev.strftime("%Y-%m")
    start, end = month_bounds(month)
    manifest = {"kind": "monthly", "month": month, "created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
    total = 0
    for t in BIG_TABLES:
        path = os.path.join(out, f"{t}-{month}.csv.gz")
        n, digest = export_query(conn, f"SELECT * FROM {t} WHERE ts >= '{start}' AND ts < '{end}' ORDER BY ts", path)
        manifest["files"][os.path.basename(path)] = {"rows": n, "sha256": digest, "bytes": os.path.getsize(path)}
        total += n
        log.info("monthly: %-28s %9d rows  %7.1f KB", os.path.basename(path), n, os.path.getsize(path) / 1024)
    with open(os.path.join(out, f"manifest-{month}.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    log.info("monthly: %d rows archived for %s", total, month)
    return total


def table_from_filename(path: str) -> str:
    base = os.path.basename(path)
    base = re.sub(r"\.csv\.gz(\.gpg)?$", "", base)
    base = re.sub(r"-\d{4}-\d{2}(-to-date)?$", "", base)
    return base


def job_restore(conn, files: list[str], table: str | None) -> int:
    pairs = [(table or table_from_filename(f), f) for f in files]
    pairs.sort(key=lambda p: RESTORE_ORDER.index(p[0]) if p[0] in RESTORE_ORDER else 99)
    total = 0
    for t, path in pairs:
        if not re.fullmatch(r"[a-z_]+", t):
            raise ValueError(f"unsafe table name {t!r}")
        with conn.cursor() as cur:
            cur.execute(f"CREATE TEMP TABLE restore_tmp (LIKE {t} INCLUDING DEFAULTS) ON COMMIT DROP")
            with gzip.open(path, "rb") as f, cur.copy("COPY restore_tmp FROM STDIN WITH (FORMAT csv, HEADER)") as cp:
                while chunk := f.read(1 << 20):
                    cp.write(chunk)
            cur.execute(f"INSERT INTO {t} SELECT * FROM restore_tmp ON CONFLICT DO NOTHING")
            n = cur.rowcount
        conn.commit()
        total += n
        log.info("restore: %-22s +%d rows from %s", t, n, os.path.basename(path))
    return total


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["weekly", "monthly", "restore"])
    ap.add_argument("files", nargs="*", help="restore: files to load")
    ap.add_argument("--out", default=os.path.join(C.BASE_DIR, "backup_out"))
    ap.add_argument("--month", default=None, help="monthly: YYYY-MM (default: previous month)")
    ap.add_argument("--table", default=None, help="restore: force the target table")
    args = ap.parse_args(argv)

    log_dir = os.path.join(C.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"archive-{datetime.now().strftime('%Y-%m-%d')}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    if args.job == "restore" and not args.files:
        print("usage: python archive.py restore FILE.csv.gz [FILE ...]", file=sys.stderr)
        return 2
    with psycopg.connect(dsn) as conn:
        if args.job == "weekly":
            job_weekly(conn, args.out)
        elif args.job == "monthly":
            job_monthly(conn, args.out, args.month)
        else:
            job_restore(conn, args.files, args.table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
