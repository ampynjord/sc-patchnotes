import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# ID du bot qui poste tous les patch notes dans le canal
NEWSBOT_ID = "1091116499936223252"


@dataclass
class PatchItem:
    title: str
    description: str = ""


@dataclass
class PatchSection:
    name: str
    items: List[PatchItem] = field(default_factory=list)


@dataclass
class PatchNote:
    version: str        # ex: "4.8.0"
    build: str          # ex: "11811531"
    environment: str    # LIVE | PTU | EVOCATI
    audience: str       # "All Waves", "Wave 3", "Evocati NDA", etc.
    iteration: int      # numéro d'itération dans l'env
    date: str
    message_id: str
    sections: List[PatchSection] = field(default_factory=list)
    raw_content: str = ""
    rsi_url: str = ""   # URL vers le thread Spectrum complet


class PatchNotesParser:
    # "Star Citizen Alpha 4.8 PTU 11811531" ou "4.8.0"
    RE_VERSION  = re.compile(r'Alpha\s+(\d+\.\d+(?:\.\d+)?)\s+(?:PTU|LIVE|EPTU)', re.I)
    RE_VERSION2 = re.compile(r'(\d+\.\d+\.\d+)', re.I)
    RE_BUILD    = re.compile(r'(?:PTU|LIVE|EPTU)\s+(\d{6,})', re.I)

    # Sections : __**Nom:**__ ou **Nom:** ou **Nom**
    RE_SEC_DECO = re.compile(r'^__\*\*(.+?)\*\*__\s*:?\s*$')
    RE_SEC_BOLD = re.compile(r'^\*\*([^*]+?)\*\*\s*:?\s*$')

    # Items : ➣ (U+27A3) ou -> ou =>
    RE_ITEM = re.compile(r'^(?:➣|->|=>|[•])\s*(.+)')

    # Préfixes d'items qui sont des métadonnées (pas des changements de jeu)
    RE_META_ITEM = re.compile(
        r'^(?:audience|server info|long term persistence|ltp|'
        r'patch channel|us only|eu only|atv|build number|'
        r'\d+ known issues?|potential fix)',
        re.I
    )

    # Mots-clés dans les titres de section → à ignorer (métadonnées, pas des changements de jeu)
    SKIP_KEYWORDS = [
        "audience", "server details", "patch details",
        "testing", "feedback focus", "known issues",
        "note for tonight", "note:", "important:",
    ]

    # Sections de contenu de jeu valides → toujours garder même si courtes
    GAME_KEYWORDS = [
        "gameplay", "ships", "vehicles", "weapons", "items", "core tech",
        "bugfix", "bug fix", "technical", "missions", "economy", "environment",
        "character", "fps", "flight", "mining", "audio", "graphics", "ai",
        "cargo", "locations", "feature", "docking", "fuel",
    ]

    def _normalize_version(self, v: str) -> str:
        """4.8 → 4.8.0"""
        parts = v.split(".")
        while len(parts) < 3:
            parts.append("0")
        return ".".join(parts)

    def _embed_description(self, message: dict) -> Optional[str]:
        """Retourne la description du premier embed qui en a une."""
        for embed in message.get("embeds", []):
            desc = embed.get("description", "")
            if desc:
                return desc
        return None

    def _embed_title(self, message: dict) -> str:
        """Retourne le titre du premier embed."""
        for embed in message.get("embeds", []):
            t = embed.get("title", "")
            if t:
                return t
        return ""

    def detect_version(self, text: str) -> Optional[str]:
        m = self.RE_VERSION.search(text)
        if m:
            return self._normalize_version(m.group(1))
        m = self.RE_VERSION2.search(text)
        if m:
            return self._normalize_version(m.group(1))
        return None

    def detect_build(self, text: str) -> str:
        m = self.RE_BUILD.search(text)
        return m.group(1) if m else ""

    def detect_environment(self, text: str) -> str:
        upper = text.upper()
        if "EVOCATI" in upper:
            return "EVOCATI"
        if "EPTU" in upper:
            return "EPTU"
        if "PTU" in upper:
            return "PTU"
        if "LIVE" in upper:
            return "LIVE"
        return "UNKNOWN"

    def detect_audience(self, text: str) -> str:
        """Extrait l'audience depuis le titre entre crochets : [All Waves] → 'All Waves'."""
        m = re.search(r'\[([^\]]+)\]', text)
        return m.group(1) if m else ""

    def parse_sections(self, content: str) -> List[PatchSection]:
        sections: List[PatchSection] = []
        current_section: Optional[PatchSection] = None
        current_title: Optional[str] = None
        current_desc: List[str] = []
        skip = False

        def flush_item():
            nonlocal current_title, current_desc
            if current_title and current_section is not None and not skip:
                current_section.items.append(
                    PatchItem(title=current_title, description=" ".join(current_desc).strip())
                )
            current_title = None
            current_desc = []

        def flush_section():
            if current_section is not None and current_section.items:
                sections.append(current_section)

        for raw_line in content.split("\n"):
            line = raw_line.strip()
            # Supprimer les balises spoiler Discord ||texte||
            line = re.sub(r'\|\|(.+?)\|\|', r'\1', line)
            if not line:
                continue

            # Section ? (on ignore les lignes trop longues — ce sont des notes, pas des headers)
            m_sec = self.RE_SEC_DECO.match(line) or self.RE_SEC_BOLD.match(line)
            if m_sec and len(m_sec.group(1).strip()) <= 60:
                flush_item()
                flush_section()
                sec_name = m_sec.group(1).strip()
                sec_lower = sec_name.lower()
                is_game = any(k in sec_lower for k in self.GAME_KEYWORDS)
                is_meta = any(k in sec_lower for k in self.SKIP_KEYWORDS)
                skip = is_meta and not is_game
                current_section = PatchSection(name=sec_name)
                continue

            if skip:
                continue

            # Item ➣ ?
            m_item = self.RE_ITEM.match(line)
            if m_item:
                flush_item()
                title = m_item.group(1).strip()
                title = re.sub(r'^\*\*(.+)\*\*$', r'\1', title)
                # Ignorer les items qui sont des métadonnées de patch
                if self.RE_META_ITEM.match(title):
                    continue
                if current_section is None:
                    current_section = PatchSection(name="General")
                current_title = title
                continue

            if current_title is not None:
                current_desc.append(line)

        flush_item()
        flush_section()
        return sections

    def _embed_url(self, message: dict) -> str:
        """Retourne l'URL RSI de l'embed (lien vers le thread Spectrum complet)."""
        for embed in message.get("embeds", []):
            url = embed.get("url", "")
            if url and "robertsspaceindustries.com" in url:
                return url
        return ""

    def parse_message(self, message: dict) -> Optional[PatchNote]:
        # Filtrer : seulement NewsBot
        if message.get("author", {}).get("id") != NEWSBOT_ID:
            return None

        # Le contenu réel est dans l'embed description
        embed_desc = self._embed_description(message)
        if not embed_desc:
            return None  # Message titre sans embed → ignoré

        title_text = message.get("content", "")
        embed_title = self._embed_title(message)
        # La version et le build sont dans le titre de l'embed
        full_text = title_text + "\n" + embed_title + "\n" + embed_desc

        version = self.detect_version(full_text)
        if not version:
            return None

        # L'audience est dans le titre de l'embed ou du message texte
        audience_src = embed_title or title_text

        return PatchNote(
            version=version,
            build=self.detect_build(full_text),
            environment=self.detect_environment(full_text),
            audience=self.detect_audience(audience_src),
            iteration=0,
            date=message.get("timestamp", ""),
            message_id=message.get("id", ""),
            sections=self.parse_sections(embed_desc),
            raw_content=embed_desc,
            rsi_url=self._embed_url(message),
        )

    def parse_all(
        self, messages: list, version_filter: str = None
    ) -> Dict[str, List[PatchNote]]:
        """Parse tous les messages et groupe par version majeure."""
        grouped: Dict[str, List[PatchNote]] = {}

        for msg in messages:
            note = self.parse_message(msg)
            if not note:
                continue
            if version_filter and not note.version.startswith(version_filter):
                continue
            grouped.setdefault(note.version, []).append(note)

        # Tri chronologique + numérotation des itérations par env
        for version, notes in grouped.items():
            notes.sort(key=lambda n: n.date)
            counters: Dict[str, int] = {}
            for note in notes:
                counters[note.environment] = counters.get(note.environment, 0) + 1
                note.iteration = counters[note.environment]

        return grouped
