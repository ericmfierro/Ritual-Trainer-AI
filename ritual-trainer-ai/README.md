# Ritual Trainer.ai

**An AI-powered match analysis and coaching dashboard for [Deadlock](https://store.steampowered.com/app/1422450/Deadlock/).**

Ritual Trainer.ai turns match statistics into practical coaching. Enter a Deadlock match ID, choose a player, inspect soul and combat timelines, and ask a locally hosted language model to suggest measurable ways to improve. The interface draws inspiration from Deadlock's occult setting, with sections such as **The Match Ledger**, **The Soul Ledger**, and **Consult the Oracle**.

> **Project status:** Working student-built MVP. Some analytics depend on third-party API availability. The Replay Forensics tab currently checks for queryable replay data; it does **not** analyze footage, hero movement, or ability casts.

## Features

- **Match lookup:** Load a Deadlock match by ID, upload match metadata as JSON, or explore a clearly labeled fictional sample match.
- **Performance timelines:** Inspect cumulative souls, combat statistics, and five-minute soul-gain comparisons against teammates.
- **Hero-aware analysis:** Select a player and use flexible community playstyles—Hard Carry, Tempo / Off-Carry, Frontliner / Space Creator, or Support & Utility—to provide context for farming expectations.
- **Optional comparisons:** Request same-hero performance curves, item-purchase trends, and patch information when the relevant API data is available.
- **AI coaching:** Generate prioritized feedback, practice drills, and next-match goals. Ask follow-up questions to refine the advice.
- **Game knowledge retrieval:** Retrieve available hero and item definitions to help keep coaching grounded in the current game data.
- **Replay Forensics preview:** Check whether the community API exposes a replay schema for the selected match. Full replay-event extraction is not yet implemented.

## How it works

1. Load a real match or choose **Sample match**.
2. Select the player and confirm their role or playstyle.
3. Review **The Match Ledger**, **The Soul Ledger**, and **Battle Chronicle**.
4. Open **Consult the Oracle** to generate a coaching report with your chosen AI provider.
5. Ask a follow-up question to explore a specific weakness or develop a practice plan.

The app calculates statistics from match data before sending a structured summary to the model. AI-generated suggestions are interpretations, not verified observations of your gameplay footage.

## Requirements

- Python **3.10 or newer**
- Windows, macOS, or Linux
- Internet access for live Deadlock data and optional Gemini requests
- An AI backend:
  - **Recommended:** [Ollama](https://ollama.com/download) with `gpt-oss:20b`, running locally with **no paid inference API**
  - **Optional:** Gemini API access through [Google AI Studio](https://aistudio.google.com/app/apikey), subject to model availability, eligibility, and quotas

A local model's speed depends on your CPU, GPU, RAM, and available VRAM. Downloading a model requires internet access initially.

## Quick start

### Windows

Clone or [download this repository](https://github.com/ericmfierro/Ritual-Trainer-AI/archive/refs/heads/main.zip), then open a terminal in its folder:

```powershell
git clone https://github.com/ericmfierro/Ritual-Trainer-AI.git
cd Ritual-Trainer-AI
```

If you downloaded the ZIP instead, extract it and open PowerShell in the extracted folder; skip the `git clone` and `cd` commands.

Install [Ollama](https://ollama.com/download), then download the default model:

```powershell
ollama pull gpt-oss:20b
```

Start the application by double-clicking `run_windows.bat`, **or** set it up manually:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address shown by Streamlit, typically **http://localhost:8501**. In the sidebar, leave **Coaching engine** set to **Ollama (local, offline)** and **AI model** set to `gpt-oss:20b`.

Ollama usually runs in the background after installation. If the app cannot connect, open a separate terminal and run `ollama serve` (unless an Ollama server is already running).

### macOS / Linux

Install [Ollama](https://ollama.com/download) and run `ollama pull gpt-oss:20b`. Then, from the repository folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If the local model does not start, refer to the [Ollama documentation](https://docs.ollama.com/) for your operating system.

### Optional configuration

For local Ollama, no API key is needed. You may copy `.env.example` to `.env` to customize the model or host:

```env
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_HOST=http://localhost:11434
```

If using Gemini instead, configure the key and an available model in your private `.env` file, then select **Gemini (free tier)** in the app:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=your_available_model_id
```

**Never commit `.env`, credentials, or API keys.** `.env.example` is a public template. The `.gitignore` excludes `.env`, `.venv/`, and Python cache files. Gemini may have usage fees outside an eligible free tier; review your account's billing and limits before enabling it.

## Prompt engineering

Ritual Trainer.ai uses three prompt engineering patterns, implemented in [`ritual_coach.py`](ritual_coach.py):

| Pattern | Purpose |
| --- | --- |
| **Persona** | Frames the model as a constructive Deadlock coach who must work from available evidence. |
| **Few-shot prompting** | Provides examples contrasting specific, actionable coaching with unhelpful generic feedback. |
| **Iterative refinement** | Uses follow-up questions and the original match context to produce more focused recommendations. |

The prompt instructs the model to distinguish confirmed statistics from hypotheses, avoid inventing hero abilities or item effects, and tailor farming advice to the player's role.

## Project structure

```text
app.py                 Streamlit application and interface
ritual_api.py          Deadlock API requests
ritual_core.py         Match normalization and timeline calculations
ritual_knowledge.py    Hero and item knowledge retrieval
ritual_coach.py        AI providers, prompts, and coaching generation
ritual_roles.py        Community role guidance and hero examples
ritual_teams.py        Patron team-name display
requirements.txt       Python dependencies
run_windows.bat        Windows startup helper
.env.example           Optional environment configuration template
data/                  Fictional demonstration data
tests/                 Automated tests
```

## Tests

After installing the application dependencies, run:

```bash
python -m pip install pytest
python -m pytest -q
```

The included tests exercise calculations, role handling, Patron mappings, and mocked API/model interactions. They are **not** a guarantee that external APIs or a locally installed model will always be available.

## Data sources and limitations

Ritual Trainer.ai uses the community-maintained [Deadlock API](https://api.deadlock-api.com/docs) for match and optional game data. Live requests are subject to API availability, coverage, and rate limits. The sample match is **fictional** and exists only for offline UI and workflow demonstrations.

The app does not currently watch replays or extract detailed positioning and ability-use events. Statistical patterns can identify periods worth reviewing, but they cannot prove the cause of a mistake. High-ranked cohort averages and item-purchase win rates are not definitive measures of the best strategy, and generated advice may be incorrect or become outdated after patches.

## Roadmap

- Extract relevant movement, objective, and combat events from supported Deadlock replay data.
- Correlate replay events with changes in soul and combat timelines.
- Improve source-backed, patch-aware recommendations and hero-specific comparisons.
- Track improvement across multiple matches.

These are planned enhancements, not features currently available in this version.

## Acknowledgments and disclaimer

**Ritual Trainer.ai is an independent, fan-made student project.** It is not affiliated with or endorsed by Valve or the Deadlock API maintainers. Deadlock and related names and game content belong to their respective rights holders.

The project currently does **not** include an open-source license. Public GitHub visibility does not, by itself, grant redistribution or modification rights.
