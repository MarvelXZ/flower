"""Tests for service-layer governance rules."""

from pathlib import Path


BOUNDED_CONTEXTS = {
    "tenancy",
    "identity",
    "locations",
    "plants",
    "pots",
    "devices",
    "telemetry",
    "care_engine",
    "integrations",
    "provider_ops",
    "marketplace",
    "notifications",
    "billing",
    "audit",
}

FORBIDDEN_API_WRITE_PATTERNS = (
    ".objects.create(",
    ".objects.update(",
    ".objects.update_or_create(",
    ".objects.get_or_create(",
    ".save(",
    ".delete(",
    ".bulk_create(",
    ".bulk_update(",
)


def test_service_only_write_rule_is_documented():
    root = Path(__file__).resolve().parents[2]
    rules = (root / "docs" / "governance" / "RULES.md").read_text(encoding="utf-8")
    ddd = (root / "docs" / "architecture" / "DDD_STRUCTURE.md").read_text(encoding="utf-8")

    assert "API views do not perform direct write operations on models" in ddd
    assert "API views do not perform direct write operations on models" in rules
    assert "services/" in ddd


def test_api_views_do_not_contain_direct_model_write_patterns():
    apps_dir = Path(__file__).resolve().parents[1] / "apps"

    for context in BOUNDED_CONTEXTS:
        api_views_dir = apps_dir / context / "api" / "views"
        if not api_views_dir.exists():
            continue

        for path in api_views_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            matches = [pattern for pattern in FORBIDDEN_API_WRITE_PATTERNS if pattern in source]
            assert matches == [], f"{path} contains direct write patterns: {matches}"
