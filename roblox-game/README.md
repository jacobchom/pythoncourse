# Sky Jump: +1 Jump Every Second

An original Roblox game in the "+1 every second" genre. Your jump power grows by 1 every second. Climb 11 floating islands to reach The Summit, earn Wins, then Rebirth to grow faster.

The whole game, map included, is built from code in `src/`, so there's no `.rbxl` file to manage.

## What's in it
- **Core loop**: +1 jump power per second, multiplied by rebirths and the 2x gamepass.
- **11 islands**: each one needs more jump power than the last. Checkpoints save your stage.
- **Wins and Rebirth**: reaching The Summit gives Wins. Rebirthing resets your jump and adds +1x to how fast it grows.
- **Daily reward**, **promo codes** (for marketing), and an optional **2x Jump gamepass**.
- **Saving**: uses DataStore with autosave. If a load fails, that session never overwrites your real save.

All balance numbers are in `src/shared/Config.luau`.

## Publish it (about 20 minutes)
1. Install [Roblox Studio](https://create.roblox.com/) and [Rojo](https://rojo.space/) (VS Code extension or CLI), plus the Rojo Studio plugin.
2. In this folder, run:
   ```bash
   rojo serve
   ```
3. In Studio, open a new **Baseplate**. Delete the `Baseplate` part and the default `SpawnLocation`. In the Rojo plugin, click **Connect**.
4. Click **Play** and test: your jump counter should go up every second, and each island should become reachable as it grows.
5. Go to **File → Publish to Roblox**. Then, in **Game Settings → Security**, turn on **Enable Studio Access to API Services** so DataStores work.
6. Optional gamepass: Creator Dashboard → your experience → Monetization → Passes → create "2x Jump". Paste its ID into `Config.GAMEPASS_2X_JUMP` and republish.
7. On the Creator Dashboard, set the experience to **Public**, fill in the description from `marketing/LAUNCH_PLAN.md`, and upload the icon and thumbnails.

## Not tested yet
This was written without Roblox Studio, and I couldn't run a Luau syntax checker on it. Run the Play test in step 4 before publishing. Errors, if any, will show up in Studio's Output window.
