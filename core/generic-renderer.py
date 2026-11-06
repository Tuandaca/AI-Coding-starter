"""
Generic Renderer for AI-Coding-starter V2 Milestone M5.

Purpose
-------
Render declarative, runtime-specific project files from canonical state
(``.ai-coding-starter/project.yaml``, ``state.yaml``, ``resources.lock``)
using runtime adapters authored as JSON documents with a ``.yaml``
extension. The direction is strictly one-way:

    canonical YAML/lock  ->  generic renderer  ->  declarative adapter  ->  project-local runtime output

Canonical files are read-only: they are never written, updated, or removed
as a side effect of rendering, install, switch, or uninstall. Runtime
output is derived, reversible, project-local, and non-authoritative.

Design principles
-----------------
* Runtime-agnostic. There are no vendor branches
  (no ``if runtime == "codex"`` style logic). All behavior is driven by
  adapter metadata: ``render.outputs``, ``install.paths``,
  ``uninstall.owned_files`` / ``uninstall.owned_dirs``,
  ``permission_policy``, ``detection``, and ``instruction_source``.
* Fail-open. A missing or malformed adapter, an absent runtime, or an
  unsupported render target returns an error result; the canonical project
  stays valid and readable and no exception propagates to corrupt state.
* Path safety. Output paths must not be absolute, contain ``..`` segments,
  use drive letters, or escape the project root through symlinks
  (``UnsafePathError``); nothing is written outside the project root.
* Ownership tracking. Every generated file (when ``mark_owned``) is
  prepended with ``<!-- ai-coding-starter runtime adapter: <id> |
  generated | owned -->`` and recorded in
  ``.ai-coding-starter/.runtime-manifest.json`` so uninstall removes only
  adapter-owned files. Adapters whose ``instruction_source`` has
  ``ownership: shared`` consume an existing shared derived file (e.g. the
  M4 root ``AGENTS.md``) and declare no owned ``render.outputs``; they are
  never marked as owners and uninstall never touches the shared file.
* Explicit selection. render/install/uninstall/switch require an explicit
  runtime_id. Detection inspects the environment only and never installs or
  writes anything.
* No global configuration writes. Generated content is also scanned for
  dangerous permission flags
  (``--dangerously-skip-permissions``, ``--dangerously-bypass-approvals-and-sandbox``,
  ``--yolo``); if found the file is rejected and not written.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.domain.contracts import (
    SchemaValidationError,
    ValidationResult,
    is_valid_id,
)
from core.spec import (
    CANONICAL_STATE_DIR,
    PROJECT_YAML,
    read_project_spec,
)
from core.state import (
    RESOURCES_LOCK,
    STATE_YAML,
    read_resources_lock,
    read_state,
)


MARKER_FORMAT = "<!-- ai-coding-starter runtime adapter: {runtime_id} | generated | owned -->"
MANIFEST_NAME = ".runtime-manifest.json"
CANONICAL_FILES = frozenset({PROJECT_YAML, STATE_YAML, RESOURCES_LOCK})
DANGEROUS_FLAGS = (
    "--dangerously-skip-permissions",
    "--dangerously-bypass-approvals-and-sandbox",
    "--yolo",
)
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


class UnsafePathError(Exception):
    """Raised when a derived output path would escape the project root."""


@dataclass(frozen=True)
class DetectionResult:
    """Side-effect free detection of a runtime in the project environment."""

    runtime_id: str
    detected: bool
    signals: list[str]
    reason: str
    writable: bool = False


@dataclass(frozen=True)
class RenderResult:
    """Outcome of rendering a runtime adapter's outputs."""

    ok: bool
    runtime_id: str
    written: list[Path]
    errors: list[str]
    manifest_updated: bool


@dataclass(frozen=True)
class UninstallResult:
    """Outcome of removing adapter-owned files for a runtime."""

    ok: bool
    runtime_id: str
    removed: list[Path]
    errors: list[str]


@dataclass(frozen=True)
class SwitchResult:
    """Outcome of switching from one runtime adapter to another."""

    ok: bool
    from_runtime: str
    to_runtime: str
    canonical_unchanged: bool
    errors: list[str]


__all__ = [
    "UnsafePathError",
    "DetectionResult",
    "RenderResult",
    "UninstallResult",
    "SwitchResult",
    "GenericRenderer",
]


class GenericRenderer:
    """
    Runtime-agnostic generic renderer.

    Consumes declarative adapter JSON files (``.yaml`` extension) and turns
    canonical project state into project-local runtime output. No runtime
    vendor logic lives here; everything is adapter-driven.
    """

    def __init__(
        self,
        project_root,
        adapters_dir: str = "runtime-adapters",
        catalog_dir: str = "catalog",
    ) -> None:
        self.project_root = Path(project_root)
        self.adapters_dir = adapters_dir
        self.catalog_dir = catalog_dir
        self.state_dir = self.project_root / CANONICAL_STATE_DIR
        self.manifest_path = self.state_dir / MANIFEST_NAME

    # ------------------------------------------------------------------
    # Adapter loading / validation
    # ------------------------------------------------------------------
    def load_adapter(self, runtime_id: str) -> Optional[dict]:
        """
        Load and parse an adapter JSON document.

        Looks for ``<adapters_dir>/<runtime_id>.yaml`` relative to the
        project root, then relative to the current working directory.
        Returns ``None`` (fail-open) when the adapter is missing, unsafe,
        or malformed.
        """
        if not runtime_id or not isinstance(runtime_id, str):
            return None
        if "/" in runtime_id or "\\" in runtime_id or runtime_id in (".", ".."):
            return None
        if Path(runtime_id).name != runtime_id:
            return None

        candidates = []
        if self.adapters_dir:
            candidates.append(self.project_root / self.adapters_dir / f"{runtime_id}.yaml")
            candidates.append(Path.cwd() / self.adapters_dir / f"{runtime_id}.yaml")
        candidates.append(self.project_root / f"{runtime_id}.yaml")

        for path in candidates:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                data = json.loads(text)
            except ValueError:
                continue
            if isinstance(data, dict):
                return data
        return None

    def validate_adapter(self, adapter: dict) -> ValidationResult:
        """Validate adapter metadata contract. Never writes anything."""
        result = ValidationResult.success()

        if not isinstance(adapter, dict):
            return ValidationResult.failure([
                SchemaValidationError(
                    "Adapter document is not a JSON object",
                    schema_id="runtime-adapter",
                )
            ])

        rid = adapter.get("id")
        if not isinstance(rid, str) or not rid:
            result = result.add_error(
                SchemaValidationError(
                    "Missing required field: 'id'",
                    field_path="id",
                    schema_id="runtime-adapter",
                )
            )
        else:
            if not is_valid_id(rid):
                result = result.add_error(
                    SchemaValidationError(
                        f"Invalid adapter id: {rid!r}",
                        field_path="id",
                        schema_id="runtime-adapter",
                    )
                )
            if adapter.get("runtime_id") != rid:
                result = result.add_error(
                    SchemaValidationError(
                        "Field 'runtime_id' must equal field 'id'",
                        field_path="runtime_id",
                        schema_id="runtime-adapter",
                    )
                )

        name = adapter.get("name")
        if not isinstance(name, str) or not name.strip():
            result = result.add_error(
                SchemaValidationError(
                    "Missing required field: 'name'",
                    field_path="name",
                    schema_id="runtime-adapter",
                )
            )

        render_block = adapter.get("render")
        if (
            not isinstance(render_block, dict)
            or not isinstance(render_block.get("outputs"), list)
        ):
            result = result.add_error(
                SchemaValidationError(
                    "Missing required field: 'render.outputs' (list)",
                    field_path="render.outputs",
                    schema_id="runtime-adapter",
                )
            )
        else:
            for index, output in enumerate(render_block["outputs"]):
                field = f"render.outputs[{index}]"
                if not isinstance(output, dict):
                    result = result.add_error(
                        SchemaValidationError(
                            f"{field} is not an object",
                            field_path=field,
                            schema_id="runtime-adapter",
                        )
                    )
                    continue
                path = output.get("path")
                if not isinstance(path, str) or not path:
                    result = result.add_error(
                        SchemaValidationError(
                            f"{field} missing non-empty 'path'",
                            field_path=f"{field}.path",
                            schema_id="runtime-adapter",
                        )
                    )
                else:
                    try:
                        self._safe_output_path(path)
                    except UnsafePathError as exc:
                        result = result.add_error(
                            SchemaValidationError(
                                str(exc),
                                field_path=f"{field}.path",
                                schema_id="runtime-adapter",
                            )
                        )

        permission_policy = adapter.get("permission_policy", {})
        if not isinstance(permission_policy, dict):
            permission_policy = {}
        if permission_policy.get("modifies_global_config") is True:
            result = result.add_error(
                SchemaValidationError(
                    "permission_policy.modifies_global_config must be False",
                    field_path="permission_policy.modifies_global_config",
                    schema_id="runtime-adapter",
                )
            )
        if permission_policy.get("requires_explicit_consent") is False:
            result = result.add_warning(
                "permission_policy.requires_explicit_consent should be True"
            )
        enabled_flags = permission_policy.get("dangerous_flags_never_enabled", [])
        if not isinstance(enabled_flags, list):
            enabled_flags = []
        for flag in DANGEROUS_FLAGS:
            if flag not in enabled_flags:
                result = result.add_warning(
                    f"permission_policy is missing dangerous flag: {flag}"
                )

        return result

    # ------------------------------------------------------------------
    # Detection (side-effect free)
    # ------------------------------------------------------------------
    def detect(self, runtime_id: str) -> DetectionResult:
        """
        Detect whether a runtime is present in the project environment.

        Read-only: inspects executables (shutil.which), config files
        (Path.exists), and environment variables (os.environ) declared by
        the adapter's ``detection`` metadata. Never installs or writes.
        """
        writable = os.access(self.project_root, os.W_OK)
        adapter = self.load_adapter(runtime_id)
        if adapter is None:
            return DetectionResult(
                runtime_id,
                False,
                [],
                f"Runtime adapter not found: {runtime_id}",
                writable=writable,
            )

        signals: list[str] = []
        detection = adapter.get("detection", {})
        if not isinstance(detection, dict):
            detection = {}

        hits = 0
        total = 0

        for executable in detection.get("executables", []):
            total += 1
            found = shutil.which(executable) is not None
            signals.append(
                f"executable '{executable}': {'found' if found else 'not found'}"
            )
            hits += 1 if found else 0

        for config_file in detection.get("config_files", []):
            total += 1
            found = (self.project_root / config_file).exists()
            signals.append(
                f"config '{config_file}': {'found' if found else 'not found'}"
            )
            hits += 1 if found else 0

        for env_var in detection.get("environment_variables", []):
            total += 1
            found = os.environ.get(env_var) is not None
            signals.append(
                f"environment variable '{env_var}': {'set' if found else 'not set'}"
            )
            hits += 1 if found else 0

        if total == 0:
            detected = False
            reason = "no detection signals configured"
        elif hits == total:
            detected = True
            reason = f"all {total} detection signal(s) matched"
        elif hits > 0:
            detected = True
            reason = f"{hits} of {total} detection signal(s) matched"
        else:
            detected = False
            reason = f"none of {total} detection signal(s) matched"

        return DetectionResult(runtime_id, detected, signals, reason, writable=writable)

    # ------------------------------------------------------------------
    # Canonical state (read-only)
    # ------------------------------------------------------------------
    def read_canonical(self):
        """
        Read canonical project spec, state, and lock from .ai-coding-starter/.

        Returns ``(spec, state, lock | None)``. Missing or unreadable files
        yield ``None`` for that component (fail-open); this method never
        modifies canonical files.
        """
        spec = None
        state = None
        lock = None
        try:
            spec = read_project_spec(self.state_dir / PROJECT_YAML)
        except Exception:
            spec = None
        try:
            state = read_state(self.state_dir / STATE_YAML)
        except Exception:
            state = None
        lock_path = self.state_dir / RESOURCES_LOCK
        if lock_path.exists():
            try:
                lock = read_resources_lock(lock_path)
            except Exception:
                lock = None
        return spec, state, lock

    # ------------------------------------------------------------------
    # Template rendering
    # ------------------------------------------------------------------
    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _marker(runtime_id: str) -> str:
        return MARKER_FORMAT.format(runtime_id=runtime_id)

    def _build_context(self, spec, state, runtime_id: str, adapter: Optional[dict]) -> dict:
        capabilities = [str(cap) for cap in (spec.capabilities or [])]
        active_tasks = [
            {
                "id": getattr(task, "id", ""),
                "title": getattr(task, "title", ""),
                "status": getattr(task, "status", ""),
            }
            for task in (state.active_tasks or [])
        ]
        active_tasks_bullets = "\n".join(
            f"- {task['id']} — {task['title']} [{task['status']}]" for task in active_tasks
        ) or "None"
        adapter = adapter or {}
        return {
            "project": {
                "name": spec.name or "",
                "id": str(spec.id),
                "description": spec.description or "",
                "created_at": spec.created_at,
                "updated_at": spec.updated_at,
                "project_type": str(spec.project_type) if spec.project_type else "",
                "stack_bundle": str(spec.stack_bundle) if spec.stack_bundle else "",
                "capabilities": capabilities,
                "capabilities_joined": ", ".join(capabilities),
                "capabilities_bullets": "\n".join(f"- {cap}" for cap in capabilities) or "None",
            },
            "state": {
                "phase": state.phase,
                "focus": state.focus or "",
                "active_tasks": active_tasks,
                "active_tasks_bullets": active_tasks_bullets,
                "completed_tasks_count": len(state.completed_tasks or []),
            },
            "runtime": {
                "id": runtime_id,
                "name": adapter.get("name", runtime_id),
                "instruction_format": adapter.get("instruction_format", ""),
            },
        }

    def _render_template(self, template: Any, context: dict) -> str:
        if isinstance(template, list):
            text = "\n".join(str(line) for line in template)
            if text:
                text += "\n"
        else:
            text = str(template or "")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            value: Any = context
            for part in key.split("."):
                if not isinstance(value, dict) or part not in value:
                    return match.group(0)
                value = value[part]
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return ", ".join(value)
            return str(value)

        return PLACEHOLDER_RE.sub(replace, text)

    # ------------------------------------------------------------------
    # Path safety
    # ------------------------------------------------------------------
    def _safe_output_path(self, rel_path: str) -> Path:
        """
        Resolve an output path beneath the project root.

        Rejects absolute paths, drive letters, ``..`` segments, and any
        path that resolves outside the project root (best-effort symlink
        escape guard). Raises ``UnsafePathError`` instead of writing.
        """
        if not isinstance(rel_path, str) or not rel_path:
            raise UnsafePathError("output path must be a non-empty string")
        if Path(rel_path).is_absolute():
            raise UnsafePathError(f"absolute output path rejected: {rel_path!r}")
        if rel_path.startswith("/") or rel_path.startswith("\\"):
            raise UnsafePathError(f"root-relative output path rejected: {rel_path!r}")
        if len(rel_path) >= 2 and rel_path[1] == ":":
            raise UnsafePathError(f"drive-letter output path rejected: {rel_path!r}")
        if any(part == ".." for part in Path(rel_path).parts):
            raise UnsafePathError(f"parent traversal ('..') rejected: {rel_path!r}")

        root = self.project_root.resolve()
        candidate = self.project_root / rel_path
        try:
            resolved = candidate.resolve()
        except (OSError, ValueError) as exc:
            raise UnsafePathError(
                f"cannot resolve output path {rel_path!r}: {exc}"
            ) from exc
        if resolved != root and root not in resolved.parents:
            raise UnsafePathError(f"output path escapes project root: {rel_path!r}")

        self._reject_symlink_escape(candidate, root)
        return resolved

    def _reject_symlink_escape(self, path: Path, root: Path) -> None:
        """Best-effort guard: reject if a symlink component points outside root."""
        current = path
        while current != root and current.parent != current:
            try:
                mode = os.lstat(current).st_mode
            except OSError:
                current = current.parent
                continue
            if stat.S_ISLNK(mode):
                try:
                    target = os.readlink(current)
                except OSError:
                    current = current.parent
                    continue
                try:
                    resolved_target = (current.parent / target).resolve()
                except (OSError, ValueError):
                    current = current.parent
                    continue
                if resolved_target != root and root not in resolved_target.parents:
                    raise UnsafePathError(f"symlink escapes project root: {current}")
            current = current.parent

    # ------------------------------------------------------------------
    # Manifest (ownership tracking)
    # ------------------------------------------------------------------
    def _read_manifest(self) -> dict:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"runtimes": {}}
        if not isinstance(data, dict):
            return {"runtimes": {}}
        runtimes = data.get("runtimes")
        if not isinstance(runtimes, dict):
            runtimes = {}
        return {"runtimes": runtimes}

    def _write_manifest(self, manifest: dict) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Render / install / uninstall / switch
    # ------------------------------------------------------------------
    def render(
        self,
        runtime_id: str,
        spec=None,
        state=None,
        lock=None,
    ) -> RenderResult:
        """
        Render adapter outputs into project-local files from canonical state.

        Fail-open: returns ``RenderResult(ok=False, ...)`` on any failure;
        canonical files are never modified.
        """
        errors: list[str] = []
        written: list[Path] = []

        adapter = self.load_adapter(runtime_id)
        if adapter is None:
            return RenderResult(
                False,
                runtime_id,
                [],
                [f"Runtime adapter not found or malformed: {runtime_id}"],
                False,
            )

        validation = self.validate_adapter(adapter)
        if not validation.is_valid:
            return RenderResult(
                False,
                runtime_id,
                [],
                [str(error) for error in validation.errors],
                False,
            )

        render_block = adapter.get("render", {})
        if not isinstance(render_block, dict):
            return RenderResult(
                False,
                runtime_id,
                [],
                [
                    f"Runtime adapter '{runtime_id}' has invalid render block"
                ],
                False,
            )

        if spec is None or state is None:
            file_spec, file_state, file_lock = self.read_canonical()
            if spec is None:
                spec = file_spec
            if state is None:
                state = file_state
            if lock is None:
                lock = file_lock

        if spec is None or state is None:
            return RenderResult(
                False,
                runtime_id,
                [],
                [
                    "Cannot read canonical project.yaml/state.yaml under "
                    f"{self.state_dir}"
                ],
                False,
            )

        # lock is accepted for signature compatibility; canonical lock is not
        # rendered into adapter output by the generic renderer.
        _ = lock

        context = self._build_context(spec, state, runtime_id, adapter)
        root = self.project_root.resolve()

        for index, output in enumerate(render_block.get("outputs", [])):
            if not isinstance(output, dict):
                errors.append(f"render.outputs[{index}] is not an object")
                continue
            rel_path = output.get("path")
            if not isinstance(rel_path, str) or not rel_path:
                errors.append(f"render.outputs[{index}] missing 'path'")
                continue
            try:
                safe_path = self._safe_output_path(rel_path)
            except UnsafePathError as exc:
                errors.append(f"Unsafe output path {rel_path!r}: {exc}")
                continue
            try:
                rel_to_root = safe_path.relative_to(root)
            except ValueError:
                errors.append(f"Output path escapes project root: {rel_path}")
                continue
            # Canonical files are read-only: never derive into them.
            if rel_to_root.name in CANONICAL_FILES:
                errors.append(
                    f"Refusing to write canonical file: {rel_to_root.as_posix()}"
                )
                continue

            try:
                content = self._render_template(output.get("template", ""), context)
            except Exception as exc:  # template rendering must not crash the renderer
                errors.append(f"Failed to render template for {rel_path}: {exc}")
                continue

            dangerous = [flag for flag in DANGEROUS_FLAGS if flag in content]
            if dangerous:
                errors.append(
                    "Refusing to write "
                    f"{rel_path}: dangerous permission flags detected: "
                    f"{', '.join(dangerous)}"
                )
                continue

            mark_owned = output.get("mark_owned", True)
            if mark_owned:
                content = self._marker(runtime_id) + "\n" + content

            try:
                safe_path.parent.mkdir(parents=True, exist_ok=True)
                safe_path.write_text(content, encoding="utf-8")
                written.append(safe_path)
            except OSError as exc:
                errors.append(f"Failed to write {rel_path}: {exc}")

        manifest_updated = False
        if written:
            try:
                manifest = self._read_manifest()
                runtimes = manifest.setdefault("runtimes", {})
                outputs_rel = [
                    str(p.relative_to(root).as_posix()) for p in written
                ]
                runtimes[runtime_id] = {
                    "installed_at": self._utc_now(),
                    "outputs": outputs_rel,
                }
                self.state_dir.mkdir(parents=True, exist_ok=True)
                self._write_manifest(manifest)
                manifest_updated = True
            except OSError as exc:
                errors.append(f"Failed to update runtime manifest: {exc}")

        return RenderResult(
            ok=not errors,
            runtime_id=runtime_id,
            written=written,
            errors=errors,
            manifest_updated=manifest_updated,
        )

    def install(self, runtime_id: str) -> RenderResult:
        """
        Render outputs plus ensure install directories; track ownership.

        Idempotent: running twice yields identical files and no duplicate
        content or accumulating garbage.
        """
        adapter = self.load_adapter(runtime_id)
        if adapter is None:
            return RenderResult(
                False,
                runtime_id,
                [],
                [f"Runtime adapter not found or malformed: {runtime_id}"],
                False,
            )

        validation = self.validate_adapter(adapter)
        if not validation.is_valid:
            return RenderResult(
                False,
                runtime_id,
                [],
                [str(error) for error in validation.errors],
                False,
            )

        result = self.render(runtime_id)
        errors = list(result.errors)
        written = list(result.written)

        install_block = adapter.get("install", {})
        if isinstance(install_block, dict):
            for dir_path in install_block.get("paths", []):
                if not isinstance(dir_path, str) or not dir_path:
                    errors.append("install.paths entry is not a non-empty string")
                    continue
                try:
                    safe_dir = self._safe_output_path(dir_path)
                except UnsafePathError as exc:
                    errors.append(f"Unsafe install path {dir_path!r}: {exc}")
                    continue
                try:
                    safe_dir.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    errors.append(
                        f"Failed to create install directory {dir_path}: {exc}"
                    )

        return RenderResult(
            ok=not errors,
            runtime_id=runtime_id,
            written=written,
            errors=errors,
            manifest_updated=result.manifest_updated,
        )

    def uninstall(self, runtime_id: str) -> UninstallResult:
        """
        Remove only adapter-owned files for a runtime.

        Removes files listed in the ownership manifest plus
        ``adapter.uninstall.owned_files`` when they still carry the runtime
        marker or are declared owned. Removes parent directories only when
        they become empty AND are listed in ``uninstall.owned_dirs``.
        Canonical files and user files are never removed.
        """
        errors: list[str] = []
        removed: list[Path] = []

        adapter = self.load_adapter(runtime_id)
        owned_files: set[str] = set()
        owned_dirs: set[str] = set()
        if isinstance(adapter, dict):
            uninstall_block = adapter.get("uninstall", {})
            if isinstance(uninstall_block, dict):
                owned_files = {
                    path
                    for path in uninstall_block.get("owned_files", [])
                    if isinstance(path, str)
                }
                owned_dirs = {
                    str(path).rstrip("/").rstrip("\\")
                    for path in uninstall_block.get("owned_dirs", [])
                    if isinstance(path, str)
                }

        manifest = self._read_manifest()
        runtimes = manifest.get("runtimes", {})
        if not isinstance(runtimes, dict):
            runtimes = {}
        entry = runtimes.get(runtime_id, {})
        if not isinstance(entry, dict):
            entry = {}
        manifest_outputs = entry.get("outputs", [])
        if not isinstance(manifest_outputs, list):
            manifest_outputs = []

        candidates: list[str] = []
        seen: set[str] = set()
        for rel in list(manifest_outputs) + sorted(owned_files):
            if rel in seen:
                continue
            seen.add(rel)
            candidates.append(rel)

        root = self.project_root.resolve()
        removed_parents: set[Path] = set()
        for rel in candidates:
            try:
                safe_path = self._safe_output_path(rel)
            except UnsafePathError as exc:
                errors.append(str(exc))
                continue
            if safe_path.name in CANONICAL_FILES:
                errors.append(f"Refusing to remove canonical file: {rel}")
                continue
            if not safe_path.exists():
                continue
            declared_owned = rel in owned_files
            carries_marker = False
            try:
                text = safe_path.read_text(encoding="utf-8")
                carries_marker = (
                    f"runtime adapter: {runtime_id} | generated | owned" in text
                )
            except OSError:
                carries_marker = False
            if not (declared_owned or carries_marker):
                continue
            try:
                safe_path.unlink()
                removed.append(safe_path)
                removed_parents.add(safe_path.parent)
            except OSError as exc:
                errors.append(f"Failed to remove {rel}: {exc}")

        # Remove empty parent directories, but only when declared owned.
        start_dirs: set[Path] = set(removed_parents)
        for rel in owned_dirs:
            try:
                start_dirs.add(self._safe_output_path(rel))
            except UnsafePathError:
                continue
        for start in start_dirs:
            current = start
            while current != root and current.parent != current:
                try:
                    rel_current = current.relative_to(root).as_posix()
                except ValueError:
                    break
                if rel_current not in owned_dirs:
                    break
                if not current.is_dir() or any(current.iterdir()):
                    break
                try:
                    current.rmdir()
                except OSError:
                    break
                current = current.parent

        if runtime_id in runtimes:
            del runtimes[runtime_id]
            try:
                self._write_manifest(manifest)
            except OSError as exc:
                errors.append(f"Failed to update runtime manifest: {exc}")

        return UninstallResult(
            ok=not errors,
            runtime_id=runtime_id,
            removed=removed,
            errors=errors,
        )

    def switch(
        self,
        from_runtime: str,
        to_runtime: str,
    ) -> SwitchResult:
        """
        Switch runtime adapters: uninstall ``from_runtime``, install
        ``to_runtime``. Canonical state is always unchanged.
        """
        errors: list[str] = []
        uninstall_result = self.uninstall(from_runtime)
        errors.extend(uninstall_result.errors)
        install_result = self.install(to_runtime)
        errors.extend(install_result.errors)

        return SwitchResult(
            ok=uninstall_result.ok and install_result.ok and not errors,
            from_runtime=from_runtime,
            to_runtime=to_runtime,
            canonical_unchanged=True,
            errors=errors,
        )
