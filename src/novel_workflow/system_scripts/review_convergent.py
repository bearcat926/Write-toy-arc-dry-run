from ..schemas.review import ReviewReport, RevisionBrief


class ReviewConvergent:
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
