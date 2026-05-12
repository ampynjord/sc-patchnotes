import requests
import json
import os
import time


class DiscordFetcher:
    BASE_URL = "https://discord.com/api/v10"

    def __init__(self, token: str, channel_id: str):
        self.channel_id = channel_id
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

    def _get(self, endpoint, params=None):
        url = f"{self.BASE_URL}{endpoint}"
        r = requests.get(url, headers=self.headers, params=params)
        if r.status_code == 429:
            retry_after = r.json().get("retry_after", 2)
            print(f"  Rate limited — attente {retry_after}s...")
            time.sleep(retry_after)
            return self._get(endpoint, params)
        r.raise_for_status()
        return r.json()

    def fetch_all_messages(self, max_messages: int = 5000) -> list:
        """Récupère tout l'historique du canal par pagination."""
        all_messages = []
        before = None

        print(f"Récupération des messages du canal {self.channel_id}...")

        while len(all_messages) < max_messages:
            params = {"limit": 100}
            if before:
                params["before"] = before

            batch = self._get(f"/channels/{self.channel_id}/messages", params)
            if not batch:
                break

            for msg in batch:
                msg["_channel_id"] = self.channel_id
            all_messages.extend(batch)
            before = batch[-1]["id"]
            print(f"  {len(all_messages)} messages récupérés...", end="\r")
            time.sleep(0.6)

        print(f"\nTotal : {len(all_messages)} messages récupérés.")
        return all_messages

    def save_raw(self, messages: list, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"Sauvegardé : {path}")

    def load_raw(self, path: str) -> list:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
