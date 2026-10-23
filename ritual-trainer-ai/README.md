# Ritual Trainer.ai

**The Patron's Ledger: a Deadlock match coach for the Cursed Apple.** Enter a match ID, select your player, trace their souls and battle statistics, and generate thorough AI coaching with drills and measurable next-match goals.

This is a student-built MVP. It is **not affiliated with Valve** or the community Deadlock API team.

## Features

- Real Deadlock match ID lookup and manual match-metadata JSON upload with player selection.
- Interactive cumulative soul and combat charts.
- 5-minute soul-gain windows comparing you with your teammates' average.
- Optional higher-ranked **same-hero cohort** net-worth curves, filtered by match average badge and recent date.
- Optional hero-specific item purchase trends (counts, buyer win rates, and average purchase times).
- Optional current patch feed context.
- AI reports and follow-up chat, powered by **Gemini Free Tier** or a locally running **Ollama** model (no paid API required).
- Offline **fictional sample match** using genuine Deadlock hero names (with fictional statistics and made-up hero IDs) so the dashboard and role auto-suggestion remain demonstrable if the game API is unavailable.
- A flexible **community role framework** centered on soul priority: Hard Carry, Tempo / Off-Carry, Frontliner / Space Creator, and Support & Utility. The UI suggests a role from hero examples, and players can override it.
- Deadlock-inspired copy throughout the UI: **The Match Ledger**, **The Soul Ledger**, **Battle Chronicle**, **Consult the Oracle**, and **The Archives**.
- Transparent evidence and data limitations.

## Requirements

- Windows, macOS, or Linux, with **Python 3.10+**.
- Internet access for real matches and model calls.
- For **Gemini**: a free-tier Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey); do not activate paid billing. Or use **Ollama** locally with a downloaded model—no API key needed.
- The Deadlock community API needs no key for ordinary access, subject to limits.

## Start on Windows (Visual Studio Code terminal or PowerShell)

Unpack or save all repository files **with the folder structure shown below**. Open a terminal inside `ritual-trainer-ai`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` in Notepad. For Gemini Free Tier, set your Google AI Studio key:

```env
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Alternatively, **Ollama does not need an API key.** Install [Ollama](https://ollama.com/download), open Windows Terminal, and run:

```powershell
ollama pull gpt-oss:20b
```

Select **Ollama (local, offline)** under **Coaching engine** in the sidebar. The default model is `gpt-oss:20b` and no paid API account is necessary. Keep Ollama running while using the app. A small local model may produce less accurate reports and run slowly on weaker computers. If Ollama is not already serving requests, run `ollama serve` in a separate terminal.

**Gemini model updates:** In October 2026, Google restricts `gemini-2.5-flash` to existing users of the 2.5 family. The updated project defaults to `gemini-3.8-flash`, which supports the existing `generateContent` endpoint. If you see a 404 stating a model is unavailable, set `GEMINI_MODEL=gemini-3.8-flash` in `.env`, and check the **AI model** field in the Streamlit sidebar. `gemini-3.5-flash-lite` is a lower-resource alternative with an eligible free tier. References: [model access notice](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash), [Gemini 3.8 GenerateContent](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.8), and [official pricing/free tier](https://ai.google.dev/gemini-api/docs/pricing).

Gemini is available at no charge **only within free-tier limits** on an eligible account/project; Google can change supported models and quotas. Do not link a billing account if you want no possible API charges. Google may use free-tier content to improve its products—do not provide private information.


Then launch:

```powershell
python -m streamlit run app.py
```

The browser usually opens at `http://localhost:8501`.

If PowerShell blocks activation, skip it and run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

You can also double-click `run_windows.bat` after you configure `.env`.

### On macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY if using Gemini; Ollama needs no key
streamlit run app.py
```

## Project layout

```text
ritual-trainer-ai/
├── app.py                      # Streamlit UI
├── ritual_api.py               # Deadlock HTTP API integration
├── ritual_knowledge.py         # Hero / ability / item context from current game assets
├── ritual_core.py              # Data cleanup, timelines, interval analysis
├── ritual_coach.py             # Persona + few-shot + evidence-grounded AI
├── ritual_roles.py             # Flexible roles, farm priority, and hero examples
├── ritual_teams.py             # Deadlock Patron display names and mappings
├── requirements.txt
├── .env.example                # Template only; never upload your real .env
├── .gitignore
├── run_windows.bat
├── data/
│   ├── sample_match.json       # Clearly marked fictional sample statistics
│   └── demo_heroes.json        # Real hero names paired with fictional demo IDs
└── tests/
    ├── test_core.py
    ├── test_coach.py
    └── test_roles.py
```

## v0.6.1: GPT-OSS and corrected verified Deadlock knowledge

- **Default provider:** local Ollama, model `gpt-oss:20b`. Gemini is still optional.
- **Game knowledge retrieval:** In **Consult the Oracle**, click **Refresh verified hero and item information** for a real match. It fetches the selected hero's current description/ability references and matching purchased-item definitions using the free [Deadlock API asset endpoints](https://api.deadlock-api.com/docs). The app also tries to retrieve this automatically before generating a report.
- **Verification safeguard:** The prompt forbids naming hero mechanics or item effects that aren't present in the retrieved definitions. If the Assets API is unavailable, coaching is restricted to role-specific statistical analysis instead of pretending to know a hero's kit.
- **Replay Forensics preview:** Open a real match and click **Check whether this replay is queryable**. A returned schema is not yet a replay parse; this build does not claim to know rotations or ability casts. Once we inspect the exposed tables for a real match, we can implement controlled event extractions.

### Test with match 120208613

1. Start `run_windows.bat` and choose **Real Deadlock match ID**.
2. Enter `120208613` and choose **Open the match ledger**. If this match is not accessible, the API will return a clear message; use **Sample match** to test other features.
3. Select your player (and override the proposed role if needed).
4. In **Consult the Oracle**, click **Refresh verified hero and item information** and review the source summary.
5. Generate coaching using Ollama / `gpt-oss:20b`. Ask the model about a particular 5-minute soul deficit.
6. In **Replay Forensics**, click **Check whether this replay is queryable**; use the schema display to decide the next extraction step.

The offline unit tests cover the data conversion and mock HTTP calls. **We cannot verify API availability for this specific match or the actual GPT-OSS report from this development environment.**

## First test

1. Choose **Sample match** > **Open the match ledger**.
2. Select **Sample You · Ivy**.
3. Open **The Soul Ledger** and look at the midgame farming gap.
4. Open **Battle Chronicle** and explore the cumulative curves.
5. Select **Ollama (local, offline)** after downloading `gpt-oss:20b`, or **Gemini (free tier)** with `GEMINI_API_KEY`; select **Consult the Oracle** > **Consult the Oracle · Generate coaching**. The AI receives **fictional, labeled** evidence in sample mode.
6. Ask a follow-up such as: *Give me a 3-game practice routine to improve farming without abandoning important team fights.*
7. Switch to **Real Deadlock match ID** and load a known match to test the live API. If the service is unavailable, you can use **Upload match metadata JSON** with a previously saved API response.
8. With a real match, load the higher-rank benchmark and optional patch context before generating a final report.
9. In the sidebar, open **Hero roles and example heroes**. **Auto-suggest from hero** is a flexible starting point; choose a different role if your build or duties differ.

## Deadlock roles and soul priority

**The roles are a community coaching convention, not exclusive Valve-assigned classes.** The intent is to make the AI consider the amount of farm a player should reasonably take and the contribution they owe the team, not merely compare every player against the same soul or damage threshold. Actual hero role depends on the lineup, build, patch and game state.

| Umbrella role | Suggested role | Example heroes (not exclusive) | Coaching focus |
| --- | --- | --- | --- |
| Carries | **Hard Carry** | Lady Geist, Mirage, Infernus, Wraith, Seven | Sustained safe soul farming, scaling, item spikes, joining valuable fights |
| Carries | **Tempo / Off-Carry** | Haze, Warden, The Drifter, Pocket | Earlier spikes, purposeful rotations, picks and pressure without neglecting farm |
| Frontliners / Space Creators | **Frontliner / Space Creator** | Abrams, Bebop, Mo & Krill | Taking space, creating openings, absorbing pressure, initiations and objectives |
| Supports & Utility | **Support & Utility** | Ivy, Dynamo, Kelvin, Viscous, McGinnis, Paige | Healing or protection when available, control, assists, picks and efficient low-economy utility |

The app's **Role / soul priority** selector defaults to **Auto-suggest from hero**. Suggestions are not definitive: players can pick the actual role they performed. For heroes not in the curated examples, the role remains unspecified instead of being guessed.

This changes the coaching itself. A low-soul support is **not automatically underperforming** compared with a hard carry, while a hard carry may need particular attention to farm efficiency and item timing. Team averages and same-hero cohort curves can contain players in different positions and cannot by themselves verify positioning mistakes or objective decisions.

The user-provided community role framework is the guiding convention for this project, not an official role queue or current-meta tier list.

## How accurate is the coaching?

The app calculates metrics deterministically from returned data. The model receives the derived numbers in a structured evidence payload. It is instructed to:

- Give specific priorities, drills, decisions, and improvement targets.
- Distinguish observed events from hypotheses.
- Avoid claiming to have watched the replay or observed a rotation.
- Treat lower-than-average economy as a **signal to investigate**, not proof of a mistake.
- Avoid naming items as meta unless the supplied evidence supports them.
- Disclose benchmark limitations. The performance curve endpoint does **not** return a sample size.

**Limits:** A match ID does not automatically produce full replay vision. A strong item buyer win rate is not causal evidence of item strength. Average match badge is not an individual pro player's rank. The API can change or be unavailable. Reports can be inaccurate, so check suggestions against actual gameplay.

## Prompt engineering used

1. **Persona** — Sets the assistant as an experienced, constructive Deadlock coach with evidence rules.
2. **Few-shot examples** — Contrasts specific, conditional recommendations with poor generic criticism.
3. **Iterative refinement** — Follow-up chat retains the match evidence and prior coaching report to refine the advice.

The prompts are in `ritual_coach.py` for your presentation. Both Gemini and Ollama use **the same persona and few-shot examples**, and both support iterative refinement through follow-up questions.

## API references

- [Community Deadlock API Docs](https://api.deadlock-api.com/docs)
- [Machine-readable OpenAPI specification](https://api.deadlock-api.com/openapi.json)
- [Community API source code](https://github.com/deadlock-api/deadlock-api)
- Match: `GET /v1/matches/{match_id}/metadata`
- Assets: `GET /v1/assets/heroes`, `GET /v1/assets/items`
- Curves: `GET /v1/analytics/player-performance-curve`
- Item analytics: `GET /v1/analytics/item-stats`
- Patches: `GET /v2/patches`
- Current hero: `GET https://api.deadlock-api.com/v1/assets/heroes/{hero_id}`
- Current ability/item catalog: `GET https://api.deadlock-api.com/v1/assets/items`
- Replay schema: `GET /v1/matches/demo/schema?match_id={match_id}`

## Testing

From the project directory, install pytest if needed and run:

```bash
python -m pip install pytest
python -m pytest -q
```

Unit tests are offline. They validate the fictional fixture, data calculations, missing-data behavior, community role assignment/overrides, Patron mapping, provider dispatch with mocked responses, and prompt evidence packaging. API connectivity and the full graphical UI must be tested on a networked computer.

## GitHub submission

Create a repository named `ritual-trainer-ai`. Upload the source, `data/`, `tests/`, README, and `.env.example`. **Do not upload `.env` or your API key.** Once uploaded, submit that repository URL along with your recorded video URL through the class Google Form.

## Optional public deployment

Streamlit Community Cloud or a similar Python host can run the app. Set `GEMINI_API_KEY` in the hosting platform's secrets/environment settings; do not put secrets in GitHub. Make sure hosting access and quota remain within Gemini's free tier. Ollama generally requires your own local computer/server, so it is not automatically available on free web hosting.

## License

Student MVP for class demonstration; any redistribution must respect Deadlock and third-party API policies.


### v0.6.1 — Hero/item DNS fix

Earlier releases used the old `assets.deadlock-api.com/v2` host. This release calls the documented current `api.deadlock-api.com/v1/assets` endpoints for hero descriptions, hero-bound abilities, and item definitions. The knowledge panel still falls back to statistics-only coaching if the API is unavailable. The endpoint change was checked against the published OpenAPI schema and mocked in tests; live connectivity still needs to be confirmed on your PC.
