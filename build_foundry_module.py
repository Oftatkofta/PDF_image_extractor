"""
Build the Foundry VTT module: copy sweetness images, generate scene-list.json (scene name = filename, underscores removed),
and parse actors.txt into sweetness-npcs.json.
"""
from pathlib import Path
import json
import re
import shutil
import zipfile

try:
    from PIL import Image
except ImportError:
    Image = None

PROJECT_ROOT = Path(__file__).resolve().parent
SWEETNESS_DIR = PROJECT_ROOT / "sweetness"
MODULE_DIR = PROJECT_ROOT / "foundry-module" / "delta-green-sweetness"
ASSETS_DIR = MODULE_DIR / "assets"
MODULE_ID = "delta-green-sweetness"

ACTORS_FILES = ("actors.txt",)

# Maps text skill names (lowercase) to Delta Green FoundryVTT system keys
SKILL_NAME_MAP = {
    "accounting": "accounting",
    "alertness": "alertness",
    "anthropology": "anthropology",
    "archeology": "archeology",
    "artillery": "artillery",
    "athletics": "athletics",
    "bureaucracy": "bureaucracy",
    "computer science": "computer_science",
    "criminology": "criminology",
    "demolitions": "demolitions",
    "disguise": "disguise",
    "dodge": "dodge",
    "drive": "drive",
    "driving": "drive",
    "firearms": "firearms",
    "first aid": "first_aid",
    "forensics": "forensics",
    "heavy machinery": "heavy_machiner",
    "heavy weapons": "heavy_weapons",
    "history": "history",
    "humint": "humint",
    "law": "law",
    "medicine": "medicine",
    "melee weapons": "melee_weapons",
    "navigate": "navigate",
    "occult": "occult",
    "persuade": "persuade",
    "pharmacy": "pharmacy",
    "psychotherapy": "psychotherapy",
    "ride": "ride",
    "search": "search",
    "sigint": "sigint",
    "stealth": "stealth",
    "surgery": "surgery",
    "survival": "survival",
    "swim": "swim",
    "unarmed combat": "unarmed_combat",
    "unnatural": "unnatural",
}

SKILL_LABELS = {
    "computer_science": "Computer Science",
    "first_aid": "First Aid",
    "heavy_machiner": "Heavy Machinery",
    "heavy_weapons": "Heavy Weapons",
    "humint": "HUMINT",
    "melee_weapons": "Melee Weapons",
    "sigint": "SIGINT",
    "unarmed_combat": "Unarmed Combat",
}


def _collapse_newlines(s: str) -> str:
    return " ".join(s.split())


def _parse_skills(skills_text: str) -> tuple[dict, list[str]]:
    """Parse 'Skill Name XX%, ...' into ({system_key: proficiency}, [unrecognised entries])."""
    known, unknown = {}, []
    for m in re.finditer(r"([A-Za-z][A-Za-z\s]*?)\s+(\d+)%", skills_text):
        name = m.group(1).strip().lower()
        val = int(m.group(2))
        key = SKILL_NAME_MAP.get(name)
        if key:
            known[key] = val
        else:
            unknown.append(f"{m.group(1).strip()} {val}%")
    return known, unknown


def parse_actors_file(path: Path) -> list[dict]:
    """Parse actors.txt into NPC dicts matching the Delta Green FoundryVTT system schema."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"\n\s*\n", text)
    npcs = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if len(lines) < 3:
            continue
        name = lines[0]
        stat_line_1 = lines[1]
        stat_line_2 = lines[2]
        rest = "\n".join(lines[3:])

        # Parse stats: "STR 12 CON 7 ..." and "HP 10 WP 9 SAN 0"
        attrs = {}
        for m in re.finditer(r"(STR|CON|DEX|INT|POW|CHA)\s+(\d+)", stat_line_1, re.I):
            attrs[m.group(1).lower()] = int(m.group(2))
        for m in re.finditer(r"(HP|WP|SAN)\s+(\d+)", stat_line_2, re.I):
            attrs[m.group(1).lower()] = int(m.group(2))

        # Split rest into ALL-CAPS labelled sections
        section_pattern = re.compile(r"^([A-Z][A-Z0-9 ]+):\s*", re.MULTILINE)
        sections = []
        for m in section_pattern.finditer(rest):
            sections.append((m.group(1).strip(), m.end(), m.start()))

        skills_data, notes_parts = {}, []
        for i, (label, content_start, _) in enumerate(sections):
            end = sections[i + 1][2] if i + 1 < len(sections) else len(rest)
            chunk = rest[content_start:end].strip()
            if not chunk:
                continue
            flat = _collapse_newlines(chunk)
            if label == "SKILLS":
                known, unknown = _parse_skills(flat)
                skills_data.update(known)
                if unknown:
                    notes_parts.append(f"SKILLS (non-standard): {', '.join(unknown)}")
            else:
                notes_parts.append(f"{label}: {flat}")

        # Build system object matching Delta Green FoundryVTT schema
        hp = attrs.get("hp", 10)
        wp_val = attrs.get("wp", 10)
        san_val = attrs.get("san", 100)
        statistics = {
            stat: {"value": attrs[stat], "distinguishing_feature": ""}
            for stat in ("str", "con", "dex", "int", "pow", "cha")
            if stat in attrs
        }
        skills = {
            key: {
                "proficiency": val,
                "label": SKILL_LABELS.get(key, key.replace("_", " ").title()),
                "failure": False,
            }
            for key, val in skills_data.items()
        }

        npcs.append({
            "name": name,
            "type": "npc",
            "img": "",
            "system": {
                "statistics": statistics,
                "health": {"min": 0, "value": hp, "max": hp},
                "wp": {"min": 0, "value": wp_val, "max": wp_val},
                "sanity": {"value": san_val, "currentBreakingPoint": san_val + 1},
                "skills": skills,
                "notes": "\n\n".join(notes_parts),
                "shortDescription": "",
            },
        })
    return npcs


def write_module_structure():
    """Create module.json, scripts/init.js, templates, and pack dirs so the build produces a complete module."""
    MODULE_DIR.mkdir(parents=True, exist_ok=True)
    (MODULE_DIR / "scripts").mkdir(parents=True, exist_ok=True)
    (MODULE_DIR / "templates").mkdir(parents=True, exist_ok=True)
    (MODULE_DIR / "packs" / "sweetness-scenes").mkdir(parents=True, exist_ok=True)
    (MODULE_DIR / "packs" / "sweetness-npcs").mkdir(parents=True, exist_ok=True)

    module_json = {
        "id": MODULE_ID,
        "title": "Delta Green: Sweetness",
        "description": "Scene pack for the Sweetness scenario (Black Sites). No grid, no fog, no token vision.",
        "version": "1.0.0",
        "compatibility": {"minimum": "13", "verified": "13"},
        "authors": [{"name": "Delta Green Sweetness"}],
        "scripts": ["scripts/init.js"],
        "packs": [
            {"name": "sweetness-scenes", "label": "Sweetness Scenes", "path": "packs/sweetness-scenes", "type": "Scene"},
            {"name": "sweetness-npcs", "label": "Sweetness NPCs", "path": "packs/sweetness-npcs", "type": "Actor", "system": "deltagreen"},
        ],
        "manifest": "https://raw.githubusercontent.com/Oftatkofta/PDF_image_extractor/master/foundry-module/delta-green-sweetness/module.json",
        "download": "https://github.com/Oftatkofta/PDF_image_extractor/releases/latest/download/delta-green-sweetness-forge.zip",
    }
    (MODULE_DIR / "module.json").write_text(json.dumps(module_json, indent=2), encoding="utf-8")
    print(f"[+] Wrote {(MODULE_DIR / 'module.json').relative_to(PROJECT_ROOT)}")

    init_js = MODULE_DIR / "scripts" / "init.js"
    init_content = r'''/* global game, Hooks, Dialog, fetch */

const MODULE_ID = "delta-green-sweetness";
const SCENES_PACK = "delta-green-sweetness.sweetness-scenes";
const NPCS_PACK = "delta-green-sweetness.sweetness-npcs";
const GRIDLESS = 0;

// EMBEDDED_DATA - build_foundry_module.py replaces this block with scene/NPC data so Populate works when JSON is skipped
window.DELTA_GREEN_SWEETNESS_SCENE_LIST = [];
window.DELTA_GREEN_SWEETNESS_NPC_LIST = [];
// END_EMBEDDED_DATA

function getSceneList() {
  if (Array.isArray(window.DELTA_GREEN_SWEETNESS_SCENE_LIST) && window.DELTA_GREEN_SWEETNESS_SCENE_LIST.length > 0) {
    return window.DELTA_GREEN_SWEETNESS_SCENE_LIST;
  }
  return null;
}

function getNpcList() {
  if (Array.isArray(window.DELTA_GREEN_SWEETNESS_NPC_LIST) && window.DELTA_GREEN_SWEETNESS_NPC_LIST.length > 0) {
    return window.DELTA_GREEN_SWEETNESS_NPC_LIST;
  }
  return null;
}

async function populateSweetnessScenes() {
  const pack = game.packs.get(SCENES_PACK);
  if (!pack) {
    ui.notifications.warn("Sweetness Scenes compendium not found.");
    return;
  }
  if (pack.locked) {
    ui.notifications.warn("Unlock the Sweetness Scenes compendium first (right-click → Toggle Edit Lock).");
    return;
  }
  let scenes = getSceneList();
  if (!scenes) {
    try {
      const res = await fetch("modules/delta-green-sweetness/scene-list.json");
      scenes = await res.json();
    } catch (e) {
      ui.notifications.error("Could not load scene list. Re-run build_foundry_module.py and ensure data is embedded.");
      return;
    }
  }
  const existing = await pack.getDocuments();
  if (existing.length > 0) {
    ui.notifications.warn("Sweetness Scenes compendium is not empty. Clear it first if you want to re-populate.");
    return;
  }
  for (const s of scenes) {
    await pack.documentClass.create({
      name: s.name,
      background: { src: s.img },
      width: s.width,
      height: s.height,
      grid: { type: GRIDLESS },
      fog: { exploration: false },
      tokenVision: false
    }, { pack: pack.collection });
  }
  ui.notifications.info(`Created ${scenes.length} scene(s) in Sweetness Scenes.`);
}

async function populateSweetnessNPCs() {
  const pack = game.packs.get(NPCS_PACK);
  if (!pack) {
    ui.notifications.warn("Sweetness NPCs compendium not found.");
    return;
  }
  if (pack.locked) {
    ui.notifications.warn("Unlock the Sweetness NPCs compendium first (right-click → Toggle Edit Lock).");
    return;
  }
  let npcs = getNpcList();
  if (!npcs) {
    try {
      const res = await fetch("modules/delta-green-sweetness/sweetness-npcs.json");
      npcs = await res.json();
    } catch (e) {
      ui.notifications.error("Could not load NPC list. Re-run build_foundry_module.py and ensure data is embedded.");
      return;
    }
  }
  const existing = await pack.getDocuments();
  if (existing.length > 0) {
    ui.notifications.warn("Sweetness NPCs compendium is not empty. Clear it first if you want to re-populate.");
    return;
  }
  for (const n of npcs) {
    await pack.documentClass.create({
      name: n.name,
      type: n.type || "npc",
      img: n.img || "",
      system: n.system || {}
    }, { pack: pack.collection });
  }
  ui.notifications.info(`Created ${npcs.length} NPC(s) in Sweetness NPCs.`);
}

Hooks.once("init", () => {
  game.settings.registerMenu(MODULE_ID, "populateScenes", {
    name: "Populate Sweetness Scenes",
    label: "Populate Sweetness Scenes",
    icon: "fas fa-scroll",
    type: PopulateSweetnessDialog
  });
  game.settings.registerMenu(MODULE_ID, "populateNpcs", {
    name: "Populate Sweetness NPCs",
    label: "Populate Sweetness NPCs",
    icon: "fas fa-users",
    type: PopulateNpcsMenuDialog
  });
});

class PopulateSweetnessDialog extends FormApplication {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      template: "modules/delta-green-sweetness/templates/populate.html",
      title: "Populate Sweetness Scenes",
      width: 400,
      height: "auto"
    });
  }

  activateListeners(html) {
    super.activateListeners(html);
    html.find(".populate-sweetness-trigger").on("click", () => {
      populateSweetnessScenes();
      this.close();
    });
  }
}

class PopulateNpcsMenuDialog extends FormApplication {
  static get defaultOptions() {
    return foundry.utils.mergeObject(super.defaultOptions, {
      template: "modules/delta-green-sweetness/templates/populate-npcs.html",
      title: "Populate Sweetness NPCs",
      width: 400,
      height: "auto"
    });
  }

  activateListeners(html) {
    super.activateListeners(html);
    html.find(".populate-npcs-trigger").on("click", () => {
      populateSweetnessNPCs();
      this.close();
    });
  }
}

Hooks.once("ready", () => {
  window.populateSweetnessScenes = populateSweetnessScenes;
  window.populateSweetnessNPCs = populateSweetnessNPCs;
});
'''
    init_js.write_text(init_content, encoding="utf-8")
    print(f"[+] Wrote {init_js.relative_to(PROJECT_ROOT)}")

    (MODULE_DIR / "templates" / "populate.html").write_text(
        '<div class="sweetness-populate">\n'
        '  <p>Create scene entries in the <b>Sweetness Scenes</b> compendium.</p>\n'
        '  <p>Settings: <b>no grid</b>, <b>no fog</b>, <b>no token vision</b>.</p>\n'
        '  <p class="notes">Unlock the compendium first (right-click → Toggle Edit Lock).</p>\n'
        '  <button type="button" class="populate-sweetness-trigger"><i class="fas fa-scroll"></i> Populate</button>\n'
        '</div>\n',
        encoding="utf-8",
    )
    (MODULE_DIR / "templates" / "populate-npcs.html").write_text(
        '<div class="sweetness-populate-npcs">\n'
        '  <p>Create NPC actors in the <b>Sweetness NPCs</b> compendium.</p>\n'
        '  <p class="notes">Unlock the compendium first (right-click → Toggle Edit Lock).</p>\n'
        '  <button type="button" class="populate-npcs-trigger"><i class="fas fa-users"></i> Populate NPCs</button>\n'
        '</div>\n',
        encoding="utf-8",
    )
    print("[+] Wrote templates/")


def build_actors():
    """Find actors.txt in sweetness, parse, write sweetness-npcs.json."""
    actors_path = None
    for name in ACTORS_FILES:
        p = SWEETNESS_DIR / name
        if p.is_file():
            actors_path = p
            break
    if not actors_path:
        print("[*] No actors.txt in sweetness/ — skipping NPCs")
        return
    npcs = parse_actors_file(actors_path)
    out_path = MODULE_DIR / "sweetness-npcs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(npcs, f, indent=2)
    print(f"[+] Wrote {len(npcs)} NPC(s) to {out_path.relative_to(PROJECT_ROOT)}")


def main():
    if not SWEETNESS_DIR.is_dir():
        print(f"[!] Sweetness folder not found: {SWEETNESS_DIR}")
        return
    MODULE_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    write_module_structure()

    # Scenes: image filename → scene name = filename with underscores removed
    scenes = []
    for f in sorted(SWEETNESS_DIR.iterdir()):
        if not f.is_file():
            continue
        suf = f.suffix.lower()
        if suf not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            continue
        dest = ASSETS_DIR / f.name
        shutil.copy2(f, dest)
        w, h = 1600, 1200
        if Image:
            try:
                with Image.open(dest) as im:
                    w, h = im.size
            except Exception:
                pass
        scene_name = f.stem.replace("_", " ").strip()
        rel_path = f"modules/{MODULE_ID}/assets/{f.name}"
        scenes.append({
            "name": scene_name,
            "img": rel_path,
            "width": w,
            "height": h,
        })
        print(f"[+] {f.name} -> assets/ ({w}x{h}) -> scene \"{scene_name}\"")
    list_path = MODULE_DIR / "scene-list.json"
    with open(list_path, "w", encoding="utf-8") as out:
        json.dump(scenes, out, indent=2)
    print(f"[+] Wrote {len(scenes)} scene(s) to {list_path.relative_to(PROJECT_ROOT)}")

    build_actors()

    # Embed scene + NPC data into init.js so Populate works when Import Wizard skips JSON (single script = module loads)
    npcs_path = MODULE_DIR / "sweetness-npcs.json"
    npcs = []
    if npcs_path.exists():
        with open(npcs_path, encoding="utf-8") as f:
            npcs = json.load(f)
    init_js = MODULE_DIR / "scripts" / "init.js"
    if not init_js.exists():
        print(f"[!] {init_js.relative_to(PROJECT_ROOT)} not found — skipping data inject. Add the full module (scripts/init.js, module.json, etc.) and re-run.")
    else:
        init_text = init_js.read_text(encoding="utf-8")
        start_marker = "// EMBEDDED_DATA - build_foundry_module.py replaces this block with scene/NPC data so Populate works when JSON is skipped\n"
        end_marker = "// END_EMBEDDED_DATA"
        if start_marker not in init_text or end_marker not in init_text:
            print("[!] init.js missing EMBEDDED_DATA block, skipping inject")
        else:
            scenes_json = json.dumps(scenes, ensure_ascii=False)
            npcs_json = json.dumps(npcs, ensure_ascii=False)
            replacement = (
                "window.DELTA_GREEN_SWEETNESS_SCENE_LIST = "
                + scenes_json
                + ";\nwindow.DELTA_GREEN_SWEETNESS_NPC_LIST = "
                + npcs_json
                + ";\n"
            )
            before = init_text.split(start_marker)[0]
            after = init_text.split(end_marker, 1)[-1]
            new_init = before + start_marker + replacement + end_marker + after
            init_js.write_text(new_init, encoding="utf-8")
            print(f"[+] Injected embedded data into {init_js.relative_to(PROJECT_ROOT)}")

    # Forge Import Wizard skips "non media" files (e.g. scene-list.json, sweetness-npcs.json). Create a zip without them.
    create_forge_zip()


def create_forge_zip():
    """Create delta-green-sweetness-forge.zip excluding data JSON so the Import Wizard skips 0 files.
    Empty directories (packs/sweetness-scenes, packs/sweetness-npcs) are included explicitly so
    Foundry can initialise the LevelDB stores on first load."""
    exclude = {"scene-list.json", "sweetness-npcs.json"}
    zip_path = PROJECT_ROOT / "delta-green-sweetness-forge.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in MODULE_DIR.rglob("*"):
            arcname = item.relative_to(MODULE_DIR.parent)
            if item.is_dir():
                # Add a directory entry so empty dirs survive the zip round-trip
                dir_entry = zipfile.ZipInfo(str(arcname).replace("\\", "/") + "/")
                zf.writestr(dir_entry, "")
                continue
            if item.name in exclude:
                continue
            zf.write(item, arcname)
    print(f"[+] Forge-ready zip: {zip_path.name} (excluded {len(exclude)} data JSON so 0 files are skipped)")


if __name__ == "__main__":
    main()
