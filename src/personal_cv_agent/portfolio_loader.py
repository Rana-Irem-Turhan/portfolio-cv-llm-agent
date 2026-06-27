"""Portfolio source loaders for project and profile evidence."""

from __future__ import annotations

import re
from pathlib import Path


class PortfolioSourceLoader:
    """Load portfolio source files as first-class CV knowledge documents."""

    DEFAULT_PATTERNS = {
        "*.md",
        "*.html",
        "src/data/*.ts",
    }

    def load(self, portfolio_path: Path) -> list[Document]:
        from langchain_core.documents import Document

        portfolio_path = portfolio_path.expanduser().resolve()

        if not portfolio_path.exists():
            raise FileNotFoundError(f"Portfolio path not found: {portfolio_path}")

        files = self._iter_source_files(portfolio_path)
        documents: list[Document] = []

        for file_path in files:
            raw_text = file_path.read_text(encoding="utf-8", errors="replace")
            text = self._clean_source_text(raw_text, suffix=file_path.suffix.lower())
            if not text:
                continue

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "source_type": "portfolio",
                        "source_file": file_path.name,
                        "source_path": str(file_path),
                        "relative_path": str(file_path.relative_to(portfolio_path)),
                    },
                )
            )

        return documents

    def _iter_source_files(self, portfolio_path: Path) -> list[Path]:
        if portfolio_path.is_file():
            return [portfolio_path]

        files: list[Path] = []
        for pattern in self.DEFAULT_PATTERNS:
            files.extend(portfolio_path.rglob(pattern))

        ignored_parts = {".git", "node_modules", ".next", "dist", "build"}
        return sorted(
            {
                file_path
                for file_path in files
                if not ignored_parts.intersection(file_path.parts)
            }
        )

    @staticmethod
    def _clean_source_text(text: str, suffix: str) -> str:
        text = PortfolioSourceLoader._normalize_text_artifacts(text.replace("\x00", " "))

        if suffix == ".html":
            text = re.sub(r"(?is)<script.*?</script>", " ", text)
            text = re.sub(r"(?is)<style.*?</style>", " ", text)
            text = re.sub(r"(?s)<[^>]+>", " ", text)

        if suffix == ".ts":
            text = PortfolioSourceLoader._clean_typescript_text(text)

        text = PortfolioSourceLoader._normalize_text_artifacts(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = "\n".join(line.strip() for line in text.splitlines())
        return text.strip()

    @staticmethod
    def _clean_typescript_text(text: str) -> str:
        text = re.sub(r"\bexport\s+type\s+\w+\s*=\s*\{.*?\};", " ", text, flags=re.DOTALL)
        text = re.sub(
            r"^\s*export\s+const\s+(\w+).*?=\s*",
            lambda match: f"\n{match.group(1).replace('_', ' ')}\n",
            text,
            flags=re.MULTILINE,
        )
        text = re.sub(
            r"\b(isPrivate|repoUrl|demoUrl|caseStudyUrl|slidesUrl|paperUrl|certificateUrl)\s*:",
            " ",
            text,
        )
        text = re.sub(r"[{}\[\];]", " ", text)
        text = text.replace('"', " ").replace("'", " ").replace(",", "\n")
        text = re.sub(
            r"\b(id|title|role|company|date|description|tech|category|problem|approach|outcome|issuer|status)\s*:",
            r"\1: ",
            text,
        )
        text = re.sub(r"\bconst\s+\w+.*", " ", text)
        return text

    @staticmethod
    def _normalize_text_artifacts(text: str) -> str:
        replacements = {
            "\u2013": "-",
            "\u2014": "-",
            "\u2022": "-",
            "\u201c": '"',
            "\u201d": '"',
            "\u2018": "'",
            "\u2019": "'",
            "\u00b7": "-",
            "\u00c2": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Drop common mojibake fragments from copied portfolio HTML.
        text = re.sub(r"[\u00e2\u00f0][^\s]{0,12}", " ", text)
        return text
