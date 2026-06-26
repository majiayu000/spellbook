"""Schema, redaction, and validation helpers for threads run logs."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
)
MAX_STRING_LENGTH = 4000
MAX_INPUT_BYTES = 64 * 1024
MAX_DEPTH = 8
MAX_ARRAY_ITEMS = 100
ALLOWED_MODES = {
    "single_agent",
    "plan_only",
    "execute_direct",
    "review_only",
    "research_spec",
    "clarify_first",
}
ALLOWED_TRUTH_LEVELS = {"A", "B", "C", "D"}
ALLOWED_FALLBACK_MODES = {"none", "single_agent", "prompt_pack_only"}
ALLOWED_NATIVE_SUBAGENTS = {"available", "unavailable"}
ALLOWED_SPAWN_REQUIREMENTS = {"required", "optional", "unavailable"}
ALLOWED_DATA_COLLECTION = {"final_report", "local_jsonl", "none"}
ALLOWED_OUTCOMES = {"success", "partial", "blocked", "failed"}
ALLOWED_REMOTE_REFRESH_OWNERS = {"coordinator", "verification_owner"}
ALLOWED_REMOTE_REFRESH_POLICIES = {"continue", "rebase", "required_stop"}
ALLOWED_PR_CLASSIFICATIONS = {
    "merge_ready",
    "review_thread_blocked",
    "ci_failed",
    "conflict_blocked",
    "stale_or_superseded",
    "needs_human_decision",
}
ALLOWED_ISSUE_TO_PR_STATUSES = {
    "covered",
    "uncovered",
    "stale_or_superseded",
    "needs_human_decision",
}
ALLOWED_LANE_ROLES = {
    "planner",
    "worker",
    "reviewer",
    "merge_reviewer",
    "researcher",
    "fix_worker",
    "closure_auditor",
}
ALLOWED_VERIFICATION_SCOPES = {"inspection_only", "targeted", "full_local", "ci_only"}
ALLOWED_NATIVE_SPAWN_TOOLS = {"multi_agent_v1.spawn_agent"}
ALLOWED_CONNECTOR_REVIEW_STATUSES = {
    "completed",
    "no_connector_expected",
    "pending",
    "unknown",
}
ALLOWED_REVIEW_LOOP_OUTCOMES = {"resolved", "review_loop", "not_applicable"}
INVALID_AGENT_IDS = {"", "none", "n/a", "na", "null", "main", "main_thread", "coordinator"}
ALLOWED_SINGLE_AGENT_REASONS = {
    "no_independent_lanes",
    "sequential_dependency",
    "shared_writable_files",
    "tool_unavailable",
    "user_requested_single_agent",
}
ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "recorded_at_utc",
    "skill",
    "skill_source",
    "active_skill_source",
    "mode",
    "repo",
    "base_ref",
    "trigger_summary",
    "goal",
    "non_goals",
    "intent_contract",
    "merge_policy",
    "data_collection",
    "truth_level",
    "native_subagents",
    "explicit_thread_request",
    "spawn_requirement",
    "native_thread_evidence",
    "fallback_mode",
    "no_spawn_reason",
    "single_agent_justification",
    "capability_gate",
    "thread_dispatch_gate",
    "queue_gate",
    "queue_bounds",
    "remote_refresh",
    "queue_ledger",
    "lane_map",
    "lanes_total",
    "lanes",
    "failure_codes",
    "remote_truth",
    "remote_closure",
    "connector_review",
    "closure_audit",
    "local_state",
    "ci_wait",
    "review_loop",
    "run_log",
    "exclusive_verification",
    "verification",
    "outcome",
    "notes",
}
ALLOWED_FAILURE_CODES = {
    "trigger_too_broad",
    "missing_intent_contract",
    "durable_log_skipped",
    "truth_level_too_low",
    "source_drift",
    "active_skill_source_unknown",
    "stale_remote_state",
    "stale_base",
    "duplicate_work_missed",
    "contributor_pr_replaced_unnecessarily",
    "role_drift",
    "write_scope_violation",
    "vague_lane_output",
    "verification_gap",
    "review_thread_missed",
    "connector_review_incomplete",
    "review_loop",
    "native_thread_not_spawned",
    "waiting_ci",
    "merge_gate_bypass",
    "tool_unavailable",
    "environment_mismatch",
    "context_loss",
    "user_interrupt",
}
SENSITIVE_ENV_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b([A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)"
    r"\s*=\s*([^\s,;]+)"
)

SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def redact_string(value: str) -> str:
    redacted = SENSITIVE_ENV_ASSIGNMENT_PATTERN.sub(r"\1=[REDACTED]", value)
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    if len(redacted) > MAX_STRING_LENGTH:
        return redacted[:MAX_STRING_LENGTH] + "...[TRUNCATED]"
    return redacted


def redact(value: Any, key_hint: str = "", depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return "[TRUNCATED_DEPTH]"
    lower_key = key_hint.lower()
    if any(part in lower_key for part in SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(key): redact(item, str(key), depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, key_hint, depth + 1) for item in value[:MAX_ARRAY_ITEMS]]
    if isinstance(value, str):
        return redact_string(value)
    return value


def normalize_record(raw: Any, allow_extra: bool = False) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("run log input must be a JSON object")
    unknown_fields = sorted(set(raw) - ALLOWED_TOP_LEVEL_FIELDS)
    if unknown_fields and not allow_extra:
        raise ValueError("unknown top-level field(s): " + ", ".join(unknown_fields))

    record = redact(raw)
    mode = record.get("mode")
    if mode is not None and mode not in ALLOWED_MODES:
        raise ValueError(f"unknown mode: {mode}")
    truth_level = record.get("truth_level")
    if truth_level is not None and truth_level not in ALLOWED_TRUTH_LEVELS:
        raise ValueError(f"unknown truth_level: {truth_level}")
    validate_enum_fields(record)
    validate_native_thread_evidence(record)

    record.setdefault("schema_version", 1)
    record["recorded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return record


def validate_enum(value: Any, allowed: set[str], field: str) -> None:
    if value is not None and value not in allowed:
        raise ValueError(f"unknown {field}: {value}")


def require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def validate_bool(value: Any, field: str) -> None:
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")


def validate_non_negative_int(value: Any, field: str) -> None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
        raise ValueError(f"{field} must be a non-negative integer")


def validate_non_negative_number(value: Any, field: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"{field} must be a non-negative number")


def validate_failure_codes(record: dict[str, Any]) -> None:
    failure_codes = record.get("failure_codes")
    if failure_codes is None:
        return
    require_list(failure_codes, "failure_codes")
    unknown = sorted(
        code
        for code in failure_codes
        if not isinstance(code, str) or code not in ALLOWED_FAILURE_CODES
    )
    if unknown:
        raise ValueError("unknown failure_codes: " + ", ".join(map(str, unknown)))


def validate_lane_entries(lanes: Any, field: str) -> None:
    for lane in require_list(lanes, field):
        lane_object = require_object(lane, f"{field} entries")
        validate_enum(lane_object.get("role"), ALLOWED_LANE_ROLES, f"{field}.role")
        validate_enum(
            lane_object.get("verification_scope"),
            ALLOWED_VERIFICATION_SCOPES,
            f"{field}.verification_scope",
        )


def validate_lanes(record: dict[str, Any]) -> None:
    lanes = record.get("lanes")
    if lanes is not None:
        validate_lane_entries(lanes, "lanes")


def validate_enum_fields(record: dict[str, Any]) -> None:
    validate_enum(nested_get(record, "native_subagents"), ALLOWED_NATIVE_SUBAGENTS, "native_subagents")
    validate_enum(
        nested_get(record, "spawn_requirement"),
        ALLOWED_SPAWN_REQUIREMENTS,
        "spawn_requirement",
    )
    validate_enum(record.get("data_collection"), ALLOWED_DATA_COLLECTION, "data_collection")
    intent_contract = record.get("intent_contract")
    if isinstance(intent_contract, dict):
        validate_enum(
            intent_contract.get("data_collection"),
            ALLOWED_DATA_COLLECTION,
            "intent_contract.data_collection",
        )
    validate_enum(record.get("outcome"), ALLOWED_OUTCOMES, "outcome")
    validate_queue_gate(record)
    validate_queue_ledger(record)
    validate_lane_map(record)
    validate_remote_closure(record)
    validate_connector_review(record)
    validate_ci_wait(record)
    validate_review_loop(record)
    validate_failure_codes(record)
    validate_lanes(record)


def remote_refresh_contract(record: dict[str, Any]) -> dict[str, Any] | None:
    remote_refresh = record.get("remote_refresh")
    if isinstance(remote_refresh, dict):
        return remote_refresh
    queue_gate = record.get("queue_gate")
    if isinstance(queue_gate, dict):
        nested = queue_gate.get("remote_refresh")
        if isinstance(nested, dict):
            return nested
    return None


def validate_queue_gate(record: dict[str, Any]) -> None:
    queue_gate = record.get("queue_gate")
    if queue_gate is None:
        return
    require_object(queue_gate, "queue_gate")

    queue_truth_level = queue_gate.get("truth_level")
    validate_enum(queue_truth_level, ALLOWED_TRUTH_LEVELS, "queue_gate.truth_level")
    top_truth_level = record.get("truth_level")
    if (
        top_truth_level is not None
        and queue_truth_level is not None
        and top_truth_level != queue_truth_level
    ):
        raise ValueError("conflicting truth_level values across top-level and queue_gate")

    remote_refresh = remote_refresh_contract(record)
    if remote_refresh is None:
        raise ValueError("remote_refresh is required when queue_gate is present")
    for field in ("owner_lane", "policy", "origin_main_sha", "local_base_sha", "stale_base"):
        if field not in remote_refresh:
            raise ValueError(f"remote_refresh.{field} is required when queue_gate is present")
    validate_enum(
        remote_refresh.get("owner_lane"),
        ALLOWED_REMOTE_REFRESH_OWNERS,
        "remote_refresh.owner_lane",
    )
    validate_enum(
        remote_refresh.get("policy"),
        ALLOWED_REMOTE_REFRESH_POLICIES,
        "remote_refresh.policy",
    )
    validate_bool(remote_refresh.get("stale_base"), "remote_refresh.stale_base")

    pr_classification = queue_gate.get("pr_classification", [])
    if pr_classification is not None:
        validate_pr_classification(pr_classification)
    validate_issue_to_pr_map(queue_gate.get("issue_to_pr_map"))
    for field in ("open_prs", "open_issues"):
        if field in queue_gate:
            require_list(queue_gate[field], f"queue_gate.{field}")


def validate_pr_classification(pr_classification: Any) -> None:
    for item in require_list(pr_classification, "queue_gate.pr_classification"):
        entry = require_object(item, "queue_gate.pr_classification entries")
        validate_enum(
            entry.get("classification"),
            ALLOWED_PR_CLASSIFICATIONS,
            "queue_gate.pr_classification.classification",
        )


def validate_issue_to_pr_map(issue_to_pr_map: Any) -> None:
    if issue_to_pr_map is None:
        return
    for item in require_list(issue_to_pr_map, "queue_gate.issue_to_pr_map"):
        entry = require_object(item, "queue_gate.issue_to_pr_map entries")
        if "issue" not in entry:
            raise ValueError("queue_gate.issue_to_pr_map.issue is required")
        if "status" not in entry:
            raise ValueError("queue_gate.issue_to_pr_map.status is required")
        validate_enum(
            entry.get("status"),
            ALLOWED_ISSUE_TO_PR_STATUSES,
            "queue_gate.issue_to_pr_map.status",
        )


def validate_queue_ledger(record: dict[str, Any]) -> None:
    queue_ledger = record.get("queue_ledger")
    if queue_ledger is None:
        return
    ledger = require_object(queue_ledger, "queue_ledger")
    for field in ("items_total", "items_closed", "items_deferred"):
        validate_non_negative_int(ledger.get(field), f"queue_ledger.{field}")
    validate_bool(ledger.get("stale_base"), "queue_ledger.stale_base")
    if "superseded_items" in ledger:
        require_list(ledger["superseded_items"], "queue_ledger.superseded_items")
    if "items" in ledger:
        for item in require_list(ledger["items"], "queue_ledger.items"):
            require_object(item, "queue_ledger.items entries")


def validate_lane_map(record: dict[str, Any]) -> None:
    lane_map = record.get("lane_map")
    if lane_map is None:
        return
    lane_map_object = require_object(lane_map, "lane_map")
    if "lanes" in lane_map_object:
        validate_lane_entries(lane_map_object["lanes"], "lane_map.lanes")


def validate_remote_closure(record: dict[str, Any]) -> None:
    remote_closure = record.get("remote_closure")
    if remote_closure is None:
        return
    closure = require_object(remote_closure, "remote_closure")
    validate_bool(closure.get("checked"), "remote_closure.checked")
    for field in ("open_prs", "open_issues", "unresolved_review_threads"):
        validate_non_negative_int(closure.get(field), f"remote_closure.{field}")


def validate_connector_review(record: dict[str, Any]) -> None:
    connector_review = record.get("connector_review")
    if connector_review is None:
        return
    review = require_object(connector_review, "connector_review")
    validate_bool(review.get("expected"), "connector_review.expected")
    validate_enum(
        review.get("status"),
        ALLOWED_CONNECTOR_REVIEW_STATUSES,
        "connector_review.status",
    )
    if "head_sha" in review and not isinstance(review["head_sha"], str):
        raise ValueError("connector_review.head_sha must be a string")


def validate_ci_wait(record: dict[str, Any]) -> None:
    ci_wait = record.get("ci_wait")
    if ci_wait is None:
        return
    wait = require_object(ci_wait, "ci_wait")
    validate_non_negative_number(wait.get("duration_seconds"), "ci_wait.duration_seconds")
    validate_bool(wait.get("budget_exhausted"), "ci_wait.budget_exhausted")
    if "pending_checks" in wait:
        require_list(wait["pending_checks"], "ci_wait.pending_checks")


def validate_review_loop(record: dict[str, Any]) -> None:
    review_loop = record.get("review_loop")
    if review_loop is None:
        return
    loop = require_object(review_loop, "review_loop")
    validate_non_negative_int(loop.get("cycles"), "review_loop.cycles")
    validate_enum(loop.get("outcome"), ALLOWED_REVIEW_LOOP_OUTCOMES, "review_loop.outcome")


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "true", "1", "required"}
    return False


def canonical_gate_value(field: str, value: Any) -> Any:
    if field == "explicit_thread_request":
        return truthy(value)
    return value


def nested_get(mapping: dict[str, Any], field: str) -> Any:
    values: list[tuple[str, Any]] = []
    if field in mapping:
        values.append(("top-level", mapping.get(field)))
    for container in ("capability_gate", "thread_dispatch_gate"):
        nested = mapping.get(container)
        if isinstance(nested, dict) and field in nested:
            values.append((container, nested.get(field)))

    present = [(source, value) for source, value in values if value is not None]
    if not present:
        return None
    canonical_values = {
        canonical_gate_value(field, value)
        for _, value in present
    }
    if len(canonical_values) > 1:
        sources = ", ".join(source for source, _ in present)
        raise ValueError(f"conflicting {field} values across {sources}")
    return present[0][1]


def native_thread_evidence(record: dict[str, Any]) -> dict[str, Any] | None:
    evidence = record.get("native_thread_evidence")
    if isinstance(evidence, dict):
        return evidence
    dispatch_gate = record.get("thread_dispatch_gate")
    if isinstance(dispatch_gate, dict):
        nested = dispatch_gate.get("native_thread_evidence")
        if isinstance(nested, dict):
            return nested
    return None


def thread_dispatch_gate(record: dict[str, Any]) -> dict[str, Any] | None:
    gate = record.get("thread_dispatch_gate")
    return gate if isinstance(gate, dict) else None


def valid_agent_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().lower() not in INVALID_AGENT_IDS


def valid_spawned_agents(record: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = native_thread_evidence(record)
    if evidence is None:
        return []
    spawned_agents = evidence.get("spawned_agents")
    if not isinstance(spawned_agents, list):
        return []
    valid_agents = []
    for agent in spawned_agents:
        if not isinstance(agent, dict):
            continue
        agent_id = agent.get("agent_id_or_thread_id") or agent.get("tool_agent_id")
        if (
            agent.get("spawn_tool") in ALLOWED_NATIVE_SPAWN_TOOLS
            and valid_agent_id(agent_id)
            and agent.get("result_collected") is True
            and bool(agent.get("wait_evidence"))
            and bool(agent.get("close_evidence"))
        ):
            valid_agents.append(agent)
    return valid_agents


def has_spawned_agent(record: dict[str, Any]) -> bool:
    return bool(valid_spawned_agents(record))


def normalize_reason(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or None


def allowed_reason(reason: Any, evidence: Any = None) -> bool:
    normalized = normalize_reason(reason)
    if normalized not in ALLOWED_SINGLE_AGENT_REASONS:
        return False
    return evidence is None or bool(evidence)


def has_single_agent_reason(record: dict[str, Any]) -> bool:
    no_spawn_reason = record.get("no_spawn_reason")
    if isinstance(no_spawn_reason, dict):
        if allowed_reason(no_spawn_reason.get("reason"), no_spawn_reason.get("evidence")):
            return True
    elif allowed_reason(no_spawn_reason):
        return True

    gate = thread_dispatch_gate(record)
    if gate is not None:
        gate_reason = gate.get("no_spawn_reason")
        if isinstance(gate_reason, dict):
            if allowed_reason(gate_reason.get("reason"), gate_reason.get("evidence")):
                return True
        elif allowed_reason(gate_reason):
            return True

    justification = record.get("single_agent_justification")
    if (
        isinstance(justification, dict)
        and allowed_reason(justification.get("reason"), justification.get("evidence"))
    ):
        return True

    evidence = native_thread_evidence(record)
    if not isinstance(evidence, dict):
        return False
    return allowed_reason(evidence.get("fallback_reason"))


def lane_has_no_spawn_reason(lane: dict[str, Any]) -> bool:
    reason = lane.get("no_spawn_reason")
    if isinstance(reason, dict):
        return allowed_reason(reason.get("reason"), reason.get("evidence"))
    return allowed_reason(reason)


def validate_planned_native_threads(record: dict[str, Any]) -> None:
    gate = thread_dispatch_gate(record)
    if gate is None:
        return
    planned_threads = gate.get("planned_native_threads")
    if planned_threads is None:
        return
    if not isinstance(planned_threads, list):
        raise ValueError("thread_dispatch_gate.planned_native_threads must be a list")

    spawned_lane_ids = {
        agent.get("lane_id")
        for agent in valid_spawned_agents(record)
        if isinstance(agent.get("lane_id"), str) and agent.get("lane_id")
    }
    missing_reasons = []
    for lane in planned_threads:
        if not isinstance(lane, dict):
            raise ValueError("thread_dispatch_gate.planned_native_threads entries must be objects")
        lane_id = lane.get("id") or lane.get("lane_id")
        if not lane_id:
            raise ValueError("thread_dispatch_gate.planned_native_threads entries require id")
        if lane_id in spawned_lane_ids:
            continue
        if lane_has_no_spawn_reason(lane):
            continue
        missing_reasons.append(str(lane_id))

    if missing_reasons:
        raise ValueError(
            "thread_dispatch_gate.planned_native_threads missing spawned evidence "
            "or no_spawn_reason for lane(s): " + ", ".join(missing_reasons)
        )


def validate_native_thread_evidence(record: dict[str, Any]) -> None:
    mode = record.get("mode")
    native_subagents = nested_get(record, "native_subagents")
    fallback_mode = nested_get(record, "fallback_mode")
    explicit_request = nested_get(record, "explicit_thread_request")
    spawn_requirement = nested_get(record, "spawn_requirement")
    dispatch_mode = mode in {
        "single_agent",
        "plan_only",
        "execute_direct",
        "review_only",
        "research_spec",
    }
    required = truthy(explicit_request) or spawn_requirement == "required"

    if fallback_mode is not None and fallback_mode not in ALLOWED_FALLBACK_MODES:
        raise ValueError(f"unknown fallback_mode: {fallback_mode}")

    explicit_native_required = dispatch_mode and native_subagents == "available" and required

    if explicit_native_required and fallback_mode is None:
        raise ValueError(
            "fallback_mode is required when native subagents are available "
            "for an explicit threads run"
        )

    if (
        explicit_native_required
        and fallback_mode == "none"
        and not has_spawned_agent(record)
    ):
        raise ValueError(
            "native_thread_evidence.spawned_agents is required when native "
            "subagents are available for an explicit threads run"
        )

    if (
        explicit_native_required
        and fallback_mode == "single_agent"
        and not has_single_agent_reason(record)
    ):
        raise ValueError(
            "single_agent fallback for an explicit threads run requires "
            "an allowed no_spawn_reason or single_agent_justification.reason"
        )

    if explicit_native_required and fallback_mode == "prompt_pack_only":
        raise ValueError(
            "prompt_pack_only fallback is invalid when native subagents are "
            "available for an explicit threads run"
        )

    if explicit_native_required and fallback_mode == "none":
        validate_planned_native_threads(record)
