"""
LLM-Wiki Graph Engine — Karpathy-style knowledge graph from interlinked markdown.

Parses wiki/*.md files, extracts YAML frontmatter + [[wikilinks]], builds an
in-memory graph for traversal during hybrid RAG queries.

Vocabulary:
  Node      = a wiki page (file path)
  Edge      = [[wikilink]] from one page to another
  Neighbor  = page reachable via 1-hop
  Subgraph  = neighborhood of radius N around a query hit
"""
import os
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


WIKI_ROOT = os.environ.get("WIKI_ROOT", "/app/wiki")
FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
WIKILINK_RE = re.compile(r'\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]')


@dataclass
class WikiPage:
    """A single wiki page with metadata and outbound links."""
    path: str               # relative to WIKI_ROOT, e.g. 'concepts/vllm-inference.md'
    title: str              # from frontmatter
    page_type: str          # entity | concept | comparison | query
    tags: list[str] = field(default_factory=list)
    content: str = ""       # body without frontmatter
    outlinks: list[str] = field(default_factory=list)  # [[target]] paths (bare names)
    summary: str = ""       # first meaningful paragraph (~200 chars)


class WikiGraph:
    """
    In-memory graph of all wiki pages.

    Usage:
        graph = WikiGraph(wiki_root="/app/wiki")
        graph.load()

        # Get a page
        page = graph.get("vllm-inference")

        # Get neighbors (1-hop)
        neighbors = graph.neighbors("vllm-inference")

        # Traverse subgraph (radius N)
        pages = graph.subgraph(["vllm-inference"], radius=2)

        # Full-text search
        pages = graph.search("GPU memory")
    """

    def __init__(self, wiki_root: str = WIKI_ROOT):
        self.root = Path(wiki_root)
        self._pages: dict[str, WikiPage] = {}  # slug → WikiPage
        self._by_title: dict[str, str] = {}    # title → slug
        self._inlinks: dict[str, set[str]] = {}  # slug → inbound slugs
        self._loaded = False

    # ── Loading ──────────────────────────────────────────────────────────

    def load(self) -> int:
        """Scan wiki/ directory and load all pages. Returns count."""
        self._pages.clear()
        self._by_title.clear()
        self._inlinks.clear()

        count = 0

        # Mode 1: hierarchical (entities/, concepts/, etc.)
        scan_dirs = ['entities', 'concepts', 'comparisons', 'queries']
        found_hierarchical = False
        for subdir in scan_dirs:
            d = self.root / subdir
            if d.is_dir():
                found_hierarchical = True
                for md_file in sorted(d.glob('*.md')):
                    page = self._parse_file(md_file)
                    if page:
                        self._index(page)
                        count += 1

        if found_hierarchical:
            self._loaded = True
            return count

        # Mode 2: flat ConfigMap layout (entities-filename.md, concepts-filename.md)
        for md_file in sorted(self.root.glob('*.md')):
            name = md_file.name
            if name in ('SCHEMA.md', 'index.md', 'log.md'):
                continue
            # Parse prefix: entities-xxx.md → entities/xxx.md
            for prefix in scan_dirs:
                if name.startswith(f'{prefix}-'):
                    page = self._parse_file(md_file, virtual_dir=prefix)
                    if page:
                        self._index(page)
                        count += 1
                    break

        self._loaded = True
        return count

    def _parse_file(self, filepath: Path, virtual_dir: str = None) -> Optional[WikiPage]:
        """Parse a single .md file into a WikiPage."""
        try:
            raw = filepath.read_text(encoding='utf-8')
        except Exception:
            return None

        if virtual_dir:
            # Flat layout: entities-xxx.md → entities/xxx.md
            rel = f"{virtual_dir}/{filepath.name}"
        else:
            rel = str(filepath.relative_to(self.root))

        # Extract frontmatter
        fm = {}
        body = raw
        m = FRONTMATTER_RE.match(raw)
        if m:
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                pass
            body = raw[m.end():]

        title = fm.get('title', filepath.stem.replace('-', ' ').title())
        page_type = fm.get('type', 'concept')
        tags = fm.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]

        # Extract [[wikilinks]] from body
        outlinks_raw = WIKILINK_RE.findall(body)
        outlinks = list(dict.fromkeys(outlinks_raw))  # deduplicate, keep order

        # Summary: first paragraph of substance (skip blank lines, headers)
        summary = self._extract_summary(body)

        return WikiPage(
            path=rel,
            title=title,
            page_type=page_type,
            tags=tags,
            content=body.strip(),
            outlinks=outlinks,
            summary=summary,
        )

    @staticmethod
    def _extract_summary(body: str, max_chars: int = 300) -> str:
        """Extract first meaningful paragraph as summary."""
        lines = body.strip().split('\n')
        para = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                if para:
                    break
                continue
            para.append(stripped)
            joined = ' '.join(para)
            if len(joined) > max_chars:
                break
        result = ' '.join(para)
        if len(result) > max_chars:
            result = result[:max_chars].rsplit(' ', 1)[0] + '…'
        return result

    def _index(self, page: WikiPage):
        """Insert page into in-memory indices."""
        slug = self._slug(page.path)
        self._pages[slug] = page
        self._by_title[page.title.lower()] = slug

        # Build inlinks: for each outlink, record that 'slug' links to it
        for target_raw in page.outlinks:
            target = self._normalize_slug(target_raw)
            if target not in self._inlinks:
                self._inlinks[target] = set()
            self._inlinks[target].add(slug)

    # ── Slug resolution ──────────────────────────────────────────────────

    @staticmethod
    def _slug(path: str) -> str:
        """Convert 'concepts/vllm-inference.md' → 'vllm-inference'."""
        return Path(path).stem.lower()

    @staticmethod
    def _normalize_slug(raw: str) -> str:
        """Normalize [[Target Name]] → 'target-name'."""
        return raw.strip().lower().replace(' ', '-').replace('_', '-')

    def _resolve(self, slug_or_title: str) -> Optional[str]:
        """Resolve a slug or title to a canonical slug. Returns None if not found."""
        key = slug_or_title.lower().replace(' ', '-').replace('_', '-')
        if key in self._pages:
            return key
        # Try by title
        return self._by_title.get(slug_or_title.lower())

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def page_count(self) -> int:
        return len(self._pages)

    def get(self, slug_or_title: str) -> Optional[WikiPage]:
        """Get a single page by slug or title."""
        key = self._resolve(slug_or_title)
        return self._pages.get(key) if key else None

    def list_all(self) -> list[WikiPage]:
        return list(self._pages.values())

    def neighbors(self, slug_or_title: str) -> list[WikiPage]:
        """1-hop neighbors (both outbound and inbound)."""
        page = self.get(slug_or_title)
        if not page:
            return []

        seen = set()
        result = []

        # Outbound: pages THIS page links to
        for target_raw in page.outlinks:
            target = self._resolve(target_raw)
            if target and target not in seen:
                seen.add(target)
                result.append(self._pages[target])

        # Inbound: pages that link TO this page
        slug = self._slug(page.path)
        for source in self._inlinks.get(slug, set()):
            if source not in seen and source in self._pages:
                seen.add(source)
                result.append(self._pages[source])

        return result

    def subgraph(self, slugs: list[str], radius: int = 1) -> list[WikiPage]:
        """
        BFS traversal from seed slugs, expanding up to `radius` hops.
        Returns all pages in the neighborhood (including seeds).
        Radius=1 = seeds + direct neighbors. Radius=2 = + neighbors of neighbors.
        """
        visited: set[str] = set()
        frontier: set[str] = set()

        for s in slugs:
            key = self._resolve(s)
            if key:
                frontier.add(key)

        for _ in range(radius + 1):
            if not frontier:
                break
            next_frontier: set[str] = set()
            for slug in frontier:
                if slug in visited:
                    continue
                visited.add(slug)
                page = self._pages.get(slug)
                if not page:
                    continue
                # Add outbound
                for target_raw in page.outlinks:
                    t = self._resolve(target_raw)
                    if t and t not in visited:
                        next_frontier.add(t)
                # Add inbound
                for source in self._inlinks.get(slug, set()):
                    if source not in visited and source in self._pages:
                        next_frontier.add(source)
            frontier = next_frontier

        return [self._pages[s] for s in visited if s in self._pages]

    def search(self, query: str, limit: int = 10) -> list[WikiPage]:
        """
        Simple full-text search across titles, tags, summaries, and content.
        For semantic search, use ChromaDB; this is for exact/keyword matching.
        """
        terms = query.lower().split()
        scored: list[tuple[float, WikiPage]] = []

        for page in self._pages.values():
            score = 0.0
            searchable = (
                page.title.lower() + ' ' +
                ' '.join(page.tags).lower() + ' ' +
                page.summary.lower() + ' ' +
                page.content.lower()
            )
            for term in terms:
                count = searchable.count(term)
                if count > 0:
                    score += count
                # Bonus for title match
                if term in page.title.lower():
                    score += 5.0
            if score > 0:
                scored.append((score, page))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]


# ── Singleton ────────────────────────────────────────────────────────────

_wiki_graph: Optional[WikiGraph] = None


def get_wiki_graph(wiki_root: str = WIKI_ROOT) -> WikiGraph:
    """Get or initialize the global WikiGraph singleton."""
    global _wiki_graph
    if _wiki_graph is None:
        _wiki_graph = WikiGraph(wiki_root)
        _wiki_graph.load()
    return _wiki_graph


def reload_wiki_graph(wiki_root: str = WIKI_ROOT) -> WikiGraph:
    """Force reload of the wiki graph (after wiki ingest)."""
    global _wiki_graph
    _wiki_graph = WikiGraph(wiki_root)
    _wiki_graph.load()
    return _wiki_graph
