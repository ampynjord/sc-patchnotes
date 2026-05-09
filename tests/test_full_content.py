"""
Dump complet du contenu brut d'un message patch note pour voir ce qu'on rate.
"""
import json, requests, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)

headers = {
    "Authorization": cfg["token"],
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# On récupère les 20 derniers messages
r = requests.get(
    f"https://discord.com/api/v10/channels/{cfg['channel_id']}/messages",
    headers=headers, params={"limit": 20},
)
messages = r.json()

NEWSBOT_ID = "1091116499936223252"

# On cherche le dernier message avec embed (le plus récent patch note)
for msg in messages:
    if msg.get("author", {}).get("id") != NEWSBOT_ID:
        continue
    embeds = msg.get("embeds", [])
    if not embeds:
        continue

    print(f"=== Message ID: {msg['id']} — {msg['timestamp'][:10]} ===")
    print(f"Content: {msg.get('content', '')[:200]}")
    print()

    for i, embed in enumerate(embeds):
        print(f"--- Embed {i} ---")
        print(f"  title      : {embed.get('title', '')}")
        print(f"  description: {embed.get('description', '')}")
        print()
        fields = embed.get("fields", [])
        if fields:
            print(f"  FIELDS ({len(fields)}) :")
            for f in fields:
                print(f"    [{f.get('name','')}]")
                print(f"    {f.get('value','')}")
                print()
        footer = embed.get("footer", {})
        if footer:
            print(f"  footer: {footer}")
        print()
    break  # Juste le premier
