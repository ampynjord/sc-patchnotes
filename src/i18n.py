LABELS = {
    "en": {
        "report_title": "Star Citizen {version} — Patch Notes Report",
        "generated_on": "Generated on",
        "toc": "Table of Contents",
        "ptu_history": "PTU / EPTU History",
        "live_release": "LIVE Release",
        "synthesis": "Final Synthesis",
        "environment": "Environment",
        "date": "Date",
        "patch_label": "{env} Patch #{num}",
        "no_notes": "No patch notes found for this version.",
        "total_patches": "Total patches",
        "back_to_top": "↑ Back to top",
        "all_changes": "All consolidated changes",
    },
    "fr": {
        "report_title": "Star Citizen {version} — Rapport des Patch Notes",
        "generated_on": "Généré le",
        "toc": "Table des matières",
        "ptu_history": "Historique PTU / EPTU",
        "live_release": "Sortie LIVE",
        "synthesis": "Synthèse Finale",
        "environment": "Environnement",
        "date": "Date",
        "patch_label": "Patch {env} n°{num}",
        "no_notes": "Aucune note de patch trouvée pour cette version.",
        "total_patches": "Total des patches",
        "back_to_top": "↑ Retour en haut",
        "all_changes": "Tous les changements consolidés",
    },
}

# Traduction des noms de sections (le contenu des patches reste en anglais,
# mais les titres de section sont traduits dans le rapport FR)
SECTIONS = {
    "features and gameplay": {"en": "Features & Gameplay", "fr": "Fonctionnalités & Gameplay"},
    "gameplay":              {"en": "Gameplay",             "fr": "Gameplay"},
    "ships & vehicles":      {"en": "Ships & Vehicles",     "fr": "Vaisseaux & Véhicules"},
    "ships and vehicles":    {"en": "Ships & Vehicles",     "fr": "Vaisseaux & Véhicules"},
    "weapons & items":       {"en": "Weapons & Items",      "fr": "Armes & Équipements"},
    "weapons and items":     {"en": "Weapons & Items",      "fr": "Armes & Équipements"},
    "core tech":             {"en": "Core Tech",            "fr": "Technologies Fondamentales"},
    "bugfixes & technical":  {"en": "Bug Fixes & Technical","fr": "Corrections & Technique"},
    "bug fixes":             {"en": "Bug Fixes",            "fr": "Corrections de Bugs"},
    "technical":             {"en": "Technical",            "fr": "Technique"},
    "known issues":          {"en": "Known Issues",         "fr": "Problèmes Connus"},
    "general":               {"en": "General",              "fr": "Général"},
    "ui":                    {"en": "User Interface",       "fr": "Interface Utilisateur"},
    "missions":              {"en": "Missions",             "fr": "Missions"},
    "economy":               {"en": "Economy",              "fr": "Économie"},
    "environment":           {"en": "Environment",          "fr": "Environnement"},
    "network":               {"en": "Network",              "fr": "Réseau"},
    "performance":           {"en": "Performance",          "fr": "Performance"},
    "ai":                    {"en": "AI",                   "fr": "Intelligence Artificielle"},
    "audio":                 {"en": "Audio",                "fr": "Audio"},
    "graphics":              {"en": "Graphics",             "fr": "Graphismes"},
    "character":             {"en": "Character",            "fr": "Personnage"},
    "fps":                   {"en": "FPS Combat",           "fr": "Combat FPS"},
    "flight":                {"en": "Flight",               "fr": "Vol"},
    "mining":                {"en": "Mining",               "fr": "Minage"},
    "medical":               {"en": "Medical",              "fr": "Médical"},
    "cargo":                 {"en": "Cargo",                "fr": "Cargo"},
    "locations":             {"en": "Locations",            "fr": "Lieux"},
}

ENV_COLORS = {
    "LIVE":    "#2ecc71",
    "PTU":     "#3498db",
    "EPTU":    "#e67e22",
    "UNKNOWN": "#95a5a6",
}

ENV_BADGES = {
    "LIVE":    "🟢 LIVE",
    "PTU":     "🔵 PTU",
    "EPTU":    "🟠 EPTU",
    "UNKNOWN": "⚪ ?",
}


def translate_section(name: str, lang: str) -> str:
    key = name.strip().lower()
    for k, v in SECTIONS.items():
        if k in key or key in k:
            return v.get(lang, name)
    return name
