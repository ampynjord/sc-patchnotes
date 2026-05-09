#!/usr/bin/env python3
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
"""
Star Citizen Patch Notes Report Generator
Usage:
  python main.py fetch              -- télécharge tous les messages du canal
  python main.py generate 4.8.0    -- génère les rapports pour la version 4.8.0
  python main.py list               -- liste les versions disponibles dans le cache
  python main.py all                -- génère les rapports pour toutes les versions
"""

import argparse
import json
import os
import sys

from src.fetcher import DiscordFetcher
from src.parser import PatchNotesParser
from src.generator import ReportGenerator
from src.rsi_fetcher import RSIFetcher


def load_config(path="config.json") -> dict:
    if not os.path.exists(path):
        print(f"[ERREUR] config.json introuvable. Copie config.json et remplis ton token.")
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
    """Télécharge tous les messages du canal Discord et les met en cache."""
    fetcher = DiscordFetcher(cfg["token"], cfg["channel_id"])
    messages = fetcher.fetch_all_messages(max_messages=cfg.get("max_messages", 5000))

    raw_path = os.path.join(cfg["data_dir"], "messages.json")
    fetcher.save_raw(messages, raw_path)
    print(f"\n{len(messages)} messages mis en cache dans {raw_path}")


def cmd_list(cfg: dict):
    """Liste toutes les versions détectées dans le cache."""
    messages = load_raw_messages(cfg["data_dir"])
    parser = PatchNotesParser()
    grouped = parser.parse_all(messages)

    if not grouped:
        print("Aucune version détectée dans le cache.")
        return

    print(f"\nVersions disponibles ({len(grouped)}) :")
    for version, notes in sorted(grouped.items()):
        envs = {}
        for n in notes:
            envs[n.environment] = envs.get(n.environment, 0) + 1
        summary = "  ".join(f"{env}: {count}" for env, count in sorted(envs.items()))
        print(f"  {version}  →  {summary}  ({len(notes)} patches)")


def cmd_enrich(cfg: dict, version: str):
    """Enrichit les patches avec le contenu complet depuis RSI Spectrum."""
    messages = load_raw_messages(cfg["data_dir"])
    parser = PatchNotesParser()
    grouped = parser.parse_all(messages, version_filter=version)

    if version not in grouped:
        print(f"[ERREUR] Version {version} introuvable.")
        sys.exit(1)

    notes = grouped[version]
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
            print(f"    → {sec_count} sections, {item_count} items")
        else:
            print(f"    → Échec de l'enrichissement")
        import time; time.sleep(0.8)

    print(f"\n{enriched}/{len(notes)} patches enrichis depuis RSI.")

    # Sauvegarder le cache enrichi
    enriched_path = os.path.join(cfg["data_dir"], f"enriched_{version}.json")
    import json, dataclasses
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump([dataclasses.asdict(n) for n in notes], f, ensure_ascii=False, indent=2)
    print(f"Cache enrichi sauvegardé : {enriched_path}")

    # Générer les rapports
    generator = ReportGenerator(output_dir=cfg["output_dir"])
    print(f"\nGénération des rapports enrichis pour la version {version}...")
    generator.generate(grouped, version)
    print(f"Rapports générés dans : {cfg['output_dir']}/{version}/")


def cmd_generate(cfg: dict, version: str):
    """Génère les rapports MD + HTML FR/EN pour une version donnée."""
    messages = load_raw_messages(cfg["data_dir"])
    parser = PatchNotesParser()
    grouped = parser.parse_all(messages, version_filter=version)

    if version not in grouped:
        print(f"[ERREUR] Version {version} introuvable dans le cache.")
        print("Versions disponibles :")
        for v in sorted(grouped.keys()):
            print(f"  {v}")
        sys.exit(1)

    generator = ReportGenerator(output_dir=cfg["output_dir"])
    print(f"\nGénération des rapports pour la version {version}...")
    generator.generate(grouped, version)
    print(f"\nRapports générés dans : {cfg['output_dir']}/{version}/")


def cmd_all(cfg: dict):
    """Génère les rapports pour toutes les versions disponibles."""
    messages = load_raw_messages(cfg["data_dir"])
    parser = PatchNotesParser()
    grouped = parser.parse_all(messages)

    if not grouped:
        print("Aucune version trouvée.")
        return

    generator = ReportGenerator(output_dir=cfg["output_dir"])
    for version in sorted(grouped.keys()):
        print(f"\n→ Version {version}")
        generator.generate(grouped, version)

    print(f"\nTous les rapports générés dans : {cfg['output_dir']}/")


def main():
    ap = argparse.ArgumentParser(
        description="Star Citizen Patch Notes Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch", help="Télécharge les messages du canal Discord")
    sub.add_parser("list", help="Liste les versions disponibles dans le cache")

    gen = sub.add_parser("generate", help="Génère les rapports pour une version")
    gen.add_argument("version", help="Numéro de version (ex: 4.8.0)")

    sub.add_parser("all", help="Génère les rapports pour toutes les versions")

    enr = sub.add_parser("enrich", help="Enrichit avec le contenu complet RSI + génère les rapports")
    enr.add_argument("version", help="Numéro de version (ex: 4.8.0)")

    args = ap.parse_args()
    cfg = load_config()

    os.makedirs(cfg.get("data_dir", "data"), exist_ok=True)
    os.makedirs(cfg.get("output_dir", "reports"), exist_ok=True)

    if args.cmd == "fetch":
        cmd_fetch(cfg)
    elif args.cmd == "list":
        cmd_list(cfg)
    elif args.cmd == "generate":
        cmd_generate(cfg, args.version)
    elif args.cmd == "all":
        cmd_all(cfg)
    elif args.cmd == "enrich":
        cmd_enrich(cfg, args.version)


if __name__ == "__main__":
    main()
