from novel_workflow.config import PauseType
from novel_workflow.pause.pause_detector import EmergencyPauseDetector, RetryPolicy
from novel_workflow.schemas.failure_event import FailureCategory, FailureEvent


class TestRouteFailureHardPause:
    def setup_method(self):
        self.detector = EmergencyPauseDetector()

    def test_security_violation_is_hard_pause(self):
        event = FailureEvent(
            category=FailureCategory.SECURITY_VIOLATION,
            source="gate_validator",
            message="unauthorized write",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.HARD_PAUSE
        assert "security_violation" in report.reason

    def test_path_violation_is_hard_pause(self):
        event = FailureEvent(
            category=FailureCategory.PATH_VIOLATION,
            source="system_script",
            artifact_path="/bad/path",
            message="path escape",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.HARD_PAUSE
        assert "path_violation" in report.reason
        assert "/bad/path" in report.affected_artifacts

    def test_apply_validation_fail_is_hard_pause(self):
        event = FailureEvent(
            category=FailureCategory.APPLY_VALIDATION_FAIL,
            source="apply_validator",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.HARD_PAUSE

    def test_gate_evidence_missing_is_hard_pause(self):
        event = FailureEvent(
            category=FailureCategory.GATE_EVIDENCE_MISSING,
            source="gate_validator",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.HARD_PAUSE

    def test_canon_conflict_is_hard_pause(self):
        event = FailureEvent(
            category=FailureCategory.CANON_DIRECT_CONFLICT,
            source="audit",
            chapter_id="ch03",
            evidence="Character died in ch01 but appears in ch03",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.HARD_PAUSE
        assert "canon_direct_conflict" in report.reason
        assert report.evidence == "Character died in ch01 but appears in ch03"


class TestRouteFailureCreativeReview:
    def setup_method(self):
        self.detector = EmergencyPauseDetector()

    def test_audit_blocking_is_creative_review(self):
        event = FailureEvent(
            category=FailureCategory.AUDIT_BLOCKING,
            source="audit",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.CREATIVE_REVIEW

    def test_aws_canon_conflict_is_creative_review(self):
        event = FailureEvent(
            category=FailureCategory.AWS_CANON_CONFLICT,
            source="chapter_effect",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.CREATIVE_REVIEW

    def test_claim_evidence_mismatch_is_creative_review(self):
        event = FailureEvent(
            category=FailureCategory.CLAIM_EVIDENCE_MISMATCH,
            source="gate_validator",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.CREATIVE_REVIEW


class TestRouteFailureSoftWarning:
    def setup_method(self):
        self.detector = EmergencyPauseDetector()

    def test_chapter_effect_fail_is_soft_warning(self):
        event = FailureEvent(
            category=FailureCategory.CHAPTER_EFFECT_FAIL,
            source="chapter_effect",
            chapter_id="ch05",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.SOFT_WARNING
        assert "chapter_effect_fail" in report.reason

    def test_evidence_not_found_is_soft_warning(self):
        event = FailureEvent(
            category=FailureCategory.EVIDENCE_NOT_FOUND,
            source="gate_validator",
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.SOFT_WARNING

    def test_retryable_schema_error_is_soft_warning(self):
        event = FailureEvent(
            category=FailureCategory.MALFORMED_JSON,
            source="proposal_validator",
            retryable=True,
        )
        report = self.detector.route_failure(event)
        assert report.pause_type == PauseType.SOFT_WARNING


class TestRetryPolicy:
    def test_retryable_error_below_max_is_retryable(self):
        policy = RetryPolicy(max_retries=2)
        event = FailureEvent(
            category=FailureCategory.MALFORMED_JSON,
            source="proposal_validator",
            retryable=True,
            retry_count=0,
            max_retries=2,
        )
        assert policy.is_retryable(event) is True
        assert policy.should_pause(event) is False

    def test_retryable_error_at_max_is_not_retryable(self):
        policy = RetryPolicy(max_retries=2)
        event = FailureEvent(
            category=FailureCategory.MALFORMED_JSON,
            source="proposal_validator",
            retryable=True,
            retry_count=2,
            max_retries=2,
        )
        assert policy.is_retryable(event) is False
        assert policy.should_pause(event) is True

    def test_non_retryable_error_is_not_retryable(self):
        policy = RetryPolicy(max_retries=2)
        event = FailureEvent(
            category=FailureCategory.SECURITY_VIOLATION,
            source="gate_validator",
            retryable=False,
            retry_count=0,
        )
        assert policy.is_retryable(event) is False
        assert policy.should_pause(event) is True

    def test_retry_exhaustion_triggers_pause(self):
        policy = RetryPolicy(max_retries=2)
        event = FailureEvent(
            category=FailureCategory.MISSING_REQUIRED_FIELD,
            source="proposal_validator",
            retryable=True,
            retry_count=2,
            max_retries=2,
        )
        assert policy.should_pause(event) is True

    def test_custom_max_retries(self):
        policy = RetryPolicy(max_retries=3)
        event = FailureEvent(
            category=FailureCategory.WRONG_TYPE,
            source="proposal_validator",
            retryable=True,
            retry_count=2,
            max_retries=3,
        )
        assert policy.is_retryable(event) is True
        assert policy.should_pause(event) is False

    def test_retry_count_increment(self):
        event = FailureEvent(
            category=FailureCategory.INVALID_ENUM,
            source="proposal_validator",
            retryable=True,
            retry_count=0,
            max_retries=2,
        )
        policy = RetryPolicy(max_retries=2)
        assert policy.is_retryable(event) is True

        # Simulate incrementing retry count
        event.retry_count += 1
        assert policy.is_retryable(event) is True

        event.retry_count += 1
        assert policy.is_retryable(event) is False
        assert policy.should_pause(event) is True

    def test_retry_exhaustion_blocks_merge(self):
        """Retry exhaustion should prevent AWS merge."""
        policy = RetryPolicy(max_retries=2)
        event = FailureEvent(
            category=FailureCategory.MALFORMED_JSON,
            source="proposal_validator",
            retryable=True,
            retry_count=2,
        )
        assert policy.should_pause(event) is True
