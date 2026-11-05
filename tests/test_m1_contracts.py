"""
M1 Contract Tests - Schema Validation and Contract Tests

Tests for:
- Schema files parse correctly
- Required fields defined
- Stable ID format
- Schema versions present
- Valid example contracts accepted
- Invalid contracts rejected
- Cross references validated where implemented
- Runtime fields cannot leak into portable-domain fixtures
"""

import json
import unittest
from pathlib import Path

# Import domain contracts for validation tests
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.domain.contracts import (
    validate_id, is_valid_id, normalize_id_candidate, CanonicalId, make_id, InvalidIdError,
    ProjectType, Capability, Technology, VersionPolicy, StackBundle,
    Compatibility, CompatibilityRule, CompatibilityCondition, Resource, RuntimeAdapterMetadata, ResourceProvenance,
    ExecutionPack, OptionalRole, ActivationConditions, RuntimeAdapter, DetectionConfig, PermissionPolicy,
    CapabilityProvider, HealthCheckConfig,
    ProjectSpec, RuntimePreferences,
    ValidationResult, UnknownReferenceError, DuplicateIdError
)


class TestIdPolicy(unittest.TestCase):
    """Test canonical ID policy validation."""

    def test_valid_ids(self):
        valid_ids = [
            "nextjs", "aspnet-core", "postgresql", "authentication",
            "file-upload", "saas", "balanced-next-dotnet-postgres",
            "project-planner", "code-reviewer", "api-documenter"
        ]
        for id_val in valid_ids:
            with self.subTest(id=id_val):
                self.assertTrue(is_valid_id(id_val))
                validate_id(id_val)  # Should not raise

    def test_invalid_ids(self):
        invalid_ids = [
            "", "a", "Next.js", "nextjs-14", "postgres-16", "123abc",
            "UPPERCASE", "with spaces", "with_underscore", "trailing-",
            "-leading", "a" * 65, "with.dot", "with@symbol"
        ]
        for id_val in invalid_ids:
            with self.subTest(id=id_val):
                self.assertFalse(is_valid_id(id_val))
                with self.assertRaises(InvalidIdError):
                    validate_id(id_val)

    test_cases_version_embedding = [
        "nextjs-14", "react-18", "postgres-16", "dotnet-8",
        "node-20", "python-3.11", "v1.0.0", "version-2"
    ]

    def test_version_embedding_rejected(self):
        for id_val in self.test_cases_version_embedding:
            with self.subTest(id=id_val):
                self.assertFalse(is_valid_id(id_val))
                with self.assertRaises(InvalidIdError) as cm:
                    validate_id(id_val)
                # Error message should indicate version or format issue
                error_msg = str(cm.exception).lower()
                self.assertTrue(
                    "version" in error_msg or "kebab-case" in error_msg or "format" in error_msg,
                    f"Expected version/format error for '{id_val}', got: {error_msg}"
                )

    def test_canonical_id_wrapper(self):
        cid = make_id("nextjs")
        self.assertEqual(str(cid), "nextjs")
        self.assertEqual(cid, "nextjs")
        self.assertEqual(hash(cid), hash("nextjs"))

        # Equality with another CanonicalId
        cid2 = make_id("nextjs")
        self.assertEqual(cid, cid2)

    def test_normalize_id_candidate(self):
        test_cases = [
            ("Next.js 14", "next-js"),
            ("API Documentation", "api-documentation"),
            ("ASP.NET Core", "asp-net-core"),
            ("PostgreSQL 16", "postgresql"),
            ("My Custom Thing", "my-custom-thing"),
        ]
        for input_val, expected in test_cases:
            with self.subTest(input=input_val):
                result = normalize_id_candidate(input_val)
                self.assertEqual(result, expected)


class TestSchemaFiles(unittest.TestCase):
    """Test that all schema files exist and are valid JSON Schema."""

    SCHEMA_DIR = Path(__file__).parent.parent / "schemas"

    SCHEMA_FILES = [
        "project-type.json",
        "capability.json",
        "technology.json",
        "stack-bundle.json",
        "compatibility.json",
        "resource.json",
        "execution-pack.json",
        "runtime-adapter.json",
        "capability-provider.json",
        "project.yaml.json",
        "state.yaml.json",
        "resources.lock.json",
        "runtime-state.json",
    ]

    def test_all_schema_files_exist(self):
        for schema_file in self.SCHEMA_FILES:
            with self.subTest(schema=schema_file):
                path = self.SCHEMA_DIR / schema_file
                self.assertTrue(path.exists(), f"Schema file missing: {schema_file}")

    def test_schemas_are_valid_json(self):
        for schema_file in self.SCHEMA_FILES:
            with self.subTest(schema=schema_file):
                path = self.SCHEMA_DIR / schema_file
                with open(path) as f:
                    schema = json.load(f)
                # Should have required JSON Schema fields
                self.assertIn("$schema", schema)
                self.assertIn("$id", schema)
                self.assertIn("title", schema)
                self.assertIn("type", schema)

    def test_schemas_have_version(self):
        for schema_file in self.SCHEMA_FILES:
            with self.subTest(schema=schema_file):
                path = self.SCHEMA_DIR / schema_file
                with open(path) as f:
                    schema = json.load(f)
                # Should have schema_version in properties or as const
                self.assertTrue(
                    "schema_version" in schema.get("properties", {}) or
                    "schema_version" in schema.get("required", []),
                    f"Schema {schema_file} missing schema_version"
                )


class TestProjectTypeContract(unittest.TestCase):
    """Test ProjectType domain model."""

    def test_valid_project_type(self):
        pt = ProjectType(
            id=make_id("saas"),
            name="SaaS Platform",
            description="Subscription-based web application",
            default_capabilities=[make_id("authentication"), make_id("payments")],
            recommended_capabilities=[make_id("analytics")],
            tags=["web", "subscription"],
            example_bundles=[make_id("nextjs-supabase")]
        )
        self.assertEqual(str(pt.id), "saas")
        self.assertEqual(len(pt.default_capabilities), 2)

    def test_project_type_from_dict(self):
        data = {
            "schema_version": "1.0.0",
            "id": "saas",
            "name": "SaaS Platform",
            "description": "Subscription-based web application",
            "default_capabilities": ["authentication", "payments"],
            "recommended_capabilities": ["analytics"],
            "tags": ["web"],
            "example_bundles": ["nextjs-supabase"]
        }
        pt = ProjectType.from_dict(data)
        self.assertEqual(str(pt.id), "saas")
        self.assertEqual(len(pt.default_capabilities), 2)

    def test_project_type_validation(self):
        pt = ProjectType.from_dict({
            "id": "saas", "name": "SaaS", "description": "desc",
            "default_capabilities": ["auth", "payments"],
            "example_bundles": ["nextjs-supabase"]
        })

        # Valid references
        result = pt.validate(
            known_capabilities=[make_id("auth"), make_id("payments")],
            known_bundles=[make_id("nextjs-supabase")]
        )
        self.assertTrue(result.is_valid)

        # Invalid capability references (both auth and payments missing from known)
        result = pt.validate(
            known_capabilities=[make_id("auth")],  # Only auth known, payments missing
            known_bundles=[make_id("nextjs-supabase")]
        )
        self.assertFalse(result.is_valid)
        # Should report 1 error for missing "payments" capability
        self.assertEqual(len(result.errors), 1)

    def test_project_type_to_dict(self):
        pt = ProjectType.from_dict({
            "id": "saas", "name": "SaaS", "description": "desc",
            "default_capabilities": ["auth"], "tags": ["web"]
        })
        data = pt.to_dict()
        self.assertEqual(data["id"], "saas")
        self.assertEqual(data["default_capabilities"], ["auth"])


class TestCapabilityContract(unittest.TestCase):
    """Test Capability domain model."""

    def test_valid_capability(self):
        cap = Capability(
            id=make_id("authentication"),
            name="Authentication",
            description="User identity verification",
            category="security",
            example_implementations=[make_id("nextauth"), make_id("supabase-auth")],
            implies=[make_id("authorization")],
            recommended_for=[make_id("saas"), make_id("ecommerce")]
        )
        self.assertEqual(str(cap.id), "authentication")
        self.assertEqual(cap.category, "security")

    def test_capability_validation(self):
        cap = Capability.from_dict({
            "id": "auth", "name": "Auth", "description": "desc",
            "example_implementations": ["nextauth"],
            "requires": ["session-mgmt"],
            "recommended_for": ["saas"]
        })

        # Valid
        result = cap.validate(
            known_technologies=[make_id("nextauth")],
            known_capabilities=[make_id("session-mgmt")],
            known_project_types=[make_id("saas")]
        )
        self.assertTrue(result.is_valid)

        # Invalid technology reference
        result = cap.validate(
            known_technologies=[],
            known_capabilities=[make_id("session-mgmt")],
            known_project_types=[make_id("saas")]
        )
        self.assertFalse(result.is_valid)


class TestTechnologyContract(unittest.TestCase):
    """Test Technology domain model."""

    def test_valid_technology(self):
        tech = Technology(
            id=make_id("nextjs"),
            name="Next.js",
            category="frontend",
            ecosystem="typescript",
            version_policy=VersionPolicy(
                strategy="latest-stable",
                default_version="14",
                supported_versions=["13", "14", "15"],
                min_version="13"
            ),
            tags=["react", "ssr"]
        )
        self.assertEqual(str(tech.id), "nextjs")
        self.assertEqual(tech.version_policy.strategy, "latest-stable")

    def test_technology_rejects_version_in_id(self):
        with self.assertRaises(Exception):
            Technology(
                id=make_id("nextjs-14"),  # This will fail in make_id
                name="Next.js 14",
                category="frontend",
                ecosystem="typescript",
                version_policy=VersionPolicy(strategy="latest-stable")
            )


class TestStackBundleContract(unittest.TestCase):
    """Test StackBundle domain model."""

    def test_valid_stack_bundle(self):
        bundle = StackBundle(
            id=make_id("nextjs-supabase"),
            name="Next.js + Supabase",
            description="Full-stack with BaaS",
            technologies={
                "frontend": make_id("nextjs"),
                "backend": make_id("nextjs"),
                "database": make_id("postgresql"),
                "auth": make_id("supabase-auth"),
                "hosting": make_id("vercel"),
                "styling": make_id("tailwindcss")
            },
            project_types=[make_id("saas"), make_id("ecommerce")],
            capabilities=[make_id("authentication"), make_id("database")],
            profile="fastest-mvp",
            constraints=["Supabase vendor lock-in"],
            tradeoffs=["Less control over auth"],
            incompatible_with=[make_id("nextjs-dotnet-postgres")]
        )
        self.assertEqual(str(bundle.id), "nextjs-supabase")
        self.assertEqual(bundle.profile, "fastest-mvp")

    def test_stack_bundle_requires_roles(self):
        with self.assertRaises(ValueError):
            StackBundle(
                id=make_id("test"),
                name="Test",
                description="Test",
                technologies={"frontend": make_id("nextjs")}  # Missing backend, database
            )

    def test_stack_bundle_validation(self):
        bundle = StackBundle.from_dict({
            "id": "nextjs-supabase", "name": "Next.js + Supabase", "description": "desc",
            "technologies": {
                "frontend": "nextjs", "backend": "nextjs", "database": "postgresql",
                "hosting": "vercel"
            },
            "project_types": ["saas"],
            "capabilities": ["authentication"],
            "incompatible_with": ["nextjs-dotnet"]
        })

        result = bundle.validate(
            known_technologies=[make_id("nextjs"), make_id("postgresql"), make_id("vercel")],
            known_project_types=[make_id("saas")],
            known_capabilities=[make_id("authentication")],
            known_bundles=[make_id("nextjs-dotnet")]
        )
        self.assertTrue(result.is_valid)


class TestCompatibilityContract(unittest.TestCase):
    """Test Compatibility rules domain model."""

    def test_valid_compatibility_rule(self):
        rule = CompatibilityRule(
            rule_type="technology-technology",
            subject=make_id("nextjs"),
            target=make_id("aspnet-core"),
            severity="error",
            reason="Cannot have two primary frontends"
        )
        self.assertEqual(rule.severity, "error")

    def test_compatibility_validation(self):
        compat = Compatibility.from_dict({
            "rules": [
                {
                    "type": "technology-technology",
                    "subject": "nextjs", "target": "aspnet-core",
                    "severity": "error", "reason": "Two frontends"
                },
                {
                    "type": "technology-capability",
                    "subject": "nextjs", "target": "realtime",
                    "severity": "warning", "reason": "Needs extra setup"
                }
            ]
        })

        result = compat.validate(
            known_technologies=[make_id("nextjs"), make_id("aspnet-core")],
            known_capabilities=[make_id("realtime")],
            known_bundles=[],
            known_project_types=[]
        )
        self.assertTrue(result.is_valid)


class TestResourceContract(unittest.TestCase):
    """Test Resource domain model."""

    def test_valid_resource(self):
        resource = Resource(
            id=make_id("code-reviewer"),
            name="Code Reviewer Agent",
            type="agent",
            description="Reviews code for quality",
            capabilities=[make_id("code-review")],
            project_types=[make_id("saas"), make_id("ecommerce")],
            runtime_adapters={
                "codex": RuntimeAdapterMetadata(
                    format="agent-md",
                    path_template=".codex/agents/code-reviewer.md"
                ),
                "opencode": RuntimeAdapterMetadata(
                    format="agent-md",
                    path_template=".opencode/agent/code-reviewer.md"
                )
            },
            provenance=ResourceProvenance(source="bundled", license="MIT")
        )
        self.assertEqual(str(resource.id), "code-reviewer")
        self.assertEqual(resource.type, "agent")
        self.assertIn("codex", resource.runtime_adapters)

    def test_resource_provenance(self):
        prov = ResourceProvenance(
            source="agency-agents",
            upstream_repo="https://github.com/msitarzewski/agency-agents",
            upstream_commit="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
            license="MIT",
            imported_date="2026-01-15",
            reviewed_date="2026-01-15"
        )
        self.assertEqual(prov.source, "agency-agents")


class TestExecutionPackContract(unittest.TestCase):
    """Test ExecutionPack domain model."""

    def test_valid_execution_pack(self):
        pack = ExecutionPack(
            id=make_id("startup-mvp"),
            name="Startup MVP",
            description="Rapid MVP development",
            mode="time-boxed",
            duration="4-8 weeks",
            core_roles=[make_id("project-planner"), make_id("fullstack-engineer")],
            optional_roles=[
                OptionalRole(
                    resource_id=make_id("payments-engineer"),
                    activation="capability-triggered",
                    trigger_capabilities=[make_id("payments")]
                )
            ],
            activation_conditions=ActivationConditions(
                project_types=[make_id("saas"), make_id("ecommerce")],
                capabilities=[make_id("authentication")]
            ),
            quality_gates=["Tests pass", "Deployed to staging"],
            workflow=["discovery", "development", "deploy"]
        )
        self.assertEqual(str(pack.id), "startup-mvp")
        self.assertEqual(pack.mode, "time-boxed")
        self.assertEqual(len(pack.core_roles), 2)

    def test_execution_pack_requires_core_roles(self):
        with self.assertRaises(ValueError):
            ExecutionPack(
                id=make_id("test"),
                name="Test",
                description="Test",
                core_roles=[]  # Must have at least one
            )


class TestRuntimeAdapterContract(unittest.TestCase):
    """Test RuntimeAdapter domain model."""

    def test_valid_runtime_adapter(self):
        adapter = RuntimeAdapter(
            id=make_id("codex"),
            name="Codex",
            instruction_format="agents-md",
            agent_format="markdown-frontmatter",
            skill_format="markdown",
            project_paths=[".codex/"],
            global_paths=["~/.codex/"],
            supports_mcp=True,
            supports_subagents=True,
            supports_commands=True,
            detection=DetectionConfig(
                executables=["codex"],
                config_files=[".codex/config.yaml"]
            ),
            permission_policy=PermissionPolicy(
                modifies_global_config=False,
                requires_explicit_consent=True
            )
        )
        self.assertEqual(str(adapter.id), "codex")
        self.assertTrue(adapter.supports_mcp)

    def test_runtime_adapter_permission_policy(self):
        adapter = RuntimeAdapter(
            id=make_id("test"), name="Test",
            permission_policy=PermissionPolicy(
                dangerous_flags_never_enabled=[
                    "--dangerously-skip-permissions",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "--yolo"
                ]
            )
        )
        result = adapter.validate()
        self.assertTrue(result.is_valid)


class TestCapabilityProviderContract(unittest.TestCase):
    """Test CapabilityProvider domain model."""

    def test_valid_capability_provider(self):
        provider = CapabilityProvider(
            id=make_id("codebase-memory"),
            capability=make_id("code-intelligence"),
            priority=1,
            name="Codebase Memory",
            description="First-class code intelligence",
            availability="external-install",
            health_check=HealthCheckConfig(command="cbm --version"),
            requirements=["Docker", "Node.js 18+"],
            fallback=make_id("source-scan"),
            optional=True
        )
        self.assertEqual(str(provider.id), "codebase-memory")
        self.assertEqual(provider.priority, 1)
        self.assertEqual(str(provider.fallback), "source-scan")

    def test_capability_provider_validation(self):
        provider = CapabilityProvider.from_dict({
            "id": "codebase-memory", "capability": "code-intelligence", "priority": 1,
            "fallback": "source-scan"
        })

        result = provider.validate(
            known_capabilities=[make_id("code-intelligence")],
            known_providers=[make_id("source-scan")]
        )
        self.assertTrue(result.is_valid)


class TestProjectStateContract(unittest.TestCase):
    """Test Portable Project State (ProjectSpec) domain model."""

    def test_valid_project_spec(self):
        spec = ProjectSpec(
            id=make_id("my-saas-app"),
            name="My SaaS App",
            created_at="2026-01-15T10:30:00Z",
            updated_at="2026-01-20T14:45:00Z",
            project_type=make_id("saas"),
            capabilities=[make_id("authentication"), make_id("payments")],
            stack_bundle=make_id("nextjs-supabase"),
            technology_overrides={"database": make_id("postgresql")},
            runtime_preferences=RuntimePreferences(
                primary=make_id("codex"),
                fallbacks=[make_id("opencode")],
                project_local_only=True
            ),
            provider_preferences={"code-intelligence": make_id("codebase-memory")}
        )
        self.assertEqual(str(spec.id), "my-saas-app")
        self.assertEqual(str(spec.project_type), "saas")

    def test_project_spec_validation(self):
        spec = ProjectSpec.from_dict({
            "project": {
                "id": "my-app", "name": "My App",
                "created_at": "2026-01-15T10:30:00Z",
                "updated_at": "2026-01-20T14:45:00Z",
                "project_type": "saas",
                "capabilities": ["auth"],
                "stack_bundle": "nextjs-supabase",
                "runtime_preferences": {"primary": "codex", "fallbacks": ["opencode"]},
                "provider_preferences": {"code-intelligence": "codebase-memory"}
            }
        })

        result = spec.validate(
            known_project_types=[make_id("saas")],
            known_capabilities=[make_id("auth")],
            known_bundles=[make_id("nextjs-supabase")],
            known_technologies=[make_id("postgresql")],
            known_runtimes=[make_id("codex"), make_id("opencode")],
            known_providers=[make_id("codebase-memory")]
        )
        self.assertTrue(result.is_valid)


class TestNoRuntimeLeakage(unittest.TestCase):
    """Ensure runtime/vendor details don't leak into portable domain contracts."""

    def test_project_type_no_runtime_fields(self):
        """ProjectType should not have runtime-specific fields."""
        pt = ProjectType(
            id=make_id("saas"), name="SaaS", description="desc"
        )
        # Check that no runtime-related fields exist
        pt_dict = pt.to_dict()
        runtime_fields = ["runtime", "adapter", "codex", "opencode", "antigravity",
                          "gemini", "claude", "cursor", "mcp", "hooks"]
        for field in runtime_fields:
            self.assertNotIn(field, str(pt_dict).lower())

    def test_capability_no_vendor_fields(self):
        """Capability should describe WHAT not WHICH VENDOR."""
        cap = Capability(
            id=make_id("auth"), name="Auth", description="desc",
            example_implementations=[make_id("nextauth")]  # This is informational only
        )
        cap_dict = cap.to_dict()
        # example_implementations is allowed as informational
        # but capability itself should not have vendor-locked fields
        self.assertNotIn("vendor", str(cap_dict).lower())
        self.assertNotIn("provider", str(cap_dict).lower())

    def test_technology_stable_id_no_version(self):
        """Technology IDs must not embed versions."""
        tech = Technology(
            id=make_id("nextjs"),  # NOT nextjs-14
            name="Next.js",  # Display name can have version
            category="frontend", ecosystem="typescript",
            version_policy=VersionPolicy(
                strategy="latest-stable", default_version="14"
            )
        )
        self.assertEqual(str(tech.id), "nextjs")
        self.assertNotIn("14", str(tech.id))

    def test_stack_bundle_coherent_not_merged(self):
        """StackBundle should be one coherent combination, not merged presets."""
        bundle = StackBundle(
            id=make_id("nextjs-supabase"),
            name="Next.js + Supabase",
            description="Coherent bundle",
            technologies={
                "frontend": make_id("nextjs"),
                "backend": make_id("nextjs"),
                "database": make_id("postgresql")
            }
        )
        # Should not have merged preset names like "nextjs + astro"
        self.assertNotIn("+", str(bundle.id))

    def test_runtime_adapter_detection_not_permission(self):
        """Runtime adapter detection should not imply permission to modify global config."""
        adapter = RuntimeAdapter(
            id=make_id("codex"), name="Codex",
            detection=DetectionConfig(executables=["codex"]),
            permission_policy=PermissionPolicy(
                modifies_global_config=False,
                requires_explicit_consent=True
            )
        )
        # Detection present but permission policy explicitly denies global modification
        self.assertTrue(len(adapter.detection.executables) > 0)
        self.assertFalse(adapter.permission_policy.modifies_global_config)
        self.assertTrue(adapter.permission_policy.requires_explicit_consent)


class TestSchemaVersioning(unittest.TestCase):
    """Test schema version strategy."""

    def test_all_schemas_have_version(self):
        """All contract classes should enforce schema_version = '1.0.0'."""
        # ProjectType
        pt = ProjectType(id=make_id("test"), name="Test", description="desc")
        self.assertEqual(pt.schema_version, "1.0.0")

        # Capability
        cap = Capability(id=make_id("test"), name="Test", description="desc")
        self.assertEqual(cap.schema_version, "1.0.0")

        # Technology
        tech = Technology(
            id=make_id("test"), name="Test", category="frontend",
            ecosystem="typescript", version_policy=VersionPolicy(strategy="latest-stable")
        )
        self.assertEqual(tech.schema_version, "1.0.0")

        # StackBundle
        bundle = StackBundle(
            id=make_id("test"), name="Test", description="desc",
            technologies={"frontend": make_id("test"), "backend": make_id("test"), "database": make_id("test")}
        )
        self.assertEqual(bundle.schema_version, "1.0.0")

        # Compatibility
        compat = Compatibility()
        self.assertEqual(compat.schema_version, "1.0.0")

        # Resource
        resource = Resource(
            id=make_id("test"), name="Test", type="agent", description="desc",
            provenance=ResourceProvenance(source="bundled")
        )
        self.assertEqual(resource.schema_version, "1.0.0")

        # ExecutionPack
        pack = ExecutionPack(id=make_id("test"), name="Test", description="desc", core_roles=[make_id("test")])
        self.assertEqual(pack.schema_version, "1.0.0")

        # RuntimeAdapter
        adapter = RuntimeAdapter(id=make_id("test"), name="Test")
        self.assertEqual(adapter.schema_version, "1.0.0")

        # CapabilityProvider
        provider = CapabilityProvider(id=make_id("test"), capability=make_id("test"), priority=1)
        self.assertEqual(provider.schema_version, "1.0.0")

        # ProjectSpec
        spec = ProjectSpec(
            id=make_id("test"), name="Test",
            created_at="2026-01-15T10:30:00Z", updated_at="2026-01-15T10:30:00Z"
        )
        self.assertEqual(spec.schema_version, "1.0.0")

    def test_unknown_schema_version_rejected(self):
        """Unknown schema versions should be rejected."""
        with self.assertRaises(ValueError):
            ProjectType(
                id=make_id("test"), name="Test", description="desc",
                schema_version="2.0.0"  # Not supported
            )


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult utility."""

    def test_success_result(self):
        result = ValidationResult.success(warnings=["warning1"])
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.warnings, ["warning1"])

    def test_failure_result(self):
        from core.domain.contracts.errors import SchemaValidationError
        error = SchemaValidationError("test error", "field", "schema")
        result = ValidationResult.failure([error], warnings=["warn"])
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.warnings, ["warn"])

    def test_merge_results(self):
        result1 = ValidationResult.success(["w1"])
        result2 = ValidationResult.failure([], ["w2"])
        merged = result1.merge(result2)
        self.assertFalse(merged.is_valid)
        self.assertEqual(merged.warnings, ["w1", "w2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
