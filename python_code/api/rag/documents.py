"""Load the Markdown knowledge base and split it into heading-based chunks.

Each knowledge base file starts with a small front matter block:

    ---
    title: Bakery
    doc_type: menu
    category: Bakery
    ---

Every `##` or `###` heading starts a new chunk, so one menu item, policy, or FAQ
answer becomes one chunk. Chunk text is prefixed with its heading path
("Bakery > Almond Croissant") so both keyword and vector search see the context.
"""
from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    title: str
    section: str
    doc_type: str
    category: str = ""
    tags: list[str] = field(default_factory=list)

    def metadata(self):
        return {
            "source": self.source,
            "title": self.title,
            "section": self.section,
            "doc_type": self.doc_type,
            "category": self.category,
            "tags": ",".join(self.tags),
        }


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_front_matter(raw_text):
    match = re.match(r"^---\n(.*?)\n---\n", raw_text, re.DOTALL)
    if not match:
        return {}, raw_text
    metadata = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata, raw_text[match.end():]


def split_sections(body):
    """Yield (heading_path, section_body) pairs, one per ##/### heading."""
    h1, h2 = "", ""
    current_path, current_lines = [], []

    def flush():
        text = "\n".join(current_lines).strip()
        if text:
            yield current_path or [h1], text

    for line in body.splitlines():
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if not heading:
            current_lines.append(line)
            continue

        yield from flush()
        level, title = len(heading.group(1)), heading.group(2).strip()
        if level == 1:
            h1, h2 = title, ""
            current_path = [h1]
        elif level == 2:
            h2 = title
            current_path = [h1, h2]
        else:
            current_path = [h1, h2, title] if h2 else [h1, title]
        current_lines = []

    yield from flush()


def load_chunks(knowledge_base_dir):
    knowledge_base_dir = Path(knowledge_base_dir)
    chunks = []
    for path in sorted(knowledge_base_dir.rglob("*.md")):
        source = path.relative_to(knowledge_base_dir).as_posix()
        front_matter, body = parse_front_matter(path.read_text(encoding="utf-8"))
        title = front_matter.get("title", path.stem)

        for heading_path, text in split_sections(body):
            heading_path = [heading for heading in heading_path if heading]
            section = heading_path[-1] if heading_path else title
            tags_match = re.search(r"^Tags:\s*(.+)$", text, re.MULTILINE)
            tags = [tag.strip() for tag in tags_match.group(1).split(",")] if tags_match else []

            chunks.append(Chunk(
                id=f"{source}#{slugify(section)}",
                text=" > ".join(heading_path) + "\n" + text,
                source=source,
                title=title,
                section=section,
                doc_type=front_matter.get("doc_type", "general"),
                category=front_matter.get("category", ""),
                tags=tags,
            ))
    return chunks
