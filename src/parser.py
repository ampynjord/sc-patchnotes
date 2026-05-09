import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict


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
    full_version: str   # ex: "4.8.0a" si présent
    environment: str    # LIVE | PTU | EPTU
    iteration: int      # numéro d'itération dans l'env
    date: str
    message_id: str
    sections: List[PatchSection] = field(default_factory=list)
    raw_content: str = ""


class PatchNotesParser:
    # Détection de version : "4.8.0", "Alpha 4.8.0", "Star Citizen 4.8.0a", etc.
    RE_VERSION = re.compile(
        r'(?:Star Citizen\s+|Alpha\s+|SC\s+)?(\d+\.\d+\.\d+[a-z]?)',
        re.IGNORECASE,
    )
    # Section header : **Texte** ou **Texte:** ou ### Texte
    RE_SECTION = re.compile(r'^\*\*([^*]+?)\*\*\s*:?\s*$')
    RE_SECTION_MD = re.compile(r'^#{1,4}\s+(.+)$')
    # Item : -> Titre ou => Titre ou - Titre
    RE_ITEM = re.compile(r'^(?:->|=>|[•\-])\s+(.+)')

    def _full_content(self, message: dict) -> str:
        parts = [message.get("content", "")]
        for embed in message.get("embeds", []):
            if embed.get("title"):
                parts.append(embed["title"])
            if embed.get("description"):
                parts.append(embed["description"])
            for field in embed.get("fields", []):
                parts.append(field.get("name", ""))
                parts.append(field.get("value", ""))
        return "\n".join(p for p in parts if p)

    def detect_version(self, text: str) -> Optional[str]:
        m = self.RE_VERSION.search(text)
        return m.group(1) if m else None

    def detect_environment(self, text: str) -> str:
        upper = text.upper()
        if "EPTU" in upper:
            return "EPTU"
        if "PTU" in upper:
            return "PTU"
        if "LIVE" in upper:
            return "LIVE"
        return "UNKNOWN"

    def parse_sections(self, content: str) -> List[PatchSection]:
        sections: List[PatchSection] = []
        current_section: Optional[PatchSection] = None
        current_title: Optional[str] = None
        current_desc: List[str] = []

        def flush_item():
            nonlocal current_title, current_desc
            if current_title and current_section is not None:
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
            if not line:
                continue

            # Section header ?
            m_sec = self.RE_SECTION.match(line) or self.RE_SECTION_MD.match(line)
            if m_sec:
                flush_item()
                flush_section()
                current_section = PatchSection(name=m_sec.group(1).strip())
                continue

            # Item ?
            m_item = self.RE_ITEM.match(line)
            if m_item:
                flush_item()
                if current_section is None:
                    current_section = PatchSection(name="General")
                current_title = m_item.group(1).strip()
                continue

            # Description de l'item courant
            if current_title is not None:
                current_desc.append(line)

        flush_item()
        flush_section()
        return sections

    def parse_message(self, message: dict) -> Optional[PatchNote]:
        content = self._full_content(message)
        version = self.detect_version(content)
        if not version:
            return None

        # version "propre" sans lettre suffixe
        base_version = re.match(r"(\d+\.\d+\.\d+)", version).group(1)

        return PatchNote(
            version=base_version,
            full_version=version,
            environment=self.detect_environment(content),
            iteration=0,
            date=message.get("timestamp", ""),
            message_id=message.get("id", ""),
            sections=self.parse_sections(content),
            raw_content=content,
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
