# 🚀 SC Patch Notes — Star Citizen Report Generator

Python CLI tool that fetches the patch notes from the **sc-patch-notes** Discord channel (`/r/starcitizen`) and generates complete, organized reports for each major version of the game.

---

## Features

- **Automatic fetch** of the channel history (PTU, EPTU, LIVE)
- **Smart parsing** of sections: Gameplay, Ships & Vehicles, Weapons & Items, Core Tech, Bugfixes...
- **One report per iteration**: each PTU/EPTU patch documented separately
- **Consolidated final summary** of all changes in the version
- **4 files generated** per version: Markdown + HTML, in French and English
- **Dark theme** for HTML reports
- Compatible with all future versions (4.9.0, 4.10.0, etc.)

---

## Requirements

- Python 3.9+
- An account that is a member of the `/r/starcitizen` Discord server

---

## Installation

```bash
git clone https://github.com/ampynjord/sc-patchnotes.git
cd sc-patchnotes
pip install -r requirements.txt
```

---

## Configuration

Copy the config file and fill in your Discord token:

```bash
cp config.json.example config.json
```

Open `config.json`:

```json
{
  "token": "PASTE_YOUR_TOKEN_HERE",
  "channel_id": "585952222853201941",
  "max_messages": 5000,
  "output_dir": "reports",
  "data_dir": "data"
}
```

### Getting your Discord token

1. Open [discord.com](https://discord.com) in the browser
2. `F12` → **Network** tab → filter on `/api/`
3. Browse Discord to trigger requests
4. Click any `discord.com` request → **Request headers**
5. Copy the value of the `Authorization` header

> ⚠️ Never commit `config.json` — it is in `.gitignore`.

---

## Usage

### 1. Download the messages (once, then on each update)

```bash
python main.py fetch
```

Messages are cached in `data/messages.json`.

### 2. List the available versions

```bash
python main.py list
```

```
Available versions (3):
  4.7.0  →  EPTU: 4  PTU: 6  LIVE: 1  (11 patches)
  4.8.0  →  EPTU: 2  PTU: 5  LIVE: 1  (8 patches)
  ...
```

### 3. Generate the reports of a version

```bash
python main.py generate 4.8.0
```

### 4. Generate all reports at once

```bash
python main.py all
```

---

## Output

```
reports/
└── 4.8.0/
    ├── report_fr.md       ← French Markdown
    ├── report_fr.html     ← French HTML (dark theme)
    ├── report_en.md       ← English Markdown
    └── report_en.html     ← English HTML (dark theme)
```

Each report contains:

| Section | Content |
|---|---|
| Table of contents | Links to each iteration + summary |
| PTU/EPTU history | Each patch with its sections and details |
| Final summary | All consolidated changes of the version |

---

## Project structure

```
sc-patchnotes/
├── main.py              ← Main CLI
├── config.json          ← Token + settings (gitignored)
├── requirements.txt
├── src/
│   ├── fetcher.py       ← Discord REST API calls
│   ├── parser.py        ← Message parsing
│   ├── generator.py     ← MD + HTML generation
│   └── i18n.py          ← FR/EN section translations
├── data/                ← Raw cache (gitignored)
└── reports/             ← Generated reports (gitignored)
```

---

## Recommended workflow for a new version

```bash
# 1. Refresh the cache when patches are released
python main.py fetch

# 2. Check that the version appears
python main.py list

# 3. Generate the reports
python main.py generate 4.9.0
```