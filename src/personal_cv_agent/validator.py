"""Basic validation for generated Markdown CVs."""

from __future__ import annotations

import re

from personal_cv_agent.schemas import EvidencePack, MarkdownCV, ValidationIssue, ValidationReport


class BasicCVValidator:
    """Run lightweight checks that can grow into stronger hallucination control."""

    REQUIRED_SECTIONS = ("Summary", "Technical Skills", "Experience", "Selected Projects")
    ENCODING_ARTIFACT_RE = re.compile(r"Ã|Â|â€|â€œ|â€|ðŸ|�|\u00e2|\u00f0")
    RAW_CODE_RE = re.compile(
        r"\bconst\b|\bexport\b|function\s+\w+|=>|className|href=|</|/>|Experience\[\]",
        flags=re.IGNORECASE,
    )
    NAVIGATION_RE = re.compile(
        r"view certificate|download cv|interactive demo|github repository|read case study|view presentation",
        flags=re.IGNORECASE,
    )
    FUTURE_WORK_RE = re.compile(
        r"expected to|will work on|incoming|expected work|planning to",
        flags=re.IGNORECASE,
    )
    DATE_ONLY_RE = re.compile(
        r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)?\s*\d{4}\s*(?:[-/]\s*(?:present|\d{4}))?$",
        flags=re.IGNORECASE,
    )

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
        self._check_forbidden_patterns(markdown, issues)
        self._check_bullets(markdown, issues)
        self._check_section_contamination(markdown, issues)
        self._check_repeated_bullets(markdown, issues)

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
                        severity="error",
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

    def _check_forbidden_patterns(self, markdown: str, issues: list[ValidationIssue]) -> None:
        checks = (
            (self.ENCODING_ARTIFACT_RE, "Encoding artifact detected in generated CV."),
            (self.RAW_CODE_RE, "Raw code or markup fragment detected in generated CV."),
            (self.NAVIGATION_RE, "Portfolio navigation/UI text detected in generated CV."),
            (self.FUTURE_WORK_RE, "Future or expected-work phrasing detected in generated CV."),
        )
        for pattern, message in checks:
            if pattern.search(markdown):
                issues.append(ValidationIssue(severity="error", message=message))

    def _check_bullets(self, markdown: str, issues: list[ValidationIssue]) -> None:
        for section, bullet in self._iter_section_bullets(markdown):
            words = re.findall(r"\b\w+\b", bullet)
            if len(words) < 6:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        section=section,
                        message=f"Bullet is too short or fragment-like: {bullet}",
                    )
                )
            if len(bullet) > 260:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        section=section,
                        message=f"Bullet is too long and likely raw evidence: {bullet[:120]}...",
                    )
                )
            if self.DATE_ONLY_RE.fullmatch(bullet.strip(" .")):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        section=section,
                        message=f"Date-only bullet detected: {bullet}",
                    )
                )

    def _check_section_contamination(self, markdown: str, issues: list[ValidationIssue]) -> None:
        education = self._section_text(markdown, "Education")
        certifications = self._section_text(markdown, "Certifications")
        experience = self._section_text(markdown, "Experience")
        projects = self._section_text(markdown, "Selected Projects")

        education_forbidden = (
            "community",
            "project",
            "etl",
            "pipeline",
            "content",
            "workshop",
            "machine learning",
            "portfolio",
        )
        certification_forbidden = (
            "project",
            "etl",
            "architecture",
            "pipeline",
            "community",
            "github",
            "download",
            "portfolio",
        )
        experience_forbidden = ("expected to", "incoming", "will work on")
        project_forbidden = ("community lead", "technical community", "organized and moderated")

        self._flag_forbidden_terms("Education", education, education_forbidden, issues)
        self._flag_forbidden_terms("Certifications", certifications, certification_forbidden, issues)
        self._flag_forbidden_terms("Experience", experience, experience_forbidden, issues)
        self._flag_forbidden_terms("Selected Projects", projects, project_forbidden, issues)

    def _check_repeated_bullets(self, markdown: str, issues: list[ValidationIssue]) -> None:
        seen = set()
        for section, bullet in self._iter_section_bullets(markdown):
            normalized = re.sub(r"\W+", " ", bullet.lower()).strip()
            if normalized in seen:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        section=section,
                        message=f"Repeated bullet detected: {bullet}",
                    )
                )
            seen.add(normalized)

    def _iter_section_bullets(self, markdown: str):
        current_section: str | None = None
        for line in markdown.splitlines():
            if line.startswith("## "):
                current_section = line.removeprefix("## ").strip()
                continue
            if line.startswith("- "):
                yield current_section or "unknown", line.removeprefix("- ").strip()

    def _section_text(self, markdown: str, section: str) -> str:
        pattern = re.compile(rf"^## {re.escape(section)}\s*$([\s\S]*?)(?=^## |\Z)", flags=re.MULTILINE)
        match = pattern.search(markdown)
        return match.group(1).lower() if match else ""

    def _flag_forbidden_terms(
        self,
        section: str,
        text: str,
        terms: tuple[str, ...],
        issues: list[ValidationIssue],
    ) -> None:
        for term in terms:
            if term in text:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        section=section,
                        message=f"Section contamination detected: {term!r} appears in {section}.",
                    )
                )
