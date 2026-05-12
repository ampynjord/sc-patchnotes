"""
Fetches RSI event pages (DefenseCon, Invictus Launch Week) and parses them
into structured ship/feature data by reusing the existing comm-link parser.
"""
import re
from typing import Optional
from .rsi_fetcher import RSIFetcher
from .parser import PatchSection, PatchItem


class EventShip:
    __slots__ = ("name", "manufacturer", "type", "status", "day")

    def __init__(self, name: str, manufacturer: str = "", ship_type: str = "",
                 status: str = "", day: str = ""):
        self.name = name
        self.manufacturer = manufacturer
        self.type = ship_type
        self.status = status   # "flyable" | "concept" | "sale" | ""
        self.day = day         # date or day label from schedule


class EventData:
    def __init__(self, title: str, url: str):
        self.title = title
        self.url = url
        self.ships: list[EventShip] = []
        self.sections: list[PatchSection] = []  # raw parsed sections (fallback)


# Known DefenseCon / ILW ship data — updated for DefenseCon 2956 / Alpha 4.8
# Used as fallback when comm-link S3 parsing yields no ships.
DEFENSECON_2956_SHIPS = [
    EventShip("Drake Ironclad",         "Drake Interplanetary",    "Armored Heavy Freighter",  "flyable",  "May 14–15"),
    EventShip("Drake Ironclad Assault", "Drake Interplanetary",    "Assault Freighter",        "flyable",  "May 14–15"),
    EventShip("Drake Pitbull",          "Drake Interplanetary",    "Ground Vehicle",           "concept",  "May 14–15"),
    EventShip("Origin M80",             "Origin Jumpworks",        "Heavy Fighter",            "concept",  "May 16–17"),
    EventShip("MISC Starlite",          "MISC",                    "Light Refueling Ship",     "concept",  "May 18–19"),
    EventShip("Aegis Tiburon",          "Aegis Dynamics",          "Combat Ship",              "concept",  "May 20–21"),
    EventShip("Anvil Odin",             "Anvil Aerospace",         "Battlecruiser",            "concept",  "May 24–25"),
]


class EventFetcher:
    def __init__(self):
        self._rsi = RSIFetcher()

    def fetch(self, url: str, title: str = "") -> Optional[EventData]:
        """
        Fetch an RSI event comm-link and return structured EventData.
        Falls back to DEFENSECON_2956_SHIPS for known DefenseCon 2956 URLs.
        """
        data = EventData(title=title or self._title_from_url(url), url=url)

        self._rsi._ensure_token()
        s3_content = self._rsi._fetch_commlink_s3(url)

        if s3_content:
            sections = self._rsi.parse_comm_link_blocks(s3_content)
            data.sections = sections
            data.ships = self._extract_ships_from_sections(sections)

        # Fallback: if we know this is DefenseCon 2956, inject known ships
        if not data.ships and "DefenseCon" in data.title:
            data.ships = list(DEFENSECON_2956_SHIPS)

        return data if (data.ships or data.sections) else None

    @staticmethod
    def _title_from_url(url: str) -> str:
        m = re.search(r'/(\d+-[^/]+)$', url)
        if m:
            return m.group(1).replace("-", " ").title()
        return "Event"

    @staticmethod
    def _extract_ships_from_sections(sections: list[PatchSection]) -> list[EventShip]:
        """
        Heuristically extract ship entries from parsed comm-link sections.
        Looks for items whose title looks like a ship name.
        """
        ships = []
        MFRS = {
            "drake": "Drake Interplanetary",
            "aegis": "Aegis Dynamics",
            "origin": "Origin Jumpworks",
            "misc": "MISC",
            "anvil": "Anvil Aerospace",
            "crusader": "Crusader Industries",
            "rsi": "Roberts Space Industries",
            "argo": "ARGO Astronautics",
            "banu": "Banu",
            "xi'an": "Xi'An",
            "esperia": "Esperia",
            "gatac": "Gatac Manufacture",
            "mirai": "Mirai",
            "tumbril": "Tumbril",
            "greycat": "Greycat",
            "kruger": "Kruger Intergalactic",
        }
        STATUS_WORDS = {"flyable", "concept", "sale", "new"}

        for sec in sections:
            for item in sec.items:
                name = item.title.strip()
                if len(name) < 3 or len(name) > 80:
                    continue
                lower = name.lower()
                mfr = next((v for k, v in MFRS.items() if k in lower), "")
                status_guess = next(
                    (w for w in STATUS_WORDS if w in (item.description or "").lower()),
                    "",
                )
                ships.append(EventShip(
                    name=name,
                    manufacturer=mfr,
                    ship_type="",
                    status=status_guess,
                ))
        return ships
