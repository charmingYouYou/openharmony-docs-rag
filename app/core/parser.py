"""Core parser module for Markdown documents."""

import re
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

from app.schemas import (
    ParsedDocument,
    DocumentMetadata,
    PageKind
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class MarkdownParser:
    """Parser for OpenHarmony Markdown documentation."""

    version = "2026-03-14-parser-v1"

    def __init__(self):
        self.md = MarkdownIt()

    def parse_file(self, file_path: Path, base_path: Path) -> Optional[ParsedDocument]:
        """
        Parse a Markdown file and extract structure and metadata.

        Args:
            file_path: Path to the Markdown file
            base_path: Base path of the documentation repository

        Returns:
            ParsedDocument or None if parsing fails
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get relative path
            rel_path = str(file_path.relative_to(base_path))

            # Extract metadata from HTML comments
            metadata = self.extract_metadata(content)

            # Identify page kind
            page_kind = self.identify_page_kind(rel_path, content)

            # Extract title
            title = self.extract_title(content)

            # Determine directory structure
            top_dir, sub_dir = self.parse_directory_structure(rel_path)

            # Generate document ID
            doc_id = self.generate_doc_id(rel_path)

            # Determine document type flags
            is_api_reference = self.is_api_reference(rel_path)
            is_guide = self.is_guide(rel_path, content, page_kind)
            is_design_spec = self.is_design_spec(rel_path, top_dir)

            return ParsedDocument(
                doc_id=doc_id,
                path=rel_path,
                title=title,
                content=content,
                metadata=metadata,
                page_kind=page_kind,
                is_api_reference=is_api_reference,
                is_guide=is_guide,
                is_design_spec=is_design_spec,
                top_dir=top_dir,
                sub_dir=sub_dir
            )

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def extract_metadata(self, content: str) -> DocumentMetadata:
        """
        Extract metadata from HTML comments.

        Example:
        <!--
        Kit: ArkUI
        Subsystem: arkui_ace_engine
        Owner: @someone
        -->
        """
        metadata = DocumentMetadata()

        # Find HTML comment blocks
        comment_pattern = r'<!--(.*?)-->'
        comments = re.findall(comment_pattern, content, re.DOTALL)

        for comment in comments:
            # Extract Kit
            kit_match = re.search(r'Kit:\s*([^\n]+)', comment, re.IGNORECASE)
            if kit_match:
                metadata.kit = kit_match.group(1).strip()

            # Extract Subsystem
            subsystem_match = re.search(r'Subsystem:\s*([^\n]+)', comment, re.IGNORECASE)
            if subsystem_match:
                metadata.subsystem = subsystem_match.group(1).strip()

            # Extract Owner
            owner_match = re.search(r'Owner:\s*([^\n]+)', comment, re.IGNORECASE)
            if owner_match:
                metadata.owner = owner_match.group(1).strip()

        return metadata

    def identify_page_kind(self, path: str, content: str) -> PageKind:
        """
        Identify the type of document.

        Priority:
        1. README files -> readme
        2. API reference (js-apis-*.md) -> reference
        3. Design specs (in design/ dir) -> design_spec
        4. Guide indicators -> guide
        5. Concept indicators -> concept
        6. Default -> unknown
        """
        path_lower = path.lower()

        # Check for README
        if 'readme' in path_lower or path_lower.endswith('readme-cn.md'):
            return PageKind.README

        # Check for API reference
        if self.is_api_reference(path):
            return PageKind.REFERENCE

        # Check for design specs
        if 'zh-cn/design' in path_lower:
            return PageKind.DESIGN_SPEC

        # Check content for guide indicators
        guide_indicators = [
            '快速入门', '开发指南', '使用指南', '最佳实践',
            '如何', '步骤', 'quick start', 'guide', 'tutorial'
        ]
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in guide_indicators):
            return PageKind.GUIDE

        # Check for concept indicators
        concept_indicators = ['概述', '概念', '介绍', 'overview', 'concept', 'introduction']
        if any(indicator in content_lower for indicator in concept_indicators):
            return PageKind.CONCEPT

        return PageKind.UNKNOWN

    def is_api_reference(self, path: str) -> bool:
        """Check if document is an API reference."""
        path_lower = path.lower()
        # API reference files typically follow pattern: js-apis-*.md or apis-*.md
        return bool(re.search(r'(js-)?apis?-[^/]+\.md$', path_lower)) or '/reference/' in path_lower

    def is_guide(self, path: str, content: str, page_kind: PageKind) -> bool:
        """Check if document is a guide."""
        if page_kind == PageKind.GUIDE:
            return True

        # Additional checks
        path_lower = path.lower()
        guide_paths = ['/guide/', '/quick-start/', '/tutorial/', '/getting-started/']
        if any(gp in path_lower for gp in guide_paths):
            return True

        # Check for step-by-step content
        if re.search(r'步骤\s*\d+|step\s*\d+', content, re.IGNORECASE):
            return True

        return False

    def is_design_spec(self, path: str, top_dir: str) -> bool:
        """Check if document is a design specification."""
        return top_dir == 'design' or '/design/' in path.lower()

    def extract_title(self, content: str) -> Optional[str]:
        """Extract document title from first H1 heading."""
        # Try to find first H1
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Fallback: try to find any heading
        heading_match = re.search(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()

        return None

    def parse_directory_structure(self, rel_path: str) -> Tuple[str, Optional[str]]:
        """
        Parse directory structure from relative path.

        Example:
        zh-cn/application-dev/quick-start/start-overview.md
        -> top_dir: application-dev, sub_dir: quick-start
        """
        parts = Path(rel_path).parts

        # Skip 'zh-cn' prefix if present
        if parts[0] == 'zh-cn':
            parts = parts[1:]

        top_dir = parts[0] if len(parts) > 0 else 'unknown'
        sub_dir = parts[1] if len(parts) > 2 else None

        return top_dir, sub_dir

    def generate_doc_id(self, rel_path: str) -> str:
        """Generate unique document ID from path."""
        return hashlib.md5(rel_path.encode()).hexdigest()[:16]
