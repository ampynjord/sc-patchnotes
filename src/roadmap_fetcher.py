import requests
from typing import Optional

RSI_ROADMAP_API = "https://robertsspaceindustries.com/api/roadmap/v1/boards/1?lang=en_US"

CATEGORY_NAMES = {
    1: "Core Tech",
    2: "Gameplay",
    3: "Characters",
    4: "Locations",
    5: "AI",
    6: "Ships and Vehicles",
    7: "Weapons and Items",
    15: "Missions and Events",
}

CATEGORY_NAMES_FR = {
    1: "Technologies Fondamentales",
    2: "Gameplay",
    3: "Personnages",
    4: "Lieux",
    5: "Intelligence Artificielle",
    6: "Vaisseaux & Véhicules",
    7: "Armes & Équipements",
    15: "Missions & Événements",
}

# Unicode symbols matching the SC aesthetic
CATEGORY_ICONS = {
    1: "⬡",   # Core Tech
    2: "◆",   # Gameplay
    3: "◈",   # Characters
    4: "▲",   # Locations
    5: "⬡",   # AI
    6: "◭",   # Ships and Vehicles
    7: "✦",   # Weapons and Items
    15: "◉",  # Missions and Events
}

# Category display order (alphabetical, matching the roadmap UI)
CATEGORY_ORDER = [3, 1, 2, 4, 15, 6, 7, 5]


class RoadmapCard:
    __slots__ = (
        "id", "name", "description", "category_id", "status",
        "released", "thumbnail_large", "thumbnail_rect", "url_slug",
    )

    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name", "")
        self.description = data.get("description", "")
        self.category_id = data.get("category_id")
        self.status = data.get("status", "")
        self.released = data.get("released", 0)
        self.url_slug = data.get("url_slug", "")
        thumb = data.get("thumbnail") or {}
        urls = thumb.get("urls") or {}
        self.thumbnail_large = urls.get("large", "")
        self.thumbnail_rect = urls.get("rect", "")


class RoadmapFetcher:
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        })
        self._data: Optional[dict] = None

    def _ensure_data(self):
        if self._data is None:
            r = self._session.get(RSI_ROADMAP_API, timeout=15)
            r.raise_for_status()
            self._data = r.json().get("data", {})

    def get_cards_for_version(self, version: str) -> list[RoadmapCard]:
        """Return roadmap cards for a version string ('4.8' or '4.8.0')."""
        self._ensure_data()
        releases = self._data.get("releases", [])
        # "4.8.0" → also try "4.8" (roadmap uses short names like "4.8")
        base = version.rsplit(".", 1)[0] if version.count(".") >= 2 else version
        release = next(
            (r for r in releases if r.get("name") in (version, base)),
            None,
        )
        if release is None:
            return []
        return [RoadmapCard(c) for c in release.get("cards", [])]

    def get_release_meta(self, version: str) -> dict:
        """Return release-level metadata (status, description/quarter, etc.)."""
        self._ensure_data()
        releases = self._data.get("releases", [])
        base = version.rsplit(".", 1)[0] if version.count(".") >= 2 else version
        return next(
            (r for r in releases if r.get("name") in (version, base)),
            {},
        )

    @staticmethod
    def get_category_name(category_id: int, lang: str = "en") -> str:
        if lang == "fr":
            return CATEGORY_NAMES_FR.get(category_id, CATEGORY_NAMES.get(category_id, "?"))
        return CATEGORY_NAMES.get(category_id, "?")

    @staticmethod
    def get_category_icon(category_id: int) -> str:
        return CATEGORY_ICONS.get(category_id, "◈")
