# Upgrade Ritual Trainer.ai to v0.6.1 — Windows

v0.6.1 fixes hero/item lookup URLs and defaults to **Ollama / gpt-oss:20b** and adds verified hero/item information plus a replay-schema availability check.

1. Close the old Ritual Trainer.ai terminal and browser tab.
2. Extract the **v0.6.1 ZIP into a NEW folder** rather than overwriting the running project.
3. Copy the existing `.env` file from your older `ritual-trainer-ai` folder to this new `ritual-trainer-ai` folder. Never share `.env`.
4. Right-click `.env`, select **Open with → Notepad**, and set `OLLAMA_MODEL=gpt-oss:20b`. If that line is missing, add it. Save with **Ctrl+S**. Gemini settings can stay in the file; they are unused when Ollama is selected.
5. Open Windows PowerShell and run `ollama list`. If `gpt-oss:20b` is missing, run `ollama pull gpt-oss:20b`. Ensure Ollama is running.
6. Double-click `run_windows.bat` in the new folder. The sidebar should show `Ollama (local, offline)` and `gpt-oss:20b`.
7. Load Deadlock match ID **120208613** and select your hero. In **Consult the Oracle**, click **Refresh verified hero and item information**. Then generate a report.
8. Check the new **Replay Forensics** tab. The schema inspection step only checks whether queryable tables exist. It does not yet extract gameplay events.

If live APIs are down, test the app's sample match and graphs. When assets are unavailable, the AI cannot claim to know verified hero-specific abilities.

## Fix for the "assets.deadlock-api.com" DNS error

The previous release called an outdated service host. v0.6.1 instead calls the published Deadlock community API routes:

- `https://api.deadlock-api.com/v1/assets/heroes/{hero_id}`
- `https://api.deadlock-api.com/v1/assets/items`

After installing v0.6.1, load the same match and click **Refresh verified hero and item information**.
If it still fails, open `https://api.deadlock-api.com/docs` in your browser: a DNS failure there indicates a network, DNS, or service issue, rather than an Ollama issue.

The correction is covered by offline mocked tests; an end-to-end live API call was not possible from the build environment.
