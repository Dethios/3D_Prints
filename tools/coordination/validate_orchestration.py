#!/usr/bin/env python3
"""Static Codex role validation and advisory plan assessment.

The built-in model matrix is the 2026-10-27 inspected-client validation baseline. It
is not a claim about live availability. Pass ``--catalog models_cache.json`` to
validate against a currently captured Codex model catalog instead.

This checker reports plan gates. It cannot establish user consent, intercept a
spawn, or prove that native role controls loaded in a running session.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tomllib
from typing import Any


REQUIRED_ROLES = frozenset({
    "latex", "troubleshooter", "print3d", "librarian", "automation",
    "computer_use", "monitor", "explorer", "researcher",
    "strategist", "strategist_max", "implementer",
    "implementer_max", "reviewer",
    "reviewer_architecture", "reviewer_compliance", "reviewer_security",
    "reviewer_critical", "reviewer_max", "adaptive_readonly", "adaptive_worker",
    "strategist_ultra", "implementer_ultra", "reviewer_ultra",
})
ULTRA_ROLES = frozenset({"strategist_ultra", "implementer_ultra", "reviewer_ultra"})
FIXED_ROLES = frozenset({"strategist_max", "implementer_max", "reviewer_max", "reviewer_critical"})
ADAPTIVE_ROLES = REQUIRED_ROLES - ULTRA_ROLES - FIXED_ROLES
ROLE_ALIASES = {
    "implementer_high": "implementer",
    "implementer_critical": "implementer",
    "strategist_deep": "strategist",
    "quick_qa": "explorer",
    "reviewer_correctness": "reviewer",
    "reviewer_regression": "reviewer",
    "reviewer_tests": "reviewer",
}

ASTRA_MODELS = frozenset({"gpt-6-astra", "gpt-6.2-astra"})

BASELINE_MODEL_CATALOG = {
    "gpt-5.6-luna": frozenset({"low", "medium", "high", "xhigh", "max"}),
    "gpt-5.6-terra": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-5.6-sol": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6.2-astra": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6.1-sol": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6-astra": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6.1-terra": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6.2-sol": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6-sol": frozenset({"low", "medium", "high", "xhigh", "max", "ultra"}),
    "gpt-6-luna": frozenset({"low", "medium", "high", "xhigh", "max"}),
}
BASELINE_DEFAULT_EFFORTS = {
    "gpt-5.6-luna": "medium",
    "gpt-5.6-terra": "medium",
    "gpt-5.6-sol": "low",
    "gpt-6.2-astra": "low",
    "gpt-6.1-sol": "low",
    "gpt-6-astra": "medium",
    "gpt-6.2-sol": "low",
    "gpt-6.1-terra": "low",
    "gpt-6-sol": "medium",
    "gpt-6-luna": "medium",
}
PORTABLE_ROLE_FIELDS = (
    "name", "description", "model", "model_reasoning_effort", "service_tier",
    "sandbox_mode", "approval_policy", "developer_instructions", "plugins",
    "mcp_servers", "skills", "agents",
)
PORTABLE_CONFIG_FIELDS = (
    "model", "model_reasoning_effort", "service_tier", "sandbox_mode",
    "approval_policy", "approvals_reviewer", "developer_instructions",
)
PORTABLE_CONFIG_TABLE_FIELDS = {
    "agents": (
        "enabled", "max_concurrent_threads_per_session", "default_subagent_model",
        "default_subagent_reasoning_effort",
    ),
    "features": ("multi_agent_v2",),
}
PORTABLE_SHARED_FILES = (
    "docs/automatic-dispatch.md",
    "docs/recurring-project-contracts.md",
    "skills/native-coordination/references/project-contract-template.md",
    "tests/test_dispatch_policy.py",
    "AGENTS.md",
    "docs/config-ownership.md",
    "skills/README.md",
    "skills/scripts/validate_orchestration.py",
    "skills/scripts/validate-orchestration.ps1",
    "skills/scripts/validate-orchestration.sh",
    "tests/test_orchestration.py",
    "docs/agent-role-migrations.json",
    "docs/native-coordination-2026-10-19.md",
    "docs/routing-update-2026-10-19.md",
    "docs/routing-update-2026-10-27.md",
    "skills/scripts/coordination_ledger.py",
    "skills/native-coordination/SKILL.md",
    "skills/native-coordination/references/operations.md",
    "tests/test_coordination_ledger.py",
    "tests/test_role_consolidation.py",
    "tests/test_routing_flexibility.py",
    "tests/test_terra_routing.py",
)
PLAN_FIELDS = frozenset({
    "workers", "prior_astra_worker_ids", "metadata", "operation_id",
    "approval_confirmed", "user_approved",
})
WORKER_FIELDS = frozenset({
    "id", "parent", "role", "model", "reasoning_effort", "stop_condition",
    "separately_billed", "allowed_children", "max_children", "objective",
    "context", "write_ownership", "authorized_actions", "required_skills",
    "evidence", "validation", "success_criteria", "deliverable",
    "source_boundary", "verification_criteria", "metadata", "user_approved",
    "approval_confirmed",
})


def _append_once(items: list[str], message: str) -> None:
    if message not in items:
        items.append(message)


def _read_toml(path: pathlib.Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_roles(home: pathlib.Path) -> dict[str, dict]:
    """Parse ``home/agents/*.toml`` and index the files by declared role name."""
    home = pathlib.Path(home)
    agents_dir = home / "agents"
    if not agents_dir.is_dir():
        raise ValueError(f"agents directory not found: {agents_dir}")

    roles: dict[str, dict] = {}
    for path in sorted(agents_dir.glob("*.toml")):
        try:
            data = _read_toml(path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ValueError(f"cannot parse role file {path.name}: {exc}") from exc
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"role file {path.name} has no nonempty string name")
        if name in roles:
            raise ValueError(f"duplicate role name {name!r} in {path.name}")
        roles[name] = data
    return roles


def load_model_catalog(path: pathlib.Path) -> tuple[dict[str, frozenset[str]], dict[str, str]]:
    """Read the relevant model/effort facts from a Codex models cache snapshot."""
    try:
        document = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"catalog parse error: {exc}") from exc
    records = document.get("models") if isinstance(document, dict) else None
    if not isinstance(records, list):
        raise ValueError("catalog parse error: top-level 'models' must be a list")

    catalog: dict[str, frozenset[str]] = {}
    defaults: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("slug"), str):
            continue
        slug = record["slug"]
        levels = record.get("supported_reasoning_levels", [])
        efforts = {
            item.get("effort") for item in levels
            if isinstance(item, dict) and isinstance(item.get("effort"), str)
        }
        if efforts:
            catalog[slug] = frozenset(efforts)
        default = record.get("default_reasoning_level")
        if isinstance(default, str):
            defaults[slug] = default
    if not catalog:
        raise ValueError("catalog parse error: no model reasoning levels found")
    return catalog, defaults


def _config_defaults(config: dict[str, Any]) -> dict[str, str]:
    agents = config.get("agents", {})
    if not isinstance(agents, dict):
        return {}
    return {
        "model": agents.get("default_subagent_model"),
        "reasoning_effort": agents.get("default_subagent_reasoning_effort"),
    }


def _model_label(model: Any) -> str:
    labels = {
        "gpt-5.6-luna": "Luna",
        "gpt-5.6-terra": "Terra",
        "gpt-5.6-sol": "Sol",
        "gpt-6-astra": "Astra",
        "gpt-6.2-astra": "GPT-6.2 Astra",
        "gpt-6.1-sol": "GPT-6.1-Sol",
        "gpt-6.2-sol": "GPT-6.2-Sol",
        "gpt-6-sol": "GPT-6-Sol",
        "gpt-6-luna": "GPT-6-Luna",
    }
    return labels.get(model, str(model))


def _validate_pair(
    worker_id: str,
    model: Any,
    effort: Any,
    catalog: dict[str, frozenset[str]],
    errors: list[str],
) -> None:
    known_efforts = set().union(*catalog.values()) if catalog else set()
    if not isinstance(model, str) or model not in catalog:
        _append_once(errors, f"worker {worker_id!r} uses unknown model {model!r}")
    if not isinstance(effort, str) or effort not in known_efforts:
        _append_once(errors, f"worker {worker_id!r} uses unknown reasoning effort {effort!r}")
        if isinstance(model, str) and model in catalog:
            _append_once(
                errors,
                f"worker {worker_id!r}: {_model_label(model)} does not advertise reasoning effort {effort!r}",
            )
        return
    if isinstance(model, str) and model in catalog and effort not in catalog[model]:
        _append_once(
            errors,
            f"worker {worker_id!r}: {_model_label(model)} does not advertise reasoning effort {effort!r}",
        )


def assess_plan(
    plan: dict,
    roles: dict[str, dict],
    defaults: dict,
    catalog: dict[str, frozenset[str]] | None = None,
    advertised_defaults: dict[str, str] | None = None,
) -> dict:
    """Resolve and assess a complete planned operation without granting consent."""
    errors: list[str] = []
    gate_reasons: list[str] = []
    resolved_workers: list[dict] = []
    catalog = catalog or BASELINE_MODEL_CATALOG
    effort_defaults = dict(BASELINE_DEFAULT_EFFORTS)
    if advertised_defaults:
        effort_defaults.update(advertised_defaults)

    if not isinstance(plan, dict):
        plan = {}
        errors.append("plan must be an object")
    else:
        for field in sorted(set(plan) - PLAN_FIELDS):
            errors.append(f"unknown plan field {field!r}")
    if "workers" not in plan:
        errors.append("plan requires a 'workers' list")
    workers = plan.get("workers", [])
    if not isinstance(workers, list):
        workers = []
        errors.append("plan workers must be a list")

    seen_ids: set[str] = set()
    records_by_id: dict[str, dict] = {}
    resolved_by_id: dict[str, dict] = {}

    for position, item in enumerate(workers):
        if not isinstance(item, dict):
            errors.append(f"worker at index {position} must be an object")
            continue
        # This is advisory plan migration, not a native custom-agent alias API.
        # Return canonical role names so the caller dispatches a discoverable role.
        item = dict(item)
        original_role = item.get("role")
        if isinstance(original_role, str):
            item["role"] = ROLE_ALIASES.get(original_role, original_role)
            if item["role"] != original_role:
                metadata = item.get("metadata")
                if metadata is None or isinstance(metadata, dict):
                    item["metadata"] = dict(metadata or {}, legacy_role=original_role)
        if isinstance(item.get("allowed_children"), list):
            item["allowed_children"] = [ROLE_ALIASES.get(name, name) if isinstance(name, str) else name for name in item["allowed_children"]]
        for field in sorted(set(item) - WORKER_FIELDS):
            errors.append(f"worker at index {position} has unknown worker field {field!r}")
        worker_id = item.get("id")
        if not isinstance(worker_id, str) or not worker_id.strip():
            worker_id = f"<index:{position}>"
            errors.append(f"worker at index {position} has no nonempty string id")
        elif worker_id in seen_ids:
            errors.append(f"duplicate worker id {worker_id!r}")
        else:
            seen_ids.add(worker_id)
            records_by_id[worker_id] = item

        parent = item.get("parent")
        if not isinstance(parent, str) or not parent:
            errors.append(f"worker {worker_id!r} parent must be a nonempty string")

        role_name = item.get("role")
        if not isinstance(role_name, str) or not role_name:
            errors.append(f"worker {worker_id!r} role must be a nonempty string")
            role_data = {}
        else:
            role_data = roles.get(role_name)
        if isinstance(role_name, str) and role_data is None:
            errors.append(f"worker {worker_id!r} uses unknown role {role_name!r}")
            role_data = {}

        stop = item.get("stop_condition")
        bounded = isinstance(stop, str) and bool(stop.strip())
        if not bounded:
            errors.append(f"worker {worker_id!r} requires a nonempty stop_condition")

        explicit_model = item.get("model")
        explicit_effort = item.get("reasoning_effort")
        if "model" in item and (not isinstance(explicit_model, str) or not explicit_model):
            errors.append(f"worker {worker_id!r} model must be a nonempty string when supplied")
        if "reasoning_effort" in item and (
            not isinstance(explicit_effort, str) or not explicit_effort
        ):
            errors.append(
                f"worker {worker_id!r} reasoning_effort must be a nonempty string when supplied"
            )
        if not isinstance(explicit_model, str) or not explicit_model:
            explicit_model = None
        if not isinstance(explicit_effort, str) or not explicit_effort:
            explicit_effort = None
        separately_billed = item.get("separately_billed", False)
        if "separately_billed" in item and not isinstance(separately_billed, bool):
            errors.append(f"worker {worker_id!r} separately_billed must be a boolean")
        configured_model = role_data.get("model")
        configured_effort = role_data.get("model_reasoning_effort")

        if isinstance(role_name, str) and role_name in ADAPTIVE_ROLES and not (
            isinstance(explicit_model, str) and isinstance(explicit_effort, str)
        ):
            errors.append(
                f"adaptive worker {worker_id!r} must explicitly supply both model and reasoning_effort"
            )
            model = "gpt-6.2-sol"
            effort = "medium"
            source = "defensive_global_fallback"
        else:
            # Resolve explicit/default values first, then apply role pins.
            # A model-only role pin preserves this previously resolved effort.
            selected_model = explicit_model or defaults.get("model", "gpt-6.2-sol")
            selected_effort = explicit_effort or defaults.get("reasoning_effort")
            if not selected_effort:
                selected_effort = effort_defaults.get(selected_model, "medium")
            model = configured_model or selected_model
            effort = configured_effort or selected_effort
            if configured_model and configured_effort:
                source = "role_fixed_pair"
            elif explicit_model or explicit_effort:
                source = "explicit_spawn_pair"
            else:
                source = "global_default"

        _validate_pair(worker_id, model, effort, catalog, errors)
        resolved = dict(item)
        resolved.update({
            "id": worker_id,
            "role": role_name,
            "model": model,
            "reasoning_effort": effort,
            "resolution_source": source,
        })
        resolved_workers.append(resolved)
        if worker_id not in resolved_by_id:
            resolved_by_id[worker_id] = resolved

        if separately_billed is not False:
            _append_once(
                gate_reasons,
                f"worker {worker_id!r} is marked separately billed and requires user confirmation",
            )
        if model in ASTRA_MODELS:
            if not bounded:
                _append_once(
                    gate_reasons,
                    f"unbounded Astra worker {worker_id!r} requires user confirmation",
                )

        is_ultra = effort == "ultra"
        if is_ultra:
            if not isinstance(explicit_model, str) or not explicit_model:
                errors.append(f"Ultra worker {worker_id!r} requires an explicit model")
            if isinstance(role_name, str) and role_name in ADAPTIVE_ROLES:
                _append_once(errors, f"adaptive leaf {worker_id!r} cannot use Ultra reasoning")
            if model == "gpt-5.6-luna":
                _append_once(errors, f"worker {worker_id!r}: Luna cannot run Ultra")
            allowed = item.get("allowed_children")
            maximum = item.get("max_children")
            if (
                not isinstance(allowed, list)
                or not allowed
                or not all(isinstance(name, str) and name for name in allowed)
            ):
                errors.append(f"Ultra worker {worker_id!r} requires a nonempty allowed_children list of role names")
            else:
                for allowed_name in allowed:
                    allowed_role = roles.get(allowed_name)
                    if allowed_role is None:
                        errors.append(
                            f"Ultra worker {worker_id!r} allowed_children contains unknown role {allowed_name!r}"
                        )
                        continue
                    allowed_enabled = (
                        allowed_role.get("agents", {}).get("enabled")
                        if isinstance(allowed_role.get("agents"), dict)
                        else None
                    )
                    if allowed_enabled is not False or allowed_role.get("model_reasoning_effort") == "ultra":
                        errors.append(
                            f"Ultra worker {worker_id!r} allowed_children role {allowed_name!r} is not a non-delegating leaf"
                        )
                    if (
                        role_data.get("sandbox_mode") == "read-only"
                        and allowed_role.get("sandbox_mode") == "workspace-write"
                    ):
                        errors.append(
                            f"Ultra worker {worker_id!r} allowed_children role {allowed_name!r} would broaden its sandbox"
                        )
            if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
                errors.append(f"Ultra worker {worker_id!r} requires a positive integer max_children")

    has_ultra = any(item.get("reasoning_effort") == "ultra" for item in resolved_workers)
    if has_ultra and "prior_astra_worker_ids" not in plan:
        errors.append("Ultra plans require an explicit prior_astra_worker_ids list")
    prior = plan.get("prior_astra_worker_ids", [])
    astra_worker_ids: list[str] = []
    if not isinstance(prior, list) or not all(isinstance(item, str) and item for item in prior):
        errors.append("prior_astra_worker_ids must be a list of nonempty strings")
        prior = []
    for worker_id in prior:
        if worker_id not in astra_worker_ids:
            astra_worker_ids.append(worker_id)
    for resolved in resolved_workers:
        if resolved["model"] in ASTRA_MODELS and resolved["id"] not in astra_worker_ids:
            astra_worker_ids.append(resolved["id"])

    # Validate the parent graph and the only permitted nesting shape.
    for worker_id, item in records_by_id.items():
        parent = item.get("parent")
        if isinstance(parent, str) and parent != "main" and parent not in records_by_id:
            errors.append(f"worker {worker_id!r} has unknown parent {parent!r}")

    for worker_id in records_by_id:
        chain: list[str] = []
        current = worker_id
        while current != "main" and current in records_by_id:
            if current in chain:
                errors.append(f"parent cycle detected involving worker {current!r}")
                break
            chain.append(current)
            next_parent = records_by_id[current].get("parent")
            if not isinstance(next_parent, str):
                break
            current = next_parent
        if len(chain) > 2:
            errors.append(f"worker {worker_id!r} is a forbidden grandchild; maximum worker depth is two")

    children_by_parent: dict[str, list[str]] = {}
    for worker_id, item in records_by_id.items():
        parent = item.get("parent")
        if isinstance(parent, str) and parent in records_by_id:
            children_by_parent.setdefault(parent, []).append(worker_id)

    for resolved in resolved_workers:
        if (
            resolved.get("reasoning_effort") == "ultra"
            and not children_by_parent.get(resolved.get("id"))
        ):
            errors.append(
                f"Ultra worker {resolved.get('id')!r} requires at least one actual child record"
            )

    for parent_id, child_ids in children_by_parent.items():
        parent_item = records_by_id[parent_id]
        parent_resolved = resolved_by_id.get(parent_id, {})
        parent_role_name = parent_item.get("role")
        parent_role = roles.get(parent_role_name, {}) if isinstance(parent_role_name, str) else {}
        parent_enabled = parent_role.get("agents", {}).get("enabled") is True
        if parent_resolved.get("reasoning_effort") != "ultra" or not parent_enabled:
            errors.append(f"worker {parent_id!r} cannot delegate because it is not an enabled Ultra role")
        allowed = parent_item.get("allowed_children")
        maximum = parent_item.get("max_children")
        if isinstance(maximum, int) and not isinstance(maximum, bool) and len(child_ids) > maximum:
            errors.append(
                f"Ultra worker {parent_id!r} has {len(child_ids)} children, exceeding max_children={maximum}"
            )
        for child_id in child_ids:
            child_item = records_by_id[child_id]
            child_role_name = child_item.get("role")
            if isinstance(allowed, list) and child_role_name not in allowed:
                errors.append(
                    f"child worker {child_id!r} role {child_role_name!r} is not allowed by parent {parent_id!r}"
                )
            child_resolved = resolved_by_id.get(child_id, {})
            child_role = roles.get(child_role_name, {}) if isinstance(child_role_name, str) else {}
            if (
                parent_role.get("sandbox_mode") == "read-only"
                and child_role.get("sandbox_mode") == "workspace-write"
            ):
                errors.append(
                    f"child worker {child_id!r} cannot broaden parent {parent_id!r} sandbox from read-only to workspace-write"
                )
            if (
                child_resolved.get("reasoning_effort") == "ultra"
                or child_role.get("agents", {}).get("enabled") is True
            ):
                errors.append(f"Ultra worker {child_id!r} cannot be a child; children must be non-delegating leaves")

    return {
        "errors": errors,
        "gate_reasons": gate_reasons,
        "resolved_workers": resolved_workers,
        "astra_worker_ids": astra_worker_ids,
    }


def validate_home(
    home: pathlib.Path,
    catalog: dict[str, frozenset[str]] | None = None,
) -> list[str]:
    """Perform static validation of one Codex home."""
    home = pathlib.Path(home)
    errors: list[str] = []
    catalog = catalog or BASELINE_MODEL_CATALOG
    try:
        config = _read_toml(home / "config.toml")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"cannot parse config.toml: {exc}"]
    try:
        roles = load_roles(home)
    except ValueError as exc:
        return [str(exc)]

    missing = sorted(REQUIRED_ROLES - set(roles))
    if missing:
        errors.append("missing required roles: " + ", ".join(missing))

    if config.get("service_tier") not in {"fast", "priority"}:
        errors.append("global Fast service_tier must be 'fast' or its native 'priority' spelling")
    if config.get("sandbox_mode") != "workspace-write":
        errors.append("global sandbox_mode must remain 'workspace-write'")
    if config.get("approval_policy") != "on-request":
        errors.append("global approval_policy must remain 'on-request'")
    if config.get("approvals_reviewer") != "auto_review":
        errors.append("global approvals_reviewer must remain 'auto_review'")
    if config.get("model") != "gpt-6.2-sol":
        errors.append("global main model must be gpt-6.2-sol; saved effort must be supported")
    _validate_pair("main", config.get("model"), config.get("model_reasoning_effort"), catalog, errors)
    features = config.get("features")
    if not isinstance(features, dict) or features.get("multi_agent_v2") is not True:
        errors.append("global features.multi_agent_v2 must be true for the V2 routing plan")

    agents = config.get("agents")
    if not isinstance(agents, dict):
        agents = {}
        errors.append("global [agents] table is required")
    if agents.get("enabled") is not True:
        errors.append("global agents.enabled must be true")
    if agents.get("max_concurrent_threads_per_session") != 8:
        errors.append("global agents.max_concurrent_threads_per_session must be 8")
    defaults = _config_defaults(config)
    if defaults != {"model": "gpt-6.2-sol", "reasoning_effort": "medium"}:
        errors.append("global Sol/Medium worker defaults are required")

    for name, data in sorted(roles.items()):
        if name in REQUIRED_ROLES:
            if not isinstance(data.get("description"), str) or not data["description"].strip():
                errors.append(f"required role {name!r} must define a nonempty description")
            instructions = data.get("developer_instructions")
            if not isinstance(instructions, str) or not instructions.strip():
                errors.append(
                    f"required role {name!r} must define nonempty developer_instructions"
                )
        if data.get("service_tier") != "fast":
            errors.append(f"role {name!r} must retain Fast service_tier")
        if data.get("sandbox_mode") not in {"read-only", "workspace-write"}:
            errors.append(f"role {name!r} must declare a safe sandbox_mode")
        if data.get("approval_policy") != "never":
            errors.append(f"role {name!r} approval_policy must be 'never'")
        enabled = data.get("agents", {}).get("enabled") if isinstance(data.get("agents"), dict) else None
        if not isinstance(enabled, bool):
            errors.append(f"role {name!r} agents.enabled must be a boolean")
        if name in ULTRA_ROLES and enabled is not True:
            errors.append(f"Ultra role {name!r} must set agents.enabled=true")
        if name in REQUIRED_ROLES - ULTRA_ROLES and enabled is not False:
            errors.append(f"leaf role {name!r} must set agents.enabled=false")

        model = data.get("model")
        effort = data.get("model_reasoning_effort")
        if name in ADAPTIVE_ROLES:
            if model is not None or effort is not None:
                errors.append(f"adaptive role {name!r} must omit fixed model and effort")
        elif name in ULTRA_ROLES:
            if model is not None or effort != "ultra":
                errors.append(f"Ultra role {name!r} must omit model and fix effort to 'ultra'")
        elif name in REQUIRED_ROLES and (not isinstance(model, str) or not isinstance(effort, str)):
            errors.append(f"fixed role {name!r} must define model and effort")

        if model is not None and effort is not None:
            _validate_pair(name, model, effort, catalog, errors)

    return errors


def compare_homes(home: pathlib.Path, peer: pathlib.Path) -> list[str]:
    """Compare portable configuration and instruction facts across two Codex homes."""
    try:
        left = load_roles(home)
        right = load_roles(peer)
    except ValueError as exc:
        return [str(exc)]
    errors: list[str] = []
    try:
        left_config = _read_toml(pathlib.Path(home) / "config.toml")
        right_config = _read_toml(pathlib.Path(peer) / "config.toml")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"cannot parse config.toml for portable comparison: {exc}"]
    left_portable_config = {key: left_config.get(key) for key in PORTABLE_CONFIG_FIELDS}
    right_portable_config = {key: right_config.get(key) for key in PORTABLE_CONFIG_FIELDS}
    for table, fields in PORTABLE_CONFIG_TABLE_FIELDS.items():
        left_table = left_config.get(table) if isinstance(left_config.get(table), dict) else {}
        right_table = right_config.get(table) if isinstance(right_config.get(table), dict) else {}
        left_portable_config[table] = {key: left_table.get(key) for key in fields}
        right_portable_config[table] = {key: right_table.get(key) for key in fields}
    if left_portable_config != right_portable_config:
        errors.append("portable global config mismatch between home and peer")
    if set(left) != set(right):
        errors.append(
            "portable role-name mismatch: "
            f"only in home={sorted(set(left) - set(right))}; "
            f"only in peer={sorted(set(right) - set(left))}"
        )
    for name in sorted(set(left) & set(right)):
        left_portable = {key: left[name].get(key) for key in PORTABLE_ROLE_FIELDS}
        right_portable = {key: right[name].get(key) for key in PORTABLE_ROLE_FIELDS}
        if left_portable != right_portable:
            errors.append(f"role {name!r} portable mismatch between home and peer")
    for relative_path in PORTABLE_SHARED_FILES:
        left_path = pathlib.Path(home) / relative_path
        right_path = pathlib.Path(peer) / relative_path
        if not left_path.exists() and not right_path.exists():
            continue
        try:
            left_content = left_path.read_bytes() if left_path.exists() else None
            right_content = right_path.read_bytes() if right_path.exists() else None
        except OSError as exc:
            errors.append(f"cannot read portable shared file {relative_path}: {exc}")
            continue
        if left_content != right_content:
            errors.append(f"portable shared file mismatch for {relative_path}")
    return errors


def _load_plan(path: pathlib.Path) -> dict:
    try:
        if path.suffix.lower() == ".toml":
            return _read_toml(path)
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"plan parse error: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=pathlib.Path)
    parser.add_argument("--peer", type=pathlib.Path)
    parser.add_argument("--plan", type=pathlib.Path)
    parser.add_argument("--catalog", type=pathlib.Path)
    args = parser.parse_args(argv)

    catalog = BASELINE_MODEL_CATALOG
    advertised_defaults = BASELINE_DEFAULT_EFFORTS
    catalog_source = "inspected baseline updated 2026-11-17 (not live availability)"
    report: dict[str, Any] = {
        "checker_scope": "static configuration and advisory plan checks; not native runtime enforcement",
        "catalog_source": catalog_source,
        "configuration_errors": [],
    }
    try:
        if args.catalog:
            catalog, advertised_defaults = load_model_catalog(args.catalog)
            report["catalog_source"] = str(args.catalog)
        report["configuration_errors"].extend(validate_home(args.home, catalog))
        if args.peer:
            report["configuration_errors"].extend(validate_home(args.peer, catalog))
            report["configuration_errors"].extend(compare_homes(args.home, args.peer))
        if args.plan:
            plan = _load_plan(args.plan)
            roles = load_roles(args.home)
            config = _read_toml(args.home / "config.toml")
            report["plan_assessment"] = assess_plan(
                plan, roles, _config_defaults(config), catalog, advertised_defaults
            )
    except (ValueError, OSError, tomllib.TOMLDecodeError) as exc:
        report["configuration_errors"].append(str(exc))

    print(json.dumps(report, indent=2, sort_keys=True))
    if report["configuration_errors"]:
        return 1
    assessment = report.get("plan_assessment", {})
    if assessment.get("errors"):
        return 1
    if assessment.get("gate_reasons"):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
