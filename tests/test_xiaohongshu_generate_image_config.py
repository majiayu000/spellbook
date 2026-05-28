import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "skills" / "xiaohongshu" / "scripts" / "generate_image.py"
TRACKED_ENV = [
    "ATLAS_API_KEY",
    "LLM_API_KEY",
    "ATLAS_API_BASE",
    "LLM_API_BASE",
    "XHS_ENV_FILE",
]


def load_script_module():
    spec = importlib.util.spec_from_file_location("generate_image_script", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class XiaohongshuGenerateImageConfigTests(unittest.TestCase):
    def setUp(self):
        self.module = load_script_module()
        self.original_env = {name: os.environ.get(name) for name in TRACKED_ENV}
        for name in TRACKED_ENV:
            os.environ.pop(name, None)

    def tearDown(self):
        for name in TRACKED_ENV:
            os.environ.pop(name, None)
            if self.original_env[name] is not None:
                os.environ[name] = self.original_env[name]

    def test_env_vars_are_used_without_env_file(self):
        os.environ["ATLAS_API_KEY"] = "atlas-key"
        os.environ["ATLAS_API_BASE"] = "https://atlas.example/v1"

        self.assertEqual(
            self.module.resolve_config(),
            ("atlas-key", "https://atlas.example/v1"),
        )

    def test_missing_credentials_do_not_read_implicit_env_file(self):
        with self.assertRaises(self.module.ConfigError) as context:
            self.module.resolve_config()

        self.assertIn("--env-file/XHS_ENV_FILE", str(context.exception))

    def test_explicit_env_file_is_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text(
                "LLM_API_KEY='file-key'\n"
                "LLM_API_BASE=https://file.example/v1 # local comment\n",
                encoding="utf-8",
            )

            self.assertEqual(
                self.module.resolve_config(str(env_path)),
                ("file-key", "https://file.example/v1"),
            )

    def test_xhs_env_file_is_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("ATLAS_API_KEY=file-key\n", encoding="utf-8")
            os.environ["XHS_ENV_FILE"] = str(env_path)

            self.assertEqual(
                self.module.resolve_config(),
                ("file-key", self.module.DEFAULT_API_BASE),
            )

    def test_missing_explicit_env_file_fails_loudly(self):
        with self.assertRaises(self.module.ConfigError) as context:
            self.module.resolve_config("/tmp/xhs-missing-env-file")

        self.assertIn("配置文件不存在", str(context.exception))


if __name__ == "__main__":
    unittest.main()
