import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from graphviz_mindmaps.commands import target_make


class TargetMakeTests(unittest.TestCase):
    def run_in_project(self, argv):
        with tempfile.TemporaryDirectory() as tempdir:
            with open(os.path.join(tempdir, "justfile"), "w") as justfile:
                justfile.write("mindmap-01.otl\n")

            with mock.patch.object(target_make.Path, "cwd", return_value=target_make.Path(tempdir)):
                with mock.patch.object(
                    target_make.subprocess,
                    "run",
                    return_value=SimpleNamespace(returncode=0),
                ) as run:
                    return_code = target_make.main(argv)

        return return_code, run

    def test_justfile_uses_build_by_default(self):
        return_code, run = self.run_in_project(["mindmap-01.otl"])

        self.assertEqual(0, return_code)
        run.assert_called_once_with(
            ["just", "-f", mock.ANY, "build", "mindmap-01.otl"]
        )
        self.assertEqual("justfile", target_make.Path(run.call_args.args[0][2]).name)

    def test_p_uses_buildpreview(self):
        return_code, run = self.run_in_project(["mindmap-01.otl", "p"])

        self.assertEqual(0, return_code)
        self.assertEqual("buildpreview", run.call_args.args[0][3])
        self.assertEqual("mindmap-01.otl", run.call_args.args[0][4])

    def test_rejects_unknown_second_argument(self):
        with mock.patch.object(target_make.subprocess, "run") as run:
            return_code = target_make.main(["mindmap-01.otl", "x"])

        self.assertEqual(2, return_code)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
