import re
import time
import requests
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

    def enrich_patch_note(self, note: PatchNote, url: str) -> bool:
        """
        Remplace les sections d'un PatchNote par le contenu complet RSI.
        Retourne True si l'enrichissement a réussi.
        """
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
