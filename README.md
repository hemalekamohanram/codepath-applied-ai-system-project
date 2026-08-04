# PawPal Applied AI System

PawPal helps pet owners turn a list of care tasks into a realistic daily plan. It schedules important tasks first, retrieves relevant information from a small pet-care knowledge base, and uses an OpenAI model to explain the plan with visible source IDs. I built it to explore how generative AI can be useful without giving it control over safety-critical scheduling rules.

## Original project

This project extends my Module 2 project, **PawPal+ (`ai110-module2show-pawpal-starter`)**. The original app stored pets and care tasks, prioritized the tasks, and generated a schedule that fit within the owner's available time. It also handled recurring tasks, conflict detection, filtering, JSON persistence, and a Streamlit interface.

For the final project, I kept that scheduling foundation and added a retrieval-augmented AI assistant, guardrails, structured logs, confidence scores, and AI-specific tests.

## What the upgraded project does

1. The owner enters a pet and adds care tasks.
2. The deterministic scheduler orders tasks by priority and fits them into the available time.
3. The owner asks a question about the generated plan.
4. PawPal retrieves the most relevant passages from `knowledge/pet_care_knowledge.json`.
5. The retrieved passages, pet species, and scheduled task names are placed in the model prompt.
6. The app displays the grounded answer, source passages, and a retrieval confidence score.
7. Emergency wording is intercepted before an API call and redirected to immediate veterinary help.

The AI explains a schedule; it does not decide medication doses, diagnose a pet, or replace a veterinarian.

## Architecture overview

The Mermaid source is in [`diagrams/architecture.mmd`](diagrams/architecture.mmd). The Streamlit app sends care tasks to a deterministic scheduler. When the owner asks for help, `PawPalAI` checks the input, retrieves local knowledge, builds a grounded prompt, and calls the OpenAI Responses API. The answer, source passages, and confidence score return to the interface, while a JSONL log records the result without storing the owner's full question.

Automated tests check the scheduler, retriever, prompt context, missing-key behavior, and emergency guardrail. The pet owner remains responsible for reviewing the guidance before using it.

## Project structure

```text
.
|-- app.py                         # Streamlit interface
|-- pawpal_system.py               # Pet, task, persistence, and scheduler logic
|-- pawpal_ai.py                   # Retrieval, model call, guardrails, confidence, logs
|-- knowledge/
|   `-- pet_care_knowledge.json    # Curated local RAG passages
|-- diagrams/
|   `-- architecture.mmd           # System architecture source
|-- tests/
|   |-- test_pawpal.py             # Original scheduling and persistence tests
|   `-- test_pawpal_ai.py          # RAG and guardrail tests
|-- assets/                        # Images used by project documentation
|-- requirements.txt
`-- .env.example
```

## Setup

### 1. Clone the project

```bash
git clone https://github.com/hemalekamohanram/codepath-applied-ai-system-project.git
cd codepath-applied-ai-system-project
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Set the OpenAI API key

Do not paste the key into the code or commit it to Git.

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your-api-key"
```

macOS or Linux:

```bash
export OPENAI_API_KEY="your-api-key"
```

`OPENAI_MODEL` is optional. If it is not set, PawPal uses `gpt-5.6-sol`.

### 5. Run the app

```bash
streamlit run app.py
```

### 6. Run the tests

```bash
python -m pytest -q
```

Runtime pet data is stored in `data.json`. AI events are stored in `logs/ai_events.jsonl`. Both paths are ignored by Git.

## Sample interactions

These examples show the current code paths. The scheduler and guardrail wording are deterministic. The RAG example uses the fake model client in `tests/test_pawpal_ai.py`, so it proves that retrieved context reaches the model boundary without claiming that a live API call was run in this workspace.

### Example 1: Generate a schedule

Input:

```text
Pet: Mochi (cat)
Available time: 30 minutes
Tasks:
- Medication, 10 minutes, high priority
- Interactive play, 20 minutes, medium priority
- Grooming, 20 minutes, low priority
```

Output:

```text
08:00  Medication       10 minutes  high
08:10  Interactive play 20 minutes  medium

Scheduled 2 of 3 tasks. Grooming was skipped because it did not fit.
```

### Example 2: Retrieved context reaches the AI

Input used by the automated test:

```text
How should I remember medication?
```

Retrieved source:

```text
[medication-safety] Medication tasks should follow the veterinarian's label exactly...
```

Mocked model output:

```text
Keep the medication time consistent [medication-safety].
```

### Example 3: Emergency guardrail

Input:

```text
My cat can't breathe.
```

Output before any model call:

```text
This may be an emergency. Contact a veterinarian or local emergency clinic now.
PawPal cannot diagnose or provide emergency instructions.
```

## Design decisions and trade-offs

### Keep scheduling deterministic

The model does not choose which task is most important or calculate whether tasks fit. Python does that work, which makes the schedule repeatable and easier to test. The trade-off is that the scheduler is less flexible than a fully agentic planner.

### Use a small local retriever

I used transparent keyword scoring instead of a vector database. This keeps setup simple and makes it possible to inspect why a passage was selected. It will not understand synonyms or subtle questions as well as an embedding-based retriever.

### Show retrieved sources and confidence

The app displays the exact passages given to the model. The confidence score measures retrieval strength, not whether every sentence in the model response is true. This distinction matters because a high retrieval score is not the same as medical accuracy.

### Fail safely

Missing API keys and API errors do not change the saved schedule. Emergency phrases skip the model completely. The phrase-based guardrail is intentionally simple and can miss wording that is not in its list.

## Testing summary

The repository contains 48 Pytest tests: 42 for the original scheduling and persistence system and 6 for retrieval and AI guardrails. The AI tests use a fake client so they do not spend API credits or depend on network access. GitHub Actions ran the full suite with Python 3.12 and also ran the seven-case evaluation harness. The [recorded CI run](https://github.com/hemalekamohanram/codepath-applied-ai-system-project/actions/runs/30882975519) passed.

```text
$ python -m pytest -q
................................................                         [100%]
48 passed in 0.07s

$ python evaluate.py --output evaluation_results.json
PASS | medication_retrieval        | top_source=medication-safety
PASS | cat_enrichment_retrieval    | sources=cat-enrichment,routine-consistency
PASS | retrieved_context_in_prompt | used_ai=True, context_found=True
PASS | emergency_guardrail         | guardrail=True, used_ai=False
PASS | missing_key_handling        | error=missing_api_key, used_ai=False
PASS | empty_question_validation   | error=empty_question
PASS | no_context_handling         | error=no_context, sources=0
Passed: 7/7
```

The first evaluation run revealed that a cat query could retrieve a dog passage because both used the word "activity." I added species filtering and a regression test, then reran the complete workflow. This was a useful reminder that a passing check can still hide a poor result if I only look at the total.

What is covered:

- Priority scheduling, available-time limits, recurrence, filtering, and conflicts
- JSON save/load behavior
- Medication-related retrieval
- Retrieved context reaching the model input
- Emergency requests skipping the model
- Missing API key handling
- Empty question validation
- Species-specific retrieval boundaries

What still needs stronger testing:

- Live API response quality across several model runs
- Streamlit interaction tests
- Broader emergency wording and misspellings
- Retrieval quality for questions that use unexpected vocabulary

## Optional stretch features completed

### RAG enhancement (+2)

PawPal uses a custom document collection in `knowledge/pet_care_knowledge.json` instead of relying only on the model's general memory. The passages cover routine consistency, feeding, medication, dog activity, cat enrichment, grooming, and urgent-care boundaries. Retrieved passages are placed inside the model prompt and displayed with the answer, so retrieval changes the response rather than appearing as a separate search result.

The reliability evaluation also improved this retrieval layer:

```text
Before species filtering:
cat question -> cat-enrichment, routine-consistency, dog-activity

After species filtering:
cat question -> cat-enrichment, routine-consistency
```

This change prevents a pet-specific passage from being used for the wrong species.

### Test harness (+2)

`evaluate.py` runs seven predefined AI-system cases and prints a pass/fail summary. It returns a nonzero exit code if any case fails and can save the detailed results as JSON with `--output`. GitHub Actions runs the harness on every push and uploads `evaluation_results.json` as a workflow artifact.

```bash
python evaluate.py --output evaluation_results.json
```

I did not implement the optional agentic-workflow or fine-tuning stretch features. I chose to keep the project focused on a RAG system that I can test and explain clearly.

## Reflection

This upgrade taught me that adding AI is not only about making an API call. I had to decide which work should stay predictable, what context the model should receive, and what the app should do when the model or network fails. The biggest lesson was that showing sources and writing tests made the AI behavior easier for me to understand and explain.

The detailed responsible-AI reflection and AI collaboration notes are documented in `model_card.md` as required by the project rubric.
