"""Explicit, coordinated maintenance of montage image artifacts."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import sys
import time

from graphviz_mindmaps.render.montage_cache import DEFAULT_CACHE_BYTES, default_cache_dir, file_lock
from graphviz_mindmaps.tools.montage_cache_stats import human_bytes


class CacheBusyError(RuntimeError):
    pass


def _object_path(root, relative, digest=None):
    parts = PurePosixPath(relative).parts
    if len(parts) != 3 or parts[0] != 'objects':
        raise ValueError(f'invalid cache object path: {relative}')
    filename = Path(parts[2])
    checksum = filename.stem
    if (len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum)
            or parts[1] != checksum[:2]
            or filename.suffix not in ('.png', '.jpg', '.gif', '.tiff', '.webp', '.bmp')
            or (digest is not None and checksum != digest)):
        raise ValueError(f'invalid cache object identity: {relative}')
    path = root.joinpath(*parts)
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError(f'refusing a symlink in the cache object store: {relative}')
    return path


def _plan(root, db, max_bytes, older_than_days, remove_all, now_ns):
    for name in ('objects', '.staging'):
        if (root / name).is_symlink():
            raise ValueError(f'refusing a symlinked cache directory: {name}')
    rows = db.execute('''SELECT blob_digest,relative_path,encoded_bytes,state,last_used_ns
                         FROM objects''').fetchall()
    tracked = {}
    for digest, relative, size, state, accessed in rows:
        _object_path(root, relative, digest)  # Validate every record before deleting anything.
        tracked[relative] = (digest, size, state, accessed)
    physical = {}
    for path in sorted((root / 'objects').glob('*/*')):
        relative = path.relative_to(root).as_posix()
        _object_path(root, relative)
        if path.is_file():
            physical[relative] = path.stat().st_size

    files = []
    evict = set()
    missing = []
    eligible = []
    for relative, actual_size in physical.items():
        record = tracked.get(relative)
        if record is None:
            reason, digest = 'untracked object', None
        else:
            digest, encoded_size, state, accessed = record
            if state != 'ready':
                reason = 'evicted object'
            elif encoded_size != actual_size:
                reason = 'size mismatch'
            else:
                eligible.append((accessed, digest, relative, actual_size))
                continue
            evict.add(digest)
        files.append({'path': str(root / relative), 'bytes': actual_size, 'reason': reason,
                      'digest': digest, 'image': True})
    for relative, (digest, _, state, _) in tracked.items():
        if state == 'ready' and relative not in physical:
            missing.append(digest)
            evict.add(digest)

    remaining = sum(item[3] for item in eligible)
    cutoff = None
    if older_than_days is not None:
        # Integer arithmetic avoids overflowing a float when converting to ns.
        days, fraction = divmod(older_than_days, 1)
        cutoff = now_ns - int(days) * 86400 * 10**9 - int(fraction * 86400 * 10**9)
    for accessed, digest, relative, size in sorted(eligible):
        reason = None
        if remove_all:
            reason = 'clear all images'
        elif cutoff is not None and accessed < cutoff:
            reason = 'older than cutoff'
        if reason:
            files.append({'path': str(root / relative), 'bytes': size, 'reason': reason,
                          'digest': digest, 'image': True})
            evict.add(digest)
            remaining -= size
    if max_bytes is not None:
        for _, digest, relative, size in sorted(eligible):
            if remaining <= max_bytes:
                break
            if digest in evict:
                continue
            files.append({'path': str(root / relative), 'bytes': size, 'reason': 'LRU size budget',
                          'digest': digest, 'image': True})
            evict.add(digest)
            remaining -= size
    staging = root / '.staging'
    if staging.is_dir():
        for path in sorted(staging.iterdir()):
            if path.is_symlink():
                raise ValueError(f'refusing a staging symlink: {path.name}')
            if path.is_file():
                files.append({'path': str(path), 'bytes': path.stat().st_size,
                              'reason': 'inactive staging file', 'digest': None, 'image': False})
    return files, missing, sum(physical.values()), remaining


def prune_cache(root: Path, max_bytes=None, older_than_days=None, remove_all=False,
                dry_run=False, now_ns=None):
    """Prune only encoded cache objects; retain recipes, history, and lock files.

    The exclusive maintenance lock excludes builders for the whole operation.
    A busy cache is reported immediately, without waiting or deleting anything.
    """
    if max_bytes is not None and max_bytes < 0:
        raise ValueError('max bytes must be nonnegative')
    if older_than_days is not None and (not math.isfinite(older_than_days) or older_than_days < 0):
        raise ValueError('older-than days must be finite and nonnegative')
    if remove_all and (max_bytes is not None or older_than_days is not None):
        raise ValueError('--all cannot be combined with --max-bytes or --older-than')
    if not remove_all and older_than_days is None and max_bytes is None:
        max_bytes = DEFAULT_CACHE_BYTES
    root = root.expanduser().resolve()
    database = root / 'index.sqlite3'
    report = {'cache_dir': str(root), 'initialized': database.is_file(), 'dry_run': dry_run,
              'max_bytes': max_bytes, 'older_than_days': older_than_days, 'all': remove_all,
              'image_bytes_before': 0, 'image_bytes_after': 0, 'selected_files': 0,
              'selected_bytes': 0, 'removed_files': 0, 'removed_bytes': 0,
              'missing_records': 0, 'files': []}
    if not report['initialized']:
        return report
    if (root / 'locks').is_symlink() or database.is_symlink():
        raise ValueError('refusing symlinked cache locks or index')
    # Existing valid caches already have this directory. Recreate it only for
    # recovery of a partially damaged cache, without initializing any schema.
    (root / 'locks').mkdir(exist_ok=True, mode=0o700)
    if (root / 'locks' / 'maintenance.lock').is_symlink():
        raise ValueError('refusing a symlinked cache maintenance lock')
    manager = file_lock(root / 'locks' / 'maintenance.lock', blocking=False)
    try:
        manager.__enter__()
    except BlockingIOError as exc:
        raise CacheBusyError('cache is busy; a build or maintenance command is active; retry after it finishes') from exc
    try:
        mode = 'ro' if dry_run else 'rw'
        with closing(sqlite3.connect(database.as_uri() + f'?mode={mode}', uri=True, timeout=5)) as db:
            files, missing, before, after = _plan(root, db, max_bytes, older_than_days,
                remove_all, time.time_ns() if now_ns is None else now_ns)
            report.update(image_bytes_before=before, image_bytes_after=after,
                          selected_files=len(files), selected_bytes=sum(f['bytes'] for f in files),
                          missing_records=len(missing), files=files)
            if not dry_run:
                for entry in files:
                    Path(entry['path']).unlink()
                    report['removed_files'] += 1
                    report['removed_bytes'] += entry['bytes']
                    if entry['digest'] is not None:
                        with db:
                            db.execute("UPDATE objects SET state='evicted' WHERE blob_digest=?", (entry['digest'],))
                with db:
                    db.executemany("UPDATE objects SET state='evicted' WHERE blob_digest=?", [(d,) for d in missing])
    finally:
        manager.__exit__(None, None, None)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(prog='montage cache-prune',
        description='Prune cached images while preserving recipes and build history')
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--max-bytes', type=int,
                        help='evict least recently used images to this budget (default: 10 GiB without an age filter)')
    parser.add_argument('--older-than', type=float, metavar='DAYS', help='remove images last used more than DAYS ago')
    parser.add_argument('--all', action='store_true', help='remove all cached images; keep index/history and locks')
    parser.add_argument('--dry-run', action='store_true', help='preview without deleting files or updating cache records')
    parser.add_argument('--json', action='store_true', help='print machine-readable results and selected paths')
    args = parser.parse_args(argv)
    if args.max_bytes is not None and args.max_bytes < 0:
        parser.error('--max-bytes must be nonnegative')
    if args.older_than is not None and (not math.isfinite(args.older_than) or args.older_than < 0):
        parser.error('--older-than must be finite and nonnegative')
    if args.all and (args.max_bytes is not None or args.older_than is not None):
        parser.error('--all cannot be combined with --max-bytes or --older-than')
    try:
        report = prune_cache(args.cache_dir if args.cache_dir is not None else default_cache_dir(),
                             args.max_bytes, args.older_than, args.all, args.dry_run)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(f"Cache: {report['cache_dir']}")
            if not report['initialized']:
                print('Cache is not initialized; nothing to prune.')
            else:
                verb = 'Would remove' if args.dry_run else 'Removed'
                print(f"{verb} {report['selected_files']} files ({human_bytes(report['selected_bytes'])}).")
                print(f"Image files: {human_bytes(report['image_bytes_before'])} -> {human_bytes(report['image_bytes_after'])}")
                print(f"Missing object records {'to mark' if args.dry_run else 'marked'} evicted: {report['missing_records']}")
                if args.dry_run:
                    for entry in report['files'][:10]:
                        print(f"  {human_bytes(entry['bytes'])}  {entry['reason']}  {entry['path']}")
                    if len(report['files']) > 10:
                        print('  More selected files omitted; use --json for the complete list.')
                print('Recipes, build history, source files, project outputs, and lock files are retained.')
    except (OSError, sqlite3.Error, ValueError, CacheBusyError) as exc:
        print(f'montage cache-prune: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
