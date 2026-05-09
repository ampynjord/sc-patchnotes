import html as htmlmod
import re
import requests
from html.parser import HTMLParser
from typing import Optional
from .parser import PatchNote, PatchSection, PatchItem

RSI_BASE    = "https://robertsspaceindustries.com"
THREAD_API  = f"{RSI_BASE}/api/spectrum/forum/thread/nested"
SPECTRUM_HOME = f"{RSI_BASE}/spectrum/"

# Sections métadonnées à ignorer (pas des changements de jeu)
SKIP_HEADERS = {
    "testing/feedback focus", "testing focus",
    "audience and server details", "audience & server details",
    "patch details",
}


class RSIFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self._token_loaded = False

    def _ensure_token(self):
        if not self._token_loaded:
            self.session.get(SPECTRUM_HOME, timeout=10)
            self._token_loaded = True

    def slug_from_url(self, url: str) -> Optional[str]:
        """Extrait le slug depuis une URL RSI Spectrum."""
        m = re.search(r'/thread/([^/\s]+)', url)
        return m.group(1) if m else None

    def fetch_thread(self, slug: str) -> Optional[dict]:
        """Retourne le JSON complet du thread RSI."""
        self._ensure_token()
        try:
            r = self.session.post(
                THREAD_API,
                json={"slug": slug, "sort": "votes", "target_reply_id": None},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("success") == 1:
                return data["data"]
        except Exception as e:
            print(f"  [RSI] Erreur pour {slug}: {e}")
        return None

    def _is_bold(self, block: dict) -> bool:
        """Vérifie si le texte du bloc est entièrement ou majoritairement en gras."""
        ranges = block.get("inlineStyleRanges", [])
        text = block.get("text", "").strip()
        if not text:
            return False
        bold_len = sum(r["length"] for r in ranges if r.get("style") == "BOLD")
        return bold_len >= len(text) * 0.5

    def parse_blocks(self, blocks: list) -> list[PatchSection]:
        """
        Convertit les content_blocks Draft.js de RSI en PatchSections.

        Types de blocs :
          header-one       → section principale (Features & Gameplay, Bugfixes…)
          header-two       → sous-section
          blockquote       → sous-section (Gameplay, Ships & Vehicles…)
          unstyled + BOLD  → titre d'item OU sous-section selon le contexte
          unstyled         → description de l'item courant
          unordered-list-item → item de liste (bug fix, known issue…)
        """
        sections: list[PatchSection] = []
        current_section: Optional[PatchSection] = None
        current_title: Optional[str] = None
        current_desc: list[str] = []
        skip = False

        def flush_item():
            nonlocal current_title, current_desc
            if current_title and current_section is not None and not skip:
                current_section.items.append(
                    PatchItem(
                        title=current_title,
                        description="\n".join(current_desc).strip(),
                    )
                )
            current_title = None
            current_desc = []

        def flush_section():
            if current_section is not None and current_section.items:
                sections.append(current_section)

        def start_section(name: str, is_skip: bool = False):
            nonlocal current_section, skip
            flush_item()
            flush_section()
            current_section = PatchSection(name=name)
            skip = is_skip

        for block in blocks:
            btype = block.get("type", "")
            raw   = block.get("text", "")
            text  = raw.strip()

            if not text:
                # Ligne vide → fin de l'item courant
                if current_title:
                    flush_item()
                continue

            # ── Section principale ──────────────────────────────────────────
            if btype in ("header-one", "header-two"):
                is_meta = text.lower() in SKIP_HEADERS
                start_section(text, is_skip=is_meta)
                continue

            # ── Sous-section (blockquote = Gameplay, Ships & Vehicles…) ─────
            if btype == "blockquote":
                start_section(text, is_skip=False)
                continue

            if skip:
                continue

            # ── Item de liste (bug fixes, known issues…) ────────────────────
            if btype == "unordered-list-item":
                flush_item()
                if current_section is None:
                    current_section = PatchSection(name="General")
                clean = text.lstrip()
                # Nettoyer les préfixes verbeux "Potential Fix: " pour le titre
                title = re.sub(r'^Potential Fix:\s*', '', clean)
                current_title = title
                continue

            # ── Texte unstyled ───────────────────────────────────────────────
            if btype == "unstyled":
                is_bold = self._is_bold(block)

                # Texte court et gras → probablement un titre d'item
                if is_bold and len(text) < 120:
                    flush_item()
                    if current_section is None:
                        current_section = PatchSection(name="General")
                    current_title = text
                    continue

                # Texte avec current_title → description
                if current_title is not None:
                    current_desc.append(text)
                    continue

                # Sinon : ligne standalone (ex: "Fixed 5 Client Crashes")
                flush_item()
                if current_section is None:
                    current_section = PatchSection(name="General")
                current_title = text

        flush_item()
        flush_section()
        return sections

    # ------------------------------------------------------------------ #
    #  COMM-LINK SUPPORT                                                  #
    # ------------------------------------------------------------------ #

    def _fetch_commlink_s3(self, page_url: str) -> Optional[str]:
        """Fetches the S3 HTML content for an RSI comm-link page."""
        try:
            r = self.session.get(page_url, timeout=15)
            r.raise_for_status()
            m = re.search(r"const s3Url\s*=\s*'([^']+)'", r.text)
            if not m:
                return None
            s3_url = m.group(1)
            r2 = self.session.get(s3_url, timeout=15)
            r2.raise_for_status()
            return r2.text
        except Exception as e:
            print(f"  [RSI] Comm-link fetch error: {e}")
            return None

    @staticmethod
    def _first_sentences(text: str, max_chars: int = 350) -> str:
        """Truncate to the first sentence(s) up to max_chars."""
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars]
        last_dot = cut.rfind('. ')
        if last_dot > max_chars // 3:
            return cut[:last_dot + 1]
        return cut.rstrip() + '…'

    def _parse_inner_html(self, raw_html: str) -> list[PatchItem]:
        """
        Parses the inner HTML of a comm-link content block into PatchItems.

        Strategy:
          1. Strip all inline formatting tags (<u>, <strong>, <em>, <span>…)
             so h3/li/p boundaries are unambiguous.
          2. Walk structural tokens: h2/h3/h4 → item title, li → item title,
             p → short description (truncated to ~2 sentences).
        """
        STRUCTURAL = re.compile(r'^/?(?:h[1-4]|p|ul|ol|li|br)\b', re.I)

        # Remove inline-only tags (keep their text content)
        cleaned = re.sub(
            r'</?(?:u|strong|em|b|i|span|a|code)[^>]*>',
            '',
            raw_html,
            flags=re.I,
        )

        items: list[PatchItem] = []
        current_title: Optional[str] = None
        current_desc: list[str] = []
        buf: list[str] = []

        def flush():
            nonlocal current_title, current_desc
            if current_title:
                desc = self._first_sentences(" ".join(current_desc).strip())
                items.append(PatchItem(
                    title=current_title.strip(),
                    description=desc,
                ))
            current_title = None
            current_desc = []

        def take_buf() -> str:
            text = re.sub(r'\s+', ' ', ''.join(buf)).strip()
            buf.clear()
            return text

        for part in re.split(r'(<[^>]+>)', cleaned):
            if not part:
                continue

            m = re.match(r'<(/?)([a-z0-9]+)', part, re.I)
            if not m:
                buf.append(part)
                continue

            closing = m.group(1) == '/'
            tag = m.group(2).lower()

            if not STRUCTURAL.match(('/' if closing else '') + tag):
                # Non-structural tag remnant (shouldn't exist after strip, safety)
                continue

            if not closing:
                # Opening structural tag: flush any stray text in buf
                stray = take_buf()
                if stray and current_title is None:
                    current_title = stray
                elif stray and current_title is not None:
                    current_desc.append(self._first_sentences(stray))
            else:
                text = take_buf()
                if not text:
                    continue
                if tag in ('h1', 'h2', 'h3', 'h4'):
                    flush()
                    current_title = text
                elif tag == 'li':
                    flush()
                    current_title = text
                elif tag == 'p':
                    short = self._first_sentences(text)
                    if current_title is not None:
                        current_desc.append(short)
                    else:
                        current_title = short

        flush()
        return items

    def parse_comm_link_blocks(self, s3_content: str) -> list[PatchSection]:
        """
        Parses RSI comm-link S3 HTML (Vue component props) into PatchSections.
        Each title+content JSON pair becomes a PatchSection.
        """
        SKIP_TITLES = {"known issues", "testing", "feedback"}
        decoded = htmlmod.unescape(s3_content)

        pairs = re.findall(r'"title":"([^"]+)","content":"(<[^"]+)"', decoded)
        if not pairs:
            return []

        sections: list[PatchSection] = []
        for title, raw_html in pairs:
            if any(s in title.lower() for s in SKIP_TITLES):
                continue
            items = self._parse_inner_html(raw_html)
            if items:
                sections.append(PatchSection(name=title, items=items))

        return sections

    def enrich_patch_note(self, note: PatchNote, url: str) -> bool:
        """
        Remplace les sections d'un PatchNote par le contenu complet RSI.
        Supporte les threads Spectrum (/spectrum/) et les comm-links (/comm-link/).
        Retourne True si l'enrichissement a réussi.
        """
        if "/comm-link/" in url:
            return self._enrich_from_comm_link(note, url)
        return self._enrich_from_spectrum(note, url)

    def _enrich_from_spectrum(self, note: PatchNote, url: str) -> bool:
        slug = self.slug_from_url(url)
        if not slug:
            return False

        thread = self.fetch_thread(slug)
        if not thread:
            return False

        content_blocks = thread.get("content_blocks", [])
        if not content_blocks:
            return False

        blocks = content_blocks[0].get("data", {}).get("blocks", [])
        if not blocks:
            return False

        sections = self.parse_blocks(blocks)
        if sections:
            note.sections = sections
            return True

        return False

    def _enrich_from_comm_link(self, note: PatchNote, url: str) -> bool:
        self._ensure_token()
        s3_content = self._fetch_commlink_s3(url)
        if not s3_content:
            return False

        sections = self.parse_comm_link_blocks(s3_content)
        if sections:
            note.sections = sections
            return True

        return False
