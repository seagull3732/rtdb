#!/usr/bin/env python3
"""
collector.py — Roblox Trend Database (rtdb), collector v0.4

Polls Roblox's public web endpoints and writes to the Postgres schema in schema.sql.

Jobs (python collector.py <job>):
  init              Apply schema.sql to DATABASE_URL (alternative: psql "$DATABASE_URL" -f schema.sql)
  probe-passes      Call the game-pass endpoints for the busiest tracked game and print what comes back,
                    so a silent change in that API shows up as "0 passes" nowhere else.
  probe             Walk the charts (explore) API once, print every sort with its id, name, first-page
                    size and whether it paginates, plus the field names on a game entry. Writes nothing
                    to the database; saves probe_get_sorts.json.
  sorts             Snapshot every front-page sort (position of each game), register the games,
                    and snapshot their stats. Run hourly.
  stats             Snapshot playing/visits/favorites/votes for tracking_tier='intensive'. Run every 30 min.
  daily             Refresh metadata for everything not paused: name/description/thumbnail change
                    logs; game passes on a weekly rotation (daily for games created in the last 14 days);
                    creators not refreshed in the last 14 days, up to RTDB_CREATOR_BUDGET per run.
Every job appends its log to logs/<job>-<YYYY-MM-DD>.log next to this script.
  promote           Apply the watchlist rules and launch-cohort labelling. Run after `sorts`.
  sample-controls   Pick N random games in a CCU band as the control population
                    (python collector.py sample-controls --n 300 --lo 200 --hi 2000).
  passes            Refresh game passes for every tracked game now (about 10 minutes); the daily job
                    otherwise refreshes a seventh of them each day.

Settings come from environment variables, or from a file named secrets.txt or .env next to this
script. In that file, a bare line starting with postgresql:// becomes DATABASE_URL; other lines
are KEY=VALUE. Environment variables win if both are present.

  DATABASE_URL             postgresql://user:pass@host:5432/db   (required)
  RTDB_CONTACT             email or URL for the User-Agent, so Roblox can reach you (recommended)
  RTDB_GAMES_INTERVAL_S    seconds between calls to games.roblox.com (default 3; it rate-limits hard)
  RTDB_CREATOR_INTERVAL_S  seconds between calls to groups/users.roblox.com (default 10; stricter still)
  RTDB_MIN_INTERVAL_S      floor for every other host (default 0.3)
  RTDB_CREATOR_BUDGET      max creator look-ups per daily run (default 150; the rest catch up next day)
  RTDB_MAX_ATTEMPTS        retries per request (default 8; 429 waits grow to two minutes)
  RTDB_SORT_DEPTH          pages fetched per sort (default 4)
  RTDB_DEEP_SORT_DEPTH     pages fetched for big sorts matched by RTDB_DEEP_SORT_KEYWORDS (default 20)
  RTDB_DEEP_SORT_KEYWORDS  comma list matched against sort names, default "popular,playing"
  RTDB_MAJOR_SORTS         comma list of sort ids that define the 'charts' population (top 200), default
                           "top-trending,up-and-coming,top-playing-now,top-earning,top-revisited,
                            most-popular,popular,fun-with-friends"
  RTDB_DEVICE / RTDB_COUNTRY   explore API params (default computer / all)
  RTDB_HASH_IMAGES         "1" to download icons/thumbnails and store a content hash (default off)

Suggested schedule (UTC), run from the directory holding this file:
  every 30 min   python collector.py stats
  hourly at :05  python collector.py sorts
  hourly at :15  python collector.py promote
  daily at 03:20 python collector.py daily
Each job takes a lock file (.lock_<job>) so a slow run is never stacked on top of itself.

Etiquette: public, unauthenticated endpoints only; one request at a time; adaptive slow-down on 429.
Read Roblox's Terms of Use before running this against the live platform.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import urlparse

import httpx
import psycopg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------------------
# Settings: secrets.txt / .env next to the script, then environment variables
# ----------------------------------------------------------------------------
def load_local_settings() -> None:
    for name in ("secrets.txt", ".env"):
        path = os.path.join(BASE_DIR, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig") as f:  # utf-8-sig swallows Notepad's BOM
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower().startswith(("postgresql://", "postgres://")):
                    os.environ.setdefault("DATABASE_URL", line)
                elif "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k:
                        os.environ.setdefault(k, v)


load_local_settings()

log = logging.getLogger("rtdb")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)   # one line per request is too noisy

# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------
GAMES_API = "https://games.roblox.com/v1/games"
VOTES_API = "https://games.roblox.com/v1/games/votes"
PASSES_API = "https://apis.roblox.com/game-passes/v1/universes/{uid}/game-passes"   # games.roblox.com/v1/games/{id}/game-passes returns 404 since 2026
PASSES_API_LEGACY = "https://games.roblox.com/v1/games/{uid}/game-passes"
ICONS_API = "https://thumbnails.roblox.com/v1/games/icons"
THUMBS_API = "https://thumbnails.roblox.com/v1/games/multiget/thumbnails"
EXPLORE_SORTS = "https://apis.roblox.com/explore-api/v1/get-sorts"
EXPLORE_CONTENT = "https://apis.roblox.com/explore-api/v1/get-sort-content"
GROUPS_API = "https://groups.roblox.com/v1/groups/{gid}"
USERS_API = "https://users.roblox.com/v1/users/{uid}"

BATCH = 50  # universe ids per multi-get call

# Per-host minimum seconds between requests. games.roblox.com returned 429s at ~2 requests/second,
# so it gets a slow default; the collector also doubles a host's interval every time it is throttled.
_SLOW = float(os.environ.get("RTDB_GAMES_INTERVAL_S", "3.0"))
_CREATOR = float(os.environ.get("RTDB_CREATOR_INTERVAL_S", "10.0"))   # groups.roblox.com throttled at 3 s
HOST_MIN_INTERVAL = {
    "apis.roblox.com": 0.5,
    "games.roblox.com": _SLOW,
    "groups.roblox.com": _CREATOR,
    "users.roblox.com": _CREATOR,
    "thumbnails.roblox.com": 1.0,
}
CREATOR_BUDGET = int(os.environ.get("RTDB_CREATOR_BUDGET", "150"))
MAX_ATTEMPTS = int(os.environ.get("RTDB_MAX_ATTEMPTS", "8"))

# The explore API is undocumented and its field names have changed before.
# `probe` shows you the live names; add any new ones here rather than editing the code below.
FIELD_ALIASES = {
    "sort_list": ("sorts",),
    "sort_id": ("sortId", "topicId", "id"),
    "sort_name": ("sortDisplayName", "topic", "name", "displayName"),
    "sort_games": ("games", "recommendationList", "items", "entries"),
    "sort_next": ("nextPageToken", "nextPageCursor"),
    "sorts_next": ("nextSortsPageToken", "nextPageToken"),
    "game_id": ("universeId", "universeID", "id"),
    "game_playing": ("playerCount", "playing", "playerCounts"),
    "game_age": ("ageRecommendationDisplayName", "ageRating", "minimumAge"),
    "game_sponsored": ("isSponsored", "sponsored"),
}

DEVICE = os.environ.get("RTDB_DEVICE", "computer")
COUNTRY = os.environ.get("RTDB_COUNTRY", "all")
SORT_DEPTH = int(os.environ.get("RTDB_SORT_DEPTH", "4"))
DEEP_SORT_DEPTH = int(os.environ.get("RTDB_DEEP_SORT_DEPTH", "20"))
DEEP_SORT_KEYWORDS = tuple(
    k.strip().lower() for k in os.environ.get("RTDB_DEEP_SORT_KEYWORDS", "popular,playing").split(",") if k.strip()
)
MAJOR_SORTS = [
    s.strip() for s in os.environ.get(
        "RTDB_MAJOR_SORTS",
        "top-trending,up-and-coming,top-playing-now,top-earning,top-revisited,most-popular,popular,fun-with-friends",
    ).split(",") if s.strip()
]
HASH_IMAGES = os.environ.get("RTDB_HASH_IMAGES", "0") == "1"


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def run_ts() -> datetime:
    """One timestamp per run, so every row from a run joins cleanly."""
    return datetime.now(timezone.utc).replace(microsecond=0)


def chunks(seq: list, n: int) -> Iterator[list]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def pick(d: dict, key: str, default=None):
    """First present alias for a logical field."""
    for k in FIELD_ALIASES[key]:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def as_int(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def parse_ts(v) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def sha1(s: str | bytes) -> str:
    b = s.encode("utf-8", "replace") if isinstance(s, str) else s
    return hashlib.sha1(b).hexdigest()


@contextlib.contextmanager
def job_lock(job: str):
    """Yields True if this job may run, False if another copy of the same job is still running."""
    path = os.path.join(BASE_DIR, f".lock_{job}")
    try:
        if os.path.exists(path) and time.time() - os.path.getmtime(path) > 3 * 3600:
            os.remove(path)  # stale lock from a crashed run
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        yield False
        return
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        yield True
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


# ----------------------------------------------------------------------------
# HTTP client: per-host pacing, adaptive slow-down, patient backoff
# ----------------------------------------------------------------------------
class Http:
    def __init__(self) -> None:
        contact = os.environ.get("RTDB_CONTACT", "contact-not-set")
        self.min_interval = float(os.environ.get("RTDB_MIN_INTERVAL_S", "0.3"))
        self.host_interval: dict[str, float] = dict(HOST_MIN_INTERVAL)
        self.host_last: dict[str, float] = {}
        self.requests = 0
        self.throttled = 0
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": f"roblox-trend-db/0.4 (research collector; +{contact})",
                "Accept": "application/json",
            },
        )

    def _pace(self, host: str) -> None:
        interval = max(self.min_interval, self.host_interval.get(host, self.min_interval))
        wait = interval - (time.monotonic() - self.host_last.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)

    def _slow_down(self, host: str) -> float:
        cur = self.host_interval.get(host, self.min_interval)
        self.host_interval[host] = min(15.0, max(1.0, cur * 2))
        return self.host_interval[host]

    def get_json(self, url: str, params: dict | None = None, attempts: int | None = None) -> Any:
        """GET and decode JSON. Returns None on 404. Retries 429/5xx/network errors with backoff."""
        attempts = attempts or MAX_ATTEMPTS
        host = urlparse(url).hostname or url
        for attempt in range(attempts):
            self._pace(host)
            try:
                r = self.client.get(url, params=params)
            except httpx.HTTPError as e:
                self.host_last[host] = time.monotonic()
                delay = min(60, 2**attempt) + random.random()
                log.warning("network error on %s (%s); retry in %.1fs", host, e, delay)
                time.sleep(delay)
                continue
            self.host_last[host] = time.monotonic()
            self.requests += 1
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    log.warning("non-JSON body from %s", url)
                    return None
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                self.throttled += 1
                pace = self._slow_down(host)
                ra = r.headers.get("Retry-After")
                ra_s = float(ra) if ra and ra.replace(".", "", 1).isdigit() else 0.0
                delay = min(120.0, max(ra_s, 10.0 * (attempt + 1))) + random.uniform(0, 3)
                log.warning("HTTP 429 from %s; waiting %.0fs, then %.1fs between calls", host, delay, pace)
                time.sleep(delay)
                continue
            if r.status_code in (500, 502, 503, 504):
                delay = min(60, 2**attempt) + random.random()
                log.warning("HTTP %s from %s; retry in %.1fs", r.status_code, host, delay)
                time.sleep(delay)
                continue
            r.raise_for_status()
        raise RuntimeError(f"gave up after {attempts} attempts: {url}")

    def get_bytes(self, url: str) -> bytes | None:
        host = urlparse(url).hostname or url
        self._pace(host)
        try:
            r = self.client.get(url)
        finally:
            self.host_last[host] = time.monotonic()
        self.requests += 1
        return r.content if r.status_code == 200 else None


# ----------------------------------------------------------------------------
# Roblox fetchers (documented-ish endpoints). A chunk that fails for good is
# skipped with a warning so one bad batch never sinks a whole run.
# ----------------------------------------------------------------------------
def _multi_get(http: Http, url: str, ids: list[int], params: dict, key: str) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for chunk in chunks(ids, BATCH):
        try:
            data = http.get_json(url, {**params, "universeIds": ",".join(map(str, chunk))}) or {}
        except RuntimeError as e:
            log.warning("skipping a batch of %d ids: %s", len(chunk), e)
            continue
        for item in data.get("data", []):
            uid = as_int(item.get(key))
            if uid:
                out[uid] = item
    return out


def fetch_games(http: Http, ids: list[int]) -> dict[int, dict]:
    return _multi_get(http, GAMES_API, ids, {}, "id")


def fetch_votes(http: Http, ids: list[int]) -> dict[int, dict]:
    return _multi_get(http, VOTES_API, ids, {}, "id")


def fetch_icons(http: Http, ids: list[int]) -> dict[int, str]:
    items = _multi_get(http, ICONS_API, ids, {"size": "512x512", "format": "Png", "isCircular": "false"}, "targetId")
    return {uid: it["imageUrl"] for uid, it in items.items() if it.get("imageUrl") and it.get("state", "Completed") == "Completed"}


def fetch_thumbnails(http: Http, ids: list[int]) -> dict[int, str]:
    items = _multi_get(http, THUMBS_API, ids, {"size": "768x432", "format": "Png", "countPerUniverse": 1}, "universeId")
    out: dict[int, str] = {}
    for uid, it in items.items():
        thumbs = it.get("thumbnails") or []
        if thumbs and thumbs[0].get("imageUrl"):
            out[uid] = thumbs[0]["imageUrl"]
    return out


def fetch_passes(http: Http, uid: int) -> list[dict]:
    """Returns [{id, name, price}] with price None when the pass is not for sale."""
    passes: list[dict] = []
    cursor = None
    for _ in range(20):  # hard stop: 2,000 passes
        params: dict = {"limit": 100, "passView": "Full"}
        if cursor:
            params["cursor"] = cursor
        data = http.get_json(PASSES_API.format(uid=uid), params)
        if not data:
            break
        items = data.get("gamePasses") or data.get("data") or []
        for p in items:
            passes.append({
                "id": p.get("id"),
                "name": p.get("displayName") or p.get("name"),
                "price": p.get("price") if p.get("isForSale", True) else None,
            })
        cursor = data.get("nextPageCursor") or data.get("cursor") or data.get("nextCursor")
        if not cursor or not items:
            break
    return passes


def fetch_creator(http: Http, ctype: str, cid: int) -> dict | None:
    if ctype == "Group":
        return http.get_json(GROUPS_API.format(gid=cid))
    if ctype == "User":
        return http.get_json(USERS_API.format(uid=cid))
    return None


# ----------------------------------------------------------------------------
# Explore (charts) API — undocumented; parsed defensively
# ----------------------------------------------------------------------------
def explore_params() -> dict:
    # The charts page sends device hints alongside sessionId/device/country; harmless if ignored.
    return {
        "sessionId": str(uuid.uuid4()), "device": DEVICE, "country": COUNTRY,
        "cpuCores": 8, "maxResolution": "1920x1080", "maxMemory": 16384, "networkType": "4g",
    }


def iter_sorts(http: Http) -> Iterator[dict]:
    token = None
    for _ in range(10):  # pages of sorts
        params = explore_params()
        if token:
            params["sortsPageToken"] = token
        data = http.get_json(EXPLORE_SORTS, params) or {}
        for s in pick(data, "sort_list", []) or []:
            yield s
        token = pick(data, "sorts_next")
        if not token:
            break


def sort_games(http: Http, sort_obj: dict, depth: int) -> list[dict]:
    games = list(pick(sort_obj, "sort_games", []) or [])
    sort_id = pick(sort_obj, "sort_id")
    token = pick(sort_obj, "sort_next")
    pages = 1
    while token and sort_id and pages < depth:
        params = explore_params()
        params.update({"sortId": sort_id, "pageToken": token})
        data = http.get_json(EXPLORE_CONTENT, params) or {}
        page = pick(data, "sort_games", []) or []
        if not page:
            break
        games.extend(page)
        token = pick(data, "sort_next")
        pages += 1
    return games


# ----------------------------------------------------------------------------
# Database writers
# ----------------------------------------------------------------------------
def upsert_experiences(conn, games: dict[int, dict], ts: datetime, extra: dict[int, dict] | None = None) -> int:
    """Insert or refresh experience rows from games API payloads. `extra` carries explore-only fields."""
    rows = []
    for uid, g in games.items():
        creator = g.get("creator") or {}
        ex = (extra or {}).get(uid) or {}
        age = pick(ex, "game_age")
        rows.append(
            (
                uid,
                as_int(g.get("rootPlaceId")),
                (g.get("name") or "")[:500],
                creator.get("type"),
                as_int(creator.get("id")),
                creator.get("name"),
                parse_ts(g.get("created")),
                parse_ts(g.get("updated")),
                g.get("genre"),
                g.get("genre_l1"),
                g.get("genre_l2"),
                as_int(g.get("maxPlayers")),
                str(age) if age is not None else None,
                ts,
                ts,
            )
        )
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO experience (universe_id, root_place_id, name, creator_type, creator_id, creator_name,
                                    created_at, updated_at_roblox, genre, genre_l1, genre_l2, max_players,
                                    age_rating, first_seen_at, last_seen_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (universe_id) DO UPDATE SET
                root_place_id     = EXCLUDED.root_place_id,
                name              = EXCLUDED.name,
                creator_type      = EXCLUDED.creator_type,
                creator_id        = EXCLUDED.creator_id,
                creator_name      = EXCLUDED.creator_name,
                created_at        = COALESCE(EXCLUDED.created_at, experience.created_at),
                updated_at_roblox = COALESCE(EXCLUDED.updated_at_roblox, experience.updated_at_roblox),
                genre             = COALESCE(EXCLUDED.genre, experience.genre),
                genre_l1          = COALESCE(EXCLUDED.genre_l1, experience.genre_l1),
                genre_l2          = COALESCE(EXCLUDED.genre_l2, experience.genre_l2),
                max_players       = COALESCE(EXCLUDED.max_players, experience.max_players),
                age_rating        = COALESCE(EXCLUDED.age_rating, experience.age_rating),
                last_seen_at      = EXCLUDED.last_seen_at
            """,
            rows,
        )
    return len(rows)


def insert_snapshots(conn, ts: datetime, games: dict[int, dict], votes: dict[int, dict]) -> int:
    rows = []
    for uid, g in games.items():
        v = votes.get(uid, {})
        rows.append(
            (
                uid,
                ts,
                as_int(g.get("playing")),
                as_int(g.get("visits")),
                as_int(g.get("favoritedCount")),
                as_int(v.get("upVotes")),
                as_int(v.get("downVotes")),
            )
        )
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO snapshot (universe_id, ts, playing, visits, favorites, upvotes, downvotes)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (universe_id, ts) DO NOTHING
            """,
            rows,
        )
        return cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else len(rows)


def record_name_desc(conn, games: dict[int, dict], ts: datetime) -> None:
    """Keyed change logs: a new (universe, value) pair means a change happened."""
    names, descs = [], []
    for uid, g in games.items():
        name = (g.get("name") or "")[:500]
        if name:
            names.append((uid, name, ts, ts))
        desc = g.get("description")
        if desc is not None:
            descs.append((uid, sha1(desc), desc, ts, ts))
    with conn.cursor() as cur:
        if names:
            cur.executemany(
                """
                INSERT INTO name_history (universe_id, name, first_seen_at, last_seen_at)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (universe_id, name) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
                """,
                names,
            )
        if descs:
            cur.executemany(
                """
                INSERT INTO description_history (universe_id, desc_hash, description, first_seen_at, last_seen_at)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (universe_id, desc_hash) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
                """,
                descs,
            )


def record_thumbnails(conn, http: Http, kind: str, urls: dict[int, str], ts: datetime) -> None:
    rows = []
    for uid, url in urls.items():
        img_hash = None
        if HASH_IMAGES:
            content = http.get_bytes(url)
            img_hash = sha1(content) if content else None
        rows.append((uid, kind, url, img_hash, ts, ts))
    if not rows:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO thumbnail_history (universe_id, kind, image_url, image_hash, first_seen_at, last_seen_at)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (universe_id, kind, image_url) DO UPDATE
               SET last_seen_at = EXCLUDED.last_seen_at,
                   image_hash   = COALESCE(thumbnail_history.image_hash, EXCLUDED.image_hash)
            """,
            rows,
        )


def record_passes(conn, uid: int, passes: list[dict], ts: datetime) -> None:
    with conn.cursor() as cur:
        for p in passes:
            pid = as_int(p.get("id"))
            if not pid:
                continue
            price = as_int(p.get("price"))
            cur.execute(
                """
                INSERT INTO gamepass (pass_id, universe_id, name, price_robux, first_seen_at, last_seen_at)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (pass_id) DO UPDATE
                   SET name = EXCLUDED.name, price_robux = EXCLUDED.price_robux, last_seen_at = EXCLUDED.last_seen_at
                """,
                (pid, uid, (p.get("displayName") or p.get("name") or "")[:300], price, ts, ts),
            )
            # Price history: extend the open row if the price is unchanged, else open a new row.
            cur.execute(
                "SELECT price_robux, first_seen_at FROM gamepass_price_history WHERE pass_id=%s ORDER BY first_seen_at DESC LIMIT 1",
                (pid,),
            )
            last = cur.fetchone()
            if last and last[0] == price:
                cur.execute(
                    "UPDATE gamepass_price_history SET last_seen_at=%s WHERE pass_id=%s AND first_seen_at=%s",
                    (ts, pid, last[1]),
                )
            else:
                cur.execute(
                    "INSERT INTO gamepass_price_history (pass_id, price_robux, first_seen_at, last_seen_at) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (pid, price, ts, ts),
                )


def record_creator(conn, ctype: str, cid: int, payload: dict | None, ts: datetime) -> None:
    name = member_count = created = None
    if payload:
        name = payload.get("name") or payload.get("displayName")
        member_count = as_int(payload.get("memberCount"))
        created = parse_ts(payload.get("created"))
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO creator (creator_type, creator_id, name, member_count, created_at, first_seen_at, last_seen_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (creator_type, creator_id) DO UPDATE
               SET name = COALESCE(EXCLUDED.name, creator.name),
                   member_count = COALESCE(EXCLUDED.member_count, creator.member_count),
                   created_at = COALESCE(EXCLUDED.created_at, creator.created_at),
                   last_seen_at = EXCLUDED.last_seen_at
            """,
            (ctype, cid, name, member_count, created, ts, ts),
        )
        if member_count is not None:
            # Group size over time is a useful external signal; attach it to each of the group's experiences.
            cur.execute(
                """
                INSERT INTO external_signal (universe_id, source, metric, value, ts)
                SELECT universe_id, 'roblox_group', 'members', %s, %s
                FROM experience WHERE creator_type=%s AND creator_id=%s
                ON CONFLICT DO NOTHING
                """,
                (member_count, ts, ctype, cid),
            )


def log_run(conn, job: str, started: datetime, ok: bool, rows: int, http_requests: int, error: str | None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO collector_run (job, started_at, finished_at, ok, rows_written, http_requests, error)
            VALUES (%s,%s,now(),%s,%s,%s,%s)
            """,
            (job, started, ok, rows, http_requests, error),
        )
    conn.commit()


# ----------------------------------------------------------------------------
# Jobs
# ----------------------------------------------------------------------------
def job_probe(conn, http: Http) -> int:
    first_page = http.get_json(EXPLORE_SORTS, explore_params()) or {}
    with open(os.path.join(BASE_DIR, "probe_get_sorts.json"), "w", encoding="utf-8") as f:
        json.dump(first_page, f, indent=2)
    print("top-level keys:", list(first_page.keys()) if isinstance(first_page, dict) else type(first_page))
    sample_game = None
    n = 0
    print(f"{'sort id':32} {'name':36} {'page1':>5}  paginates?")
    for s in iter_sorts(http):
        n += 1
        games = pick(s, "sort_games", []) or []
        print(f"{str(pick(s, 'sort_id')):32} {str(pick(s, 'sort_name') or ''):36} {len(games):5}  {'yes' if pick(s, 'sort_next') else 'no'}")
        if sample_game is None and games:
            sample_game = games[0]
    print(f"sorts found: {n}")
    if sample_game is not None:
        print("game entry keys:", list(sample_game.keys()))
        print("game id parsed as:", as_int(pick(sample_game, "game_id")))
    else:
        print("no game entries parsed — extend FIELD_ALIASES['sort_games']")
    print("Saved first page to probe_get_sorts.json.")
    return 0


def job_passes(conn, http: Http) -> int:
    """One-off / ad hoc: refresh game passes for every tracked game (the daily job only does a weekly rotation)."""
    ts = run_ts()
    ids = [u for u, *_ in _tracked(conn, "tracking_tier <> 'paused'")]
    n_passes = 0
    for i, uid in enumerate(ids, 1):
        try:
            passes = fetch_passes(http, uid)
            record_passes(conn, uid, passes, ts)
            n_passes += len(passes)
        except Exception as e:
            log.warning("passes failed for %s: %s", uid, e)
        if i % 50 == 0:
            conn.commit()
            log.info("passes: %d/%d games, %d passes so far", i, len(ids), n_passes)
    conn.commit()
    log.info("passes: %d games, %d passes recorded; %d requests, %d throttled", len(ids), n_passes, http.requests, http.throttled)
    return n_passes


def job_probe_passes(conn, http: Http) -> int:
    with conn.cursor() as cur:
        cur.execute("""SELECT e.universe_id, e.name FROM experience e JOIN v_velocity v USING (universe_id)
                       ORDER BY v.ccu_24h DESC NULLS LAST LIMIT 1""")
        row = cur.fetchone()
    if not row:
        print("no tracked games yet"); return 0
    uid, name = row
    print(f"testing game-pass endpoints for {name!r} (universe {uid})")
    for label, url, params in (
        ("apis.roblox.com (current)", PASSES_API.format(uid=uid), {"limit": 100, "passView": "Full"}),
        ("games.roblox.com (legacy)", PASSES_API_LEGACY.format(uid=uid), {"limit": 100, "sortOrder": "Asc"}),
    ):
        http._pace("games.roblox.com")
        r = http.client.get(url, params=params)
        body = r.text[:400].replace("\n", " ")
        print(f"- {label}: HTTP {r.status_code}; body starts: {body}")
    with conn.cursor() as cur:
        cur.execute("SELECT count(*), count(DISTINCT universe_id) FROM gamepass")
        n, g = cur.fetchone()
    print(f"gamepass table: {n} passes across {g} games")
    return 0


def job_sorts(conn, http: Http) -> int:
    ts = run_ts()
    seen: dict[int, dict] = {}
    n_rows = 0
    with conn.cursor() as cur:
        for s in iter_sorts(http):
            sid = pick(s, "sort_id")
            sname = pick(s, "sort_name")
            if not sid:
                continue
            depth = DEEP_SORT_DEPTH if any(k in str(sname or "").lower() for k in DEEP_SORT_KEYWORDS) else SORT_DEPTH
            games = sort_games(http, s, depth)
            rows, pos, seen_in_sort = [], 0, set()
            for g in games:
                uid = as_int(pick(g, "game_id"))
                if not uid or uid in seen_in_sort:   # pagination can repeat a game; keep positions gap-free
                    continue
                seen_in_sort.add(uid)
                pos += 1
                rows.append((ts, str(sid), sname, DEVICE, COUNTRY, uid, pos, bool(pick(g, "game_sponsored", False))))
                seen.setdefault(uid, g)
            if not rows:
                continue
            cur.execute(
                """
                INSERT INTO sort_catalog (sort_id, sort_name, first_seen_at, last_seen_at) VALUES (%s,%s,%s,%s)
                ON CONFLICT (sort_id) DO UPDATE SET sort_name = EXCLUDED.sort_name, last_seen_at = EXCLUDED.last_seen_at
                """,
                (str(sid), sname, ts, ts),
            )
            cur.executemany(
                """
                INSERT INTO chart_position (ts, sort_id, sort_name, device, country, universe_id, position, is_sponsored)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING
                """,
                rows,
            )
            n_rows += len(rows)
            log.info("sort %-40s %5d games", str(sname)[:40], len(rows))
    ids = list(seen)
    if not ids:
        log.warning("no games parsed from explore API — run `probe` and check FIELD_ALIASES")
        conn.rollback()
        return 0
    conn.commit()   # chart positions are safe even if the stats fetch below has a bad day
    log.info("sorts: %d chart rows saved for %d games; fetching stats (about %d s at current pacing)",
             n_rows, len(ids), int(2 * -(-len(ids) // BATCH) * http.host_interval["games.roblox.com"]))
    games = fetch_games(http, ids)
    votes = fetch_votes(http, ids)
    upsert_experiences(conn, games, ts, extra=seen)
    n_snap = insert_snapshots(conn, ts, games, votes)
    record_name_desc(conn, games, ts)
    conn.commit()
    missing = len(ids) - len(games)
    log.info("sorts: %d snapshots written%s; %d requests, %d throttled",
             n_snap, f" ({missing} games skipped this run)" if missing else "", http.requests, http.throttled)
    return n_rows + n_snap


def _tracked(conn, where: str) -> list[tuple[int, str, bool, bool]]:
    """(universe_id, tracking_tier, launch_cohort, created_within_14d) for experiences matching `where`."""
    with conn.cursor() as cur:
        cur.execute(
            f"""SELECT universe_id, tracking_tier, launch_cohort,
                       created_at > now() - interval '14 days'
                FROM experience WHERE {where} ORDER BY universe_id"""
        )
        return [(r[0], r[1], bool(r[2]), bool(r[3])) for r in cur.fetchall()]


def job_stats(conn, http: Http) -> int:
    ts = run_ts()
    ids = [u for u, *_ in _tracked(conn, "tracking_tier = 'intensive'")]
    if not ids:
        log.info("nothing in the intensive tier yet — run `sorts` then `promote` first")
        return 0
    games = fetch_games(http, ids)
    votes = fetch_votes(http, ids)
    upsert_experiences(conn, games, ts)
    n = insert_snapshots(conn, ts, games, votes)
    record_name_desc(conn, games, ts)
    conn.commit()
    log.info("stats: %d snapshots for %d tracked games; %d requests, %d throttled", n, len(ids), http.requests, http.throttled)
    return n


def job_daily(conn, http: Http) -> int:
    ts = run_ts()
    tracked = _tracked(conn, "tracking_tier <> 'paused'")
    ids = [u for u, *_ in tracked]
    if not ids:
        return 0
    games = fetch_games(http, ids)
    votes = fetch_votes(http, ids)
    upsert_experiences(conn, games, ts)
    n = insert_snapshots(conn, ts, games, votes)
    record_name_desc(conn, games, ts)
    conn.commit()
    log.info("daily: %d games refreshed", len(ids))

    record_thumbnails(conn, http, "icon", fetch_icons(http, ids), ts)
    record_thumbnails(conn, http, "thumbnail", fetch_thumbnails(http, ids), ts)
    conn.commit()
    log.info("daily: thumbnails logged")

    # Game passes: one seventh of the games each day, plus every game created in the last 14 days
    # (new games change their monetization fast; established ones rarely do).
    weekday = ts.weekday()
    due = [u for u, _tier, _cohort, recent in tracked if u % 7 == weekday or recent]
    slow = http.host_interval["games.roblox.com"]
    creator_pace = http.host_interval["groups.roblox.com"]
    log.info("daily: %d game-pass refreshes due (about %d min)", len(due), int(len(due) * slow / 60) + 1)
    for i, uid in enumerate(due, 1):
        try:
            record_passes(conn, uid, fetch_passes(http, uid), ts)
        except Exception as e:  # keep going; one bad game shouldn't kill the run
            log.warning("passes failed for %s: %s", uid, e)
        if i % 25 == 0:
            conn.commit()
            log.info("daily: passes %d/%d", i, len(due))
    conn.commit()

    # Creators: only those never seen or not refreshed in 14 days, capped per run; the rest catch up tomorrow.
    creators = sorted({(g["creator"]["type"], as_int(g["creator"]["id"]))
                       for g in games.values() if g.get("creator") and g["creator"].get("id")})
    with conn.cursor() as cur:
        cur.execute("SELECT creator_type, creator_id FROM creator WHERE last_seen_at > now() - interval '14 days'")
        fresh = set(cur.fetchall())
    due_c = [c for c in creators if c not in fresh][:CREATOR_BUDGET]
    log.info("daily: %d of %d creators due for refresh (about %d min)", len(due_c), len(creators), int(len(due_c) * creator_pace / 60) + 1)
    for j, (ctype, cid) in enumerate(due_c, 1):
        try:
            record_creator(conn, ctype, cid, fetch_creator(http, ctype, cid), ts)
        except Exception as e:
            log.warning("creator failed for %s %s: %s", ctype, cid, e)
        if j % 25 == 0:
            conn.commit()
            log.info("daily: creators %d/%d", j, len(due_c))
    conn.commit()
    log.info("daily: done — %d games, %d pass refreshes, %d creators; %d requests, %d throttled",
             len(ids), len(due), len(due_c), http.requests, http.throttled)
    return n


# (sql, params) pairs, applied in order.
PROMOTION_RULES = [
    # 1) charts population: top 200 on a major sort in the last 24h (does not override control/own).
    ("""
    UPDATE experience e SET population = 'charts'
    WHERE e.population IS NULL
      AND EXISTS (SELECT 1 FROM chart_position c
                   WHERE c.universe_id = e.universe_id
                     AND c.ts > now() - interval '24 hours'
                     AND NOT c.is_sponsored
                     AND c.sort_id = ANY(%s) AND c.position <= 200)
    """, lambda: (MAJOR_SORTS,)),
    # 2) launch cohort: created within 60 days of first being seen and crossed 500 CCU at least once.
    ("""
    UPDATE experience e SET launch_cohort = TRUE
    WHERE NOT e.launch_cohort
      AND e.created_at IS NOT NULL
      AND e.created_at > e.first_seen_at - interval '60 days'
      AND EXISTS (SELECT 1 FROM snapshot s WHERE s.universe_id = e.universe_id AND s.playing >= 500)
    """, lambda: None),
    # 3) promote to intensive: controls/own; top-200 on a major sort or any up-and-coming/rising sort in
    #    the last 24h; a growth alert; or a launch-cohort game first seen within 60 days.
    ("""
    UPDATE experience e SET tracking_tier = 'intensive'
    WHERE e.tracking_tier = 'daily'
      AND (
           e.population IN ('control','own')
        OR EXISTS (SELECT 1 FROM chart_position c
                    WHERE c.universe_id = e.universe_id
                      AND c.ts > now() - interval '24 hours'
                      AND NOT c.is_sponsored
                      AND ((c.sort_id = ANY(%s) AND c.position <= 200)
                           OR lower(coalesce(c.sort_name, c.sort_id)) LIKE '%%up-and-coming%%'
                           OR lower(coalesce(c.sort_name, c.sort_id)) LIKE '%%up & coming%%'
                           OR lower(coalesce(c.sort_name, c.sort_id)) LIKE '%%up and coming%%'
                           OR lower(coalesce(c.sort_name, c.sort_id)) LIKE '%%rising%%'))
        OR EXISTS (SELECT 1 FROM v_growth_alerts g WHERE g.universe_id = e.universe_id)
        OR (e.launch_cohort AND e.first_seen_at > now() - interval '60 days')
      )
    """, lambda: (MAJOR_SORTS,)),
    # 4) demote: nothing on any sort for 14 days and max CCU < 200 over 14 days (controls/own never demote).
    ("""
    UPDATE experience e SET tracking_tier = 'daily'
    WHERE e.tracking_tier = 'intensive'
      AND (e.population IS NULL OR e.population = 'charts')
      AND NOT EXISTS (SELECT 1 FROM chart_position c
                       WHERE c.universe_id = e.universe_id AND c.ts > now() - interval '14 days')
      AND COALESCE((SELECT max(playing) FROM snapshot s
                     WHERE s.universe_id = e.universe_id AND s.ts > now() - interval '14 days'), 0) < 200
    """, lambda: None),
]


def job_promote(conn, http: Http) -> int:
    total = 0
    with conn.cursor() as cur:
        for i, (sql, params) in enumerate(PROMOTION_RULES, 1):
            cur.execute(sql, params())
            log.info("promote rule %d: %d rows", i, cur.rowcount)
            total += cur.rowcount
        cur.execute("SELECT tracking_tier, count(*) FROM experience GROUP BY 1 ORDER BY 1")
        log.info("tiers now: %s", dict(cur.fetchall()))
        cur.execute("SELECT coalesce(population, '(other)'), count(*) FROM experience GROUP BY 1 ORDER BY 1")
        log.info("populations: %s", dict(cur.fetchall()))
        cur.execute("SELECT count(*) FROM v_growth_alerts")
        log.info("growth alerts today: %s", cur.fetchone()[0])
    conn.commit()
    return total


def job_sample_controls(conn, http: Http, n: int, lo: int, hi: int) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (universe_id) universe_id, playing
                FROM snapshot WHERE ts > now() - interval '2 days'
                ORDER BY universe_id, ts DESC
            ),
            pool AS (
                SELECT l.universe_id FROM latest l JOIN experience e USING (universe_id)
                WHERE l.playing BETWEEN %s AND %s AND e.population IS NULL
                ORDER BY random() LIMIT %s
            )
            UPDATE experience e SET population = 'control', tracking_tier = 'intensive'
            FROM pool WHERE e.universe_id = pool.universe_id
            """,
            (lo, hi, n),
        )
        k = cur.rowcount
    conn.commit()
    log.info("sampled %d controls in [%d, %d] CCU", k, lo, hi)
    if k < n:
        log.info("pool was smaller than requested — it grows as more sorts are collected; run again in a few days")
    return k


def job_init(conn, http: Http, schema_path: str) -> int:
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    conn.execute(sql)
    conn.commit()
    log.info("schema applied from %s", schema_path)
    return 0


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", choices=["init", "probe", "probe-passes", "sorts", "stats", "daily", "promote", "sample-controls", "passes"])
    ap.add_argument("--schema", default=os.path.join(BASE_DIR, "schema.sql"))
    ap.add_argument("--n", type=int, default=300, help="sample-controls: how many")
    ap.add_argument("--lo", type=int, default=200, help="sample-controls: min CCU")
    ap.add_argument("--hi", type=int, default=2000, help="sample-controls: max CCU")
    args = ap.parse_args(argv)

    log_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, f"{args.job}-{datetime.now().strftime('%Y-%m-%d')}.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger().addHandler(fh)

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set (put the connection string in secrets.txt next to collector.py)", file=sys.stderr)
        return 2

    with job_lock(args.job) as acquired:
        if not acquired:
            log.warning("%s is already running (lock file present); skipping this run", args.job)
            return 0
        http = Http()
        started = datetime.now(timezone.utc)
        with psycopg.connect(dsn, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5, connect_timeout=30) as conn:
            try:
                if args.job == "init":
                    rows = job_init(conn, http, args.schema)
                elif args.job == "probe":
                    rows = job_probe(conn, http)
                elif args.job == "probe-passes":
                    rows = job_probe_passes(conn, http)
                elif args.job == "sorts":
                    rows = job_sorts(conn, http)
                elif args.job == "stats":
                    rows = job_stats(conn, http)
                elif args.job == "daily":
                    rows = job_daily(conn, http)
                elif args.job == "promote":
                    rows = job_promote(conn, http)
                elif args.job == "passes":
                    rows = job_passes(conn, http)
                else:
                    rows = job_sample_controls(conn, http, args.n, args.lo, args.hi)
            except Exception as e:
                conn.rollback()
                log.exception("%s failed", args.job)
                if args.job not in ("init", "probe", "probe-passes"):
                    log_run(conn, args.job, started, False, 0, http.requests, repr(e)[:2000])
                return 1
            if args.job not in ("init", "probe", "probe-passes"):
                log_run(conn, args.job, started, True, rows, http.requests, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
