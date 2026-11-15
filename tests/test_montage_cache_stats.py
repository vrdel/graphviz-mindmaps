import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from graphviz_mindmaps.render.montage_cache import DEFAULT_CACHE_BYTES, MontageCache
from graphviz_mindmaps.tools.montage import build_parser, main
from graphviz_mindmaps.tools.montage_cache_stats import inspect_cache


class MontageCacheStatsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / 'cache with spaces #1'

    def populate(self):
        work = self.directory / 'work'
        work.mkdir()
        image = work / 'sample.png'
        Image.new('RGB', (30, 20), 'cyan').save(image)
        cache = MontageCache(self.root, work)
        for kind, key in (('group', 'a' * 64), ('row', 'b' * 64)):
            node = SimpleNamespace(kind=kind, key=key, children=(), descriptor={'operation': kind})
            cache.store(node, image, 12)
        with cache.db:
            cache.db.execute('''INSERT INTO runs
                (spec_path,spec_digest,destination,export_key,sources_json,status,started_ns,completed_ns,stats_json)
                VALUES (?,?,?,?,?,?,?,?,?)''',
                ('/example/montage.yaml', 'c' * 64, '/example/output.jpg', 'b' * 64, '{}',
                 'success', 1000, 2000, json.dumps({'hits': 2, 'rendered': 4, 'total_seconds': 1.25})))
        cache.close()
        return image.stat().st_size

    def test_default_budget_is_twenty_gib(self):
        self.assertEqual(20 * 1024**3, DEFAULT_CACHE_BYTES)
        args = build_parser().parse_args(['-o', 'result.jpg', 'input.yaml'])
        self.assertEqual(DEFAULT_CACHE_BYTES, args.cache_max_bytes)

    def test_uninitialized_cache_does_not_create_directory(self):
        report = inspect_cache(self.root)
        self.assertFalse(report['initialized'])
        self.assertEqual(0, report['image_files'])
        self.assertFalse(self.root.exists())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(0, main(['cache-stats', '--cache-dir', str(self.root)]))
        self.assertIn('not initialized', output.getvalue())
        self.assertFalse(self.root.exists())

    def test_shared_artifacts_are_counted_once_and_index_is_unchanged(self):
        size = self.populate()
        before = (self.root / 'index.sqlite3').read_bytes()
        report = inspect_cache(self.root)
        self.assertTrue(report['initialized'])
        self.assertEqual(2, report['recipes'])
        self.assertEqual(1, report['available_objects'])
        self.assertEqual(1, report['image_files'])
        self.assertEqual(size, report['image_bytes'])
        groups = {entry['kind']: entry for entry in report['operations']}
        self.assertEqual('column/group', groups['group']['label'])
        self.assertEqual(size, groups['group']['encoded_bytes'])
        self.assertEqual(size, groups['row']['encoded_bytes'])
        self.assertEqual(['group', 'row'], report['largest_objects'][0]['kinds'])
        self.assertEqual({'hits': 2, 'rendered': 4, 'total_seconds': 1.25}, report['recent_builds'][0]['stats'])
        self.assertEqual(before, (self.root / 'index.sqlite3').read_bytes())

    def test_missing_mismatched_evicted_and_untracked_files_are_visible_without_cleanup(self):
        self.populate()
        report = inspect_cache(self.root)
        artifact = Path(report['largest_objects'][0]['path'])
        artifact.chmod(0o600)
        artifact.write_bytes(b'bad')
        report = inspect_cache(self.root)
        self.assertEqual(1, report['size_mismatch_objects'])
        self.assertEqual(0, report['available_objects'])
        self.assertEqual(3, report['image_bytes'])
        artifact.unlink()
        self.assertEqual(1, inspect_cache(self.root)['missing_objects'])
        with sqlite3.connect(self.root / 'index.sqlite3') as db:
            db.execute("UPDATE objects SET state='evicted'")
        extra = self.root / 'objects' / 'ff' / ('f' * 64 + '.png')
        extra.parent.mkdir()
        extra.write_bytes(b'orphan')
        report = inspect_cache(self.root)
        self.assertEqual(1, report['evicted_objects'])
        self.assertEqual(1, report['untracked_image_files'])
        self.assertEqual(6, report['image_bytes'])
        self.assertTrue(extra.exists())

    def test_stats_cli_json_and_human_output_do_not_render(self):
        self.populate()
        with patch('graphviz_mindmaps.tools.montage.MontageRenderer', side_effect=AssertionError('render attempted')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, main(['cache-stats', '--cache-dir', str(self.root), '--json', '--limit', '0']))
            report = json.loads(output.getvalue())
            self.assertEqual(1, report['available_objects'])
            self.assertEqual([], report['largest_objects'])
            self.assertEqual([], report['recent_builds'])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, main(['cache-stats', '--cache-dir', str(self.root)]))
            text = output.getvalue()
            for phrase in ('20.00 GiB', 'column/group', '30x20', 'rendered=4', 'hits=2', 'output.jpg'):
                self.assertIn(phrase, text)

    def test_default_directory_and_corrupt_database_errors(self):
        self.populate()
        with patch('graphviz_mindmaps.tools.montage_cache_stats.default_cache_dir', return_value=self.root):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, main(['cache-stats']))
        (self.root / 'index.sqlite3').write_bytes(b'not a database')
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(1, main(['cache-stats', '--cache-dir', str(self.root)]))
        self.assertIn('not a database', errors.getvalue())

    def test_inspection_sees_live_wal_without_pruning_or_touching_access_times(self):
        self.populate()
        cache = MontageCache(self.root, self.directory)
        self.addCleanup(cache.close)
        with cache.db:
            cache.db.execute('UPDATE objects SET last_used_ns=12345')
            cache.db.execute("UPDATE nodes SET kind='title' WHERE kind='row'")
        report = inspect_cache(self.root)
        self.assertEqual({'group', 'title'}, {entry['kind'] for entry in report['operations']})
        self.assertEqual(12345, cache.db.execute('SELECT last_used_ns FROM objects').fetchone()[0])
        self.assertEqual(1, report['available_objects'])

    def test_negative_limit_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(['cache-stats', '--limit', '-1'])
        self.assertEqual(2, error.exception.code)
