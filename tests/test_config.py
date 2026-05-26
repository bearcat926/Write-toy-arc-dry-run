from novel_workflow.config import (
    SUPPORTED_SCHEMA_VERSIONS,
    PAUSE_TAXONOMY,
    RETRY_POLICY,
    ROLE_ALLOWLIST,
)


def test_supported_versions_is_set():
    assert isinstance(SUPPORTED_SCHEMA_VERSIONS, set)
    assert "1.0" in SUPPORTED_SCHEMA_VERSIONS


def test_pause_taxonomy_has_three_types():
    assert set(PAUSE_TAXONOMY) == {"hard_pause", "creative_review", "soft_warning"}


def test_retry_policy_has_defaults():
    assert RETRY_POLICY["max_schema_repairable"] == 2
    assert RETRY_POLICY["max_audit_failure"] == 2


def test_role_allowlist_excludes_agent_from_canon():
    agent_paths = ROLE_ALLOWLIST["agent"]["write"]
    assert "canon" not in agent_paths
    assert "ledgers" not in agent_paths
