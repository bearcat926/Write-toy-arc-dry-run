"""AuditorComparator — Phase B dual-run comparison between legacy and structured auditor.

TEMP.md Wave 3 §5 Phase B: Compare old Auditor with Structured Auditor,
statistically track misses, false positives, and severity deviations.
"""
from dataclasses import dataclass, field
from pathlib import Path


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
        ftype = finding.get("type", finding.get("drift_type", "unknown"))
        desc = finding.get("description", finding.get("evidence", ""))[:50]
        return f"{ftype}:{desc}"

    def compare_reports(
        self,
        *,
        arc_id: str,
        chapter_id: str,
        legacy_review_path: Path,
        structured_report_path: Path,
        runtime_id: str = "",
    ) -> "AuditorCalibrationReport":
        """Compare legacy and structured reports, persist calibration report.

        TEMP.md §12: Phase B dual-run comparison with file I/O and report persistence.
        """
        import json

        # Parse legacy findings from review file
        legacy_findings = self._parse_legacy_findings(legacy_review_path)
        # Parse structured findings from JSON report
        structured_findings = self._parse_structured_findings(structured_report_path)

        # Compare
        comparison = self.compare(legacy_findings, structured_findings)

        # Build calibration report
        report = AuditorCalibrationReport(
            arc_id=arc_id,
            chapter_id=chapter_id,
            runtime_id=runtime_id,
            agreement_count=comparison.agreement_count,
            total_findings=comparison.total_findings,
            agreement_rate=comparison.agreement_rate,
            missed_count=len(comparison.missed_findings),
            extra_count=len(comparison.extra_findings),
            severity_diffs_count=len(comparison.severity_diffs),
            missed=comparison.missed_findings,
            extra=comparison.extra_findings,
            severity_diffs=comparison.severity_diffs,
        )

        # Persist
        report_dir = legacy_review_path.parent / "auditor_calibration"
        if not report_dir.exists():
            report_dir = legacy_review_path.parent.parent.parent / "workspace" / "reports" / "auditor_calibration" / arc_id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{chapter_id}.json"
        report_path.write_text(
            json.dumps(report.to_dict(), indent=2),
            encoding="utf-8",
        )

        return report

    @staticmethod
    def _parse_legacy_findings(path: Path) -> list[dict]:
        """Parse legacy review file for findings. Simple keyword extraction."""
        if not path.exists():
            return []
        content = path.read_text(encoding="utf-8", errors="replace")
        findings = []
        # Extract finding-like patterns from legacy markdown
        lines = content.split("\n")
        for line in lines:
            if any(kw in line.lower() for kw in ["ooc", "out of character", "inconsistent",
                                                    "contradiction", "violation", "error",
                                                    "issue", "warning", "problem"]):
                severity = "soft_warning"
                if "hard" in line.lower() or "critical" in line.lower():
                    severity = "hard_pause"
                elif "creative" in line.lower() or "review" in line.lower():
                    severity = "creative_review"
                findings.append({
                    "type": "legacy_finding",
                    "description": line.strip(),
                    "severity": severity,
                })
        return findings

    @staticmethod
    def _parse_structured_findings(path: Path) -> list[dict]:
        """Parse structured audit report JSON."""
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("findings", [])
        except (json.JSONDecodeError, KeyError):
            return []


@dataclass
class AuditorCalibrationReport:
    """Calibration report from Phase B dual-run comparison."""
    arc_id: str
    chapter_id: str
    runtime_id: str = ""
    agreement_count: int = 0
    total_findings: int = 0
    agreement_rate: float = 0.0
    missed_count: int = 0
    extra_count: int = 0
    severity_diffs_count: int = 0
    missed: list[dict] = field(default_factory=list)
    extra: list[dict] = field(default_factory=list)
    severity_diffs: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "schema_version": "AUDITOR_CALIBRATION_REPORT_V1",
            "arc_id": self.arc_id,
            "chapter_id": self.chapter_id,
            "runtime_id": self.runtime_id,
            "agreement_rate": round(self.agreement_rate, 3),
            "agreement_count": self.agreement_count,
            "total_findings": self.total_findings,
            "missed_count": self.missed_count,
            "extra_count": self.extra_count,
            "severity_diffs_count": self.severity_diffs_count,
            "missed": self.missed,
            "extra": self.extra,
            "severity_diffs": self.severity_diffs,
        }
