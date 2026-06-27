"""Basic validation for generated Markdown CVs."""

from __future__ import annotations

import re

from personal_cv_agent.schemas import EvidencePack, MarkdownCV, ValidationIssue, ValidationReport


class BasicCVValidator:
    """Run lightweight checks that can grow into stronger hallucination control."""

    REQUIRED_SECTIONS = ("Summary", "Technical Skills", "Experience", "Selected Projects")

    def __init__(self, max_words: int = 1100, words_per_page: int = 475) -> None:
        self.max_words = max_words
        self.words_per_page = words_per_page

    def validate(self, cv: MarkdownCV, evidence_pack: EvidencePack) -> ValidationReport:
        issues: list[ValidationIssue] = []
        markdown = cv.markdown.strip()
        word_count = len(re.findall(r"\b\w+\b", markdown))
        estimated_pages = round(word_count / self.words_per_page, 2)
        evidence_text = " ".join(item.content for item in evidence_pack.items).lower()

        if not markdown:
            issues.append(ValidationIssue(severity="error", message="Generated Markdown CV is empty."))

        for section in self.REQUIRED_SECTIONS:
            if f"## {section}" not in markdown:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        section=section,
                        message=f"Missing required section: {section}.",
                    )
                )

        if word_count > self.max_words:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"CV is {word_count} words; target is {self.max_words} or fewer.",
                )
            )

        if estimated_pages > 2.0:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message=f"Estimated length is {estimated_pages} pages; target is 2 pages or fewer.",
                )
            )

        if not evidence_pack.items:
            issues.append(ValidationIssue(severity="error", message="No evidence was available for validation."))

        self._check_unsupported_numbers(markdown, evidence_text, issues)
        self._check_leadership_language(markdown, evidence_text, issues)

        return ValidationReport(
            passed=not any(issue.severity == "error" for issue in issues),
            issues=issues,
            estimated_pages=estimated_pages,
            word_count=word_count,
        )

    def _check_unsupported_numbers(
        self,
        markdown: str,
        evidence_text: str,
        issues: list[ValidationIssue],
    ) -> None:
        numbers = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?%?", markdown))
        for number in sorted(numbers):
            if number not in evidence_text:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message=f"Number appears in CV but not retrieved evidence: {number}.",
                    )
                )

    def _check_leadership_language(
        self,
        markdown: str,
        evidence_text: str,
        issues: list[ValidationIssue],
    ) -> None:
        if re.search(r"\bled\b|\bleading\b|\blead\b", markdown, flags=re.IGNORECASE) and not re.search(
            r"\bled\b|\bleading\b|\blead\b",
            evidence_text,
            flags=re.IGNORECASE,
        ):
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="Leadership wording appears in CV but was not found in retrieved evidence.",
                )
            )
