# Ritual Trainer.ai — Live Demo Plan

**Problem:** Deadlock players see scores and graphs, but interpreting what to practice next is hard.

**Solution:** An evidence-grounded AI coaching tool that turns match timelines and high-rank cohort reference data into detailed drills and measurable goals.

## Recommended demonstration (recording; under 2 minutes per assignment)

1. Open `http://localhost:8501`, select **Sample match**, and click **Open the match ledger** as a network-independent fallback.
2. Show the **The Soul Ledger** tab. Highlight the 5-minute soul-gain gap and explain that the app measures the gap without pretending it knows the player's intention.
3. Switch to **Consult the Oracle** and generate a multi-part improvement plan using a free Gemini API key or a local Ollama model.
4. Ask: "How can I improve midgame farming without missing decisive teamfights?" Demonstrate iterative refinement.
5. If the community API is available, switch to a **real match ID** and show the actual chart and high-rank hero cohort comparison.

## Prompt engineering slide

- Persona: constructive, careful Deadlock analyst.
- Few-shot: specific conditional coaching versus generic criticism.
- Iterative refinement: natural-language follow-up grounded in the same statistics.

## Under 2-minute short-form video outline

**0:00–0:15:** "Ever finish a Deadlock match wondering where your souls went? Ritual Trainer.ai turns your match data into a personal training plan."

**0:15–0:40:** Show match input, player selection and soul progression chart. "It calculates exactly when my soul income slowed compared with teammates."

**0:40–1:10:** Show higher-rank reference curves or show the coaching report when online. "The AI doesn't just criticize. It explains the numbers, gives a practice drill, and sets a measurable goal."

**1:10–1:35:** Ask a question in coaching chat. "The coaching adapts to my hero, role, and the match evidence."

**1:35–1:50:** "Ritual Trainer.ai — every soul leaves a trace. Rewrite the next ritual."

Only claim live meta benchmarks in the video if the API returned actual data for the demonstrated hero and filter. Show the demo badge when sample data is used.

## Before presenting

- Confirm the Gemini free-tier key or local Ollama model works; generate a full coaching report and a follow-up. No paid billing is needed.
- Run `pytest` and open the app on the presentation computer.
- Load a known real match and verify its player selection and chart coverage.
- Keep demo mode ready if the community service rate-limits or returns incomplete metadata. The demo uses real Deadlock hero names paired with invented IDs and completely fictional match statistics; keep the demo warning visible.
- Record a backup screen capture of one successful run if the professor allows it.

## Deadlock lore and role customization (v0.4)

The interface references the Cursed Apple, Patrons, rituals, souls, and a match ledger.
These are **original UI phrases**, not quotations from official Deadlock dialogue.

Show the sidebar **Role / soul priority** dropdown or its expandable hero list.
Explain that Deadlock does not require fixed role classes. The project uses flexible
role archetypes: Hard Carry, Tempo / Off-Carry, Frontliner / Space Creator, and
Support & Utility. The user can override the hero-based suggestion to reflect
their actual build and farm responsibilities. Explain that the coach judges a support
by team-enabling contribution rather than against a carry’s expected soul income.

Do not claim the AI knows a hero's real build, positioning, or actual in-game job
from the role selection alone.


## v0.4 demo highlights

- AI provider selector: **Gemini (free tier)** or **Ollama (local, offline)**. Both reuse the same Persona + Few-Shot prompts; follow-ups demonstrate Iterative Refinement.
- The player selector and scoreboard show **The Hidden King** and **The Archmother** instead of numeric IDs.
- The role selector uses the role names without numbers and still gives hero examples.
- Do not present Gemini free-tier access as unlimited; do not enable paid billing just for the class demo.

## v0.6 presentation update

- Demo the default free local model **GPT-OSS 20B on Ollama**, not a paid API.
- Demonstrate **Verified hero knowledge** after loading a real Deadlock match. Describe this as retrieval grounded in the Assets API, not an LLM that memorized the entire Deadlock meta.
- The **Replay Forensics** tab is an initial schema check; **do not claim it already analyzes hero movements**. Full replay event extraction is a future enhancement.
- Compare one generic model response to the grounded report as evidence of prompt engineering effectiveness; only use actual generated outputs during the recording.
