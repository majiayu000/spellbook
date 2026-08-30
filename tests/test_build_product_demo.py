from __future__ import annotations

import argparse
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest import mock

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "skills" / "build-product-demo" / "scripts"


def _load_script(name: str) -> ModuleType:
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _load_script("validate_demo_plan")
PROBE = _load_script("probe_demo_media")
PACING = _load_script("analyze_demo_pacing")


def _beat(
    beat_id: str,
    start: float,
    end: float,
    *,
    beat_type: str = "normal",
    truth_mode: str = "live",
    surface: str = "native",
    events: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": beat_id,
        "type": beat_type,
        "start_seconds": start,
        "end_seconds": end,
        "claim": "The product changes state.",
        "visible_action": "Show the state changing.",
        "audience_before": f"Before {beat_id}",
        "audience_after": f"After {beat_id}",
        "entry_state": f"Entry {beat_id}",
        "exit_state": f"Exit {beat_id}",
        "narration": "Watch the result.",
        "audio_intent": "Action and narration land together.",
        "truth_mode": truth_mode,
        "surface": surface,
        "events": events
        or [
            {
                "at_seconds": start + 0.5,
                "kind": "product_action",
                "description": "The product responds.",
            }
        ],
        "evidence": [] if beat_type == "title" else ["evidence/result.json"],
        "cut_reason": "The audience is ready for the next proof.",
    }


def _valid_plan() -> dict[str, object]:
    return {
        "schema_version": 2,
        "product": {
            "name": "Example",
            "repository": "https://example.com/repository",
            "revision": "abc123",
        },
        "audience": "Developers",
        "proof_proposition": "The product produces a visible result.",
        "reference_benchmark": "reference/demo.mp4",
        "duration_seconds": 4,
        "max_information_gap_seconds": 5,
        "max_attention_gap_seconds": 5,
        "first_product_action_seconds": 1,
        "native_surface_target_ratio": 1.0,
        "delivery": {
            "width": 1920,
            "height": 1080,
            "fps": 29.97,
            "container": "mp4",
        },
        "truth_boundary": {
            "live": ["real product path"],
            "deterministic": [],
            "composite": [],
            "excluded": [],
        },
        "beats": [_beat("proof", 0, 4)],
    }


def test_validator_requires_integer_schema_version() -> None:
    plan = _valid_plan()
    plan["schema_version"] = 2.0

    errors = VALIDATOR.validate_plan(plan)

    assert "schema_version must be integer 2" in errors


@pytest.mark.parametrize(
    ("path", "bad_value"),
    [
        (("beats", 0, "type"), []),
        (("beats", 0, "truth_mode"), {}),
        (("beats", 0, "surface"), []),
        (("beats", 0, "events", 0, "kind"), {}),
    ],
)
def test_validator_reports_non_string_enums(
    path: tuple[object, ...], bad_value: object
) -> None:
    plan = _valid_plan()
    target: object = plan
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = bad_value  # type: ignore[index]

    errors = VALIDATOR.validate_plan(plan)

    assert any("must be one of" in error for error in errors)


@pytest.mark.parametrize(("field", "value"), [("width", 1920.0), ("height", 1080.5)])
def test_validator_requires_integer_dimensions(field: str, value: float) -> None:
    plan = _valid_plan()
    plan["delivery"][field] = value  # type: ignore[index]

    errors = VALIDATOR.validate_plan(plan)

    assert f"delivery.{field} must be a positive integer" in errors


def test_title_or_composite_events_do_not_satisfy_first_native_product_action() -> None:
    plan = _valid_plan()
    plan["duration_seconds"] = 4
    plan["native_surface_target_ratio"] = 0.75
    plan["beats"] = [
        _beat(
            "title",
            0,
            1,
            beat_type="title",
            truth_mode="title",
            surface="title",
            events=[
                {
                    "at_seconds": 0.2,
                    "kind": "product_action",
                    "description": "A claim card animates.",
                }
            ],
        ),
        _beat(
            "native-proof",
            1,
            4,
            events=[
                {
                    "at_seconds": 2,
                    "kind": "product_action",
                    "description": "The native product responds.",
                }
            ],
        ),
    ]

    errors = VALIDATOR.validate_plan(plan)

    assert any("first product action occurs at 2.000s" in error for error in errors)


def test_declared_native_surface_exception_allows_a_lower_target() -> None:
    plan = _valid_plan()
    plan["native_surface_target_ratio"] = 0.25
    plan["native_surface_exception"] = (
        "The physical installation is the proof surface; native UI appears only for setup."
    )
    plan["beats"] = [
        _beat("native-setup", 0, 1),
        _beat(
            "installation",
            1,
            4,
            truth_mode="composite",
            surface="composite",
            events=[
                {
                    "at_seconds": 2,
                    "kind": "reveal",
                    "description": "The installation changes visibly.",
                }
            ],
        ),
    ]

    assert VALIDATOR.validate_plan(plan) == []


def test_explanatory_surface_limit_requires_a_declared_exception() -> None:
    plan = _valid_plan()
    plan["first_product_action_seconds"] = 3
    plan["native_surface_target_ratio"] = 0.6
    plan["beats"] = [
        _beat(
            "title",
            0,
            1.6,
            beat_type="title",
            truth_mode="title",
            surface="title",
            events=[
                {
                    "at_seconds": 0.5,
                    "kind": "reveal",
                    "description": "A claim card appears.",
                }
            ],
        ),
        _beat("native-proof", 1.6, 4),
    ]

    errors = VALIDATOR.validate_plan(plan)

    assert any("explanatory surface ratio is 0.400" in error for error in errors)


def test_title_beat_cannot_claim_the_native_surface() -> None:
    plan = _valid_plan()
    title = _beat(
        "title",
        0,
        4,
        beat_type="title",
        truth_mode="title",
        surface="native",
        events=[
            {
                "at_seconds": 0.5,
                "kind": "reveal",
                "description": "A title appears.",
            }
        ],
    )
    plan["beats"] = [title]

    errors = VALIDATOR.validate_plan(plan)

    assert "beats[0].surface must be 'title' for a title beat" in errors


def test_title_truth_mode_requires_a_title_beat_and_surface() -> None:
    plan = _valid_plan()
    beat = _beat("fake-native-proof", 0, 4, truth_mode="title", surface="native")
    beat["evidence"] = []
    plan["beats"] = [beat]

    errors = VALIDATOR.validate_plan(plan)

    assert "beats[0].type must be 'title' when truth_mode is 'title'" in errors
    assert "beats[0].surface must be 'title' when truth_mode is 'title'" in errors


def test_plan_validation_report_uses_plan_basename(tmp_path: Path) -> None:
    plan_path = tmp_path / "client-name" / "beat-plan.json"
    plan_path.parent.mkdir()
    plan_path.write_text(json.dumps(_valid_plan()), encoding="utf-8")
    stdout = io.StringIO()
    with (
        mock.patch.object(sys, "argv", ["validate_demo_plan.py", str(plan_path)]),
        mock.patch.object(sys, "stdout", stdout),
    ):
        result = VALIDATOR.main()

    report = json.loads(stdout.getvalue())
    assert result == 0
    assert report["plan"] == "beat-plan.json"


def _probe_args(media: Path, **overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "media": media,
        "expect_width": 1920,
        "expect_height": 1080,
        "expect_fps": 30.0,
        "fps_tolerance": 0.1,
        "expect_duration": 60.0,
        "duration_tolerance": 0.25,
        "min_duration": None,
        "max_duration": None,
        "expect_container": "mp4",
        "expect_video_codec": None,
        "expect_audio_codec": None,
        "require_audio": True,
        "json_out": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _ffprobe_result(*, duration: float = 60.0, container: str = "mov,mp4,m4a,3gp,3g2,mj2") -> subprocess.CompletedProcess[str]:
    payload = {
        "format": {"duration": str(duration), "format_name": container},
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "sample_rate": "48000",
                "channels": 2,
            },
        ],
    }
    return subprocess.CompletedProcess([], 0, json.dumps(payload), "")


def test_probe_checks_declared_duration_and_container_without_exposing_path(
    tmp_path: Path,
) -> None:
    media = tmp_path / "client-name" / "demo.webm"
    media.parent.mkdir()
    media.write_bytes(b"video")
    stdout = io.StringIO()
    with (
        mock.patch.object(PROBE, "parse_cli_args", return_value=_probe_args(media)),
        mock.patch.object(PROBE.shutil, "which", return_value="/usr/bin/ffprobe"),
        mock.patch.object(
            PROBE.subprocess,
            "run",
            return_value=_ffprobe_result(duration=61.0, container="matroska,webm"),
        ),
        mock.patch.object(sys, "stdout", stdout),
    ):
        result = PROBE.main()

    report = json.loads(stdout.getvalue())
    assert result == 1
    assert report["media"] == "demo.webm"
    assert any("container" in error for error in report["errors"])
    assert any("expected 60.000s" in error for error in report["errors"])


def test_probe_parser_accepts_all_plan_delivery_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "probe_demo_media.py",
            "demo.mp4",
            "--expect-fps",
            "30",
            "--expect-duration",
            "60",
            "--expect-container",
            "mp4",
        ],
    )

    args = PROBE.parse_cli_args()

    assert args.expect_duration == 60
    assert args.expect_container == "mp4"


def test_pacing_report_uses_media_basename(tmp_path: Path) -> None:
    media = tmp_path / "client-name" / "demo.mp4"
    media.parent.mkdir()
    media.write_bytes(b"video")
    args = argparse.Namespace(
        media=media,
        silence_noise="-35dB",
        silence_min_duration=0.45,
        freeze_noise="-50dB",
        freeze_min_duration=1.0,
        max_silence_ratio=0.18,
        max_silence_segment=1.75,
        max_low_motion_ratio=0.40,
        max_low_motion_segment=4.0,
        plan=None,
        json_out=None,
    )
    probe_payload = json.dumps(
        {
            "format": {"duration": "60"},
            "streams": [
                {"codec_type": "video", "duration": "60"},
                {"codec_type": "audio", "duration": "60"},
            ],
        }
    )
    stdout = io.StringIO()
    with (
        mock.patch.object(PACING, "parse_args", return_value=args),
        mock.patch.object(PACING.shutil, "which", return_value="/usr/bin/tool"),
        mock.patch.object(PACING, "run", side_effect=[probe_payload, "", ""]),
        mock.patch.object(sys, "stdout", stdout),
    ):
        result = PACING.main()

    report = json.loads(stdout.getvalue())
    assert result == 0
    assert report["media"] == "demo.mp4"


def test_pacing_validates_every_audio_stream_duration(tmp_path: Path) -> None:
    media = tmp_path / "demo.mp4"
    media.write_bytes(b"video")
    args = argparse.Namespace(
        media=media,
        plan=None,
        silence_noise="-35dB",
        silence_min_duration=0.45,
        freeze_noise="-50dB",
        freeze_min_duration=1.0,
        max_silence_ratio=0.18,
        max_silence_segment=1.75,
        max_low_motion_ratio=0.40,
        max_low_motion_segment=4.0,
        json_out=None,
    )
    probe_payload = json.dumps(
        {
            "format": {"duration": "60"},
            "streams": [
                {"index": 0, "codec_type": "video", "duration": "60"},
                {"index": 1, "codec_type": "audio", "duration": "12"},
                {"index": 2, "codec_type": "audio", "duration": "60"},
            ],
        }
    )
    stdout = io.StringIO()
    with (
        mock.patch.object(PACING, "parse_args", return_value=args),
        mock.patch.object(PACING.shutil, "which", return_value="/usr/bin/tool"),
        mock.patch.object(PACING, "run", side_effect=[probe_payload, "", ""]),
        mock.patch.object(sys, "stdout", stdout),
    ):
        result = PACING.main()

    report = json.loads(stdout.getvalue())
    assert result == 1
    assert any("audio stream 1 duration 12.000s" in error for error in report["errors"])


def _freeze_output(*segments: tuple[float, float]) -> str:
    lines: list[str] = []
    for start, end in segments:
        lines.extend(
            [
                f"[freezedetect] lavfi.freezedetect.freeze_start: {start}",
                f"[freezedetect] lavfi.freezedetect.freeze_duration: {end - start}",
                f"[freezedetect] lavfi.freezedetect.freeze_end: {end}",
            ]
        )
    return "\n".join(lines)


def _run_pacing_with_freezes(
    tmp_path: Path, *segments: tuple[float, float]
) -> tuple[int, dict[str, object]]:
    media = tmp_path / "demo.mp4"
    media.write_bytes(b"video")
    plan_path = tmp_path / "beat-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "beats": [
                    {
                        "type": "hold",
                        "start_seconds": 0,
                        "end_seconds": 6,
                        "hold_reason": "The audience needs to read the completed result.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    args = argparse.Namespace(
        media=media,
        plan=plan_path,
        silence_noise="-35dB",
        silence_min_duration=0.45,
        freeze_noise="-50dB",
        freeze_min_duration=1.0,
        max_silence_ratio=0.18,
        max_silence_segment=1.75,
        max_low_motion_ratio=0.40,
        max_low_motion_segment=4.0,
        json_out=None,
    )
    probe_payload = json.dumps(
        {
            "format": {"duration": "60"},
            "streams": [
                {"codec_type": "video", "duration": "60"},
                {"codec_type": "audio", "duration": "60"},
            ],
        }
    )
    stdout = io.StringIO()
    with (
        mock.patch.object(PACING, "parse_args", return_value=args),
        mock.patch.object(PACING.shutil, "which", return_value="/usr/bin/tool"),
        mock.patch.object(
            PACING,
            "run",
            side_effect=[probe_payload, "", _freeze_output(*segments)],
        ),
        mock.patch.object(sys, "stdout", stdout),
    ):
        result = PACING.main()
    return result, json.loads(stdout.getvalue())


def test_declared_hold_exempts_only_its_low_motion_interval(tmp_path: Path) -> None:
    result, report = _run_pacing_with_freezes(tmp_path, (0, 6))

    assert result == 0
    assert report["low_motion"]["exempt_seconds"] == 6


def test_low_motion_outside_declared_hold_still_fails(tmp_path: Path) -> None:
    result, report = _run_pacing_with_freezes(tmp_path, (0, 6), (10, 15))

    assert result == 1
    assert any("longest low-motion span 5.000s" in error for error in report["errors"])


def test_open_ended_low_motion_segment_extends_to_media_end() -> None:
    segments = PACING.timed_segments(
        PACING.FREEZE_START_RE,
        PACING.FREEZE_END_RE,
        PACING.FREEZE_DURATION_RE,
        "lavfi.freezedetect.freeze_start: 1.5",
        10.0,
    )

    assert segments == [(1.5, 10.0, 8.5)]
