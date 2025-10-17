#!/usr/bin/env python3
"""
Git Notes Browser - A single-file web server for browsing PR summaries stored in git notes.

Usage:
    python notes_browser.py [--port PORT] [--repo PATH] [--ref REF]

Dependencies:
    pip install flask markdown2
"""

import argparse
import re
import subprocess
from datetime import datetime
from typing import Optional
from flask import Flask, render_template_string, request, jsonify
import markdown2

app = Flask(__name__)

# Configuration
REPO_PATH = "."
NOTES_REF = "refs/notes/commits"


class GitNotesReader:
    """Handle reading git notes from repository."""

    def __init__(self, repo_path: str = ".", notes_ref: str = "refs/notes/commits"):
        self.repo_path = repo_path
        self.notes_ref = notes_ref

    def _run_git_command(self, args: list[str]) -> tuple[bool, str]:
        """Run a git command and return success status and output."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0, result.stdout.strip()
        except Exception as e:
            return False, str(e)

    def list_available_refs(self) -> list[str]:
        """List all available git notes refs."""
        success, output = self._run_git_command(
            ["for-each-ref", "--format=%(refname)", "refs/notes/"]
        )

        if not success or not output:
            return ["refs/notes/commits"]  # Default ref

        refs = [line.strip() for line in output.split("\n") if line.strip()]
        return refs if refs else ["refs/notes/commits"]

    def get_file_at_commit(self, commit_sha: str, file_path: str) -> Optional[str]:
        """Get file content at a specific commit."""
        success, output = self._run_git_command(
            ["show", f"{commit_sha}:{file_path}"]
        )
        return output if success else None

    def get_file_lines_at_commit(
        self, commit_sha: str, file_path: str, line_num: int, context_lines: int = 3
    ) -> Optional[dict]:
        """Get specific lines from a file at a commit with context.

        Returns:
            dict with keys: lines (list of tuples (line_num, line_content)),
                           start_line, end_line
        """
        content = self.get_file_at_commit(commit_sha, file_path)
        if not content:
            return None

        lines = content.split("\n")
        start_line = max(1, line_num - context_lines)
        end_line = min(len(lines), line_num + context_lines)

        # Extract lines with their numbers
        result_lines = []
        for i in range(start_line - 1, end_line):
            if i < len(lines):
                result_lines.append((i + 1, lines[i]))

        return {
            "lines": result_lines,
            "start_line": start_line,
            "end_line": end_line,
            "target_line": line_num
        }

    def list_notes(self) -> list[dict]:
        """List all commits that have notes attached."""
        success, output = self._run_git_command(
            ["notes", "--ref", self.notes_ref, "list"]
        )

        if not success or not output:
            return []

        notes = []
        for line in output.split("\n"):
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) >= 2:
                note_sha, commit_sha = parts[0], parts[1]

                # Get commit info
                success, commit_info = self._run_git_command([
                    "log", "-1", "--format=%H%n%an%n%ae%n%at%n%s",
                    commit_sha
                ])

                if success:
                    lines = commit_info.split("\n")
                    if len(lines) >= 5:
                        commit_hash, author_name, author_email, timestamp, subject = lines[:5]

                        # Get note content to extract PR number
                        note_content = self.get_note(commit_sha)
                        pr_number = self._extract_pr_number(note_content)

                        notes.append({
                            "commit_sha": commit_sha,
                            "commit_sha_short": commit_sha[:7],
                            "note_sha": note_sha,
                            "author_name": author_name,
                            "author_email": author_email,
                            "timestamp": int(timestamp),
                            "date": datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M:%S"),
                            "subject": subject,
                            "pr_number": pr_number,
                        })

        # Sort by timestamp, newest first
        notes.sort(key=lambda x: x["timestamp"], reverse=True)
        return notes

    def get_note(self, commit_sha: str) -> Optional[str]:
        """Get the note content for a specific commit."""
        success, output = self._run_git_command(
            ["notes", "--ref", self.notes_ref, "show", commit_sha]
        )
        return output if success else None

    def _extract_pr_number(self, note_content: Optional[str]) -> Optional[int]:
        """Extract PR number from note content."""
        if not note_content:
            return None

        # Look for "# 🟣 PR #123:" pattern
        match = re.search(r"#\s*🟣\s*PR\s*#(\d+)", note_content)
        if match:
            return int(match.group(1))

        # Fallback: look for any "PR #123" pattern
        match = re.search(r"PR\s*#(\d+)", note_content)
        if match:
            return int(match.group(1))

        return None


def parse_note_sections(content: str) -> dict:
    """Parse markdown note content into structured sections."""
    sections = {
        "title": "",
        "pr_number": None,
        "pr_url": "",
        "metadata": "",
        "description": "",
        "commits": "",
        "file_changes": "",
        "reviews": "",
        "discussion": "",
        "conversation": "",
        "code_comments": "",
        "checks": "",
        "footer": "",
    }

    if not content:
        return sections

    # Extract title (first line with 🟣 PR #)
    lines = content.split("\n")
    if lines and "🟣" in lines[0]:
        sections["title"] = lines[0].strip("# ").strip()
        # Extract PR number from title
        pr_match = re.search(r'PR\s*#(\d+)', sections["title"])
        if pr_match:
            sections["pr_number"] = int(pr_match.group(1))

    # Split by headers
    current_section = None
    current_content = []

    for line in lines[1:]:
        # Check if this is a section header
        if line.startswith("## "):
            # Save previous section
            if current_section and current_content:
                sections[current_section] = "\n".join(current_content).strip()

            # Start new section
            header = line.strip("# ").strip()
            if "Metadata" in header:
                current_section = "metadata"
            elif "Description" in header:
                current_section = "description"
            elif "Commits" in header:
                current_section = "commits"
            elif "File Changes" in header:
                current_section = "file_changes"
            elif "Reviews" in header:
                current_section = "reviews"
            elif "Discussion" in header:
                current_section = "discussion"
            elif "Checks" in header:
                current_section = "checks"
            else:
                current_section = None

            current_content = []
        elif line.startswith("### "):
            # Sub-section within discussion
            if current_section == "discussion":
                sub_header = line.strip("# ").strip()
                if "Conversation" in sub_header:
                    if current_content:
                        sections["conversation"] = "\n".join(current_content).strip()
                    current_content = []
                elif "Code Review Comments" in sub_header:
                    if current_content:
                        sections["conversation"] = "\n".join(current_content).strip()
                    current_content = []
                    current_section = "code_comments"
        elif line.startswith("---"):
            # Footer section
            if current_section and current_content:
                if current_section == "code_comments":
                    sections["code_comments"] = "\n".join(current_content).strip()
                elif current_section:
                    sections[current_section] = "\n".join(current_content).strip()
            current_section = "footer"
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_section and current_content:
        if current_section == "code_comments":
            sections["code_comments"] = "\n".join(current_content).strip()
        else:
            sections[current_section] = "\n".join(current_content).strip()

    # Extract PR URL from metadata section
    if sections.get("metadata"):
        url_match = re.search(r'\*\*URL:\*\*\s+(https://github\.com/[^\s]+)', sections["metadata"])
        if url_match:
            sections["pr_url"] = url_match.group(1)

    return sections


def parse_code_comments(content: str) -> list[dict]:
    """Parse code review comments into structured format with file:line context.

    Matches the format from formatter.py:
    **@username** on `file.py:123` (timestamp)
    > comment body
    """
    comments = []
    if not content:
        return comments

    lines = content.split("\n")
    current_comment = None

    for i, line in enumerate(lines):
        # Match: **@username** on `file.py:123` (timestamp)
        match = re.match(r'\*\*@([\w-]+)\*\*\s+on\s+`(.+?):(\d+)`', line)
        if match:
            # Save previous comment
            if current_comment:
                comments.append(current_comment)

            author, file_path, line_num = match.groups()
            current_comment = {
                "file": file_path,
                "line": int(line_num),
                "author": author,
                "body": []
            }
            continue

        # Add body lines to current comment
        if current_comment is not None:
            # Stop at empty lines that separate comments
            if not line.strip() and current_comment["body"]:
                # Empty line after body content - might be end of comment
                continue
            elif line.strip():
                # Remove leading '> ' from quoted lines
                clean_line = line[2:] if line.startswith("> ") else line
                if clean_line.strip():  # Only add non-empty content
                    current_comment["body"].append(clean_line)

    # Save last comment
    if current_comment:
        comments.append(current_comment)

    return comments


def linkify_authors(html: str) -> str:
    """Convert @username references to clickable GitHub profile links."""
    # Match @username (but not inside HTML tags or already in links)
    pattern = r'@([\w-]+)'

    def replace_author(match):
        username = match.group(1)
        return f'<a href="https://github.com/{username}" target="_blank" class="author-link">@{username}</a>'

    # Simple replacement - this works for most cases
    # More sophisticated parsing would be needed to avoid replacing inside existing tags
    return re.sub(pattern, replace_author, html)


def render_code_comment_html(
    comment: dict,
    commit_sha: str,
    reader: GitNotesReader
) -> str:
    """Render a code comment in GitHub style with code context from commit."""
    html_parts = []

    # File header
    html_parts.append(f'<div class="code-comment">')
    html_parts.append(f'<div class="code-comment-header">')
    html_parts.append(f'<span class="file-path">{comment["file"]}</span>')
    html_parts.append(f'<span class="line-number">Line {comment["line"]}</span>')
    html_parts.append(f'</div>')

    # Get code context from the commit
    code_context = reader.get_file_lines_at_commit(
        commit_sha,
        comment["file"],
        comment["line"],
        context_lines=3
    )

    if code_context:
        html_parts.append(f'<div class="code-context">')
        html_parts.append(f'<table class="code-lines">')

        for line_num, line_content in code_context["lines"]:
            # Highlight the target line
            is_target = line_num == code_context["target_line"]
            row_class = ' class="target-line"' if is_target else ''

            # Escape HTML in line content
            escaped_line = (line_content
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

            html_parts.append(f'<tr{row_class}>')
            html_parts.append(f'<td class="line-num">{line_num}</td>')
            html_parts.append(f'<td class="line-code">{escaped_line}</td>')
            html_parts.append(f'</tr>')

        html_parts.append(f'</table>')
        html_parts.append(f'</div>')

    # Comment body
    html_parts.append(f'<div class="code-comment-body">')
    html_parts.append(f'<div class="comment-meta">')
    author_username = comment["author"]
    html_parts.append(f'<a href="https://github.com/{author_username}" target="_blank" class="author-link comment-author">{author_username}</a> commented')
    html_parts.append(f'</div>')

    body_text = "\n".join(comment["body"])
    # Convert markdown in body
    body_html = markdown2.markdown(
        body_text,
        extras=["fenced-code-blocks", "break-on-newline"]
    )
    # Linkify any @mentions in the body
    body_html = linkify_authors(body_html)
    html_parts.append(body_html)
    html_parts.append(f'</div>')
    html_parts.append(f'</div>')

    return "\n".join(html_parts)


# HTML Templates
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git Notes Browser - PR Summaries</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            line-height: 1.5;
        }

        .header {
            background-color: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 16px 32px;
        }

        .header-content {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .header h1 {
            font-size: 20px;
            font-weight: 600;
            color: #f0f6fc;
            flex: 1;
        }

        .header p {
            color: #8b949e;
            font-size: 14px;
            margin-top: 4px;
        }

        .ref-selector {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .ref-selector label {
            color: #8b949e;
            font-size: 14px;
        }

        .ref-selector select {
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #c9d1d9;
            padding: 5px 12px;
            font-size: 14px;
            cursor: pointer;
        }

        .ref-selector select:hover {
            border-color: #58a6ff;
        }

        .ref-selector select:focus {
            outline: none;
            border-color: #58a6ff;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 24px 32px;
        }

        .notes-list {
            background-color: #0d1117;
        }

        .note-item {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 16px;
            transition: border-color 0.2s;
        }

        .note-item:hover {
            border-color: #58a6ff;
        }

        .note-item a {
            text-decoration: none;
            color: inherit;
            display: block;
        }

        .note-header {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 8px;
        }

        .pr-badge {
            background-color: #8957e5;
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }

        .note-title {
            font-size: 16px;
            font-weight: 600;
            color: #58a6ff;
            flex: 1;
        }

        .note-meta {
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 12px;
            color: #8b949e;
            margin-top: 8px;
        }

        .commit-sha {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            background-color: #1f6feb1a;
            color: #58a6ff;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
        }

        .empty-state {
            text-align: center;
            padding: 64px 32px;
            color: #8b949e;
        }

        .empty-state h2 {
            font-size: 24px;
            margin-bottom: 8px;
            color: #c9d1d9;
        }

        .empty-state p {
            font-size: 14px;
        }

        .empty-state code {
            background-color: #161b22;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div>
                <h1>🟣 Git Notes Browser</h1>
                <p>PR Summaries stored in git notes</p>
            </div>
            <div class="ref-selector">
                <label for="ref-select">Ref:</label>
                <select id="ref-select" onchange="window.location.href='/?ref=' + this.value">
                    {% for ref in available_refs %}
                    <option value="{{ ref }}" {% if ref == notes_ref %}selected{% endif %}>
                        {{ ref }}
                    </option>
                    {% endfor %}
                </select>
            </div>
        </div>
    </div>

    <div class="container">
        {% if notes %}
        <div class="notes-list">
            {% for note in notes %}
            <div class="note-item">
                <a href="/note/{{ note.commit_sha }}?ref={{ notes_ref }}">
                    <div class="note-header">
                        {% if note.pr_number %}
                        <span class="pr-badge">PR #{{ note.pr_number }}</span>
                        {% endif %}
                        <div class="note-title">{{ note.subject }}</div>
                    </div>
                    <div class="note-meta">
                        <span class="commit-sha">{{ note.commit_sha_short }}</span>
                        <span>{{ note.author_name }}</span>
                        <span>{{ note.date }}</span>
                    </div>
                </a>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h2>No notes found</h2>
            <p>No git notes were found in <code>{{ notes_ref }}</code></p>
            <p style="margin-top: 16px;">Make sure you've fetched the notes reference:</p>
            <p style="margin-top: 8px;"><code>git fetch origin {{ notes_ref }}:{{ notes_ref }}</code></p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

NOTE_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ sections.title or 'PR Summary' }} - Git Notes Browser</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            background-color: #0d1117;
            color: #c9d1d9;
            line-height: 1.5;
        }

        .header {
            background-color: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 16px 32px;
        }

        .header-content {
            max-width: 1280px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .back-link {
            color: #58a6ff;
            text-decoration: none;
            font-size: 14px;
        }

        .back-link:hover {
            text-decoration: underline;
        }

        .header h1 {
            font-size: 20px;
            font-weight: 600;
            color: #f0f6fc;
            flex: 1;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
            padding: 24px 32px;
        }

        .pr-header {
            margin-bottom: 24px;
        }

        .pr-title {
            font-size: 32px;
            font-weight: 600;
            color: #f0f6fc;
            margin-bottom: 16px;
            line-height: 1.25;
        }

        .pr-title-link {
            color: #f0f6fc;
            text-decoration: none;
        }

        .pr-title-link:hover {
            color: #58a6ff;
        }

        .author-link {
            color: inherit;
            text-decoration: none;
            font-weight: 600;
        }

        .author-link:hover {
            color: #58a6ff;
            text-decoration: underline;
        }

        .section {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin-bottom: 16px;
            overflow: hidden;
        }

        .section-header {
            background-color: #161b22;
            padding: 16px;
            border-bottom: 1px solid #30363d;
            font-size: 14px;
            font-weight: 600;
            color: #f0f6fc;
        }

        .section-content {
            padding: 16px;
        }

        .metadata-grid {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 8px 16px;
            font-size: 14px;
        }

        .metadata-label {
            color: #8b949e;
            font-weight: 600;
        }

        .metadata-value {
            color: #c9d1d9;
        }

        .commit-list, .file-list, .comment-list {
            list-style: none;
        }

        .commit-item, .file-item {
            padding: 8px 0;
            border-bottom: 1px solid #21262d;
            font-size: 14px;
        }

        .commit-item:last-child, .file-item:last-child {
            border-bottom: none;
        }

        .commit-sha {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            background-color: #1f6feb1a;
            color: #58a6ff;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
            margin-right: 8px;
        }

        .file-path {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            color: #58a6ff;
        }

        .comment {
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin-bottom: 16px;
            overflow: hidden;
        }

        .comment-header {
            padding: 8px 16px;
            background-color: #161b22;
            border-bottom: 1px solid #30363d;
            font-size: 12px;
            color: #8b949e;
        }

        .comment-author {
            color: #f0f6fc;
            font-weight: 600;
        }

        .comment-body {
            padding: 16px;
            font-size: 14px;
        }

        .check-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #21262d;
            font-size: 14px;
        }

        .check-item:last-child {
            border-bottom: none;
        }

        .check-status {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }

        .check-status.success {
            background-color: #238636;
            color: white;
        }

        .check-status.failure {
            background-color: #da3633;
            color: white;
        }

        .check-status.other {
            background-color: #6e7681;
            color: white;
        }

        .check-name {
            flex: 1;
            color: #f0f6fc;
        }

        .check-duration {
            color: #8b949e;
            font-size: 12px;
        }

        .markdown-content {
            font-size: 14px;
            line-height: 1.6;
        }

        .markdown-content p {
            margin-bottom: 16px;
        }

        .markdown-content ul, .markdown-content ol {
            margin-left: 24px;
            margin-bottom: 16px;
        }

        .markdown-content li {
            margin-bottom: 4px;
        }

        .markdown-content code {
            background-color: #1f6feb1a;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 12px;
        }

        .markdown-content pre {
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 16px;
            overflow-x: auto;
            margin-bottom: 16px;
        }

        .markdown-content pre code {
            background: none;
            padding: 0;
            font-size: 12px;
        }

        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            margin-top: 24px;
            margin-bottom: 16px;
            color: #f0f6fc;
        }

        .markdown-content h1 {
            font-size: 24px;
            border-bottom: 1px solid #30363d;
            padding-bottom: 8px;
        }

        .markdown-content h2 {
            font-size: 20px;
        }

        .markdown-content h3 {
            font-size: 16px;
        }

        .markdown-content blockquote {
            border-left: 4px solid #30363d;
            padding-left: 16px;
            margin: 16px 0;
            color: #8b949e;
        }

        .markdown-content a {
            color: #58a6ff;
            text-decoration: none;
        }

        .markdown-content a:hover {
            text-decoration: underline;
        }

        .footer {
            text-align: center;
            padding: 16px;
            color: #8b949e;
            font-size: 12px;
            border-top: 1px solid #30363d;
            margin-top: 24px;
        }

        .empty-section {
            color: #8b949e;
            font-style: italic;
            font-size: 14px;
        }

        .code-comment {
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            margin-bottom: 16px;
            overflow: hidden;
        }

        .code-comment-header {
            background-color: #161b22;
            padding: 8px 16px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .code-comment-header .file-path {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            color: #c9d1d9;
            font-size: 14px;
        }

        .code-comment-header .line-number {
            font-size: 12px;
            color: #8b949e;
        }

        .code-context {
            background-color: #0d1117;
            border-bottom: 1px solid #30363d;
            overflow-x: auto;
        }

        .code-context pre {
            margin: 0;
            padding: 12px 16px;
            background-color: #161b22;
            border: none;
            border-radius: 0;
        }

        .code-context code {
            font-size: 12px;
            color: #c9d1d9;
            line-height: 1.5;
        }

        .code-lines {
            width: 100%;
            border-collapse: collapse;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 12px;
            line-height: 20px;
        }

        .code-lines td {
            padding: 0;
            border: none;
        }

        .code-lines .line-num {
            width: 1%;
            min-width: 50px;
            padding: 0 10px;
            text-align: right;
            color: #6e7681;
            background-color: #0d1117;
            user-select: none;
            vertical-align: top;
        }

        .code-lines .line-code {
            padding: 0 10px;
            color: #c9d1d9;
            background-color: #0d1117;
            white-space: pre;
            vertical-align: top;
        }

        .code-lines tr:hover .line-num,
        .code-lines tr:hover .line-code {
            background-color: #161b22;
        }

        .code-lines tr.target-line .line-num,
        .code-lines tr.target-line .line-code {
            background-color: #ffd33d1a;
        }

        .code-lines tr.target-line .line-num {
            color: #ffd33d;
            font-weight: 600;
        }

        .code-comment-body {
            padding: 16px;
        }

        .comment-meta {
            margin-bottom: 12px;
            font-size: 12px;
            color: #8b949e;
        }

        .comment-meta .comment-author {
            color: #f0f6fc;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <a href="/?ref={{ notes_ref }}" class="back-link">← Back to list</a>
            <h1>PR Summary</h1>
        </div>
    </div>

    <div class="container">
        <div class="pr-header">
            {% if sections.pr_url %}
            <h1 class="pr-title"><a href="{{ sections.pr_url }}" target="_blank" class="pr-title-link">{{ sections.title or 'Pull Request Summary' }}</a></h1>
            {% else %}
            <h1 class="pr-title">{{ sections.title or 'Pull Request Summary' }}</h1>
            {% endif %}
        </div>

        {% if sections.metadata %}
        <div class="section">
            <div class="section-header">📋 Metadata</div>
            <div class="section-content">
                <div class="markdown-content">
                    {{ sections.metadata|safe }}
                </div>
            </div>
        </div>
        {% endif %}

        {% if sections.description %}
        <div class="section">
            <div class="section-header">📝 Description</div>
            <div class="section-content">
                <div class="markdown-content">
                    {{ sections.description|safe }}
                </div>
            </div>
        </div>
        {% endif %}

        {% if sections.commits %}
        <div class="section">
            <div class="section-header">💾 Commits</div>
            <div class="section-content">
                <div class="markdown-content">
                    {{ sections.commits|safe }}
                </div>
            </div>
        </div>
        {% endif %}

        {% if sections.file_changes %}
        <div class="section">
            <div class="section-header">📁 File Changes</div>
            <div class="section-content">
                <div class="markdown-content">
                    {{ sections.file_changes|safe }}
                </div>
            </div>
        </div>
        {% endif %}

        {% if sections.reviews %}
        <div class="section">
            <div class="section-header">👀 Reviews</div>
            <div class="section-content">
                <div class="markdown-content">
                    {{ sections.reviews|safe }}
                </div>
            </div>
        </div>
        {% endif %}

        {% if sections.conversation or sections.code_comments %}
        <div class="section">
            <div class="section-header">💬 Discussion</div>
            <div class="section-content">
                {% if sections.conversation %}
                <h3 style="font-size: 16px; margin-bottom: 12px; color: #f0f6fc;">Conversation</h3>
                <div class="markdown-content">
                    {{ sections.conversation|safe }}
                </div>
                {% endif %}

                {% if parsed_code_comments %}
                <h3 style="font-size: 16px; margin-top: 24px; margin-bottom: 12px; color: #f0f6fc;">Code Review Comments</h3>
                {% for comment_html in parsed_code_comments %}
                    {{ comment_html|safe }}
                {% endfor %}
                {% elif sections.code_comments %}
                <h3 style="font-size: 16px; margin-top: 24px; margin-bottom: 12px; color: #f0f6fc;">Code Review Comments</h3>
                <div class="markdown-content">
                    {{ sections.code_comments|safe }}
                </div>
                {% endif %}
            </div>
        </div>
        {% endif %}

        {% if sections.checks %}
        <div class="section">
            <div class="section-header">✅ Checks</div>
            <div class="section-content">
                <div class="markdown-content">
                    {{ sections.checks|safe }}
                </div>
            </div>
        </div>
        {% endif %}

        {% if sections.footer %}
        <div class="footer">
            {{ sections.footer|safe }}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""


# Routes
@app.route("/")
def index():
    """Display list of all notes."""
    notes_ref = request.args.get("ref", NOTES_REF)
    reader = GitNotesReader(REPO_PATH, notes_ref)
    notes = reader.list_notes()
    available_refs = reader.list_available_refs()
    return render_template_string(
        INDEX_TEMPLATE,
        notes=notes,
        notes_ref=notes_ref,
        available_refs=available_refs
    )


@app.route("/note/<commit_sha>")
def note_detail(commit_sha: str):
    """Display detailed view of a specific note."""
    notes_ref = request.args.get("ref", NOTES_REF)
    reader = GitNotesReader(REPO_PATH, notes_ref)
    note_content = reader.get_note(commit_sha)

    if not note_content:
        return f"<h1>Note not found</h1><p>No note found for commit {commit_sha}</p>", 404

    # Parse sections
    sections = parse_note_sections(note_content)

    # Parse code comments for special rendering
    parsed_code_comments = []
    if sections.get("code_comments"):
        comments = parse_code_comments(sections["code_comments"])
        parsed_code_comments = [
            render_code_comment_html(c, commit_sha, reader)
            for c in comments
        ]

    # Convert markdown to HTML for each section (except code_comments if parsed)
    for key, value in sections.items():
        if value and key != "title" and key != "code_comments" and key != "pr_url" and key != "pr_number":
            html = markdown2.markdown(
                value,
                extras=["fenced-code-blocks", "tables", "break-on-newline"]
            )
            # Linkify author mentions
            sections[key] = linkify_authors(html)

    # Only convert code_comments to markdown if we didn't parse them
    if sections.get("code_comments") and not parsed_code_comments:
        html = markdown2.markdown(
            sections["code_comments"],
            extras=["fenced-code-blocks", "tables", "break-on-newline"]
        )
        sections["code_comments"] = linkify_authors(html)

    return render_template_string(
        NOTE_DETAIL_TEMPLATE,
        sections=sections,
        commit_sha=commit_sha,
        notes_ref=notes_ref,
        parsed_code_comments=parsed_code_comments
    )


@app.route("/api/notes")
def api_notes():
    """API endpoint to get list of notes as JSON."""
    notes_ref = request.args.get("ref", NOTES_REF)
    reader = GitNotesReader(REPO_PATH, notes_ref)
    notes = reader.list_notes()
    return jsonify(notes)


@app.route("/api/note/<commit_sha>")
def api_note_detail(commit_sha: str):
    """API endpoint to get note content as JSON."""
    notes_ref = request.args.get("ref", NOTES_REF)
    reader = GitNotesReader(REPO_PATH, notes_ref)
    note_content = reader.get_note(commit_sha)

    if not note_content:
        return jsonify({"error": "Note not found"}), 404

    sections = parse_note_sections(note_content)
    return jsonify({
        "commit_sha": commit_sha,
        "sections": sections,
        "raw_content": note_content,
        "notes_ref": notes_ref
    })


@app.route("/api/refs")
def api_refs():
    """API endpoint to get list of available refs as JSON."""
    reader = GitNotesReader(REPO_PATH, NOTES_REF)
    refs = reader.list_available_refs()
    return jsonify({"refs": refs})


def main():
    """Main entry point."""
    global REPO_PATH, NOTES_REF

    parser = argparse.ArgumentParser(
        description="Web browser for git notes containing PR summaries"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the server on (default: 5000)"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to git repository (default: current directory)"
    )
    parser.add_argument(
        "--ref",
        type=str,
        default="refs/notes/commits",
        help="Git notes reference to browse (default: refs/notes/commits)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )

    args = parser.parse_args()

    REPO_PATH = args.repo
    NOTES_REF = args.ref

    print(f"🟣 Git Notes Browser")
    print(f"   Repository: {REPO_PATH}")
    print(f"   Notes ref: {NOTES_REF}")
    print(f"   Server: http://{args.host}:{args.port}")
    print()

    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
