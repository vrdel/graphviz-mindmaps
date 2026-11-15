"""Inspect the persistent montage cache without rendering or pruning it."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys

from graphviz_mindmaps.render.montage_cache import DEFAULT_CACHE_BYTES, default_cache_dir


KIND_LABELS = {'group': 'column/group', 'row': 'row', 'stack': 'stack',
               'transform': 'transform', 'title': 'title', 'export': 'export'}


def human_bytes(value):
    amount = float(value)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(amount) < 1024 or unit == 'TiB':
            return f'{amount:.2f} {unit}'
        amount /= 1024


def inspect_cache(root: Path, limit=5):
    """Use a consistent SQLite read snapshot and inexpensive filesystem stats.

    Files can change during a live build. This is a usage report, not a checksum
    integrity check. Recipe totals may share the same immutable image object.
    """
    if limit < 0:
        raise ValueError('limit must be nonnegative')
    root = root.expanduser().resolve()
    database = root / 'index.sqlite3'
    report = {
        'cache_dir': str(root), 'initialized': database.is_file(),
        'default_budget_bytes': DEFAULT_CACHE_BYTES,
        'image_files': 0, 'image_bytes': 0, 'metadata_bytes': 0, 'staging_bytes': 0,
        'ready_objects': 0, 'available_objects': 0, 'evicted_objects': 0,
        'missing_objects': 0, 'size_mismatch_objects': 0,
        'untracked_image_files': 0, 'recipes': 0, 'sources': 0,
        'builds': 0, 'operations': [], 'largest_objects': [], 'recent_builds': [],
    }
    if not report['initialized']:
        return report

    # mode=ro avoids initializing or modifying the cache schema. Do not use
    # immutable=1: it ignores a live WAL and can report stale cache contents.
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True, timeout=5)
    try:
        connection.execute('BEGIN')
        objects = connection.execute('''SELECT blob_digest,relative_path,encoded_bytes,
            width,height,format,state FROM objects''').fetchall()
        nodes = connection.execute('SELECT kind,blob_digest FROM nodes').fetchall()
        report['sources'] = connection.execute('SELECT count(*) FROM source_files').fetchone()[0]
        report['builds'] = connection.execute('SELECT count(*) FROM runs').fetchone()[0]
        runs = connection.execute('''SELECT spec_path,destination,status,completed_ns,stats_json
            FROM runs ORDER BY run_id DESC LIMIT ?''', (limit,)).fetchall()
    finally:
        connection.close()

    physical = {}
    for path in (root / 'objects').glob('*/*'):
        try:
            if path.is_file():
                physical[path.relative_to(root).as_posix()] = path.stat().st_size
        except FileNotFoundError:
            pass  # Eviction may race the filesystem scan.
    report['image_files'] = len(physical)
    report['image_bytes'] = sum(physical.values())
    for path in root.glob('index.sqlite3*'):
        try:
            if path.is_file():
                report['metadata_bytes'] += path.stat().st_size
        except FileNotFoundError:
            pass
    for path in (root / '.staging').iterdir() if (root / '.staging').is_dir() else ():
        try:
            if path.is_file():
                report['staging_bytes'] += path.stat().st_size
        except FileNotFoundError:
            pass

    tracked = {row[1] for row in objects}
    report['untracked_image_files'] = len(set(physical) - tracked)
    available = {}
    for digest, relative, size, width, height, fmt, state in objects:
        if state == 'evicted':
            report['evicted_objects'] += 1
            continue
        if state != 'ready':
            continue
        report['ready_objects'] += 1
        actual_size = physical.get(relative)
        if actual_size is None:
            report['missing_objects'] += 1
        elif actual_size != size:
            report['size_mismatch_objects'] += 1
        else:
            available[digest] = {
                'checksum': digest, 'path': str(root / relative), 'encoded_bytes': size,
                'width': width, 'height': height, 'format': fmt, 'kinds': [],
            }
    report['available_objects'] = len(available)
    report['recipes'] = len(nodes)
    kinds = {}
    for kind, digest in nodes:
        entry = kinds.setdefault(kind, {'kind': kind, 'label': KIND_LABELS.get(kind, kind),
                                       'recipes': 0, 'available_recipes': 0, 'objects': set()})
        entry['recipes'] += 1
        if digest in available:
            entry['available_recipes'] += 1
            entry['objects'].add(digest)
            if kind not in available[digest]['kinds']:
                available[digest]['kinds'].append(kind)
    for kind in sorted(kinds):
        entry = kinds[kind]
        unique = entry.pop('objects')
        entry['available_objects'] = len(unique)
        entry['encoded_bytes'] = sum(available[d]['encoded_bytes'] for d in unique)
        report['operations'].append(entry)
    report['largest_objects'] = sorted(available.values(),
        key=lambda item: (-item['encoded_bytes'], item['checksum']))[:limit]
    for spec, destination, status, completed_ns, stats_json in runs:
        try:
            stats = json.loads(stats_json) if stats_json else {}
            if not isinstance(stats, dict):
                stats = {}
        except (ValueError, TypeError):
            stats = {}
        report['recent_builds'].append({
            'spec_path': spec, 'destination': destination, 'status': status,
            'completed_ns': completed_ns, 'stats': stats,
        })
    return report


def print_report(report):
    print(f"Cache: {report['cache_dir']}")
    print(f"Default image budget: {human_bytes(report['default_budget_bytes'])} (builds can override)")
    if not report['initialized']:
        print('Cache is not initialized; no directory or database was created.')
        return
    print(f"Image files: {report['image_files']} ({human_bytes(report['image_bytes'])})")
    print(f"Index/WAL: {human_bytes(report['metadata_bytes'])}; staging: {human_bytes(report['staging_bytes'])}")
    print(f"Available objects: {report['available_objects']}; evicted records: {report['evicted_objects']}; "
          f"missing files: {report['missing_objects']}; size mismatches: {report['size_mismatch_objects']}")
    print(f"Untracked image files: {report['untracked_image_files']}")
    print(f"Recipes: {report['recipes']}; observed sources: {report['sources']}; recorded builds: {report['builds']}")
    print('\nOperations:')
    print(f"{'Kind':<15} {'Recipes':>9} {'Available':>10} {'Objects':>8} {'Image bytes':>13}")
    for entry in report['operations']:
        print(f"{entry['label']:<15} {entry['recipes']:>9} {entry['available_recipes']:>10} "
              f"{entry['available_objects']:>8} {human_bytes(entry['encoded_bytes']):>13}")
    print('Objects shared across kinds are counted in each row; image-file totals count them once.')
    print('\nLargest available objects:')
    for entry in report['largest_objects']:
        labels = ', '.join(KIND_LABELS.get(kind, kind) for kind in sorted(entry['kinds']))
        print(f"  {human_bytes(entry['encoded_bytes'])}  {entry['width']}x{entry['height']}  "
              f"{entry['format']}  {labels}")
        print(f"    {entry['path']}")
    print('\nRecent builds:')
    for entry in report['recent_builds']:
        when = (datetime.fromtimestamp(entry['completed_ns'] / 1e9).astimezone().isoformat(timespec='seconds')
                if entry['completed_ns'] is not None else 'unfinished')
        stats = entry['stats']
        print(f"  {when}  {entry['status']}")
        print(f"    {entry['spec_path']} -> {entry['destination']}")
        print(f"    rendered={stats.get('rendered', '?')}  hits={stats.get('hits', '?')}  "
              f"seconds={stats.get('total_seconds', '?')}")
    print('\nFilesystem sizes are a live snapshot; image checksums were not scanned.')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='montage cache-stats',
                                     description='Inspect cache usage without rendering or pruning')
    parser.add_argument('--cache-dir', type=Path, default=None)
    parser.add_argument('--json', action='store_true', help='print machine-readable statistics')
    parser.add_argument('--limit', type=int, default=5, help='largest objects and recent builds to list (default: 5)')
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error('--limit must be nonnegative')
    try:
        report = inspect_cache(args.cache_dir if args.cache_dir is not None else default_cache_dir(), args.limit)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_report(report)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f'montage cache-stats: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
