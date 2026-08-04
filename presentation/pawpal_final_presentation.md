---
marp: true
theme: default
paginate: true
style: |
  section { font-family: Arial, sans-serif; padding: 56px; }
  h1 { color: #183153; }
  h2 { color: #245b78; }
  strong { color: #1f6f8b; }
  code { background: #f3f6f8; }
---

# PawPal Applied AI System

### Grounded AI guidance for everyday pet-care planning

Hemaleka Mohanram

<!--
Introduce PawPal as an upgrade of my Module 2 scheduling project. My goal was not to add AI everywhere. I wanted to add it where explanation and retrieval are useful while keeping the schedule predictable.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project
-->

---

# PawPal now schedules and explains care

| Original PawPal+ | Final applied AI system |
|---|---|
| Stores pets and care tasks | Keeps the original task system |
| Prioritizes tasks by time available | Retrieves relevant care passages |
| Detects conflicts and recurrence | Generates grounded explanations |
| Uses deterministic Python rules | Adds guardrails, confidence, and logs |

**Design goal:** Add AI without giving it control of scheduling rules.

<!--
Explain that the original Module 2 project already did useful scheduling and persistence. The upgrade keeps those strengths. The main new problem is helping an owner understand and follow the plan, while showing where the answer came from.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/README.md
-->

---

# PawPal separates planning, retrieval, and generation

## 1. Plan

Python prioritizes tasks and fits them into the available time.

## 2. Retrieve

The retriever selects task- and species-relevant passages from a local care guide.

## 3. Explain and check

The model receives the plan plus retrieved context. Guardrails, confidence, and logs make the result easier to review.

**Human check:** the pet owner sees both the response and the passages used.

<!--
Walk through the three components. Stress that retrieval is inside the prompt, so it changes what the model sees. Mention that emergency phrases stop before the model and that the owner remains part of the checking process.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/diagrams/architecture.mmd
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/pawpal_ai.py
-->

---

# A schedule and an AI explanation work together

```text
Pet: Mochi (cat)              Available time: 30 min
Medication: 10 min, high      Interactive play: 20 min, medium
Grooming: 20 min, low
```

```text
08:00 Medication
08:10 Interactive play
Skipped: Grooming
```

**Question:** How should I remember the medication?

**Retrieved context:** `[medication-safety]`

**Grounded test response:** Keep the medication time consistent `[medication-safety]`.

<!--
Demo the schedule first, then the question. Point out which output comes from deterministic Python and which crosses the AI boundary. Be transparent that the displayed response is the mocked response used by the automated integration test; a live response requires an API key and its wording can vary.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/tests/test_pawpal_ai.py
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/README.md
-->

---

# Reliability is measured on every push

# 48 / 48

Unit tests passed

# 7 / 7

Reliability evaluation cases passed

# 0

Paid model calls required by CI

The harness checks retrieval, prompt grounding, emergency blocking, missing configuration, empty input, and missing context.

<!--
Explain why the model is replaced with a fake client in CI: I can verify that the correct context reaches the model boundary without network variation or API cost. Be clear that this does not replace live response-quality evaluation.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/actions/runs/30882975519
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/evaluate.py
-->

---

# A passing evaluation still exposed a bad result

## Before

```text
Cat query -> cat-enrichment, routine-consistency, dog-activity
```

The evaluator passed because it only checked that the correct cat passage was present.

## After

```text
Cat query -> cat-enrichment, routine-consistency
```

I added species filtering and a regression test that also checks the wrong passage is absent.

<!--
This is the most important learning moment. The first total was 7 out of 7, but I read the details and noticed the dog passage. Explain the code fix and why evaluating unwanted behavior is as important as checking expected behavior.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/model_card.md
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/tests/test_pawpal_ai.py
-->

---

# This project shows how I want to build AI systems

- Keep important rules **deterministic and testable**
- Ground model responses in **visible custom documents**
- Treat confidence as a signal, **not proof of truth**
- Design safe behavior for missing context, errors, and emergencies
- Read the detailed output instead of trusting a green checkmark

**Next step:** run repeated live-model evaluations and have the care guide reviewed by a veterinary professional.

Repository: github.com/hemalekamohanram/codepath-applied-ai-system-project

<!--
Close by connecting the technical choices to what I learned as an aspiring AI engineer. I can build an end-to-end system, test it, find a weakness, fix it, and communicate its limits. The next step is live response evaluation and expert review, not adding more features.

[Sources]
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project/blob/main/model_card.md
- https://github.com/hemalekamohanram/codepath-applied-ai-system-project
-->
