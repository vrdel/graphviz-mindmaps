from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import tempfile
import unittest

from graphviz_mindmaps.commands.create_mm import main


class CreateMindmapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, previous)

    def run_create(self, *args):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(list(args)))

    def test_omitted_wiki_is_not_created_or_referenced(self):
        for mode in ('-s', '-m'):
            with self.subTest(mode=mode):
                self.run_create(mode, '-f', 'justfile', '-p', 'example.otl',
                                '-o', 'result.jpg')
                self.assertFalse(list(Path('.').glob('*.wiki')))
                build = Path('justfile').read_text()
                for reference in ('wiki', 'Vimwiki2HTML', 'vim -c'):
                    self.assertNotIn(reference, build)
                self.assertIn('example.otl', build)
                self.assertTrue(Path('example.otl').exists())
                if mode == '-m':
                    self.assertIn('result.jpg', build)
                    self.assertTrue(Path('montage.yml').exists())

    def test_omitted_wiki_leaves_existing_file_untouched(self):
        wiki = Path('Template.wiki')
        wiki.write_text('Existing notes\n')
        for mode in ('-s', '-m'):
            self.run_create(mode)
            self.assertEqual('Existing notes\n', wiki.read_text())

    def test_explicit_wiki_is_created_and_referenced_in_both_modes(self):
        for mode in ('-s', '-m'):
            for name in ('Template.wiki', 'Notes.wiki'):
                with self.subTest(mode=mode, name=name):
                    self.run_create(mode, '-w', name, '-f', 'build.just',
                                    '-p', 'example.otl', '-o', 'result.jpg')
                    wiki = Path(name).read_text()
                    self.assertIn('example', wiki)
                    self.assertNotIn('mindmap-01', wiki)
                    build = Path('build.just').read_text()
                    self.assertIn('wiki := "' + name + '"', build)
                    self.assertIn('Vimwiki2HTML', build)
                    if mode == '-m':
                        self.assertIn('result.jpg', wiki)

    def test_single_can_create_wiki_without_build_file(self):
        self.run_create('-s', '-w', 'Notes.wiki')
        self.assertTrue(Path('Notes.wiki').exists())
        self.assertFalse(Path('justfile').exists())

    def test_auto_matches_explicit_montage_project(self):
        for auto in ('-a', '--auto'):
            with self.subTest(auto=auto):
                self.run_create('-m', auto, '-o', 'example.release.jpg')
                files = ('example.release-1.otl', 'example.release.yml', 'example.release.just')
                generated = {name: Path(name).read_bytes() for name in files}
                self.assertEqual(set(files), {path.name for path in Path('.').iterdir()})
                build = Path(files[2]).read_text()
                self.assertIn('scale := "90"', build)
                self.assertIn('example.release-1.otl', build)
                self.assertIn('example.release.yml', build)
                self.assertIn('example.release.jpg', build)
                self.assertNotIn('wiki', build)
                self.assertIn('example.release-1.jpg', Path(files[1]).read_text())
                self.run_create('-m', '-o', 'example.release.jpg',
                                '-p', files[0], '-g', files[1], '-j', files[2])
                self.assertEqual(generated, {name: Path(name).read_bytes() for name in files})

    def test_auto_respects_explicit_overrides(self):
        self.run_create('-m', '-a', '-o', 'example.jpg', '-p', 'custom.otl',
                        '-g', 'custom.yaml', '-j', 'custom.just', '-l', '80', '-w', 'Notes.wiki')
        self.assertEqual({'custom.otl', 'custom.yaml', 'custom.just', 'Notes.wiki'},
                         {path.name for path in Path('.').iterdir()})
        build = Path('custom.just').read_text()
        self.assertIn('scale := "80"', build)
        self.assertIn('custom.otl', build)
        self.assertIn('custom.yaml', build)
        self.assertIn('example.jpg', build)
        self.assertIn('Vimwiki2HTML', build)

    def test_auto_requires_montage_and_output_before_creating_files(self):
        for args in (('-m', '-a'), ('-s', '-a', '-o', 'example.jpg'),
                     ('-a', '-o', 'example.jpg'), ('-s', '-m', '-a', '-o', 'example.jpg')):
            with self.subTest(args=args), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(list(args))
                self.assertEqual(2, error.exception.code)
                self.assertFalse(list(Path('.').iterdir()))


if __name__ == '__main__':
    unittest.main()
