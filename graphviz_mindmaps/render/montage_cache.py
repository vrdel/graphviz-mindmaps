"""Local, rebuildable montage metadata and immutable encoded image objects."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

from PIL import Image


DEFAULT_CACHE_BYTES = 10 * 1024**3


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def recipe_digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def default_cache_dir() -> Path:
    base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    return base / 'graphviz-mindmaps' / 'montage' / 'v1'


@contextmanager
def file_lock(path: Path, exclusive=True, blocking=True):
    with path.open('a+b') as stream:
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        if not blocking:
            operation |= fcntl.LOCK_NB
        fcntl.flock(stream, operation)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class MontageCache:
    """Cache errors disable persistence, never the actual image renderer.

    A hit is linked (or copied) into the invocation's private temporary directory
    while holding a shared object lock. Consumers only read that private path.
    Consequently eviction can unlink the cache name without racing a consumer.
    Public outputs must always be copies, never hardlinks to these objects.
    """

    def __init__(self, root: Path, work: Path, max_bytes=DEFAULT_CACHE_BYTES, enabled=True):
        self.root = root
        self.work = work
        self.max_bytes = max_bytes
        self.enabled = enabled
        self.db = None
        self.maintenance = None
        self.touched = {}
        if not enabled:
            return
        try:
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            for name in ('objects', 'locks', '.staging'):
                (root / name).mkdir(exist_ok=True, mode=0o700)
            self.maintenance = file_lock(root / 'locks' / 'maintenance.lock', exclusive=False)
            self.maintenance.__enter__()
            # Serialize first-open WAL/schema setup; WAL activation can fail
            # immediately when two new databases are initialized concurrently.
            with file_lock(root / 'locks' / 'index.lock'):
                self.db = sqlite3.connect(root / 'index.sqlite3', timeout=5)
                self.db.execute('PRAGMA journal_mode=WAL')
                self.db.execute('PRAGMA synchronous=NORMAL')
                self.db.execute('PRAGMA foreign_keys=ON')
                self.db.executescript('''
                    CREATE TABLE IF NOT EXISTS objects (
                        blob_digest TEXT PRIMARY KEY, relative_path TEXT NOT NULL UNIQUE,
                        encoded_bytes INTEGER NOT NULL, width INTEGER NOT NULL,
                        height INTEGER NOT NULL, format TEXT NOT NULL,
                        state TEXT NOT NULL, created_ns INTEGER NOT NULL,
                        last_used_ns INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS nodes (
                        node_key TEXT PRIMARY KEY, kind TEXT NOT NULL,
                        descriptor_json TEXT NOT NULL,
                        blob_digest TEXT REFERENCES objects(blob_digest),
                        render_ms REAL, created_ns INTEGER NOT NULL, last_used_ns INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS edges (
                        parent_key TEXT REFERENCES nodes(node_key) ON DELETE CASCADE,
                        position INTEGER NOT NULL, child_kind TEXT NOT NULL, child_key TEXT NOT NULL,
                        PRIMARY KEY(parent_key, position));
                    CREATE TABLE IF NOT EXISTS source_files (
                        path TEXT PRIMARY KEY, device INTEGER, inode INTEGER,
                        encoded_bytes INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
                        ctime_ns INTEGER NOT NULL, content_sha256 TEXT NOT NULL, checked_ns INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id INTEGER PRIMARY KEY, spec_path TEXT NOT NULL,
                        spec_digest TEXT NOT NULL, destination TEXT NOT NULL,
                        export_key TEXT NOT NULL, sources_json TEXT NOT NULL, status TEXT NOT NULL,
                        started_ns INTEGER NOT NULL, completed_ns INTEGER, stats_json TEXT);
                    CREATE INDEX IF NOT EXISTS objects_lru ON objects(state,last_used_ns);
                    CREATE INDEX IF NOT EXISTS nodes_by_blob ON nodes(blob_digest);
                    CREATE INDEX IF NOT EXISTS runs_by_spec ON runs(spec_path,destination,started_ns);
                ''')
        except (OSError, sqlite3.Error) as exc:
            self.disable(exc)

    def disable(self, exc):
        if self.enabled:
            print(f'montage: cache unavailable; continuing without persistence: {exc}', file=sys.stderr)
        self.enabled = False

    def object_path(self, relative):
        # Do not trust arbitrary filesystem paths from a damaged index.
        path = self.root / relative
        if path.parent.parent != self.root / 'objects' or path.suffix not in ('.png', '.jpg', '.gif', '.tiff', '.webp', '.bmp'):
            raise OSError('invalid cache object path')
        digest = path.stem
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest) or path.parent.name != digest[:2]:
            raise OSError('invalid cache object checksum')
        return path

    @contextmanager
    def recipe_lock(self, key):
        if not self.enabled:
            yield
            return
        manager = file_lock(self.root / 'locks' / f'recipe-{key}.lock')
        try:
            manager.__enter__()
        except OSError as exc:
            self.disable(exc)
            yield
            return
        try:
            yield
        finally:
            manager.__exit__(None, None, None)

    def lookup(self, key):
        if not self.enabled:
            return None
        try:
            row = self.db.execute('''SELECT o.blob_digest,o.relative_path,o.encoded_bytes
                FROM nodes n JOIN objects o USING(blob_digest)
                WHERE n.node_key=? AND o.state='ready' ''', (key,)).fetchone()
            if row is None:
                return None
            digest, relative, size = row
            path = self.object_path(relative)
            with file_lock(self.root / 'locks' / f'blob-{digest}.lock', exclusive=False):
                if not path.is_file() or path.stat().st_size != size or file_digest(path) != digest:
                    with self.db:
                        self.db.execute("UPDATE objects SET state='evicted' WHERE blob_digest=?", (digest,))
                    return None
                private = self.work / f'cached-{key}{path.suffix}'
                private.unlink(missing_ok=True)
                try:
                    os.link(path, private)
                except OSError:
                    shutil.copyfile(path, private)
            self.touched[digest] = time.time_ns()
            return private
        except (OSError, sqlite3.Error) as exc:
            self.disable(exc)
            return None

    def store(self, node, path, elapsed_ms):
        if not self.enabled:
            return
        try:
            size = path.stat().st_size
            # Do not let a single giant intermediate dominate the budget.
            if size > self.max_bytes // 4 or not size:
                return
            with Image.open(path) as image:
                width, height = image.size
                fmt = image.format
                image.verify()
            extension = {'PNG': '.png', 'JPEG': '.jpg', 'GIF': '.gif',
                         'TIFF': '.tiff', 'WEBP': '.webp', 'BMP': '.bmp'}.get(fmt)
            if extension is None:
                return  # Other output formats still render normally.
            digest = file_digest(path)
            relative = f'objects/{digest[:2]}/{digest}{extension}'
            destination = self.object_path(relative)
            with file_lock(self.root / 'locks' / f'blob-{digest}.lock'):
                destination.parent.mkdir(exist_ok=True, mode=0o700)
                if not destination.is_file() or file_digest(destination) != digest:
                    # This cache-filesystem staging file exists only under its
                    # blob lock. No inactive-build guessing or age-based cleanup.
                    fd, name = tempfile.mkstemp(dir=self.root / '.staging', suffix=extension)
                    os.close(fd)
                    pending = Path(name)
                    try:
                        shutil.copyfile(path, pending)
                        pending.chmod(0o400)
                        pending.replace(destination)
                    finally:
                        pending.unlink(missing_ok=True)
                now = time.time_ns()
                with self.db:
                    self.db.execute('''INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(blob_digest) DO UPDATE SET state='ready',last_used_ns=excluded.last_used_ns''',
                        (digest, relative, size, width, height, fmt, 'ready', now, now))
                    self.db.execute('''INSERT INTO nodes VALUES (?,?,?,?,?,?,?)
                        ON CONFLICT(node_key) DO UPDATE SET blob_digest=excluded.blob_digest,
                        render_ms=excluded.render_ms,last_used_ns=excluded.last_used_ns''',
                        (node.key, node.kind, canonical_json(node.descriptor), digest, elapsed_ms, now, now))
                    self.db.executemany('INSERT OR REPLACE INTO edges VALUES (?,?,?,?)',
                        [(node.key, i, child.kind if child.kind == 'source' else 'node', child.key)
                         for i, child in enumerate(node.children)])
            self.touched[digest] = time.time_ns()
            self.prune()
        except (OSError, sqlite3.Error, ValueError) as exc:
            self.disable(exc)

    def previous_sources(self, spec, destination):
        if not self.enabled:
            return None
        try:
            row = self.db.execute("""SELECT sources_json FROM runs WHERE spec_path=?
                AND destination=? AND status='success' ORDER BY run_id DESC LIMIT 1""",
                (str(spec.resolve()), str(destination))).fetchone()
            return json.loads(row[0]) if row else None
        except (OSError, sqlite3.Error, ValueError) as exc:
            self.disable(exc)
            return None

    def observe_sources(self, sources):
        if not self.enabled:
            return
        try:
            with self.db:
                self.db.executemany('INSERT OR REPLACE INTO source_files VALUES (?,?,?,?,?,?,?,?)',
                    [(str(s.path), s.stat.st_dev, s.stat.st_ino, s.stat.st_size,
                      s.stat.st_mtime_ns, s.stat.st_ctime_ns, s.key, time.time_ns()) for s in sources])
        except (OSError, sqlite3.Error) as exc:
            self.disable(exc)

    def record_run(self, spec, spec_digest, destination, root_key, sources, stats, started_ns):
        if not self.enabled:
            return
        try:
            now = time.time_ns()
            with self.db:
                self.db.execute('''INSERT INTO runs
                    (spec_path,spec_digest,destination,export_key,sources_json,status,started_ns,completed_ns,stats_json)
                    VALUES (?,?,?,?,?,'success',?,?,?)''',
                    (str(spec.resolve()), spec_digest, str(destination), root_key,
                     canonical_json({str(s.path): s.key for s in sources}), started_ns, now, canonical_json(stats)))
        except (OSError, sqlite3.Error) as exc:
            self.disable(exc)

    def prune(self):
        if not self.enabled:
            return
        try:
            with self.db:
                self.db.executemany('UPDATE objects SET last_used_ns=? WHERE blob_digest=?',
                                    [(accessed, digest) for digest, accessed in self.touched.items()])
            self.touched.clear()
            total = self.db.execute("SELECT COALESCE(SUM(encoded_bytes),0) FROM objects WHERE state='ready'").fetchone()[0]
            candidates = self.db.execute("SELECT blob_digest,relative_path,encoded_bytes,last_used_ns FROM objects WHERE state='ready' ORDER BY last_used_ns").fetchall()
            for digest, relative, size, observed_access in candidates:
                if total <= self.max_bytes:
                    break
                try:
                    with file_lock(self.root / 'locks' / f'blob-{digest}.lock', blocking=False):
                        # Recheck after locking; another process may have touched it.
                        fresh = self.db.execute('SELECT state,last_used_ns FROM objects WHERE blob_digest=?', (digest,)).fetchone()
                        if fresh is None or fresh[0] != 'ready' or fresh[1] > observed_access:
                            continue
                        self.object_path(relative).unlink(missing_ok=True)
                        with self.db:
                            self.db.execute("UPDATE objects SET state='evicted' WHERE blob_digest=?", (digest,))
                        total -= size
                except BlockingIOError:
                    continue
        except (OSError, sqlite3.Error) as exc:
            self.disable(exc)

    def recover_orphans(self):
        if not self.enabled:
            return
        try:
            with file_lock(self.root / 'locks' / 'maintenance.lock', blocking=False):
                for pending in (self.root / '.staging').iterdir():
                    if pending.is_file():
                        pending.unlink()
                known = {row[0] for row in self.db.execute(
                    "SELECT relative_path FROM objects WHERE state='ready'")}
                for path in (self.root / 'objects').glob('*/*'):
                    if str(path.relative_to(self.root)) not in known:
                        path.unlink()
        except BlockingIOError:
            pass  # Another live invocation owns its staging files.
        except (OSError, sqlite3.Error) as exc:
            self.disable(exc)

    def close(self):
        try:
            self.prune()
        finally:
            if self.maintenance is not None:
                self.maintenance.__exit__(None, None, None)
                self.maintenance = None
            if self.db is not None:
                try:
                    self.recover_orphans()
                finally:
                    self.db.close()
                    self.db = None
