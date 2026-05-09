"""
Dump JSON brut des 5 derniers patches pour voir toute la structure disponible.
"""
import json, requests, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)

headers = {
    "Authorization": cfg["token"],
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

r = requests.get(
    f"https://discord.com/api/v10/channels/{cfg['channel_id']}/messages",
    headers=headers, params={"limit": 50},
)
messages = r.json()

NEWSBOT_ID = "1091116499936223252"

count = 0
for msg in messages:
    if msg.get("author", {}).get("id") != NEWSBOT_ID:
        continue
    embeds = msg.get("embeds", [])
    if not embeds:
        continue
    count += 1
    if count > 2:
        break

    print(f"\n{'='*60}")
    print(f"Message {msg['id']} — {msg['timestamp'][:10]}")
    print(json.dumps(msg, indent=2, ensure_ascii=False))
    print()
