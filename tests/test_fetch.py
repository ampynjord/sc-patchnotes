"""
Script de test : affiche les 20 derniers messages du canal
pour identifier le format et les auteurs des patch notes.
"""
import json
import requests

with open("config.json", encoding="utf-8") as f:
    cfg = json.load(f)

headers = {
    "Authorization": cfg["token"],
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

url = f"https://discord.com/api/v10/channels/{cfg['channel_id']}/messages"
r = requests.get(url, headers=headers, params={"limit": 20})

if r.status_code != 200:
    print(f"Erreur {r.status_code} : {r.text}")
    exit(1)

messages = r.json()
print(f"{len(messages)} messages récupérés\n")
print("=" * 80)

NEWSBOT_ID = "1091116499936223252"

for msg in messages:
    author = msg.get("author", {})
    if author.get("id") != NEWSBOT_ID:
        continue  # on ignore les humains

    date    = msg.get("timestamp", "")[:10]
    content = msg.get("content", "").replace("\n", " ")[:120]
    embeds  = msg.get("embeds", [])

    def safe(s, limit=300):
        return s[:limit].encode("ascii", "replace").decode("ascii").replace("\n", " | ")

    print(f"[{date}] contenu : {safe(content or '(vide)')}")
    for i, embed in enumerate(embeds):
        print(f"  -- embed {i} --")
        print(f"  title      : {safe(embed.get('title', ''), 100)}")
        print(f"  description: {safe(embed.get('description') or '', 500)}")
        for field in embed.get("fields", []):
            print(f"  field [{safe(field.get('name',''), 50)}] : {safe(str(field.get('value','')), 200)}")
    print()
