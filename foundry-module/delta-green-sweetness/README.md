# Delta Green: Sweetness (Foundry v13)

Scene and NPC compendium for the Sweetness scenario. No grid, no fog, no token vision.

---

## Install on The Forge (manifest only — no file uploads)

On The Forge, Bazaar is a marketplace and modules are installed only via **manifest URL**. You need to host the module somewhere and then install it from that URL.

### 1. Build the module (on your PC)

```bash
python build_foundry_module.py
```

You get:
- Folder: `foundry-module/delta-green-sweetness/`
- Zip: `delta-green-sweetness-forge.zip` (in the project root)

### 2. Host the module so Foundry can install it

You need **two public URLs**:
- **Manifest URL**: the URL of your `module.json` file.
- **Download URL**: the URL of the **zip** file (Foundry will download this when installing).

**Option A — GitHub (simple)**  
1. Create a new repo (can be private; use a **GitHub Release** for the zip so it’s downloadable).  
2. Upload the **contents** of `foundry-module/delta-green-sweetness/` into the repo (e.g. in a folder `delta-green-sweetness/` so the manifest is at `delta-green-sweetness/module.json`).  
3. Create a **Release**, attach `delta-green-sweetness-forge.zip` from your project root.  
4. Copy the **release zip’s direct link** (right‑click “delta-green-sweetness-forge.zip” → Copy link address).  
5. In the repo, edit `delta-green-sweetness/module.json`. Set `"download"` to that zip URL. Commit and push.  
6. Get the **raw URL** of `module.json` (e.g. on GitHub: open the file → Raw → copy the browser URL). That is your **manifest URL**.

**Option B — Any static host**  
1. Upload `delta-green-sweetness-forge.zip` and get its URL.  
2. Upload the full `delta-green-sweetness` folder so `module.json` is available at a URL.  
3. Edit `module.json` and set `"download"` to the zip URL.  
4. Upload the updated `module.json`. The URL of that file is your **manifest URL**.

### 3. Install in Foundry (on The Forge)

1. Open your **world** in Foundry.
2. Go to **Setup** (⚙️) → **Add-on Modules**.
3. Click **Install Module** (or **Install from Manifest**).
4. Paste the **manifest URL** (the URL to your hosted `module.json`).
5. Click **Install**. Foundry will use the `download` field in the manifest to fetch the zip and install the module.
6. Enable **Delta Green: Sweetness** in the module list, then **Save**.

### 4. Populate compendiums (one-time)

1. In the **Compendium** tab, right‑click **Sweetness Scenes** and **Sweetness NPCs** → **Toggle Edit Lock** (unlock).
2. **Setup** → **Module Settings** → **Delta Green: Sweetness**.
3. Click **Populate Sweetness Scenes** → **Populate**.
4. Click **Populate Sweetness NPCs** → **Populate NPCs**.

---

## Local / self‑hosted (no Forge)

Copy the **delta-green-sweetness** folder into Foundry’s `Data/modules/`. In Setup → Add-on Modules, enable **Delta Green: Sweetness**, then run the Populate steps above.
