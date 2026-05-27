from ..schemas.review import ReviewReport, RevisionBrief


class ReviewConvergent:
    def parse_raw_review(self, reviewer_role: str, raw_text: str) -> ReviewReport:
        """Parse raw reviewer output text into a ReviewReport.

        Expected format: key-value lines like
            blocking_issues: ...
            recommended_action: ...
        """
        blocking_issues: list[str] = []
        recommended_action = "approve"

        for line in raw_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "blocking_issues" and value:
                    blocking_issues.append(value)
                elif key == "recommended_action" and value:
                    recommended_action = value

        return ReviewReport(
            reviewer_role=reviewer_role,
            blocking_issues=blocking_issues,
            recommended_action=recommended_action,
        )

    def converge(self, chapter_id: str, reviews: list[ReviewReport]) -> RevisionBrief:
        all_revisions = []
        source_roles = []
        for r in reviews:
            source_roles.append(r.reviewer_role)
            all_revisions.extend(r.high_priority_revisions)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for rev in all_revisions:
            if rev not in seen:
                seen.add(rev)
                unique.append(rev)

        # Cap at 5
        return RevisionBrief(
            chapter_id=chapter_id,
            items=unique[:5],
            source_reviews=source_roles,
        )
