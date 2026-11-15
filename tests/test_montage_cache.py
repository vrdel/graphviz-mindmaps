import io
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from graphviz_mindmaps.render.montage_cache import MontageCache, file_digest
from graphviz_mindmaps.render.montage_plan import SourceChanged
from graphviz_mindmaps.tools.montage import MontageRenderer, normalize_spec, main


def concurrent_render(directory, queue):
    os.chdir(directory)
    renderer = MontageRenderer(Path('montage.yml'), f'{os.getpid()}.png', cache_dir=Path('cache'))
    try:
        renderer.render_spec(normalize_spec({'entries': ['A.png', 'B.png']}))
        queue.put(('ok', renderer.last_stats))
    except Exception as exc:
        queue.put(('error', repr(exc)))
    finally:
        renderer.cleanup()


@unittest.skipUnless(shutil.which('gm'), 'GraphicsMagick required')
class MontageCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, self.previous)
        self.cache_dir = Path(self.temp.name) / 'cache'
        for name, color in zip('ABCDE', ('red', 'blue', 'green', 'cyan', 'yellow')):
            Image.new('RGB', (40, 30), color).save(f'{name}.png')
        Path('montage.yml').write_text('entries: [A.png, B.png]\n')
        self.spec = normalize_spec({'title': 'Five images', 'size': 'xs', 'entries': [
            {'image_gray': 'A.png'}, 'B.png', {'image_negate': 'C.png'},
            {'new_row': True}, {'image_sketch': 'D.png'}, 'E.png']})
        quiet = patch('graphviz_mindmaps.tools.montage.run_command',
                      side_effect=lambda cmd: subprocess.run(cmd, check=True, capture_output=True))
        quiet.start()
        self.addCleanup(quiet.stop)

    def renderer(self, **kwargs):
        r = MontageRenderer(Path('montage.yml'), kwargs.pop('output', 'result.png'),
                            cache_dir=self.cache_dir, **kwargs)
        self.addCleanup(r.cleanup)
        return r

    def build(self, spec=None, **kwargs):
        r = self.renderer(**kwargs)
        r.render_spec(spec or self.spec)
        stats = r.last_stats.copy()
        r.cleanup()
        return stats

    def pixels(self, filename='result.png'):
        with Image.open(filename) as image:
            return image.size, image.convert('RGBA').tobytes()

    def test_warm_root_skips_all_image_operations_and_is_independent_output(self):
        self.assertEqual(8, self.build()['rendered'])
        expected = self.pixels()
        with patch.object(MontageRenderer, 'render_operation', side_effect=AssertionError('warm render')):
            self.assertEqual(0, self.build()['rendered'])
        self.assertEqual(expected, self.pixels())
        # Editing the public output must not poison the immutable cached object.
        Path('result.png').write_bytes(b'edited public output')
        self.assertEqual(0, self.build()['rendered'])
        self.assertEqual(expected, self.pixels())

    def test_changed_c_only_rebuilds_its_ancestors_and_reversion_hits_old_export(self):
        self.build()
        original = Path('C.png').read_bytes()
        Image.new('RGB', (40, 30), 'purple').save('C.png')
        stats = self.build()
        self.assertEqual({'transform': 1, 'row': 1, 'stack': 1, 'title': 1, 'export': 1}, stats['operations'])
        self.assertEqual(2, stats['hits'])
        changed_pixels = self.pixels()
        self.build(cache='off')
        self.assertEqual(changed_pixels, self.pixels())
        Path('C.png').write_bytes(original)
        self.assertEqual(0, self.build()['rendered'])

    def test_touch_does_not_invalidate_but_same_size_same_mtime_edit_does(self):
        # BMP has fixed-size uncompressed pixels, making this a genuine same-size edit.
        Image.new('RGB', (40, 30), 'red').save('fixed.bmp')
        spec = normalize_spec({'entries': ['fixed.bmp', 'B.png']})
        self.build(spec)
        os.utime('fixed.bmp', None)
        self.assertEqual(0, self.build(spec)['rendered'])
        previous = Path('fixed.bmp').stat()
        Image.new('RGB', (40, 30), 'blue').save('fixed.bmp')
        os.utime('fixed.bmp', ns=(previous.st_atime_ns, previous.st_mtime_ns))
        self.assertEqual(previous.st_size, Path('fixed.bmp').stat().st_size)
        self.assertEqual(2, self.build(spec)['rendered'])

    def test_title_scale_order_and_dimensions_invalidation(self):
        self.build()
        changed = dict(self.spec, title='Another title')
        self.assertEqual({'title': 1, 'export': 1}, self.build(changed)['operations'])
        self.assertEqual({'export': 1}, self.build(changed, scale='50')['operations'])
        self.assertEqual(0, self.build(changed, scale='50.0')['rendered'])
        Image.new('RGB', (80, 60), 'purple').save('C.png')
        self.assertEqual(5, self.build(changed)['rendered'])
        expected = self.pixels()
        self.build(changed, cache='off')
        self.assertEqual(expected, self.pixels())

    def test_parent_hit_does_not_need_children_but_no_clean_materializes_nested_outputs(self):
        spec = normalize_spec({'title': 'auto', 'size': 'xs', 'entries': [
            {'submontage': {'title': 'auto', 'size': 'xs', 'entries': ['A.png', 'B.png']}}, 'C.png']})
        self.build(spec)
        self.assertFalse(Path('montage-m1.png').exists())
        with sqlite3.connect(self.cache_dir / 'index.sqlite3') as db:
            final_blob = db.execute('SELECT blob_digest FROM nodes WHERE node_key=(SELECT export_key FROM runs ORDER BY run_id DESC LIMIT 1)').fetchone()[0]
            others = db.execute('SELECT relative_path FROM objects WHERE blob_digest<>?', (final_blob,)).fetchall()
        for (relative,) in others:
            (self.cache_dir / relative).unlink()
        self.assertEqual(0, self.build(spec)['rendered'])
        stats = self.build(spec, no_clean=True)
        self.assertGreater(stats['rendered'], 0)
        self.assertTrue(Path('montage-m1.png').is_file())
        self.assertEqual(0, self.build(spec, no_clean=True)['rendered'])

    def test_corrupt_or_missing_root_rebuilds_only_export(self):
        self.build()
        with sqlite3.connect(self.cache_dir / 'index.sqlite3') as db:
            relative = db.execute('''SELECT relative_path FROM objects JOIN nodes USING(blob_digest)
                WHERE node_key=(SELECT export_key FROM runs ORDER BY run_id DESC LIMIT 1)''').fetchone()[0]
        path = self.cache_dir / relative
        path.chmod(0o600)
        path.write_bytes(b'corrupt')
        self.assertEqual({'export': 1}, self.build()['operations'])
        path.unlink()
        self.assertEqual({'export': 1}, self.build()['operations'])

    def test_missing_source_is_error_even_with_final_hit(self):
        self.build()
        expected = Path('result.png').read_bytes()
        Path('C.png').unlink()
        with self.assertRaises(FileNotFoundError):
            self.build()
        self.assertEqual(expected, Path('result.png').read_bytes())

    def test_repeated_columns_render_once_with_cache_disabled_too(self):
        spec = normalize_spec({'entries': [{'column': ['A.png', 'B.png']},
                                           {'column': ['A.png', 'B.png']}]})
        stats = self.build(spec, cache='off')
        self.assertEqual({'group': 1, 'row': 1, 'export': 1}, stats['operations'])
        self.assertEqual(1, stats['memo_hits'])

    def test_cache_directory_failure_falls_back_and_zero_budget_is_valid(self):
        self.cache_dir.write_text('not a directory')
        with patch('sys.stderr', new_callable=io.StringIO) as errors:
            self.assertEqual(8, self.build()['rendered'])
        self.assertIn('continuing without persistence', errors.getvalue())
        self.cache_dir.unlink()
        self.assertEqual(8, self.build(cache_max_bytes=0)['rendered'])
        self.assertFalse(list(self.cache_dir.glob('objects/*/*')))

    def test_source_mutation_between_plan_and_snapshot_preserves_output(self):
        Path('result.png').write_bytes(b'previous result')
        original = MontageCache.lookup
        changed = False
        def mutate(cache, key):
            nonlocal changed
            if not changed:
                changed = True
                Image.new('RGB', (40, 30), 'purple').save('A.png')
            return original(cache, key)
        with patch.object(MontageCache, 'lookup', mutate):
            with self.assertRaises(SourceChanged):
                self.build()
        self.assertEqual(b'previous result', Path('result.png').read_bytes())

    def test_eviction_and_retained_parent_can_rebuild_later(self):
        self.build()
        cache = MontageCache(self.cache_dir, Path(self.temp.name), max_bytes=1)
        cache.close()
        with sqlite3.connect(self.cache_dir / 'index.sqlite3') as db:
            self.assertEqual(0, db.execute("SELECT COUNT(*) FROM objects WHERE state='ready'").fetchone()[0])
        self.assertEqual(8, self.build()['rendered'])

    def test_eviction_cannot_remove_private_consumer_input(self):
        self.build()
        cache = MontageCache(self.cache_dir, Path(self.temp.name))
        self.addCleanup(cache.close)
        with sqlite3.connect(self.cache_dir / 'index.sqlite3') as db:
            key = db.execute('SELECT export_key FROM runs ORDER BY run_id DESC LIMIT 1').fetchone()[0]
        private = cache.lookup(key)
        expected = file_digest(private)
        other = MontageCache(self.cache_dir, Path(self.temp.name), max_bytes=0)
        other.close()
        self.assertEqual(expected, file_digest(private))
        with Image.open(private) as image:
            image.load()

    def test_orphan_recovery_waits_for_other_invocations(self):
        first = MontageCache(self.cache_dir, Path(self.temp.name))
        second = MontageCache(self.cache_dir, Path(self.temp.name))
        pending = self.cache_dir / '.staging' / 'interrupted.png'
        pending.write_bytes(b'incomplete')
        digest = 'a' * 64
        orphan = self.cache_dir / 'objects' / 'aa' / (digest + '.png')
        orphan.parent.mkdir(exist_ok=True)
        orphan.write_bytes(b'unindexed')
        first.close()
        self.assertTrue(pending.exists())
        second.close()
        self.assertFalse(pending.exists())
        self.assertFalse(orphan.exists())

    def test_failed_render_and_failed_cache_store_preserve_publication_rules(self):
        Path('result.png').write_bytes(b'previous output')
        with patch.object(MontageRenderer, 'render_operation',
                          side_effect=subprocess.CalledProcessError(1, ['gm'])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.build()
        self.assertEqual(b'previous output', Path('result.png').read_bytes())
        original_copy = shutil.copyfile
        def fail_cache_copy(source, destination, *args, **kwargs):
            if '.staging' in Path(destination).parts:
                raise OSError('simulated cache disk full')
            return original_copy(source, destination, *args, **kwargs)
        with patch('shutil.copyfile', side_effect=fail_cache_copy), patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(8, self.build()['rendered'])
        with Image.open('result.png') as image:
            image.load()
        self.assertFalse(list((self.cache_dir / '.staging').iterdir()))

    def test_two_processes_share_recipes_without_partial_objects(self):
        ctx = multiprocessing.get_context('fork')
        queue = ctx.Queue()
        workers = [ctx.Process(target=concurrent_render, args=(self.temp.name, queue)) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=20)
            if worker.is_alive():
                worker.terminate()
                worker.join()
                self.fail('concurrent renderer hung')
            self.assertEqual(0, worker.exitcode)
        results = [queue.get(timeout=2) for _ in workers]
        self.assertTrue(all(state == 'ok' for state, _ in results), results)
        # Literal titles absent: output filenames do not change export keys.
        self.assertEqual(2, sum(stats['rendered'] for _, stats in results))
        for path in self.cache_dir.glob('objects/*/*'):
            self.assertEqual(path.stem, file_digest(path))

    def test_cli_controls_and_stats(self):
        with patch('sys.stderr', new_callable=io.StringIO) as stderr:
            self.assertEqual(0, main(['--cache-dir', str(self.cache_dir), '--cache-stats', '--cache-explain',
                                     '-o', 'result.png', 'montage.yml']))
        self.assertIn('miss; rendering', stderr.getvalue())
        with patch('sys.stderr', new_callable=io.StringIO) as stderr:
            self.assertEqual(0, main(['--cache-dir', str(self.cache_dir), '--cache-explain',
                                     '-o', 'result.png', 'montage.yml']))
        self.assertIn('hit', stderr.getvalue())
        self.assertNotIn('miss', stderr.getvalue())
