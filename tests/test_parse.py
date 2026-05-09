"""
Test du parser sur les 20 derniers messages réels.
"""
import json
import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.parser import PatchNotesParser

with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)

headers = {
    "Authorization": cfg["token"],
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

r = requests.get(
    f"https://discord.com/api/v10/channels/{cfg['channel_id']}/messages",
    headers=headers,
    params={"limit": 20},
)
messages = r.json()

parser = PatchNotesParser()
grouped = parser.parse_all(messages)

if not grouped:
    print("Aucun patch note parsé.")
else:
    for version, notes in sorted(grouped.items()):
        print(f"\n=== Version {version} ({len(notes)} patches) ===")
        for n in notes:
            print(f"  [{n.date[:10]}] {n.environment} #{n.iteration} | build {n.build} | audience: {n.audience}")
            for sec in n.sections:
                print(f"    Section: {sec.name} ({len(sec.items)} items)")
                for item in sec.items[:3]:
                    print(f"      - {item.title[:80]}")
                if len(sec.items) > 3:
                    print(f"      ... +{len(sec.items)-3} autres")
