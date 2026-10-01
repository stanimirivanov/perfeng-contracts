"""Validate mechanical documentation and workflow policy without dependencies."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKIP = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".ty_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "vendor",
}
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
WORD = re.compile(r"[\w]+(?:['_-][\w]+)*", re.UNICODE)
INLINE_LINK = re.compile(r"!?\[[^]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")
REFERENCE_LINK = re.compile(
    r"^[ ]{0,3}\[[^]]+\]:\s*(?:<([^>]+)>|([^\s]+))(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*$"
)
ADR_FILE = re.compile(r"^(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
ADR_HEADING = re.compile(r"^# ADR-(\d{4}): (\S.*)$")
ADR_META = re.compile(r"^- ([A-Za-z][A-Za-z ]+):\s*(.*?)\s*$")
ADR_INDEX = re.compile(
    r"^\|\s*\[(?:ADR-)?(\d{4})\]\(([^)]+)\)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
)
MILESTONE = re.compile(r"^M\d{2} — \S.*$")
ADR_STATUSES = {"Proposed", "Accepted", "Rejected", "Deprecated", "Superseded"}
ADR_FIELDS = ("Status", "Date", "Milestone", "Deciders", "Supersedes", "Superseded by")
PR_HEADINGS = (
    "Linked work",
    "Outcome and scope",
    "Design, compatibility and release",
    "Verification",
    "Limitations and review",
)
PR_MARKERS = (
    "Issue:",
    "Milestone:",
    "Problem and resulting contract behavior:",
    "Affected producers and consumers:",
    "Boundaries and deliberate exclusions:",
    "Assumptions and unresolved questions:",
    "ADRs:",
    "Compatibility and migration:",
    "Security effects:",
    "Bundle/release effects:",
    "Commands and non-secret evidence:",
    "Checks not run, blocking reason and residual risk:",
    "Known limitations and follow-up:",
)


@dataclass(frozen=True, order=True)
class Violation:
    path: str
    line: int
    rule: str
    message: str
    fix: str
    policy: str

    def __str__(self) -> str:
        return (
            f"{self.path}:{self.line}: [{self.rule}] {self.message}; "
            f"fix: {self.fix}; policy: {self.policy}"
        )


@dataclass(frozen=True)
class MarkdownHeading:
    level: int
    text: str
    line: int


@dataclass
class Document:
    path: str
    lines: list[str]
    headings: list[MarkdownHeading]
    anchors: set[str]
    links: list[tuple[str, int]]
    words: int

    @property
    def h2(self) -> list[MarkdownHeading]:
        return [heading for heading in self.headings if heading.level == 2]


@dataclass(frozen=True)
class ADR:
    number: str
    path: str
    metadata: dict[str, tuple[str, int]]


def _anchor(text: str) -> str:
    text = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text).lower()
    result: list[str] = []
    space = False
    for character in text:
        if character.isalnum() or character in "_-":
            if space and result:
                result.append("-")
            result.append(character)
            space = False
        elif character.isspace():
            space = True
    return "".join(result)


def _parse(path: str, content: str) -> Document:
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    headings: list[MarkdownHeading] = []
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    links: list[tuple[str, int]] = []
    words = 0
    fence = ""
    width = 0
    for line_number, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        marker_match = re.match(r"^(`{3,}|~{3,})", stripped)
        if marker_match:
            marker = marker_match.group(1)
            if not fence:
                fence, width = marker[0], len(marker)
            elif marker[0] == fence and len(marker) >= width:
                fence, width = "", 0
            continue
        if fence:
            continue
        reference = REFERENCE_LINK.match(line)
        if reference:
            links.append((reference.group(1) or reference.group(2), line_number))
        prose = re.sub(r"`[^`]*`", " ", line)
        words += len(WORD.findall(prose))
        links.extend(
            (match.group(1) or match.group(2), line_number) for match in INLINE_LINK.finditer(prose)
        )
        heading_match = HEADING.match(stripped)
        if heading_match:
            heading = MarkdownHeading(
                len(heading_match.group(1)), heading_match.group(2).strip(), line_number
            )
            headings.append(heading)
            base = _anchor(heading.text)
            count = counts.get(base, 0)
            anchors.add(base if count == 0 else f"{base}-{count}")
            counts[base] = count + 1
    return Document(path, lines, headings, anchors, links, words)


def _documents(root: Path) -> dict[str, Document]:
    result: dict[str, Document] = {}
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part in SKIP for part in relative.parts):
            continue
        name = relative.as_posix()
        result[name] = _parse(name, path.read_text(encoding="utf-8"))
    return result


def _exact_path(root: Path, relative: Path) -> bool:
    current = root
    if relative == Path("."):
        return True
    for part in relative.parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError:
            return False
        if part not in names:
            return False
        current /= part
    return True


def _check_links(root: Path, documents: dict[str, Document]) -> list[Violation]:
    violations: list[Violation] = []
    resolved_root = root.resolve()
    for document in documents.values():
        for destination, line in document.links:
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or destination.startswith("//"):
                continue
            path_text = unquote(parsed.path)
            if not path_text:
                relative = Path(document.path)
            elif path_text.startswith(("/", "\\")):
                relative = Path(path_text.lstrip("/\\"))
            else:
                relative = Path(document.path).parent / path_text
            target = (resolved_root / relative).resolve()
            try:
                normalized = target.relative_to(resolved_root)
            except ValueError:
                violations.append(
                    Violation(
                        document.path,
                        line,
                        "docs.internal-link",
                        f'link "{destination}" escapes the repository root',
                        "link to a checked-in path",
                        "CONTRIBUTING.md#documentation",
                    )
                )
                continue
            if not _exact_path(resolved_root, normalized):
                violations.append(
                    Violation(
                        document.path,
                        line,
                        "docs.internal-link",
                        f'link "{destination}" does not resolve with matching case',
                        "correct the path or capitalization",
                        "CONTRIBUTING.md#documentation",
                    )
                )
                continue
            target_document = documents.get(normalized.as_posix())
            if (
                parsed.fragment
                and target_document is not None
                and unquote(parsed.fragment) not in target_document.anchors
            ):
                violations.append(
                    Violation(
                        document.path,
                        line,
                        "docs.internal-link",
                        f'link "{destination}" references a missing heading',
                        "use the target heading's generated anchor",
                        "CONTRIBUTING.md#documentation",
                    )
                )
    return violations


def _check_tldr(documents: dict[str, Document]) -> list[Violation]:
    violations: list[Violation] = []
    for document in documents.values():
        if document.path.startswith(".github/"):
            continue
        lower = document.path.lower()
        selective = (
            lower.startswith("docs/architecture/")
            or lower == "security.md"
            or any(
                word in lower
                for word in (
                    "compatibility",
                    "migration",
                    "workflow",
                    "operations",
                    "runbook",
                    "end-to-end",
                )
            )
        )
        if not (document.words >= 800 or len(document.h2) > 5 or selective):
            continue
        if document.h2 and document.h2[0].text == "TL;DR":
            continue
        line = document.h2[0].line if document.h2 else 1
        violations.append(
            Violation(
                document.path,
                line,
                "docs.tldr",
                "long or selectively consulted documentation does not start with `## TL;DR`",
                "add TL;DR after title and metadata",
                "CONTRIBUTING.md#documentation",
            )
        )
    return violations


def _read_adrs(documents: dict[str, Document]) -> tuple[dict[str, ADR], list[Violation]]:
    records: dict[str, ADR] = {}
    violations: list[Violation] = []
    for path, document in documents.items():
        if not path.startswith("docs/decisions/") or path == "docs/decisions/README.md":
            continue
        filename_match = ADR_FILE.fullmatch(Path(path).name)
        if not filename_match:
            violations.append(
                Violation(
                    path,
                    1,
                    "adr.filename",
                    "ADR filename is not four-digit lowercase kebab-case",
                    "rename it and update links",
                    "docs/decisions/README.md#naming-and-lifecycle",
                )
            )
            continue
        number = filename_match.group(1)
        heading = ADR_HEADING.fullmatch(document.lines[0] if document.lines else "")
        if heading is None or heading.group(1) != number:
            violations.append(
                Violation(
                    path,
                    1,
                    "adr.heading",
                    "ADR heading and filename number do not agree",
                    "use `# ADR-NNNN: Decision title`",
                    "docs/decisions/README.md#naming-and-lifecycle",
                )
            )
        metadata: dict[str, tuple[str, int]] = {}
        first_section = min((item.line for item in document.h2), default=len(document.lines) + 1)
        for line_number, line in enumerate(document.lines[1 : first_section - 1], start=2):
            match = ADR_META.fullmatch(line.strip())
            if match:
                if match.group(1) in metadata:
                    violations.append(
                        Violation(
                            path,
                            line_number,
                            "adr.metadata",
                            f'duplicate metadata field "{match.group(1)}"',
                            "keep exactly one value before the first section",
                            "docs/decisions/README.md#template",
                        )
                    )
                metadata[match.group(1)] = (match.group(2), line_number)
        for field in ADR_FIELDS:
            if field not in metadata:
                violations.append(
                    Violation(
                        path,
                        1,
                        "adr.metadata",
                        f'missing metadata field "{field}"',
                        f"add `- {field}: ...`",
                        "docs/decisions/README.md#template",
                    )
                )
        status = metadata.get("Status", ("", 1))
        if status[0] and status[0] not in ADR_STATUSES:
            violations.append(
                Violation(
                    path,
                    status[1],
                    "adr.status",
                    f'unsupported status "{status[0]}"',
                    "use a documented lifecycle status",
                    "docs/decisions/README.md#naming-and-lifecycle",
                )
            )
        recorded_date = metadata.get("Date", ("", 1))
        if recorded_date[0]:
            try:
                date.fromisoformat(recorded_date[0])
            except ValueError:
                violations.append(
                    Violation(
                        path,
                        recorded_date[1],
                        "adr.date",
                        f'invalid ISO date "{recorded_date[0]}"',
                        "use YYYY-MM-DD",
                        "docs/decisions/README.md#template",
                    )
                )
        milestone = metadata.get("Milestone", ("", 1))
        if milestone[0] and not MILESTONE.fullmatch(milestone[0]):
            violations.append(
                Violation(
                    path,
                    milestone[1],
                    "adr.milestone",
                    f'invalid milestone "{milestone[0]}"',
                    "use the exact `MNN — Outcome` title",
                    "CONTRIBUTING.md#milestones",
                )
            )
        if number in records:
            violations.append(
                Violation(
                    path,
                    1,
                    "adr.number",
                    f"ADR-{number} duplicates {records[number].path}",
                    "renumber the later unpublished ADR from fresh state",
                    "docs/decisions/README.md#naming-and-lifecycle",
                )
            )
        else:
            records[number] = ADR(number, path, metadata)
    return records, violations


def _check_adrs(documents: dict[str, Document]) -> list[Violation]:
    records, violations = _read_adrs(documents)
    numbers = sorted(int(number) for number in records)
    if numbers != list(range(1, len(numbers) + 1)):
        violations.append(
            Violation(
                "docs/decisions/README.md",
                1,
                "adr.sequence",
                "ADR numbers are not contiguous from 0001",
                "restore history or renumber unpublished ADRs",
                "docs/decisions/README.md#naming-and-lifecycle",
            )
        )
    index = documents.get("docs/decisions/README.md")
    if index is None:
        return violations + [
            Violation(
                "docs/decisions/README.md",
                1,
                "adr.index",
                "ADR index is missing",
                "restore it",
                "CONTRIBUTING.md#policy-language-and-sources-of-truth",
            )
        ]
    entries: dict[str, tuple[str, str, int]] = {}
    for line_number, line in enumerate(index.lines, start=1):
        match = ADR_INDEX.match(line.strip())
        if match:
            if match.group(1) in entries:
                violations.append(
                    Violation(
                        index.path,
                        line_number,
                        "adr.index",
                        f"ADR-{match.group(1)} has duplicate index rows",
                        "keep one row per decision number",
                        "docs/decisions/README.md#index",
                    )
                )
            entries[match.group(1)] = (match.group(2).strip(), match.group(3).strip(), line_number)
    for number, record in records.items():
        entry = entries.get(number)
        if entry is None:
            violations.append(
                Violation(
                    record.path,
                    1,
                    "adr.index",
                    f"ADR-{number} is absent from the index",
                    "add a linked index row",
                    "docs/decisions/README.md#index",
                )
            )
            continue
        if Path(entry[0]).name != Path(record.path).name:
            violations.append(
                Violation(
                    index.path,
                    entry[2],
                    "adr.index",
                    f"ADR-{number} index link is wrong",
                    "link its decision file",
                    "docs/decisions/README.md#index",
                )
            )
        if entry[1] != record.metadata.get("Status", ("", 1))[0]:
            violations.append(
                Violation(
                    index.path,
                    entry[2],
                    "adr.index",
                    f"ADR-{number} index status differs",
                    "copy metadata status",
                    "docs/decisions/README.md#index",
                )
            )
    for number, entry in entries.items():
        if number not in records:
            violations.append(
                Violation(
                    index.path,
                    entry[2],
                    "adr.index",
                    f"ADR-{number} has no file",
                    "restore it or remove an unpublished row",
                    "docs/decisions/README.md#index",
                )
            )
    for record in records.values():
        status = record.metadata.get("Status", ("", 1))[0]
        replacement, line = record.metadata.get("Superseded by", ("", 1))
        references = re.findall(r"ADR-(\d{4})", replacement)
        if status == "Superseded" and not references:
            violations.append(
                Violation(
                    record.path,
                    line,
                    "adr.supersession",
                    "superseded ADR has no replacement",
                    "link its replacement",
                    "docs/decisions/README.md#naming-and-lifecycle",
                )
            )
        for reference in references:
            if reference not in records:
                violations.append(
                    Violation(
                        record.path,
                        line,
                        "adr.supersession",
                        f"replacement ADR-{reference} does not exist",
                        "link an existing ADR",
                        "docs/decisions/README.md#naming-and-lifecycle",
                    )
                )
    return violations


def _issue_body(document: Document) -> str | None:
    body: list[str] = []
    inside = False
    for line in document.lines:
        stripped = line.strip()
        if not inside and stripped.lower() in {"```markdown", "~~~markdown"}:
            inside, body = True, []
        elif inside and stripped in {"```", "~~~"}:
            candidate = "\n".join(body)
            if "**Repository:**" in candidate and "**Milestone:**" in candidate:
                return candidate
            inside = False
        elif inside:
            body.append(line)
    return None


def _check_templates(documents: dict[str, Document]) -> list[Violation]:
    violations: list[Violation] = []
    policy = documents.get("CONTRIBUTING.md")
    issue = documents.get(".github/ISSUE_TEMPLATE/work-item.md")
    pull_request = documents.get(".github/PULL_REQUEST_TEMPLATE.md")
    if policy is None or issue is None:
        return [
            Violation(
                "CONTRIBUTING.md",
                1,
                "template.issue",
                "policy or issue template is missing",
                "restore both",
                "CONTRIBUTING.md#required-issue-structure",
            )
        ]
    body = _issue_body(policy)
    if body is None:
        violations.append(
            Violation(
                policy.path,
                1,
                "template.issue",
                "canonical fenced issue body is missing",
                "restore it",
                "CONTRIBUTING.md#required-issue-structure",
            )
        )
    else:
        canonical = _parse("canonical.md", body)
        issue_content = "\n".join(issue.lines)
        repository_marker = "**Repository:** perfeng-contracts"
        if repository_marker not in body or repository_marker not in issue_content:
            violations.append(
                Violation(
                    issue.path,
                    1,
                    "template.issue",
                    "issue template repository identity differs from canonical policy",
                    f"restore `{repository_marker}` in policy and template",
                    "CONTRIBUTING.md#required-issue-structure",
                )
            )
        if [item.text for item in canonical.h2] != [item.text for item in issue.h2]:
            violations.append(
                Violation(
                    issue.path,
                    1,
                    "template.issue",
                    "issue headings differ from canonical policy",
                    "align names and order",
                    "CONTRIBUTING.md#required-issue-structure",
                )
            )
        canonical_checks = sum(
            line.strip().startswith(("- [ ] ", "- [x] ", "- [X] ")) for line in canonical.lines
        )
        actual_checks = sum(
            line.strip().startswith(("- [ ] ", "- [x] ", "- [X] ")) for line in issue.lines
        )
        if canonical_checks != actual_checks:
            violations.append(
                Violation(
                    issue.path,
                    1,
                    "template.issue",
                    "acceptance checklist differs from canonical policy",
                    "align the checkboxes",
                    "CONTRIBUTING.md#required-issue-structure",
                )
            )
    if pull_request is None:
        violations.append(
            Violation(
                ".github/PULL_REQUEST_TEMPLATE.md",
                1,
                "template.pull-request",
                "pull request template is missing",
                "restore it",
                "CONTRIBUTING.md#pull-request-description",
            )
        )
    else:
        if tuple(item.text for item in pull_request.h2) != PR_HEADINGS:
            violations.append(
                Violation(
                    pull_request.path,
                    1,
                    "template.pull-request",
                    "pull request headings have drifted",
                    "restore names and order",
                    "CONTRIBUTING.md#pull-request-description",
                )
            )
        content = "\n".join(pull_request.lines)
        for marker in PR_MARKERS:
            if marker not in content:
                violations.append(
                    Violation(
                        pull_request.path,
                        1,
                        "template.pull-request",
                        f'missing prompt "{marker}"',
                        "restore the required prompt",
                        "CONTRIBUTING.md#pull-request-description",
                    )
                )
    return violations


def check_repository(root: Path) -> list[Violation]:
    documents = _documents(root)
    return sorted(
        (
            *_check_links(root, documents),
            *_check_tldr(documents),
            *_check_adrs(documents),
            *_check_templates(documents),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    root = parser.parse_args().root.resolve()
    violations = check_repository(root)
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        print(f"repo-check: found {len(violations)} policy violation(s)", file=sys.stderr)
        return 1
    print("repo-check: repository policy checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
