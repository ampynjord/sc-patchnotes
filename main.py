#!/usr/bin/env python3
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
Star Citizen Patch Notes Report Generator
Usage:
  python main.py fetch                          -- télécharge tous les messages du canal
  python main.py list                           -- liste les versions disponibles dans le cache
  python main.py report 4.8.0                  -- génère le rapport pour la version 4.8.0
  python main.py report 4.8.0 --env PTU EPTU  -- seulement les builds PTU et EPTU
"""

import argparse
import json
import os
import sys
import time

from src.fetcher import DiscordFetcher
from src.parser import PatchNotesParser
from src.generator import ReportGenerator
from src.rsi_fetcher import RSIFetcher
from src.roadmap_fetcher import RoadmapFetcher
from src.event_fetcher import EventFetcher


def load_config(path="config.json") -> dict:
    if not os.path.exists(path):
        print(f"[ERREUR] config.json introuvable. Copie config.json.example et remplis ton token.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    if cfg.get("token") == "COLLE_TON_TOKEN_ICI":
        print("[ERREUR] Ouvre config.json et remplace COLLE_TON_TOKEN_ICI par ton token Discord.")
        sys.exit(1)
    return cfg


def load_raw_messages(data_dir: str) -> list:
    raw_path = os.path.join(data_dir, "messages.json")
    if not os.path.exists(raw_path):
        print(f"[ERREUR] Pas de cache trouvé dans {raw_path}.")
        print("Lance d'abord : python main.py fetch")
        sys.exit(1)
    with open(raw_path, encoding="utf-8") as f:
        return json.load(f)


def cmd_fetch(cfg: dict):
    """Télécharge tous les messages des canaux Discord et les met en cache."""
    channel_ids = cfg.get("channel_ids") or [cfg["channel_id"]]
    announcement_ids = cfg.get("announcement_channel_ids", [])
    # Fetch all channels (patch notes + announcements), dedup later
    all_channel_ids = list(channel_ids) + [c for c in announcement_ids if c not in channel_ids]
    all_messages = []

    for channel_id in all_channel_ids:
        fetcher = DiscordFetcher(cfg["token"], channel_id)
        messages = fetcher.fetch_all_messages(max_messages=cfg.get("max_messages", 10000))
        all_messages.extend(messages)

    # Dédoublonnage par ID de message
    seen = set()
    unique_messages = []
    for m in all_messages:
        if m["id"] not in seen:
            seen.add(m["id"])
            unique_messages.append(m)

    raw_path = os.path.join(cfg["data_dir"], "messages.json")
    fetcher.save_raw(unique_messages, raw_path)
    print(f"\n{len(unique_messages)} messages mis en cache dans {raw_path}")


def cmd_list(cfg: dict):
    """Liste toutes les versions détectées dans le cache."""
    messages = load_raw_messages(cfg["data_dir"])
    parser = PatchNotesParser()
    announcement_ids = set(cfg.get("announcement_channel_ids", []))
    grouped = parser.parse_all(messages, announcement_channel_ids=announcement_ids)

    if not grouped:
        print("Aucune version détectée dans le cache.")
        return

    print(f"\nVersions disponibles ({len(grouped)}) :")
    for version, notes in sorted(grouped.items()):
        envs = {}
        for n in notes:
            envs[n.environment] = envs.get(n.environment, 0) + 1
        summary = "  ".join(f"{env}: {count}" for env, count in sorted(envs.items()))
        print(f"  {version}  ->  {summary}  ({len(notes)} patches)")


def cmd_report(cfg: dict, version: str, env_filter: list, live_preview: bool = False):
    """Enrichit depuis RSI Spectrum et génère les rapports MD + HTML FR/EN."""
    messages = load_raw_messages(cfg["data_dir"])
    parser = PatchNotesParser()
    announcement_ids = set(cfg.get("announcement_channel_ids", []))
    grouped = parser.parse_all(messages, version_filter=version, announcement_channel_ids=announcement_ids)

    if version not in grouped:
        print(f"[ERREUR] Version {version} introuvable dans le cache.")
        print("Versions disponibles :")
        for v in sorted(grouped.keys()):
            print(f"  {v}")
        sys.exit(1)

    notes = grouped[version]

    # Filtrage par environnement
    if env_filter:
        env_upper = [e.upper() for e in env_filter]
        notes = [n for n in notes if n.environment.upper() in env_upper]
        if not notes:
            print(f"[ERREUR] Aucun patch trouvé pour la version {version} avec les envs : {env_upper}")
            sys.exit(1)
        print(f"Filtre env : {env_upper} -> {len(notes)} patch(es) sélectionné(s)")

    # Enrichissement RSI
    rsi = RSIFetcher()
    enriched = 0
    for note in notes:
        if not note.rsi_url:
            print(f"  [{note.environment} #{note.iteration}] Pas d'URL RSI — skip")
            continue
        print(f"  [{note.environment} #{note.iteration}] {note.rsi_url[:80]}...")
        ok = rsi.enrich_patch_note(note, note.rsi_url)
        if ok:
            enriched += 1
            sec_count = len(note.sections)
            item_count = sum(len(s.items) for s in note.sections)
            print(f"    -> {sec_count} sections, {item_count} items")
        else:
            print(f"    -> Echec de l'enrichissement")
        time.sleep(0.8)

    print(f"\n{enriched}/{len(notes)} patches enrichis depuis RSI.")

    # Roadmap RSI
    roadmap_cards = []
    release_meta = {}
    print(f"\nRécupération des données roadmap pour {version}...")
    try:
        roadmap = RoadmapFetcher()
        roadmap_cards = roadmap.get_cards_for_version(version)
        release_meta = roadmap.get_release_meta(version)
        print(f"  -> {len(roadmap_cards)} cards roadmap ({release_meta.get('status','?')} — {release_meta.get('description','?')})")
    except Exception as e:
        print(f"  -> Roadmap indisponible : {e}")

    # Event ships (DefenseCon / Invictus Launch Week)
    event_data_list = []
    event_urls_cfg = cfg.get("event_urls", {})
    # Support both dict {"4.8.0": [...]} and list (global)
    if isinstance(event_urls_cfg, dict):
        version_short = version.rsplit(".", 1)[0]  # "4.8.0" -> "4.8"
        event_urls = (
            event_urls_cfg.get(version)
            or event_urls_cfg.get(version_short)
            or []
        )
    else:
        event_urls = list(event_urls_cfg)

    if event_urls:
        print(f"\nRécupération des données événement ({len(event_urls)} URL(s))...")
        ef = EventFetcher()
        for url in event_urls:
            try:
                ev = ef.fetch(url)
                if ev:
                    event_data_list.append(ev)
                    print(f"  -> {ev.title} : {len(ev.ships)} ship(s)")
                else:
                    print(f"  -> Aucune donnée pour {url}")
            except Exception as e:
                print(f"  -> Erreur event {url}: {e}")
            time.sleep(0.5)

    # Génération des rapports
    generator = ReportGenerator(output_dir=cfg["output_dir"])
    env_upper = [e.upper() for e in env_filter] if env_filter else None

    if live_preview:
        print(f"\nGénération du live preview pour la version {version}...")
        generator.generate_live_preview(
            grouped, version,
            env_filter=env_upper,
            roadmap_cards=roadmap_cards or None,
            release_meta=release_meta or None,
            event_data_list=event_data_list or None,
        )
    else:
        print(f"\nGénération des rapports pour la version {version}...")
        generator.generate(
            grouped, version,
            env_filter=env_upper,
            roadmap_cards=roadmap_cards or None,
            release_meta=release_meta or None,
            event_data_list=event_data_list or None,
        )
    print(f"\nRapports générés dans : {cfg['output_dir']}/{version}/")


def main():
    ap = argparse.ArgumentParser(
        description="Star Citizen Patch Notes Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="Télécharge les messages du canal Discord")
    sub.add_parser("list", help="Liste les versions disponibles dans le cache")

    rep = sub.add_parser("report", help="Enrichit depuis RSI et génère les rapports pour une version")
    rep.add_argument("version", help="Numéro de version (ex: 4.8.0)")
    rep.add_argument(
        "--env",
        nargs="+",
        metavar="ENV",
        choices=["EPTU", "PTU", "LIVE", "EVOCATI", "eptu", "ptu", "live", "evocati"],
        help="Filtrer par environnement (ex: --env PTU EPTU)",
    )
    rep.add_argument(
        "--live-preview",
        action="store_true",
        help="Génère une version LIVE clean basée sur la dernière note PTU",
    )

    args = ap.parse_args()
    cfg = load_config()

    os.makedirs(cfg.get("data_dir", "data"), exist_ok=True)
    os.makedirs(cfg.get("output_dir", "reports"), exist_ok=True)

    if args.cmd == "fetch":
        cmd_fetch(cfg)
    elif args.cmd == "list":
        cmd_list(cfg)
    elif args.cmd == "report":
        cmd_report(cfg, args.version, args.env or [], live_preview=getattr(args, "live_preview", False))


if __name__ == "__main__":
    main()
