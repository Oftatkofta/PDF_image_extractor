/* global game, Hooks, Dialog, fetch */

const MODULE_ID = "delta-green-sweetness";
const SCENES_PACK = "delta-green-sweetness.sweetness-scenes";
const NPCS_PACK = "delta-green-sweetness.sweetness-npcs";
const GRIDLESS = 0;

// EMBEDDED_DATA - build_foundry_module.py replaces this block with scene/NPC data so Populate works when JSON is skipped
window.DELTA_GREEN_SWEETNESS_SCENE_LIST = [{"name": "Bernier house", "img": "modules/delta-green-sweetness/assets/Bernier_house.png", "width": 1006, "height": 1277}, {"name": "Garrison appartment note", "img": "modules/delta-green-sweetness/assets/Garrison_appartment_note.jpeg", "width": 1046, "height": 545}, {"name": "Invite", "img": "modules/delta-green-sweetness/assets/Invite.png", "width": 1024, "height": 1536}, {"name": "Sarah Garrison", "img": "modules/delta-green-sweetness/assets/Sarah_Garrison.jpeg", "width": 976, "height": 512}, {"name": "sweetness cover", "img": "modules/delta-green-sweetness/assets/sweetness_cover.jpeg", "width": 1243, "height": 1620}, {"name": "The Mark", "img": "modules/delta-green-sweetness/assets/The_Mark.jpeg", "width": 475, "height": 1238}];
window.DELTA_GREEN_SWEETNESS_NPC_LIST = [{"name": "Sarah Garrison", "type": "npc", "img": "", "system": {"attributes": {"str": 12, "con": 7, "dex": 10, "int": 14, "pow": 9, "cha": 9, "hp": 10, "wp": 9, "san": 0}, "biography": "SKILLS: Alertness 45%, Athletics 30%, Bureaucracy 45%, Criminology 35%, Dodge 55%, Driving 55%, Firearms 45%, First Aid 25%, Forensics 30%, Law 25%, Persuade 45%, Stealth 35%, Search 60%, Unarmed Combat 45%.\n\nATTACKS: Charter Arms “Bulldog” revolver (.357 magnum, 5 shots) 45%, damage 1D12. Unarmed 45%, damage 1D4−1."}}, {"name": "The Shadowman", "type": "npc", "img": "", "system": {"attributes": {"str": 22, "con": 30, "dex": 13, "int": 7, "pow": 10, "hp": 26, "wp": 10}, "biography": "SKILLS: Jumping 45%, Swimming Through Air 75%.\n\nATTACKS: Grab 50%, damage special.\n\nGRAB: If the Shadowman grabs a victim, it swims toward the nearest Portal. Once per turn, the victim may attempt a STR test against the Shadowman’s STR to break free. So can each helper trying to pull the victim free. If the attempt fails, it does not slow the Shadowman and the victim at all.\n\nTHE HOST: If the Stone of Yos is occupied, the Shadowman’s INT, POW, WP, and SAN scores are those of the occupant, and it knows languages known by the host.\n\nTHE NAME: The creatures’ chief vulnerability is the name of YogSothoth. Whispering the name is enough to inflict 1 damage on the creature. Saying it inflicts 1D4. Screaming it, 1D20. If the Shadowman hits 0 HP, it is dismissed it as if it had traveled through a Portal, though it may return. And you can bet anyone who knows that name will not see it coming a second time....\n\nPORTALS: Any reflective surface can be used by the Shadowman as a portal for escape. The Shadowman’s form must obey the proportions of the surface, so it must be of sufficient size (no leaping into a fork). It typically manifests through mirrors, but a window seen from inside a bright room at night would also work. Whenever the Shadowman moves into a portal, Sarah Garrison loses control of it, and must reenter the Stone of Yos to establish a new connection. It takes her 1D20 minutes to regain control and move the Shadowman back to the Bernier house.\n\nSWIMMING: The Shadowman moves through the air as if it were water. It swims about as fast as a human walks. It can swim upwards, drift down, and float indefinitely in space. Seeing this strange movement for the first time costs 0/1 SAN. When the Shadowman alights on a floor, it can move as a normal human, but always seems to be working against some sort of invisible force of resistance.\n\nTRANSCENDENT: The Shadowman is immune to all physical attacks. Period.\n\nVANISH: In direct sunlight, or when hit with a high intensity illumination device, the Shadowman collapses instantly into a tiny mote of darkness, like a magic trick. Seeing this for the first time costs 1/1D4 SAN. It is very easy to assume it has teleported away. However, with a successful Search roll, this shadow is still visible as a tiny blob of impossible darkness. Hitting it again with a burst of such bright light causes the creature to retreat to a Portal.\n\nSAN LOSS: 1/1D4."}}];
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
  const SceneDocument = pack.documentClass;
  for (const s of scenes) {
    const doc = new SceneDocument({
      name: s.name,
      background: { src: s.img },
      width: s.width,
      height: s.height,
      grid: { type: GRIDLESS },
      fog: { exploration: false },
      tokenVision: false
    }, { pack: SCENES_PACK });
    await pack.createDocument(doc);
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
  const ActorDocument = pack.documentClass;
  for (const n of npcs) {
    const doc = new ActorDocument({
      name: n.name,
      type: n.type || "npc",
      img: n.img || "",
      system: n.system || {}
    }, { pack: NPCS_PACK });
    await pack.createDocument(doc);
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
    return mergeObject(super.defaultOptions, {
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
    return mergeObject(super.defaultOptions, {
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
