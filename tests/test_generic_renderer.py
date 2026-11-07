#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Generic renderer tests (corrected shared-ownership model).

Covers requirement 45 (TEST PLAN — RENDERING):
  - canonical fixture + adapter -> expected project-local output
  - correct path
  - correct format (canonical state placeholders resolved)
  - deterministic content
  - no global path writes
  - reads M4 canonical state (project.yaml / state.yaml / resources.lock)
  - shared M4 AGENTS.md is consumed, never owned or deleted by adapters

Standard library only. No network.
"""
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

generic_renderer = importlib.import_module("core.generic-renderer")  # noqa: E402
GenericRenderer = generic_renderer.GenericRenderer

from core.spec import build_project_spec, write_project_spec  # noqa: E402
from core.state import (  # noqa: E402
    build_initial_state,
    build_resources_lock,
    write_resources_lock,
    write_state,
)

ADAPTERS_DIR = REPO_ROOT / "runtime-adapters"
SHARED_CONSUMERS = ["codex", "opencode", "claude-code", "cursor"]
OWNED_ADAPTER = "antigravity"
ALL_RUNTIME_IDS = SHARED_CONSUMERS + [OWNED_ADAPTER]

EXPECTED_OWNED_OUTPUT = {
    "antigravity": ".agent/GEMINI.md",
}


def make_canonical_project(root, project_name="My Project",
                           project_type="saas", stack_bundle="nextjs-supabase",
                           capabilities=None, phase="planning", focus="design"):
    """Build a minimal M4 canonical project under ``root`` plus a shared
    root AGENTS.md (as M4 portable_renderer would derive)."""
    root = Path(root)
    spec = build_project_spec(
        project_name, project_type_id=project_type,
        capabilities=capabilities or ["authentication", "payments"],
        stack_bundle_id=stack_bundle,
    )
    write_project_spec(root, spec)
    state = build_initial_state(str(spec.id), phase=phase, focus=focus)
    write_state(root, state)
    lock = build_resources_lock(stack_bundle, requested_bundle_id=stack_bundle)
    write_resources_lock(root, lock)
    # M4 derives a shared root AGENTS.md that runtimes may consume.
    (root / "AGENTS.md").write_text(
        f"# {project_name}\n\nDerived M4 project instructions.\n",
        encoding="utf-8",
    )
    return root, spec, state, lock


class TestGenericRendererRendering(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-renderer-"))
        self.root, self.spec, self.state, self.lock = make_canonical_project(
            self.temp_dir
        )
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))

    def test_shared_consumers_install_ok_with_no_owned_file(self):
        """codex/opencode/claude-code/cursor consume shared AGENTS.md;
        they generate no owned instruction file."""
        for runtime_id in SHARED_CONSUMERS:
            with self.subTest(runtime=runtime_id):
                result = self.renderer.install(runtime_id)
                self.assertTrue(result.ok, msg=f"{runtime_id}: {result.errors}")
                self.assertEqual(result.written, [])
                # No owned instruction file created for a shared consumer.
                self.assertEqual(
                    len(list(self.root.glob(".agent/**/*"))) +
                    len(list(self.root.glob(".codex/**/*"))) +
                    len(list(self.root.glob(".claude/**/*"))) +
                    len(list(self.root.glob(".cursor/**/*"))),
                    0,
                )
                # Canonical files untouched.
                self.assertTrue(
                    (self.root / ".ai-coding-starter" / "project.yaml").exists()
                )

    def test_antigravity_renders_owned_output_with_canonical_state(self):
        result = self.renderer.install("antigravity")
        self.assertTrue(result.ok, msg=result.errors)
        owned = self.root / ".agent/GEMINI.md"
        self.assertTrue(owned.exists())
        self.assertIn(owned, result.written)
        content = owned.read_text(encoding="utf-8")
        self.assertIn("My Project", content)
        self.assertIn(str(self.spec.id), content)
        self.assertIn("saas", content)
        self.assertIn("nextjs-supabase", content)
        self.assertIn("authentication, payments", content)
        self.assertIn("planning", content)
        self.assertIn("design", content)
        self.assertIn(
            "<!-- ai-coding-starter runtime adapter: antigravity | generated | owned -->",
            content,
        )

    def test_rendering_is_deterministic(self):
        contents = {}
        for runtime_id in ALL_RUNTIME_IDS:
            result = self.renderer.install(runtime_id)
            self.assertTrue(result.ok, msg=f"{runtime_id}: {result.errors}")
            if runtime_id == OWNED_ADAPTER:
                contents[runtime_id] = (
                    self.root / EXPECTED_OWNED_OUTPUT[runtime_id]
                ).read_text(encoding="utf-8")
        for runtime_id in [OWNED_ADAPTER]:
            self.renderer.install(runtime_id)
            again = (
                self.root / EXPECTED_OWNED_OUTPUT[runtime_id]
            ).read_text(encoding="utf-8")
            self.assertEqual(again, contents[runtime_id])

    def test_no_global_path_writes(self):
        for runtime_id in ALL_RUNTIME_IDS:
            result = self.renderer.install(runtime_id)
            self.assertTrue(result.ok)
            for written in result.written:
                self.assertIn(
                    self.temp_dir.resolve(),
                    written.resolve().parents,
                )

    def test_manifest_only_for_owned_adapter(self):
        self.renderer.install("antigravity")
        manifest_path = self.root / ".ai-coding-starter" / ".runtime-manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIn("antigravity", manifest["runtimes"])
        self.assertIn(".agent/GEMINI.md",
                      manifest["runtimes"]["antigravity"]["outputs"])
        for runtime_id in SHARED_CONSUMERS:
            self.assertNotIn(runtime_id, manifest["runtimes"])

    def test_unknown_adapter_fail_open(self):
        result = self.renderer.install("does-not-exist")
        self.assertFalse(result.ok)
        self.assertTrue(result.errors)
        self.assertTrue((self.root / ".ai-coding-starter" / "project.yaml").exists())

    def test_canonical_files_not_written(self):
        before = {
            name: (self.root / ".ai-coding-starter" / name).read_text(encoding="utf-8")
            for name in ("project.yaml", "state.yaml", "resources.lock")
        }
        for runtime_id in ALL_RUNTIME_IDS:
            self.renderer.install(runtime_id)
        after = {
            name: (self.root / ".ai-coding-starter" / name).read_text(encoding="utf-8")
            for name in ("project.yaml", "state.yaml", "resources.lock")
        }
        self.assertEqual(before, after)


class TestGenericRendererSharedAgentsMd(unittest.TestCase):
    """Shared M4 root AGENTS.md must be consumed, never owned or deleted."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-shared-"))
        self.root, _, _, _ = make_canonical_project(self.temp_dir)
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))
        self.agents_md = self.root / "AGENTS.md"
        self.before = self.agents_md.read_text(encoding="utf-8")

    def test_shared_agents_md_preserved_across_install_uninstall(self):
        for runtime_id in SHARED_CONSUMERS:
            with self.subTest(runtime=runtime_id):
                install_result = self.renderer.install(runtime_id)
                self.assertTrue(install_result.ok, msg=install_result.errors)
                self.assertTrue(self.agents_md.exists())
                self.assertEqual(
                    self.agents_md.read_text(encoding="utf-8"), self.before
                )
                uninstall_result = self.renderer.uninstall(runtime_id)
                self.assertTrue(uninstall_result.ok, msg=uninstall_result.errors)
                self.assertTrue(self.agents_md.exists())
                self.assertEqual(
                    self.agents_md.read_text(encoding="utf-8"), self.before
                )

    def test_no_adapter_claims_ownership_of_agents_md(self):
        for runtime_id in ALL_RUNTIME_IDS:
            adapter_path = ADAPTERS_DIR / f"{runtime_id}.yaml"
            import json as _json
            adapter = _json.loads(adapter_path.read_text(encoding="utf-8"))
            source = adapter.get("instruction_source", {})
            if runtime_id == OWNED_ADAPTER:
                self.assertEqual(source.get("ownership"), "owned")
                self.assertEqual(source.get("path"), ".agent/GEMINI.md")
            else:
                self.assertEqual(source.get("ownership"), "shared")
                self.assertEqual(source.get("path"), "AGENTS.md")


class TestGenericRendererLoadAndValidate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-load-"))
        self.renderer = GenericRenderer(self.temp_dir, adapters_dir=str(ADAPTERS_DIR))

    def test_load_adapter_returns_dict(self):
        adapter = self.renderer.load_adapter("codex")
        self.assertIsInstance(adapter, dict)
        self.assertEqual(adapter.get("id"), "codex")

    def test_load_adapter_missing_returns_none_fail_open(self):
        self.assertIsNone(self.renderer.load_adapter("not-a-real-runtime"))

    def test_validate_adapter_accepts_valid_adapter(self):
        adapter = self.renderer.load_adapter("codex")
        result = self.renderer.validate_adapter(adapter)
        self.assertTrue(result.is_valid)

    def test_validate_adapter_accepts_empty_outputs(self):
        """Shared-consumer adapters declare no render.outputs; that is valid."""
        adapter = self.renderer.load_adapter("opencode")
        result = self.renderer.validate_adapter(adapter)
        self.assertTrue(result.is_valid)

    def test_validate_adapter_rejects_global_config_writer(self):
        adapter = self.renderer.load_adapter("codex")
        adapter = dict(adapter)
        adapter["permission_policy"] = dict(adapter["permission_policy"])
        adapter["permission_policy"]["modifies_global_config"] = True
        result = self.renderer.validate_adapter(adapter)
        self.assertFalse(result.is_valid)


class TestGenericRendererRenderAgents(unittest.TestCase):
    """M6.6: Per-agent runtime-native rendering via render_agents()."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-render-agents-"))
        self.root, self.spec, self.state, self.lock = make_canonical_project(
            self.temp_dir
        )
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))
        self.agents = [
            {
                "id": "engineering-frontend-developer",
                "name": "Frontend Developer",
                "description": "Expert frontend developer specializing in React/Vue/Angular.",
                "division": "engineering",
                "body": "You are an expert frontend developer...",
            },
            {
                "id": "security-appsec-engineer",
                "name": "AppSec Engineer",
                "description": "Application security engineer focused on threat modeling.",
                "division": "security",
                "body": "You are an application security engineer...",
            },
        ]

    def _agent_files_for(self, runtime_id):
        """Expected agent output paths per runtime."""
        expected = {
            "codex": [".codex/agents/engineering-frontend-developer.toml",
                      ".codex/agents/security-appsec-engineer.toml"],
            "opencode": [".opencode/agents/engineering-frontend-developer.md",
                         ".opencode/agents/security-appsec-engineer.md"],
            "claude-code": [".claude/agents/engineering-frontend-developer.md",
                            ".claude/agents/security-appsec-engineer.md"],
            "cursor": [".cursor/rules/engineering-frontend-developer.mdc",
                       ".cursor/rules/security-appsec-engineer.mdc"],
            "antigravity": [".agent/skills/engineering-frontend-developer/SKILL.md",
                            ".agent/skills/security-appsec-engineer/SKILL.md"],
        }
        return expected.get(runtime_id, [])

    def test_render_agents_all_runtimes(self):
        """All 5 supported runtimes render per-agent files successfully."""
        for runtime_id in ALL_RUNTIME_IDS:
            with self.subTest(runtime=runtime_id):
                result = self.renderer.render_agents(runtime_id, self.agents)
                self.assertTrue(result.ok, msg=f"{runtime_id}: {result.errors}")
                self.assertEqual(len(result.written), 2,
                                 f"{runtime_id} should write 2 agent files")
                for expected_path in self._agent_files_for(runtime_id):
                    self.assertTrue(
                        (self.root / expected_path).exists(),
                        f"{runtime_id}: {expected_path} not created",
                    )

    def test_render_agents_correct_content_placeholders(self):
        """Placeholders {slug}, {name}, {description}, {division}, {body} resolved."""
        result = self.renderer.render_agents("claude-code", self.agents)
        self.assertTrue(result.ok, msg=result.errors)
        content = (
            self.root / ".claude/agents/engineering-frontend-developer.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Frontend Developer", content)
        self.assertIn("Expert frontend developer", content)
        self.assertIn("engineering", content)
        self.assertIn("You are an expert frontend developer...", content)
        self.assertIn(
            "<!-- ai-coding-starter runtime adapter: claude-code | generated | owned -->",
            content,
        )

    def test_render_agents_codex_toml_format(self):
        """Codex agents use TOML format (name = ..., description = ...)."""
        result = self.renderer.render_agents("codex", self.agents)
        self.assertTrue(result.ok, msg=result.errors)
        content = (
            self.root / ".codex/agents/engineering-frontend-developer.toml"
        ).read_text(encoding="utf-8")
        self.assertIn('name = "Frontend Developer"', content)
        self.assertIn("description =", content)
        self.assertIn("developer_instructions =", content)

    def test_render_agents_cursor_mdc_format(self):
        """Cursor agents use MDC format with frontmatter."""
        result = self.renderer.render_agents("cursor", self.agents)
        self.assertTrue(result.ok, msg=result.errors)
        content = (
            self.root / ".cursor/rules/engineering-frontend-developer.mdc"
        ).read_text(encoding="utf-8")
        self.assertIn("description:", content)
        self.assertIn("alwaysApply: false", content)
        self.assertIn("globs: \"\"", content)

    def test_render_agents_deterministic(self):
        """Same input produces byte-identical output across runs."""
        result_a = self.renderer.render_agents("opencode", self.agents)
        self.assertTrue(result_a.ok)
        content_a = (
            self.root / ".opencode/agents/engineering-frontend-developer.md"
        ).read_text(encoding="utf-8")
        self.renderer.render_agents("opencode", self.agents)
        content_b = (
            self.root / ".opencode/agents/engineering-frontend-developer.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(content_a, content_b)

    def test_render_agents_no_canonical_files_modified(self):
        """Canonical state files untouched by agent rendering."""
        before = {
            name: (self.root / ".ai-coding-starter" / name).read_text(encoding="utf-8")
            for name in ("project.yaml", "state.yaml", "resources.lock")
        }
        self.renderer.render_agents("claude-code", self.agents)
        after = {
            name: (self.root / ".ai-coding-starter" / name).read_text(encoding="utf-8")
            for name in ("project.yaml", "state.yaml", "resources.lock")
        }
        self.assertEqual(before, after)

    def test_render_agents_owned_files_removed_on_uninstall(self):
        """Agent files are mark_owned and removed on uninstall."""
        self.renderer.render_agents("antigravity", self.agents)
        self.assertTrue(
            (self.root / ".agent/skills/engineering-frontend-developer/SKILL.md").exists()
        )
        uninstall_result = self.renderer.uninstall("antigravity")
        self.assertTrue(uninstall_result.ok, msg=uninstall_result.errors)
        self.assertFalse(
            (self.root / ".agent/skills/engineering-frontend-developer/SKILL.md").exists()
        )

    def test_render_agents_empty_list(self):
        """Empty agent list is a no-op, returns ok."""
        result = self.renderer.render_agents("claude-code", [])
        self.assertTrue(result.ok)
        self.assertEqual(result.written, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
