"""AuditorComparator — Phase B dual-run comparison between legacy and structured auditor.

TEMP.md Wave 3 §5 Phase B: Compare old Auditor with Structured Auditor,
statistically track misses, false positives, and severity deviations.
"""
from dataclasses import dataclass, field


@dataclass
class ComparisonResult:
    """Result of comparing legacy and structured auditor outputs."""
    missed_findings: list[dict] = field(default_factory=list)   # Structured has, legacy doesn't
    extra_findings: list[dict] = field(default_factory=list)    # Legacy has, structured doesn't
    severity_diffs: list[dict] = field(default_factory=list)    # Severity mismatch
    agreement_count: int = 0
    total_findings: int = 0
    agreement_rate: float = 0.0


class AuditorComparator:
    """Compares legacy markdown review with structured audit report."""

    def compare(
        self,
        legacy_findings: list[dict],
        structured_findings: list[dict],
    ) -> ComparisonResult:
        """Compare legacy and structured findings.

        Args:
            legacy_findings: List of dicts with 'type', 'description', 'severity' from legacy
            structured_findings: List of dicts with 'drift_type', 'evidence', 'severity' from structured

        Returns:
            ComparisonResult with comparison metrics
        """
        result = ComparisonResult()

        # Build lookup sets
        legacy_keys = {self._finding_key(f): f for f in legacy_findings}
        structured_keys = {self._finding_key(f): f for f in structured_findings}

        # Find agreements and misses
        for key, s_finding in structured_keys.items():
            if key in legacy_keys:
                result.agreement_count += 1
                l_finding = legacy_keys[key]
                # Check severity agreement
                s_sev = s_finding.get("severity", "none")
                l_sev = l_finding.get("severity", "none")
                if s_sev != l_sev:
                    result.severity_diffs.append({
                        "key": key,
                        "structured_severity": s_sev,
                        "legacy_severity": l_sev,
                    })
            else:
                result.missed_findings.append({
                    "key": key,
                    "finding": s_finding,
                    "reason": "structured_has_legacy_misses",
                })

        for key, l_finding in legacy_keys.items():
            if key not in structured_keys:
                result.extra_findings.append({
                    "key": key,
                    "finding": l_finding,
                    "reason": "legacy_has_structured_misses",
                })

        total = len(legacy_findings) + len(structured_findings) - result.agreement_count
        result.total_findings = total
        result.agreement_rate = result.agreement_count / total if total > 0 else 1.0

        return result

    @staticmethod
    def _finding_key(finding: dict) -> str:
        """Generate a comparable key for a finding."""
        # Use type/drift_type + first 50 chars of description/evidence
        ftype = finding.get("type", finding.get("drift_type", "unknown"))
        desc = finding.get("description", finding.get("evidence", ""))[:50]
        return f"{ftype}:{desc}"
