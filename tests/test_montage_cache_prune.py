import contextlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest

from PIL import Image

from graphviz_mindmaps.render.montage_cache import MontageCache
from graphviz_mindmaps.tools.montage import main
from graphviz_mindmaps.tools.montage_cache_prune import CacheBusyError, prune_cache
from graphviz_mindmaps.tools.montage_cache_stats import inspect_cache


DAY = 86400 * 10**9
NOW = 100 * DAY


class MontageCachePruneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / 'cache with spaces #1'
        self.work = self.directory / 'work'
        self.work.mkdir()
        self.source = self.work / 'source.png'
        self.output = self.work / 'public-output.jpg'
        self.output.write_bytes(b'published output')
        cache = MontageCache(self.root, self.work)
        self.keys = []
        for index, color in enumerate(('red', 'blue', 'green')):
            Image.new('RGB', (40 + index, 25), color).save(self.source)
            key = str(index + 1) * 64
            self.keys.append(key)
            cache.store(SimpleNamespace(kind='group', key=key, descriptor={'color': color}, children=()),
                        self.source, 10)
        # A row and a group deliberately share the exact same encoded object.
        cache.store(SimpleNamespace(kind='row', key='d' * 64, descriptor={}, children=()), self.source, 10)
        cache.close()
        with sqlite3.connect(self.root / 'index.sqlite3') as db:
            self.objects = []
            for key, age in zip(self.keys, (60, 30, 1)):
                digest, relative, size = db.execute('''SELECT o.blob_digest,o.relative_path,o.encoded_bytes
                    FROM objects o JOIN nodes n USING(blob_digest) WHERE n.node_key=?''', (key,)).fetchone()
                db.execute('UPDATE objects SET last_used_ns=? WHERE blob_digest=?', (NOW - age * DAY, digest))
                self.objects.append((digest, self.root / relative, size))
            db.execute('''INSERT INTO runs (spec_path,spec_digest,destination,export_key,sources_json,
                       status,started_ns,completed_ns,stats_json) VALUES (?,?,?,?,?,?,?,?,?)''',
                       ('example.yaml', 'a' * 64, str(self.output), self.keys[-1], '{}', 'success', 1, 2, '{}'))
        self.total = sum(item[2] for item in self.objects)
        self.original_source = self.source.read_bytes()

    def assert_project_files_untouched(self):
        self.assertEqual(self.original_source, self.source.read_bytes())
        self.assertEqual(b'published output', self.output.read_bytes())

    def test_lru_budget_removes_oldest_objects_and_preserves_shared_objects(self):
        budget = self.objects[-1][2]
        report = prune_cache(self.root, max_bytes=budget)
        self.assertEqual(2, report['removed_files'])
        self.assertEqual(budget, report['image_bytes_after'])
        self.assertFalse(self.objects[0][1].exists())
        self.assertFalse(self.objects[1][1].exists())
        self.assertTrue(self.objects[2][1].exists())
        stats = inspect_cache(self.root)
        self.assertEqual(4, stats['recipes'])
        self.assertEqual(1, stats['available_objects'])
        self.assertEqual(2, sum(row['available_recipes'] for row in stats['operations']))
        self.assert_project_files_untouched()

    def test_age_only_and_combined_age_then_size(self):
        report = prune_cache(self.root, older_than_days=45, now_ns=NOW)
        self.assertIsNone(report['max_bytes'])
        self.assertEqual(1, report['removed_files'])
        self.assertTrue(self.objects[1][1].exists())
        report = prune_cache(self.root, older_than_days=20, max_bytes=0, now_ns=NOW)
        self.assertEqual(['older than cutoff', 'LRU size budget'], [f['reason'] for f in report['files']])
        self.assertEqual(0, report['image_bytes_after'])

    def test_dry_run_and_json_preview_do_not_modify_records_or_delete_files(self):
        index = self.root / 'index.sqlite3'
        original = index.read_bytes()
        report = prune_cache(self.root, remove_all=True, dry_run=True)
        self.assertEqual(3, report['selected_files'])
        self.assertEqual(self.total, report['selected_bytes'])
        self.assertEqual(0, report['removed_files'])
        self.assertEqual(0, report['removed_bytes'])
        self.assertEqual(original, index.read_bytes())
        self.assertTrue(all(path.exists() for _, path, _ in self.objects))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(['cache-prune', '--cache-dir', str(self.root), '--all', '--dry-run', '--json']))
        self.assertEqual(3, json.loads(output.getvalue())['selected_files'])
        self.assert_project_files_untouched()

    def test_clear_retains_history_recipes_locks_and_sources(self):
        locks = sorted(path.name for path in (self.root / 'locks').iterdir())
        report = prune_cache(self.root, remove_all=True)
        self.assertEqual(3, report['removed_files'])
        stats = inspect_cache(self.root)
        self.assertEqual(0, stats['image_files'])
        self.assertEqual(0, stats['available_objects'])
        self.assertEqual(3, stats['evicted_objects'])
        self.assertEqual(4, stats['recipes'])
        self.assertEqual(1, stats['builds'])
        self.assertEqual(locks, sorted(path.name for path in (self.root / 'locks').iterdir()))
        self.assert_project_files_untouched()
        self.assertEqual(0, prune_cache(self.root, remove_all=True)['removed_files'])

    def test_active_build_is_busy_and_nothing_is_deleted(self):
        cache = MontageCache(self.root, self.work)
        try:
            with self.assertRaises(CacheBusyError):
                prune_cache(self.root, remove_all=True)
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(1, main(['cache-prune', '--cache-dir', str(self.root), '--all']))
            self.assertIn('cache is busy', errors.getvalue())
            self.assertTrue(all(path.exists() for _, path, _ in self.objects))
        finally:
            cache.close()

    def test_cleared_recipe_can_be_stored_and_reused_again(self):
        prune_cache(self.root, remove_all=True)
        cache = MontageCache(self.root, self.work)
        try:
            self.assertIsNone(cache.lookup(self.keys[-1]))
            cache.store(SimpleNamespace(kind='group', key=self.keys[-1], descriptor={}, children=()),
                        self.source, 10)
            restored = cache.lookup(self.keys[-1])
            self.assertIsNotNone(restored)
            self.assertEqual(self.original_source, restored.read_bytes())
        finally:
            cache.close()
        self.assertEqual(1, inspect_cache(self.root)['available_objects'])

    def test_cleanup_orphans_staging_mismatches_and_missing_records(self):
        digest, missing, _ = self.objects[0]
        missing.unlink()
        damaged = self.objects[1][1]
        damaged.chmod(0o600)
        damaged.write_bytes(b'bad')
        orphan = self.root / 'objects' / 'ff' / ('f' * 64 + '.png')
        orphan.parent.mkdir()
        orphan.write_bytes(b'orphan')
        pending = self.root / '.staging' / 'interrupted.png'
        pending.write_bytes(b'partial')
        preview = prune_cache(self.root, dry_run=True)
        self.assertEqual(3, preview['selected_files'])
        self.assertEqual(1, preview['missing_records'])
        self.assertTrue(orphan.exists())
        report = prune_cache(self.root)
        self.assertEqual(3, report['removed_files'])
        self.assertFalse(pending.exists())
        self.assertFalse(orphan.exists())
        self.assertTrue(self.objects[2][1].exists())
        with sqlite3.connect(self.root / 'index.sqlite3') as db:
            self.assertEqual('evicted', db.execute('SELECT state FROM objects WHERE blob_digest=?', (digest,)).fetchone()[0])
        self.assert_project_files_untouched()

    def test_invalid_object_path_is_rejected_before_any_deletion(self):
        with sqlite3.connect(self.root / 'index.sqlite3') as db:
            db.execute('UPDATE objects SET relative_path=? WHERE blob_digest=?',
                       ('../../work/public-output.jpg', self.objects[-1][0]))
        with self.assertRaisesRegex(ValueError, 'invalid cache object path'):
            prune_cache(self.root, remove_all=True)
        self.assertTrue(all(path.exists() for _, path, _ in self.objects))
        self.assert_project_files_untouched()

    def test_symlinks_cannot_redirect_deletion_outside_cache(self):
        pending = self.root / '.staging' / 'unsafe.png'
        pending.symlink_to(self.output)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            prune_cache(self.root, remove_all=True)
        self.assertTrue(all(path.exists() for _, path, _ in self.objects))
        self.assert_project_files_untouched()

    def test_no_cache_is_noop_and_does_not_create_directories(self):
        missing = self.directory / 'absent'
        self.assertFalse(prune_cache(missing)['initialized'])
        self.assertFalse(missing.exists())
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(['cache-prune', '--cache-dir', str(missing)]))
        self.assertIn('nothing to prune', output.getvalue())

    def test_cli_validation_and_human_output(self):
        for options in (['--max-bytes', '-1'], ['--older-than', '-1'], ['--older-than', 'nan'],
                        ['--older-than', 'inf'], ['--all', '--max-bytes', '0'], ['--all', '--older-than', '1']):
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['cache-prune', *options])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(['cache-prune', '--cache-dir', str(self.root), '--max-bytes', '0', '--dry-run']))
        self.assertIn('Would remove 3 files', output.getvalue())
        self.assertTrue(all(path.exists() for _, path, _ in self.objects))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0, main(['cache-prune', '--cache-dir', str(self.root), '--max-bytes', '0']))
        self.assertIn('Removed 3 files', output.getvalue())
