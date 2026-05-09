# 🚀 SC Patch Notes — Star Citizen Report Generator

Outil CLI Python qui récupère les patch notes du canal Discord **sc-patch-notes** (`/r/starcitizen`) et génère des rapports complets et organisés pour chaque version majeure du jeu.

---

## Fonctionnalités

- **Fetch automatique** de l'historique du canal Discord (PTU, EPTU, LIVE)
- **Parsing intelligent** des sections : Gameplay, Ships & Vehicles, Weapons & Items, Core Tech, Bugfixes…
- **Rapport par itération** : chaque patch PTU/EPTU documenté séparément
- **Synthèse finale** consolidée de tous les changements de la version
- **4 fichiers générés** par version : Markdown + HTML, en français et en anglais
- **Thème sombre** pour les rapports HTML
- Compatible avec toutes les versions futures (4.9.0, 4.10.0, etc.)

---

## Prérequis

- Python 3.9+
- Un compte membre du serveur Discord `/r/starcitizen`

---

## Installation

```bash
git clone https://github.com/ampynjord/sc-patchnotes.git
cd sc-patchnotes
pip install -r requirements.txt
```

---

## Configuration

Copie le fichier de config et renseigne ton token Discord :

```bash
cp config.json.example config.json
```

Ouvre `config.json` :

```json
{
  "token": "COLLE_TON_TOKEN_ICI",
  "channel_id": "585952222853201941",
  "max_messages": 5000,
  "output_dir": "reports",
  "data_dir": "data"
}
```

### Obtenir son token Discord

1. Ouvre [discord.com](https://discord.com) dans le navigateur
2. `F12` → onglet **Network** → filtre sur `/api/`
3. Navigue dans Discord pour déclencher des requêtes
4. Clique sur n'importe quelle requête `discord.com` → **En-têtes de la requête**
5. Copie la valeur du header `Authorization`

> ⚠️ Ne commite jamais `config.json` — il est dans le `.gitignore`.

---

## Utilisation

### 1. Télécharger les messages (une fois, puis à chaque mise à jour)

```bash
python main.py fetch
```

Les messages sont mis en cache dans `data/messages.json`.

### 2. Voir les versions disponibles

```bash
python main.py list
```

```
Versions disponibles (3) :
  4.7.0  →  EPTU: 4  PTU: 6  LIVE: 1  (11 patches)
  4.8.0  →  EPTU: 2  PTU: 5  LIVE: 1  (8 patches)
  ...
```

### 3. Générer les rapports d'une version

```bash
python main.py generate 4.8.0
```

### 4. Générer tous les rapports d'un coup

```bash
python main.py all
```

---

## Résultat

```
reports/
└── 4.8.0/
    ├── report_fr.md       ← Markdown français
    ├── report_fr.html     ← HTML français (thème sombre)
    ├── report_en.md       ← Markdown anglais
    └── report_en.html     ← HTML anglais (thème sombre)
```

Chaque rapport contient :

| Section | Contenu |
|---|---|
| Table des matières | Liens vers chaque itération + synthèse |
| Historique PTU/EPTU | Chaque patch avec ses sections et détails |
| Synthèse finale | Tous les changements consolidés de la version |

---

## Structure du projet

```
sc-patchnotes/
├── main.py              ← CLI principal
├── config.json          ← Token + paramètres (gitignore)
├── requirements.txt
├── src/
│   ├── fetcher.py       ← Appels Discord REST API
│   ├── parser.py        ← Parsing des messages
│   ├── generator.py     ← Génération MD + HTML
│   └── i18n.py          ← Traductions FR/EN des sections
├── data/                ← Cache brut (gitignore)
└── reports/             ← Rapports générés (gitignore)
```

---

## Workflow recommandé pour une nouvelle version

```bash
# 1. Mettre à jour le cache quand des patches sortent
python main.py fetch

# 2. Vérifier que la version apparaît
python main.py list

# 3. Générer les rapports
python main.py generate 4.9.0
```
