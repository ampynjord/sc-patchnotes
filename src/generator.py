import os
import re
from datetime import datetime
from typing import Dict, List

from .parser import PatchNote
from .i18n import LABELS, ENV_COLORS, ENV_BADGES, translate_section


class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir

    # ------------------------------------------------------------------ #
    #  MARKDOWN                                                            #
    # ------------------------------------------------------------------ #

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

        # Table des matières
        lines += [f"## {t['toc']}", ""]
        lines.append(f"- [{t['ptu_history']}](#ptu-eptu-history)")
        for n in notes:
            label = t["patch_label"].format(env=n.environment, num=n.iteration)
            anchor = f"{n.environment.lower()}-{n.iteration}"
            lines.append(f"  - [{label}](#{anchor})")
        lines.append(f"- [{t['synthesis']}](#synthesis)")
        lines.append("")

        # Itérations
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
                f"**{t['environment']}:** `{n.environment}`{audience_info}{build_info} &nbsp;&nbsp; **{t['date']}:** {date_str}",
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

        # Synthèse finale
        lines += [f"## {t['synthesis']} {{#synthesis}}", ""]
        lines.append(f"*{t['all_changes']}*")
        lines.append("")

        # Sections à exclure de la synthèse (métadonnées / testing focus)
        SYNTH_SKIP = {"ai", "general", "patch details", "audience", "testing"}

        consolidated: Dict[str, set] = {}
        for n in notes:
            for sec in n.sections:
                key = translate_section(sec.name, lang)
                if any(s in key.lower() for s in SYNTH_SKIP):
                    continue
                consolidated.setdefault(key, set())
                for item in sec.items:
                    # Dans la synthèse on déduplique les crash fixes
                    if re.match(r'^fixed \d+', item.title, re.I):
                        continue
                    consolidated[key].add(item.title)

        for sec_name, items in sorted(consolidated.items()):
            if not items:
                continue
            lines += [f"### {sec_name}", ""]
            for item in sorted(items):
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  HTML                                                                #
    # ------------------------------------------------------------------ #

    def _html_report(self, notes: List[PatchNote], version: str, lang: str) -> str:
        t = LABELS[lang]
        title = t["report_title"].format(version=version)
        date_gen = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Build iteration sections HTML
        iterations_html = ""
        for n in notes:
            anchor = f"{n.environment.lower()}-{n.iteration}"
            label = t["patch_label"].format(env=n.environment, num=n.iteration)
            date_str = n.date[:10] if n.date else "?"
            color = ENV_COLORS.get(n.environment, "#95a5a6")
            badge = ENV_BADGES.get(n.environment, n.environment)

            sections_html = ""
            for section in n.sections:
                sec_name = translate_section(section.name, lang)
                items_html = ""
                for item in section.items:
                    desc = f"<p class='item-desc'>{item.description}</p>" if item.description else ""
                    items_html += f"""
                    <div class="patch-item">
                        <div class="item-title">→ {item.title}</div>
                        {desc}
                    </div>"""
                sections_html += f"""
                <div class="section">
                    <h4 class="section-title">{sec_name}</h4>
                    {items_html}
                </div>"""

            audience_str = f" <span class='audience-tag'>{n.audience}</span>" if n.audience else ""
            build_str = f"<span class='build-tag'>build {n.build}</span>" if n.build else ""
            iterations_html += f"""
            <div class="patch-block" id="{anchor}">
                <div class="patch-header" style="border-left: 5px solid {color};">
                    <span class="env-badge" style="background:{color};">{badge}</span>
                    <span class="patch-label">{label}{audience_str}</span>
                    {build_str}
                    <span class="patch-date">{date_str}</span>
                    <a href="#toc" class="back-top">{t['back_to_top']}</a>
                </div>
                <div class="patch-content">
                    {sections_html}
                </div>
            </div>"""

        # Synthesis
        SYNTH_SKIP = {"ai", "general", "patch details", "audience", "testing"}
        consolidated: Dict[str, set] = {}
        for n in notes:
            for sec in n.sections:
                key = translate_section(sec.name, lang)
                if any(s in key.lower() for s in SYNTH_SKIP):
                    continue
                consolidated.setdefault(key, set())
                for item in sec.items:
                    if re.match(r'^fixed \d+', item.title, re.I):
                        continue
                    consolidated[key].add(item.title)

        synth_html = ""
        for sec_name, items in consolidated.items():
            items_li = "".join(f"<li>{i}</li>" for i in sorted(items))
            synth_html += f"""
            <div class="section">
                <h4 class="section-title">{sec_name}</h4>
                <ul class="synth-list">{items_li}</ul>
            </div>"""

        # TOC
        toc_items = ""
        for n in notes:
            anchor = f"{n.environment.lower()}-{n.iteration}"
            label = t["patch_label"].format(env=n.environment, num=n.iteration)
            color = ENV_COLORS.get(n.environment, "#95a5a6")
            toc_items += f'<li><a href="#{anchor}" style="color:{color}">{label}</a></li>'

        no_notes_msg = f"<p>{t['no_notes']}</p>" if not notes else ""

        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: #0d1117;
    --bg2: #161b22;
    --bg3: #21262d;
    --border: #30363d;
    --text: #c9d1d9;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --live: #2ecc71;
    --ptu: #3498db;
    --eptu: #e67e22;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  .container {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }}

  /* Header */
  .report-header {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; padding: 2rem; margin-bottom: 2rem; }}
  .report-title {{ font-size: 2rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem; }}
  .report-meta {{ color: var(--text-muted); font-size: 0.9rem; }}
  .version-badge {{ display: inline-block; background: var(--accent); color: #000; font-weight: 700; padding: 0.2rem 0.8rem; border-radius: 20px; font-size: 1.1rem; margin-bottom: 0.5rem; }}

  /* TOC */
  .toc-box {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; }}
  .toc-box h2 {{ font-size: 1.2rem; margin-bottom: 1rem; color: var(--accent); }}
  .toc-box ul {{ list-style: none; padding-left: 0; }}
  .toc-box > ul > li {{ margin-bottom: 0.4rem; font-weight: 600; }}
  .toc-box ul ul {{ padding-left: 1.5rem; margin-top: 0.3rem; }}
  .toc-box ul ul li {{ font-weight: 400; margin-bottom: 0.2rem; font-size: 0.9rem; }}

  /* Patch block */
  .patch-block {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 1.5rem; overflow: hidden; }}
  .patch-header {{ display: flex; align-items: center; gap: 0.7rem; padding: 1rem 1.5rem; background: var(--bg3); flex-wrap: wrap; }}
  .env-badge {{ padding: 0.2rem 0.7rem; border-radius: 20px; font-size: 0.8rem; font-weight: 700; color: #fff; }}
  .patch-label {{ font-size: 1.1rem; font-weight: 600; color: #fff; }}
  .audience-tag {{ font-size: 0.8rem; font-weight: 400; color: var(--text-muted); }}
  .build-tag {{ font-size: 0.75rem; color: var(--text-muted); font-family: monospace; background: var(--bg); padding: 0.1rem 0.4rem; border-radius: 4px; }}
  .patch-date {{ color: var(--text-muted); font-size: 0.9rem; margin-left: auto; }}
  .back-top {{ font-size: 0.8rem; color: var(--text-muted); }}
  .patch-content {{ padding: 1.5rem; }}

  /* Section */
  .section {{ margin-bottom: 1.5rem; }}
  .section-title {{ font-size: 1rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; margin-bottom: 1rem; }}

  /* Item */
  .patch-item {{ margin-bottom: 1rem; padding: 0.8rem 1rem; background: var(--bg); border-radius: 6px; border-left: 3px solid var(--border); }}
  .item-title {{ font-weight: 600; color: #fff; margin-bottom: 0.3rem; }}
  .item-desc {{ color: var(--text-muted); font-size: 0.9rem; line-height: 1.5; }}

  /* Synthesis */
  .synthesis-block {{ background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; }}
  .synth-list {{ list-style: none; padding: 0; }}
  .synth-list li {{ padding: 0.3rem 0; border-bottom: 1px solid var(--border); color: var(--text); font-size: 0.9rem; }}
  .synth-list li::before {{ content: "→ "; color: var(--accent); }}

  h2.section-header {{ font-size: 1.4rem; color: #fff; margin: 2rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--border); }}
</style>
</head>
<body>
<div class="container">

  <div class="report-header">
    <div class="version-badge">v{version}</div>
    <div class="report-title">{title}</div>
    <div class="report-meta">{t['generated_on']}: {date_gen}</div>
  </div>

  {no_notes_msg}

  <div class="toc-box" id="toc">
    <h2>📋 {t['toc']}</h2>
    <ul>
      <li><a href="#ptu-history">📜 {t['ptu_history']}</a>
        <ul>{toc_items}</ul>
      </li>
      <li><a href="#synthesis">🔎 {t['synthesis']}</a></li>
    </ul>
  </div>

  <h2 class="section-header" id="ptu-history">📜 {t['ptu_history']}</h2>
  {iterations_html}

  <h2 class="section-header" id="synthesis">🔎 {t['synthesis']}</h2>
  <p style="color:var(--text-muted);margin-bottom:1rem;font-size:0.9rem;">{t['all_changes']}</p>
  <div class="synthesis-block">
    {synth_html}
  </div>

</div>
</body>
</html>"""

    # ------------------------------------------------------------------ #
    #  ENTRY POINT                                                         #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        notes_by_version: Dict[str, List[PatchNote]],
        version: str,
        env_filter: List[str] = None,
    ):
        version_dir = os.path.join(self.output_dir, version)
        os.makedirs(version_dir, exist_ok=True)

        version_notes = notes_by_version.get(version, [])
        if env_filter:
            version_notes = [n for n in version_notes if n.environment.upper() in env_filter]

        for lang in ("en", "fr"):
            md = self._md_report(version_notes, version, lang)
            md_path = os.path.join(version_dir, f"report_{lang}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"  OK {md_path}")

            html = self._html_report(version_notes, version, lang)
            html_path = os.path.join(version_dir, f"report_{lang}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  OK {html_path}")
