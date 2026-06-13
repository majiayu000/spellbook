import importlib.util
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SKILL_CREATOR_ROOT = ROOT / "skills" / "skill-creator"
RUN_EVAL_SCRIPT = SKILL_CREATOR_ROOT / "scripts" / "run_eval.py"


def load_run_eval():
    sys.path.insert(0, str(SKILL_CREATOR_ROOT))
    previous_scripts = sys.modules.pop("scripts", None)
    package = types.ModuleType("scripts")
    package.__path__ = [str(SKILL_CREATOR_ROOT / "scripts")]
    sys.modules["scripts"] = package
    try:
        spec = importlib.util.spec_from_file_location("skill_creator_run_eval_test", RUN_EVAL_SCRIPT)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SKILL_CREATOR_ROOT))
        sys.modules.pop("skill_creator_run_eval_test", None)
        sys.modules.pop("scripts", None)
        if previous_scripts is not None:
            sys.modules["scripts"] = previous_scripts


run_eval = load_run_eval()


class RunEvalPathSafetyTests(unittest.TestCase):
    def test_run_single_query_rejects_unsafe_skill_name_before_writing_command(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".claude" / "commands").mkdir(parents=True)

            with self.assertRaises(ValueError):
                run_eval.run_single_query(
                    query="use the skill",
                    skill_name="../../pwned",
                    skill_description="Unsafe name should be rejected.",
                    timeout=1,
                    project_root=str(root),
                )

            self.assertEqual(list((root / ".claude" / "commands").iterdir()), [])
            self.assertFalse(any(path.name.startswith("pwned") for path in root.iterdir()))


if __name__ == "__main__":
    unittest.main()
