import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from .parser import PatchNote
from .i18n import LABELS, ENV_COLORS, ENV_BADGES, translate_section

_RE_NOISE = re.compile(
    r'^(?:fixed \d+|'
    r'https?://|'
    r'audience:|server info:|long term|'
    r'alpha patch \d|patch should now|'
    r'testing[/ ]feedback|not ready for|'
    r'stability[,\s]|wave \d|all waves|'
    r'server info:|us only|eu only|'
    r'known issues?$|'
    r'▲\s)',
    re.I,
)


def _is_synth_noise(title: str) -> bool:
    return bool(_RE_NOISE.match(title.strip()))


# ── CSS ──────────────────────────────────────────────────────────────────────

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&family=Barlow:wght@300;400;500&display=swap');

/* === DESIGN TOKENS (calqués sur starvis.ampynjord.bzh) === */
:root {
  --void:          #050b14;
  --panel:         #0a1628;
  --panel-2:       #0d1e35;
  --card:          #111f38;
  --card-hover:    #162840;
  --border:        #1a3a5c;
  --border-bright: #2a5f8f;
  --border-gold:   #6a4e10;
  --amber:         #ffb800;
  --amber-bright:  #ffd040;
  --amber-glow:    rgba(255,184,0,.18);
  --amber-dim:     rgba(255,184,0,.07);
  --cyan:          #00d4ff;
  --cyan-bright:   #70e8ff;
  --cyan-mid:      #0099bb;
  --cyan-glow:     rgba(0,212,255,.1);
  --text:          #c8e0ef;
  --text-dim:      #4a7fa5;
  --text-dimmer:   #2a5070;
  --env-live:      #00c758;
  --env-live-bg:   rgba(0,199,88,.09);
  --env-ptu:       #0288d1;
  --env-ptu-bg:    rgba(2,136,209,.09);
  --env-eptu:      #ff8f00;
  --env-eptu-bg:   rgba(255,143,0,.09);
  --env-evocati:   #ab47bc;
  --env-evocati-bg:rgba(171,71,188,.09);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }

body {
  background: var(--void);
  background-image:
    linear-gradient(rgba(0,140,200,.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,140,200,.015) 1px, transparent 1px),
    radial-gradient(ellipse at 20% 0%, rgba(0,40,120,.25) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 100%, rgba(0,25,80,.18) 0%, transparent 50%);
  background-size: 44px 44px, 44px 44px, 100% 100%, 100% 100%;
  color: var(--text);
  font-family: 'Barlow', system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.7;
  min-height: 100vh;
}

a { color: var(--cyan); text-decoration: none; }
a:hover { color: var(--cyan-bright); }

/* ── LAYOUT ─────────────────────────────────────────────────────── */
.sc-wrap { max-width: 1200px; margin: 0 auto; padding: 0 1.5rem 5rem; }

/* ── HERO ───────────────────────────────────────────────────────── */
.sc-hero {
  position: relative;
  padding: 3.5rem 1.5rem 2.5rem;
  max-width: 1200px;
  margin: 0 auto;
}
.sc-hero::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, var(--amber) 30%, var(--cyan) 70%, transparent 100%);
}
.sc-hero::after {
  content: '';
  position: absolute;
  bottom: 0; left: 6%; right: 6%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border-bright), transparent);
}
.sc-hero-eyebrow {
  font-family: 'Rajdhani', sans-serif;
  font-size: .8rem;
  letter-spacing: .5em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: .75rem;
  display: flex;
  align-items: center;
  gap: .5rem;
}
.sc-hero-eyebrow::before { content: '◈'; color: var(--amber); font-size: .7rem; }
.sc-hero-version {
  font-family: 'Orbitron', sans-serif;
  font-size: clamp(3rem, 10vw, 6.5rem);
  font-weight: 900;
  line-height: 1;
  letter-spacing: .02em;
  background: linear-gradient(125deg, var(--amber-bright) 0%, var(--amber) 40%, var(--cyan) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 1rem;
}
.sc-hero-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}
.sc-badge {
  font-family: 'Rajdhani', sans-serif;
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .2em;
  text-transform: uppercase;
  padding: .25rem 1rem;
  border: 1px solid;
  clip-path: polygon(8px 0%, 100% 0%, calc(100% - 8px) 100%, 0% 100%);
}
.sc-badge--committed { color: var(--amber-bright); border-color: var(--amber); background: var(--amber-glow); }
.sc-badge--tentative { color: #90a4ae; border-color: #455a64; background: rgba(69,90,100,.2); }
.sc-badge--released  { color: #b9f6ca; border-color: var(--env-live); background: var(--env-live-bg); }
.sc-hero-quarter, .sc-hero-date {
  font-family: 'Rajdhani', sans-serif;
  font-size: .85rem;
  color: var(--text-dim);
  letter-spacing: .1em;
}
.sc-hero-sep { color: var(--border-bright); }

/* ── NAV ────────────────────────────────────────────────────────── */
.sc-nav {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: .5rem;
  margin-bottom: 2.5rem;
  padding: 1rem 1.25rem;
  background: var(--panel);
  border: 1px solid var(--border);
  border-top: 2px solid var(--amber);
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(8px);
}
.sc-nav-item {
  display: flex;
  align-items: center;
  gap: .6rem;
  padding: .5rem .8rem;
  border: 1px solid transparent;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: .07em;
  transition: all .18s;
}
.sc-nav-item:hover {
  border-color: var(--border-bright);
  background: var(--card);
  color: var(--cyan-bright);
}
.sc-nav-num {
  font-family: 'Share Tech Mono', monospace;
  font-size: .68rem;
  color: var(--amber);
  min-width: 20px;
}
@media (max-width: 600px) { .sc-nav { grid-template-columns: 1fr; } }

/* ── SECTION HEADER ─────────────────────────────────────────────── */
.sc-section { margin-bottom: 3rem; }
.sc-section-hd {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  margin-bottom: 1.75rem;
  padding-bottom: .75rem;
  border-bottom: 1px solid var(--border);
  position: relative;
}
.sc-section-hd::after {
  content: '';
  position: absolute;
  bottom: -1px; left: 0;
  width: 64px; height: 2px;
  background: var(--amber);
}
.sc-section-num {
  font-family: 'Share Tech Mono', monospace;
  font-size: .7rem;
  color: var(--amber);
  min-width: 22px;
}
.sc-section-title {
  font-family: 'Orbitron', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: .08em;
  color: var(--text);
  text-transform: uppercase;
}
.sc-section-sub {
  margin-top: -.9rem;
  margin-bottom: 1.5rem;
  font-size: .88rem;
  color: var(--text-dim);
}

/* ── ROADMAP CARDS ──────────────────────────────────────────────── */
.sc-roadmap-cat { margin-bottom: 2.5rem; }
.sc-roadmap-cat-hd {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin-bottom: 1rem;
  padding: .4rem 0;
  border-bottom: 1px solid var(--border);
}
.sc-cat-icon { color: var(--amber); min-width: 22px; text-align: center; }
.sc-cat-name {
  font-family: 'Rajdhani', sans-serif;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: var(--amber);
}
.sc-cat-count {
  margin-left: auto;
  font-family: 'Share Tech Mono', monospace;
  font-size: .72rem;
  color: var(--text-dim);
}
.sc-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}
.sc-card {
  position: relative;
  background: var(--panel-2);
  border: 1px solid var(--border);
  overflow: hidden;
  transition: border-color .2s, transform .2s, box-shadow .2s;
}
.sc-card:hover {
  border-color: var(--border-gold);
  transform: translateY(-2px);
  box-shadow: 0 6px 28px rgba(0,0,0,.55), 0 0 0 1px var(--border-gold);
}
.sc-card::before, .sc-card::after {
  content: '';
  position: absolute;
  width: 10px; height: 10px;
  border-color: var(--amber-dim);
  border-style: solid;
  z-index: 2;
  transition: border-color .2s;
}
.sc-card::before { top: 0; left: 0;  border-width: 1px 0 0 1px; }
.sc-card::after  { top: 0; right: 0; border-width: 1px 1px 0 0; }
.sc-card:hover::before, .sc-card:hover::after { border-color: var(--amber); }
.sc-card-img {
  position: relative;
  padding-top: 50%;
  overflow: hidden;
  background: var(--panel);
}
.sc-card-img img {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  transition: transform .4s ease;
  display: block;
}
.sc-card:hover .sc-card-img img { transform: scale(1.05); }
.sc-card-img-overlay {
  position: absolute;
  bottom: 0; left: 0; right: 0; height: 50%;
  background: linear-gradient(to top, var(--panel-2), transparent);
  pointer-events: none;
}
.sc-card-body { padding: 1rem 1.1rem 1.1rem; }
.sc-card-name {
  font-family: 'Rajdhani', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: .03em;
  margin-bottom: .45rem;
  line-height: 1.3;
}
.sc-card-desc {
  font-size: .9rem;
  color: var(--text-dim);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.sc-card-foot {
  display: flex;
  align-items: center;
  margin-top: .8rem;
  padding-top: .65rem;
  border-top: 1px solid var(--border);
}
.sc-status {
  font-family: 'Rajdhani', sans-serif;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .18em;
  padding: .18rem .7rem;
  clip-path: polygon(5px 0%, 100% 0%, calc(100% - 5px) 100%, 0% 100%);
}
.sc-status--committed { color: var(--amber-bright); background: var(--amber-glow); }
.sc-status--tentative { color: #78909c; background: rgba(55,71,79,.35); }
.sc-status--released  { color: #b9f6ca; background: var(--env-live-bg); }

/* ── PATCH ACCORDION ────────────────────────────────────────────── */
.sc-patch {
  margin-bottom: .6rem;
  border: 1px solid var(--border);
  background: var(--panel);
  overflow: hidden;
}
.sc-patch-hd {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .9rem 1.25rem;
  cursor: pointer;
  user-select: none;
  border-left: 3px solid;
  transition: background .15s;
  flex-wrap: wrap;
}
.sc-patch-hd:hover { background: var(--card-hover); }
.sc-patch-hd--live    { border-left-color: var(--env-live);    background: var(--env-live-bg); }
.sc-patch-hd--ptu     { border-left-color: var(--env-ptu);     background: var(--env-ptu-bg); }
.sc-patch-hd--eptu    { border-left-color: var(--env-eptu);    background: var(--env-eptu-bg); }
.sc-patch-hd--evocati { border-left-color: var(--env-evocati); background: var(--env-evocati-bg); }
.sc-patch-hd--unknown { border-left-color: #546e7a; }
.sc-env-badge {
  font-family: 'Rajdhani', sans-serif;
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .2em;
  padding: .18rem .7rem;
  clip-path: polygon(5px 0%, 100% 0%, calc(100% - 5px) 100%, 0% 100%);
  white-space: nowrap;
}
.sc-env-badge--live    { color: #b9f6ca; background: rgba(0,199,88,.22); }
.sc-env-badge--ptu     { color: #80d8ff; background: rgba(2,136,209,.22); }
.sc-env-badge--eptu    { color: #ffe082; background: rgba(255,143,0,.22); }
.sc-env-badge--evocati { color: #e1bee7; background: rgba(171,71,188,.22); }
.sc-env-badge--unknown { color: #b0bec5; background: rgba(84,110,122,.22); }
.sc-patch-label {
  font-family: 'Rajdhani', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: .06em;
}
.sc-patch-audience {
  font-family: 'Rajdhani', sans-serif;
  font-size: .85rem;
  color: var(--text-dim);
}
.sc-patch-build {
  font-family: 'Share Tech Mono', monospace;
  font-size: .75rem;
  color: var(--text-dim);
  background: rgba(0,0,0,.3);
  padding: .1rem .5rem;
  border: 1px solid var(--border);
}
.sc-patch-date {
  font-family: 'Rajdhani', sans-serif;
  font-size: .9rem;
  color: var(--text-dim);
  margin-left: auto;
  letter-spacing: .05em;
}
.sc-ltp-badge {
  font-family: 'Share Tech Mono', monospace;
  font-size: .67rem;
  letter-spacing: .05em;
  padding: .14rem .55rem;
  clip-path: polygon(4px 0%, 100% 0%, calc(100% - 4px) 100%, 0% 100%);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 280px;
  cursor: default;
}
.sc-ltp-badge--wipe  { color: #ff6e6e; background: rgba(255,82,82,.13); border: 1px solid rgba(255,100,100,.35); }
.sc-ltp-badge--ok    { color: #b9f6ca; background: rgba(0,200,83,.11); border: 1px solid rgba(0,200,83,.3); }
.sc-ltp-badge--info  { color: var(--amber); background: var(--amber-dim); border: 1px solid var(--border-gold); }
.sc-patch-toggle {
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0 .2rem;
  transition: transform .3s, color .2s;
  flex-shrink: 0;
}
.sc-patch-toggle:hover { color: var(--amber); }
.sc-patch.collapsed .sc-patch-toggle { transform: rotate(-90deg); }
.sc-patch-body {
  padding: 1.4rem 1.5rem;
  border-top: 1px solid var(--border);
}
.sc-patch.collapsed .sc-patch-body { display: none; }

/* ── SECTION DANS UN PATCH ──────────────────────────────────────── */
.sc-sub { margin-bottom: 1.75rem; }
.sc-sub:last-child { margin-bottom: 0; }
.sc-sub-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: .88rem;
  font-weight: 700;
  letter-spacing: .25em;
  text-transform: uppercase;
  color: var(--cyan-mid);
  padding: .3rem 0 .5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: .5rem;
}
.sc-sub-title::before { content: '▸'; color: var(--amber); font-size: .65rem; }

/* Items — colonnes journal pour éviter les cellules vides du grid */
.sc-items-grid {
  columns: 2;
  column-gap: .75rem;
}
@media (max-width: 860px) { .sc-items-grid { columns: 1; } }

.sc-item {
  break-inside: avoid;
  -webkit-column-break-inside: avoid;
  display: block;
  padding: .75rem 1rem;
  margin-bottom: .5rem;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-left: 2px solid var(--border-bright);
  transition: border-left-color .15s, background .15s;
}
.sc-item:hover {
  border-left-color: var(--amber);
  background: var(--card);
}
.sc-item-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: .975rem;
  font-weight: 600;
  color: var(--text);
  line-height: 1.35;
  margin-bottom: .25rem;
}
.sc-item-desc {
  font-size: .875rem;
  color: var(--text-dim);
  line-height: 1.6;
}

/* ── SYNTHÈSE ───────────────────────────────────────────────────── */
.sc-synth-cat { margin-bottom: 1.75rem; }
.sc-synth-cat-title {
  font-family: 'Rajdhani', sans-serif;
  font-size: .85rem;
  font-weight: 700;
  letter-spacing: .22em;
  text-transform: uppercase;
  color: var(--amber);
  padding: .4rem 0;
  margin-bottom: .75rem;
  border-bottom: 1px solid var(--border);
}
.sc-synth-list {
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: .35rem;
}
.sc-synth-list li {
  padding: .35rem .65rem;
  font-size: .9rem;
  color: var(--text);
  border-left: 2px solid var(--border);
  transition: border-color .15s;
  line-height: 1.45;
}
.sc-synth-list li:hover { border-left-color: var(--cyan-mid); }
.sc-synth-list li::before { content: '→ '; color: var(--cyan-mid); }

/* ── EVENT SHIPS ────────────────────────────────────────────────── */
.sc-event-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: .5rem;
  margin-bottom: 1.75rem;
}
.sc-event-ship {
  display: flex;
  align-items: flex-start;
  gap: .75rem;
  padding: .7rem 1rem;
  background: var(--panel-2);
  border: 1px solid var(--border);
  border-left: 2px solid var(--border-bright);
  transition: border-left-color .15s, background .15s;
}
.sc-event-ship:hover { border-left-color: var(--amber); background: var(--card); }
.sc-event-ship-name {
  font-family: 'Rajdhani', sans-serif;
  font-size: .975rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.3;
}
.sc-event-ship-mfr {
  font-size: .8rem;
  color: var(--text-dim);
  margin-top: .1rem;
}
.sc-event-ship-type {
  font-size: .78rem;
  color: var(--text-dimmer);
  margin-top: .05rem;
  font-style: italic;
}
.sc-event-ship-day {
  font-family: 'Share Tech Mono', monospace;
  font-size: .65rem;
  color: var(--text-dim);
  margin-left: auto;
  white-space: nowrap;
  flex-shrink: 0;
  align-self: center;
}
.sc-ship-status {
  font-family: 'Rajdhani', sans-serif;
  font-size: .65rem;
  font-weight: 700;
  letter-spacing: .15em;
  padding: .1rem .4rem;
  clip-path: polygon(3px 0%, 100% 0%, calc(100% - 3px) 100%, 0% 100%);
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: .15rem;
}
.sc-ship-status--flyable { color: #b9f6ca; background: rgba(0,200,83,.18); }
.sc-ship-status--concept  { color: var(--amber); background: var(--amber-dim); }
.sc-ship-status--sale     { color: #80d8ff; background: rgba(2,136,209,.18); }

/* ── MISC ───────────────────────────────────────────────────────── */
.sc-no-content { color: var(--text-dim); font-size: .9rem; }

/* ── RETOUR EN HAUT ─────────────────────────────────────────────── */
.sc-top {
  position: fixed;
  bottom: 2rem; right: 2rem;
  width: 40px; height: 40px;
  background: var(--panel);
  border: 1px solid var(--border-bright);
  color: var(--cyan);
  display: flex; align-items: center; justify-content: center;
  font-size: .95rem;
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
  transition: background .2s, color .2s;
  z-index: 100;
}
.sc-top:hover { background: var(--card-hover); color: var(--cyan-bright); }

@media (max-width: 768px) {
  .sc-hero-version { font-size: 2.8rem; }
  .sc-cards-grid   { grid-template-columns: 1fr; }
  .sc-synth-list   { grid-template-columns: 1fr; }
  .sc-patch-date   { display: none; }
  .sc-items-grid   { columns: 1; }
}
"""

# ── JS ────────────────────────────────────────────────────────────────────────

_JS = """
document.querySelectorAll('.sc-patch-hd').forEach(hd => {
  hd.addEventListener('click', () => {
    hd.closest('.sc-patch').classList.toggle('collapsed');
  });
});
// Collapse all except the most recent patch on load
const patches = document.querySelectorAll('.sc-patch');
patches.forEach((p, i) => { if (i < patches.length - 1) p.classList.add('collapsed'); });
"""


class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir

    @staticmethod
    def _ltp_badge(ltp_text: str) -> str:
        if not ltp_text:
            return ""
        lower = ltp_text.lower()
        if any(w in lower for w in ["complete wipe", "full wipe", "wipe complet", "total wipe", "wipe but"]):
            cls, icon = "wipe", "⚠"
        elif any(w in lower for w in ["enabled", "persist", "no wipe", "intact", "conserv", "blueprints"]):
            cls, icon = "ok", "✓"
        else:
            cls, icon = "info", "◈"
        short = ltp_text[:80] + ("…" if len(ltp_text) > 80 else "")
        full = ltp_text.replace('"', '&quot;')
        return f'<span class="sc-ltp-badge sc-ltp-badge--{cls}" title="{full}">{icon} LTP: {short}</span>'

    # ── ROADMAP SECTION ──────────────────────────────────────────────────────

    def _roadmap_section_html(self, cards: list, lang: str) -> str:
        if not cards:
            return ""

        from .roadmap_fetcher import RoadmapFetcher, CATEGORY_ORDER
        t = LABELS[lang]

        by_cat: Dict[int, list] = defaultdict(list)
        for card in cards:
            by_cat[card.category_id].append(card)

        # Sort categories: use CATEGORY_ORDER first, then any remaining
        ordered_ids = [cid for cid in CATEGORY_ORDER if cid in by_cat]
        ordered_ids += [cid for cid in sorted(by_cat) if cid not in ordered_ids]

        cats_html = ""
        for cat_id in ordered_ids:
            cat_cards = by_cat[cat_id]
            cat_name = RoadmapFetcher.get_category_name(cat_id, lang)
            icon = RoadmapFetcher.get_category_icon(cat_id)
            n = len(cat_cards)
            entries = t.get("entries", "entries")

            cards_html = ""
            for card in cat_cards:
                status_lower = card.status.lower()
                status_labels = {
                    "committed": t.get("committed_label", "COMMITTED"),
                    "tentative": t.get("tentative_label", "TENTATIVE"),
                    "released":  t.get("released_label",  "RELEASED"),
                }
                status_label = status_labels.get(status_lower, card.status.upper())

                img_html = ""
                if card.thumbnail_large:
                    img_html = (
                        f'<div class="sc-card-img">'
                        f'<img src="{card.thumbnail_large}" alt="" loading="lazy">'
                        f'<div class="sc-card-img-overlay"></div>'
                        f'</div>'
                    )

                cards_html += f"""
                  <div class="sc-card">
                    {img_html}
                    <div class="sc-card-body">
                      <h4 class="sc-card-name">{card.name}</h4>
                      <p class="sc-card-desc">{card.description}</p>
                      <div class="sc-card-foot">
                        <span class="sc-status sc-status--{status_lower}">{status_label}</span>
                      </div>
                    </div>
                  </div>"""

            cats_html += f"""
              <div class="sc-roadmap-cat">
                <div class="sc-roadmap-cat-hd">
                  <span class="sc-cat-icon">{icon}</span>
                  <span class="sc-cat-name">{cat_name}</span>
                  <span class="sc-cat-count">{n} {entries}</span>
                </div>
                <div class="sc-cards-grid">{cards_html}</div>
              </div>"""

        return f"""
          <section class="sc-section" id="roadmap">
            <div class="sc-section-hd">
              <span class="sc-section-num">01</span>
              <h2 class="sc-section-title">{t.get('roadmap_overview','ROADMAP OVERVIEW')}</h2>
            </div>
            <p class="sc-section-sub">{t.get('roadmap_desc','Committed features for this release')}</p>
            {cats_html}
          </section>"""

    # ── EVENT SHIPS SECTION ───────────────────────────────────────────────────

    def _event_section_html(self, event_data_list: list, section_num: str, lang: str) -> str:
        if not event_data_list:
            return ""

        title_en = "Event Ships"
        title_fr = "Vaisseaux Événement"
        title = title_fr if lang == "fr" else title_en
        sub_en = "Ships added or revealed during in-game events — may not appear on the official roadmap"
        sub_fr = "Vaisseaux ajoutés ou révélés lors des événements en jeu — peuvent ne pas figurer sur la roadmap officielle"
        sub = sub_fr if lang == "fr" else sub_en

        STATUS_LABELS = {
            "flyable": {"en": "FLYABLE",  "fr": "JOUABLE"},
            "concept":  {"en": "CONCEPT",  "fr": "CONCEPT"},
            "sale":     {"en": "SALE",     "fr": "VENTE"},
        }

        events_html = ""
        for ev in event_data_list:
            if not ev.ships:
                continue
            ships_html = ""
            for ship in ev.ships:
                status_key = ship.status.lower() if ship.status else ""
                status_label = (STATUS_LABELS.get(status_key, {}).get(lang, ship.status.upper())
                                if status_key else "")
                status_html = (
                    f'<span class="sc-ship-status sc-ship-status--{status_key}">{status_label}</span>'
                    if status_label else ""
                )
                mfr_html = f'<div class="sc-event-ship-mfr">{ship.manufacturer}</div>' if ship.manufacturer else ""
                type_html = f'<div class="sc-event-ship-type">{ship.type}</div>' if ship.type else ""
                day_html = f'<span class="sc-event-ship-day">{ship.day}</span>' if ship.day else ""
                ships_html += f"""
                  <div class="sc-event-ship">
                    {status_html}
                    <div>
                      <div class="sc-event-ship-name">{ship.name}</div>
                      {mfr_html}
                      {type_html}
                    </div>
                    {day_html}
                  </div>"""

            events_html += f"""
              <div style="margin-bottom:1.5rem">
                <div class="sc-synth-cat-title">{ev.title}</div>
                <div class="sc-event-grid">{ships_html}</div>
              </div>"""

        if not events_html:
            return ""

        return f"""
          <section class="sc-section" id="event-ships">
            <div class="sc-section-hd">
              <span class="sc-section-num">{section_num}</span>
              <h2 class="sc-section-title">{title}</h2>
            </div>
            <p class="sc-section-sub">{sub}</p>
            {events_html}
          </section>"""

    # ── MARKDOWN ─────────────────────────────────────────────────────────────

    def _md_report(self, notes: List[PatchNote], version: str, lang: str) -> str:
        t = LABELS[lang]
        lines = []

        lines += [
            f"# {t['report_title'].format(version=version)}",
            "",
            f"*{t['generated_on']}: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]

        if not notes:
            lines.append(t["no_notes"])
            return "\n".join(lines)

        lines += [f"## {t['toc']}", ""]
        lines.append(f"- [{t['ptu_history']}](#ptu-eptu-history)")
        for n in notes:
            label = t["patch_label"].format(env=n.environment, num=n.iteration)
            anchor = f"{n.environment.lower()}-{n.iteration}"
            lines.append(f"  - [{label}](#{anchor})")
        lines.append(f"- [{t['synthesis']}](#synthesis)")
        lines.append("")

        lines += [f"## {t['ptu_history']}", ""]

        for n in notes:
            anchor = f"{n.environment.lower()}-{n.iteration}"
            label = t["patch_label"].format(env=n.environment, num=n.iteration)
            date_str = n.date[:10] if n.date else "?"

            build_info = f" — build `{n.build}`" if n.build else ""
            audience_info = f" ({n.audience})" if n.audience else ""
            lines += [
                f"### {label}{audience_info} — {date_str} {{#{anchor}}}",
                "",
                f"**{t['environment']}:** `{n.environment}`{audience_info}{build_info}"
                f" &nbsp;&nbsp; **{t['date']}:** {date_str}",
                "",
            ]

            for section in n.sections:
                sec_name = translate_section(section.name, lang)
                lines += [f"#### {sec_name}", ""]
                for item in section.items:
                    lines.append(f"**→ {item.title}**")
                    if item.description:
                        lines.append(f"  {item.description}")
                    lines.append("")

            lines += ["---", ""]

        lines += [f"## {t['synthesis']} {{#synthesis}}", ""]
        lines.append(f"*{t['all_changes']}*")
        lines.append("")

        SYNTH_SKIP = {
            "ai", "general", "patch details", "audience", "testing",
            "star citizen alpha patch", "alpha patch",
            "known issues", "not ready", "stability",
        }

        consolidated: Dict[str, set] = {}
        for n in notes:
            for sec in n.sections:
                key = translate_section(sec.name, lang)
                if any(s in key.lower() for s in SYNTH_SKIP):
                    continue
                consolidated.setdefault(key, set())
                for item in sec.items:
                    ti = item.title
                    if _is_synth_noise(ti):
                        continue
                    consolidated[key].add(ti)

        for sec_name, items in sorted(consolidated.items()):
            if not items:
                continue
            lines += [f"### {sec_name}", ""]
            for item in sorted(items):
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    # ── HTML ──────────────────────────────────────────────────────────────────

    def _html_report(
        self,
        notes: List[PatchNote],
        version: str,
        lang: str,
        roadmap_cards: Optional[list] = None,
        release_meta: Optional[dict] = None,
        event_data_list: Optional[list] = None,
    ) -> str:
        t = LABELS[lang]
        title = t["report_title"].format(version=version)
        date_gen = datetime.now().strftime("%Y-%m-%d %H:%M")

        # ── Roadmap status badge ──────────────────────────────────────────────
        rm_status = (release_meta or {}).get("status", "")
        rm_quarter = (release_meta or {}).get("description", "")
        status_cls = rm_status.lower() if rm_status else "committed"
        hero_badge = (
            f'<span class="sc-badge sc-badge--{status_cls}">{rm_status.upper()}</span>'
            if rm_status else ""
        )
        hero_quarter = (
            f'<span class="sc-hero-sep">|</span><span class="sc-hero-quarter">{rm_quarter}</span>'
            if rm_quarter else ""
        )

        # ── Nav / TOC — sections numbered in display order ────────────────────
        sec = 0
        def _sn():
            nonlocal sec; sec += 1; return f"{sec:02d}"

        roadmap_sn    = _sn() if roadmap_cards    else ""
        event_sn      = _sn() if event_data_list  else ""
        patch_num     = _sn()
        synth_num     = _sn()

        ev_lbl = "Vaisseaux Événement" if lang == "fr" else "Event Ships"
        roadmap_nav = (
            f'<a href="#roadmap" class="sc-nav-item">'
            f'<span class="sc-nav-num">{roadmap_sn}</span>{t.get("nav_roadmap","Roadmap")}</a>'
        ) if roadmap_sn else ""
        event_nav = (
            f'<a href="#event-ships" class="sc-nav-item">'
            f'<span class="sc-nav-num">{event_sn}</span>{ev_lbl}</a>'
        ) if event_sn else ""

        nav_html = f"""
          <nav class="sc-nav" id="top">
            {roadmap_nav}
            {event_nav}
            <a href="#patches" class="sc-nav-item">
              <span class="sc-nav-num">{patch_num}</span>{t.get('nav_patches','Patch History')}</a>
            <a href="#synthesis" class="sc-nav-item">
              <span class="sc-nav-num">{synth_num}</span>{t.get('nav_synthesis','Synthesis')}</a>
          </nav>"""

        # ── Roadmap section ───────────────────────────────────────────────────
        roadmap_html = self._roadmap_section_html(roadmap_cards or [], lang)
        # ── Event ships section ───────────────────────────────────────────────
        event_html = self._event_section_html(event_data_list or [], event_sn or "01", lang)

        # ── Patch iterations ──────────────────────────────────────────────────
        SYNTH_SKIP = {
            "ai", "general", "patch details", "audience", "testing",
            "star citizen alpha patch", "alpha patch",
            "known issues", "not ready", "stability",
        }

        iterations_html = ""
        for i, n in enumerate(notes):
            anchor = f"{n.environment.lower()}-{n.iteration}"
            label = t["patch_label"].format(env=n.environment, num=n.iteration)
            date_str = n.date[:10] if n.date else "?"
            env_lower = n.environment.lower()

            build_html = (
                f'<span class="sc-patch-build">{n.build}</span>' if n.build else ""
            )
            audience_html = (
                f'<span class="sc-patch-audience">{n.audience}</span>' if n.audience else ""
            )
            ltp_html = self._ltp_badge(getattr(n, "ltp_status", ""))

            sections_html = ""
            for section in n.sections:
                sec_name = translate_section(section.name, lang)
                items_html = ""
                for item in section.items:
                    desc = (
                        f'<p class="sc-item-desc">{item.description}</p>'
                        if item.description else ""
                    )
                    items_html += f"""
                      <div class="sc-item">
                        <div class="sc-item-title">{item.title}</div>
                        {desc}
                      </div>"""
                sections_html += f"""
                  <div class="sc-sub">
                    <div class="sc-sub-title">{sec_name}</div>
                    <div class="sc-items-grid">{items_html}</div>
                  </div>"""

            collapsed_cls = "collapsed" if i < len(notes) - 1 else ""
            iterations_html += f"""
              <div class="sc-patch {collapsed_cls}" id="{anchor}">
                <div class="sc-patch-hd sc-patch-hd--{env_lower}">
                  <span class="sc-env-badge sc-env-badge--{env_lower}">{n.environment}</span>
                  <span class="sc-patch-label">{label}</span>
                  {audience_html}
                  {build_html}
                  {ltp_html}
                  <span class="sc-patch-date">{date_str}</span>
                  <button class="sc-patch-toggle">▾</button>
                </div>
                <div class="sc-patch-body">
                  {sections_html or '<p class="sc-no-content">—</p>'}
                </div>
              </div>"""

        # ── Synthesis ─────────────────────────────────────────────────────────
        consolidated: Dict[str, set] = {}
        for n in notes:
            for sec in n.sections:
                key = translate_section(sec.name, lang)
                if any(s in key.lower() for s in SYNTH_SKIP):
                    continue
                consolidated.setdefault(key, set())
                for item in sec.items:
                    if _is_synth_noise(item.title):
                        continue
                    consolidated[key].add(item.title)

        synth_html = ""
        for sec_name, items in sorted(consolidated.items()):
            if not items:
                continue
            items_li = "".join(f"<li>{i}</li>" for i in sorted(items))
            synth_html += f"""
              <div class="sc-synth-cat">
                <div class="sc-synth-cat-title">{sec_name}</div>
                <ul class="sc-synth-list">{items_li}</ul>
              </div>"""

        no_notes_msg = f'<p class="sc-no-content">{t["no_notes"]}</p>' if not notes else ""

        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>

  <header class="sc-hero">
    <p class="sc-hero-eyebrow">STAR CITIZEN — PATCH NOTES</p>
    <h1 class="sc-hero-version">ALPHA {version}</h1>
    <div class="sc-hero-meta">
      {hero_badge}
      {hero_quarter}
      <span class="sc-hero-sep">|</span>
      <span class="sc-hero-date">{t['generated_on']}: {date_gen}</span>
    </div>
  </header>

  <div class="sc-wrap">
    {nav_html}

    {roadmap_html}

    {event_html}

    <section class="sc-section" id="patches">
      <div class="sc-section-hd">
        <span class="sc-section-num">{patch_num}</span>
        <h2 class="sc-section-title">{t.get('patch_history','PATCH HISTORY')}</h2>
      </div>
      {no_notes_msg}
      {iterations_html}
    </section>

    <section class="sc-section" id="synthesis">
      <div class="sc-section-hd">
        <span class="sc-section-num">{synth_num}</span>
        <h2 class="sc-section-title">{t.get('synthesis','FINAL SYNTHESIS')}</h2>
      </div>
      <p class="sc-section-sub">{t['all_changes']}</p>
      {synth_html}
    </section>
  </div>

  <a href="#top" class="sc-top">▲</a>

<script>{_JS}</script>
</body>
</html>"""

    # ── LIVE PREVIEW ─────────────────────────────────────────────────────────

    def _html_live_report(
        self,
        note: PatchNote,
        version: str,
        lang: str,
        roadmap_cards: Optional[list] = None,
        release_meta: Optional[dict] = None,
        event_data_list: Optional[list] = None,
    ) -> str:
        t = LABELS[lang]
        title = t["report_title"].format(version=version) + " — LIVE"
        date_gen = datetime.now().strftime("%Y-%m-%d %H:%M")

        rm_quarter = (release_meta or {}).get("description", "")
        hero_quarter = (
            f'<span class="sc-hero-sep">|</span><span class="sc-hero-quarter">{rm_quarter}</span>'
            if rm_quarter else ""
        )

        # Build / audience / LTP meta line in hero
        meta_chips = []
        if note.build:
            meta_chips.append(f'<span class="sc-patch-build">{note.build}</span>')
        if note.audience:
            meta_chips.append(f'<span class="sc-patch-audience">{note.audience}</span>')
        ltp_chip = self._ltp_badge(getattr(note, "ltp_status", ""))
        if ltp_chip:
            meta_chips.append(ltp_chip)
        meta_chips_html = " ".join(meta_chips)

        roadmap_html = self._roadmap_section_html(roadmap_cards or [], lang)

        _ls = 0
        def _lsn():
            nonlocal _ls; _ls += 1; return f"{_ls:02d}"

        rm_sn   = _lsn() if roadmap_cards   else ""
        ev_sn   = _lsn() if event_data_list else ""
        notes_num = _lsn()

        ev_lbl = "Vaisseaux Événement" if lang == "fr" else "Event Ships"
        roadmap_nav = (
            f'<a href="#roadmap" class="sc-nav-item">'
            f'<span class="sc-nav-num">{rm_sn}</span>{t.get("nav_roadmap","Roadmap")}</a>'
        ) if rm_sn else ""
        event_nav = (
            f'<a href="#event-ships" class="sc-nav-item">'
            f'<span class="sc-nav-num">{ev_sn}</span>{ev_lbl}</a>'
        ) if ev_sn else ""

        nav_html = f"""
          <nav class="sc-nav" id="top">
            {roadmap_nav}
            {event_nav}
            <a href="#changes" class="sc-nav-item">
              <span class="sc-nav-num">{notes_num}</span>{t.get('nav_patches','Patch Notes')}</a>
          </nav>"""

        roadmap_html = self._roadmap_section_html(roadmap_cards or [], lang)
        event_html   = self._event_section_html(event_data_list or [], ev_sn or "01", lang)

        SYNTH_SKIP = {
            "ai", "general", "patch details", "audience", "testing",
            "star citizen alpha patch", "alpha patch",
            "known issues", "not ready", "stability",
        }

        sections_html = ""
        for section in note.sections:
            sec_name = translate_section(section.name, lang)
            if any(s in sec_name.lower() for s in SYNTH_SKIP):
                continue
            items_html = ""
            for item in section.items:
                if _is_synth_noise(item.title):
                    continue
                desc = (
                    f'<p class="sc-item-desc">{item.description}</p>'
                    if item.description else ""
                )
                items_html += f"""
                  <div class="sc-item">
                    <div class="sc-item-title">{item.title}</div>
                    {desc}
                  </div>"""
            if items_html:
                sections_html += f"""
                  <div class="sc-sub">
                    <div class="sc-sub-title">{sec_name}</div>
                    <div class="sc-items-grid">{items_html}</div>
                  </div>"""

        no_content = f'<p class="sc-no-content">{t["no_notes"]}</p>' if not sections_html else ""

        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>

  <header class="sc-hero">
    <p class="sc-hero-eyebrow">STAR CITIZEN — LIVE RELEASE NOTES</p>
    <h1 class="sc-hero-version">ALPHA {version}</h1>
    <div class="sc-hero-meta">
      <span class="sc-badge sc-badge--released">{t.get('released_label','RELEASED')}</span>
      {hero_quarter}
      <span class="sc-hero-sep">|</span>
      {meta_chips_html}
      <span class="sc-hero-sep">|</span>
      <span class="sc-hero-date">{t['generated_on']}: {date_gen}</span>
    </div>
  </header>

  <div class="sc-wrap">
    {nav_html}

    {roadmap_html}

    {event_html}

    <section class="sc-section" id="changes">
      <div class="sc-section-hd">
        <span class="sc-section-num">{notes_num}</span>
        <h2 class="sc-section-title">{t.get('patch_history','PATCH NOTES')}</h2>
      </div>
      {no_content}
      {sections_html}
    </section>
  </div>

  <a href="#top" class="sc-top">▲</a>

</body>
</html>"""

    # ── ENTRY POINT ──────────────────────────────────────────────────────────

    def generate(
        self,
        notes_by_version: Dict[str, List[PatchNote]],
        version: str,
        env_filter: List[str] = None,
        roadmap_cards: Optional[list] = None,
        release_meta: Optional[dict] = None,
        event_data_list: Optional[list] = None,
    ):
        version_dir = os.path.join(self.output_dir, version)
        os.makedirs(version_dir, exist_ok=True)

        version_notes = notes_by_version.get(version, [])
        if env_filter:
            version_notes = [n for n in version_notes if n.environment.upper() in env_filter]

        env_suffix = ("-" + "-".join(sorted(env_filter))) if env_filter else ""
        base = f"report_{version}{env_suffix}"

        for lang in ("en", "fr"):
            md = self._md_report(version_notes, version, lang)
            md_path = os.path.join(version_dir, f"{base}_{lang}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"  OK {md_path}")

            html = self._html_report(
                version_notes, version, lang,
                roadmap_cards=roadmap_cards,
                release_meta=release_meta,
                event_data_list=event_data_list,
            )
            html_path = os.path.join(version_dir, f"{base}_{lang}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  OK {html_path}")

    def generate_live_preview(
        self,
        notes_by_version: Dict[str, List[PatchNote]],
        version: str,
        env_filter: List[str] = None,
        roadmap_cards: Optional[list] = None,
        release_meta: Optional[dict] = None,
        event_data_list: Optional[list] = None,
    ):
        """Generate a clean LIVE-release-style report from the most recent PTU note."""
        version_dir = os.path.join(self.output_dir, version)
        os.makedirs(version_dir, exist_ok=True)

        version_notes = notes_by_version.get(version, [])
        if env_filter:
            version_notes = [n for n in version_notes if n.environment.upper() in env_filter]

        if not version_notes:
            print(f"[ERREUR] Aucune note trouvée pour {version}.")
            return

        # Pick the most recent note by date
        latest = max(version_notes, key=lambda n: n.date)
        print(f"  Live preview basée sur : [{latest.environment} #{latest.iteration}] {latest.date[:10]}")

        for lang in ("en", "fr"):
            html = self._html_live_report(
                latest, version, lang,
                roadmap_cards=roadmap_cards,
                release_meta=release_meta,
                event_data_list=event_data_list,
            )
            html_path = os.path.join(version_dir, f"live_preview_{version}_{lang}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  OK {html_path}")
