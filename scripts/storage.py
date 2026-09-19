"""Plain Markdown, immutable sources, atomic revisions. No third-party dependencies."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

MAX_FILE_BYTES = 16_000
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
HEADER = "<!-- jev-wiki "


class WikiError(Exception):
    """An actionable error safe to display without credentials or response bodies."""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def read_text(path: Path, limit: int = MAX_FILE_BYTES) -> str:
    if path.is_symlink():
        raise WikiError("Symlink files are not supported")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise WikiError(f"File exceeds {limit} bytes; split it into smaller Markdown documents")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise WikiError("Only UTF-8 text is supported") from None
    if "\x00" in text:
        raise WikiError("Binary input is not supported")
    return text


def atomic_write(path: Path, text: str) -> None:
    """Same-filesystem replacement with fsync; old content survives a failed write."""
    if path.is_symlink():
        raise WikiError("Refusing to overwrite a symlink")
    fd, temp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def valid_slug(value: str) -> str:
    if not SLUG.fullmatch(value):
        raise WikiError("Page IDs must be 1–64 lowercase ASCII letters, digits or hyphens; start with a letter or digit")
    return value


def links(text: str) -> list[str]:
    return re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", text)


def tokens(text: str) -> set[str]:
    words = set(re.findall(r"[^\W_]{2,}", text.casefold()))
    # CJK character bigrams retain useful overlap without a tokenizer dependency.
    for run in re.findall(r"[\u3400-\u9fff\uac00-\ud7af]+", text):
        words.update(run[i:i + 2] for i in range(len(run) - 1))
    return words


class Vault:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def path(self, relative: str) -> Path:
        path = self.root / relative
        if path.is_absolute() and not path.is_relative_to(self.root):
            raise WikiError("Path escapes the vault")
        for part in path.relative_to(self.root).parts:
            if part in ("..", "."):
                raise WikiError("Invalid vault path")
        cursor = self.root
        for part in path.relative_to(self.root).parts:
            cursor /= part
            if cursor.is_symlink():
                raise WikiError("Symlinks inside the vault are not supported")
        return path

    def init(self) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        for folder in ("wiki", "sources", ".jev-wiki", ".jev-wiki/cache", ".jev-wiki/history"):
            self.path(folder).mkdir(exist_ok=True)
        with self.lock(require_config=False):
            config = self.path(".jev-wiki/config.json")
            if not config.exists():
                atomic_write(config, encode({"version": 1, "confidence": 0.85, "support": 0.9, "risk": 0.1, "top_k": 6}) + "\n")
            self.config()
        return {"status": "ready", "vault": str(self.root)}

    def config(self) -> dict:
        try:
            config = json.loads(read_text(self.path(".jev-wiki/config.json")))
        except FileNotFoundError:
            raise WikiError("Not a jev-wiki vault; run init first") from None
        if not isinstance(config, dict) or config.get("version") != 1:
            raise WikiError("Unsupported vault configuration")
        for key in ("confidence", "support", "risk"):
            value = config.get(key)
            if type(value) not in (int, float) or not 0 <= value <= 1:
                raise WikiError(f"Invalid {key} threshold")
        if type(config.get("top_k")) is not int or not 1 <= config["top_k"] <= 6:
            raise WikiError("top_k must be an integer between 1 and 6")
        return config

    @contextlib.contextmanager
    def lock(self, require_config=True):
        if require_config:
            self.config()
        with self.path(".jev-wiki/lock").open("a+") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise WikiError("Vault is busy; retry after the current command completes") from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def source(self, source_id: str) -> str:
        if not HASH.fullmatch(source_id):
            raise WikiError("Invalid source SHA-256")
        text = read_text(self.path(f"sources/{source_id}.md"))
        if digest(text) != source_id:
            raise WikiError("Source integrity check failed")
        return text

    def add_source(self, text: str) -> tuple[str, bool]:
        if not text.strip() or "\x00" in text or len(text.encode()) > MAX_FILE_BYTES:
            raise WikiError("Source must be nonempty text of at most 16000 UTF-8 bytes")
        source_id = digest(text)
        path = self.path(f"sources/{source_id}.md")
        if path.exists():
            self.source(source_id)
            return source_id, False
        atomic_write(path, text)
        return source_id, True

    def page(self, slug: str) -> dict:
        raw = read_text(self.path(f"wiki/{valid_slug(slug)}.md"), MAX_FILE_BYTES + 4096)
        line, separator, body = raw.partition("\n")
        if not line.startswith(HEADER) or not line.endswith(" -->") or not separator:
            raise WikiError(f"Page {slug} has invalid metadata; import edits through publish")
        try:
            meta = json.loads(line[len(HEADER):-4])
        except ValueError:
            raise WikiError(f"Invalid metadata in {slug}") from None
        if (not isinstance(meta, dict) or meta.get("version") != 1
                or not isinstance(meta.get("sources"), list) or not meta["sources"]
                or len(meta["sources"]) > 8
                or any(not isinstance(s, str) or not HASH.fullmatch(s) for s in meta["sources"])):
            raise WikiError(f"Invalid source metadata in {slug}")
        return {"id": slug, "revision": digest(raw), "sources": meta["sources"], "content": body}

    def pages(self) -> list[dict]:
        # ponytail: scan plain Markdown on each command; add a derived index when scan latency matters.
        return [self.page(p.stem) for p in sorted(self.path("wiki").glob("*.md"))]

    def revision(self, slug: str) -> str:
        path = self.path(f"wiki/{valid_slug(slug)}.md")
        return self.page(slug)["revision"] if path.exists() else "new"

    def publish(self, slug: str, body: str, source_ids: list[str], expected: str) -> dict:
        valid_slug(slug)
        if self.revision(slug) != expected:
            raise WikiError("Revision conflict; reread the current page before publishing")
        if not source_ids or len(source_ids) > 8:
            raise WikiError("A page needs 1–8 immutable sources")
        for source_id in source_ids:
            self.source(source_id)
        if not re.search(r"^# .+", body, re.M) or HEADER in body:
            raise WikiError("Draft needs a Markdown title and must not contain jev-wiki metadata")
        if len(body.encode()) > MAX_FILE_BYTES:
            raise WikiError("Draft exceeds page size limit")
        missing = [target for target in links(body) if target != slug and not self.path(f"wiki/{valid_slug(target)}.md").exists()]
        if missing:
            raise WikiError("Draft contains unresolved wikilinks: " + ", ".join(missing))
        path = self.path(f"wiki/{slug}.md")
        if expected != "new":
            history = self.path(f".jev-wiki/history/{slug}")
            history.mkdir(exist_ok=True)
            atomic_write(history / f"{expected}.md", read_text(path, MAX_FILE_BYTES + 4096))
        raw = HEADER + encode({"version": 1, "sources": sorted(set(source_ids))}) + " -->\n" + body
        atomic_write(path, raw)
        return {"status": "published", "page": slug, "revision": digest(raw), "sources": sorted(set(source_ids))}


def candidates(pages: list[dict], query: str, top_k: int, byte_budget: int = 12_000) -> tuple[list[dict], dict]:
    wanted = tokens(query)
    ranked = sorted(pages, key=lambda p: (-len(wanted & tokens(p["id"] + " " + p["content"])), p["id"]))
    selected = []
    used = 0
    for page in ranked:
        size = len(encode(page).encode())
        if len(selected) < top_k and used + size <= byte_budget:
            selected.append(page)
            used += size
    return selected, {"total_pages": len(pages), "selected_pages": len(selected), "complete": len(selected) == len(pages), "method": "lexical overlap, full pages; no truncation"}
