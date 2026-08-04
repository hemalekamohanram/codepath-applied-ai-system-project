# PawPal Applied AI System — Model Card

## System purpose

PawPal is a learning project that helps a pet owner organize routine care tasks and ask questions about the generated plan. Python creates the schedule, a local retriever selects relevant care passages, and a Claude model explains the plan using those passages. The system is meant for organization and general education, not diagnosis, emergency response, or treatment decisions.

## Intended users and uses

The intended user is an adult pet owner who wants help keeping track of normal tasks such as feeding, walking, play, grooming, or veterinarian-prescribed medication reminders. A user should review the retrieved sources and use PawPal as a planning aid.

PawPal should not be used to decide whether a pet is sick, choose a medication, change a dose, replace veterinary care, or handle an emergency.

## What are the limitations or biases in the system?

The knowledge base is small and written in English. It includes general passages for dogs, cats, and routine pet care, so it does not represent every species, disability, culture, living situation, or veterinary recommendation. The advice may fit common pet-care routines better than unusual or complex cases.

The retriever uses keyword overlap. It can miss synonyms, misspellings, or questions that describe a topic indirectly. Its confidence score measures how strongly the words matched the local passages; it does not measure medical correctness or the model's certainty.

The model can still misunderstand context or produce an unsupported statement. The prompt asks it to use only retrieved material and cite passage IDs, but prompting cannot guarantee perfect compliance. The emergency guardrail also depends on a short phrase list, so wording outside that list may reach the model.

The automated tests use a fake model client. This verifies the retrieval and model-call boundary without spending API credits. Live Claude requests also succeeded during integration, but a few responses do not measure variation, hallucination rate, latency, or quality across different questions. A larger evaluation with veterinary review would be needed before this system could be treated as more than a student project.

## Could the AI be misused, and how would I prevent that?

A user could try to use PawPal for diagnosis, medication changes, poisoning advice, or emergency instructions. The interface states that PawPal is not a veterinarian. The prompt forbids diagnosis and dose changes, medication passages direct users back to the prescribing clinic, and known emergency phrases stop the workflow before any model call.

The app also shows the retrieved passages beside the response so the user can compare the answer with its context. Missing context, a missing API key, an empty question, and API errors produce safe messages instead of an invented answer. The deterministic schedule remains unchanged when AI generation fails.

To reduce privacy and security risk, the API key is read from an environment variable and `.env` is ignored by Git. The structured log stores event type, source IDs, confidence, and error type, but it does not store the API key or full owner question.

These controls reduce risk but do not remove it. A stronger version would add broader emergency detection, rate limits, response citation validation, moderation, clearer data-retention controls, and review of the knowledge base by a veterinarian.

## What surprised me while testing reliability?

My first evaluation run reported 7 out of 7 passing cases, but the details showed that a cat-enrichment query also retrieved the `dog-activity` passage. Both passages used the word “activity,” and my first evaluator only checked that the correct cat source was present. It did not check that an incorrect species source was absent.

I fixed the retriever so a species-specific passage is excluded when it does not match the owner's pet. I also added a regression test and strengthened the evaluation condition. The next CI run passed 48 unit tests and 7 evaluation cases, with the cat query returning only `cat-enrichment` and the general `routine-consistency` passage. This taught me to inspect outputs, not only pass totals.

The first successful live Claude run revealed a different false match. A medication question retrieved `cat-enrichment` because the word “can” appeared in both the question and that passage. The model did not cite the irrelevant passage, but I still treated the retrieval as flawed. I removed species names from the keyword query, added “can” to the stop-word list, and updated the regression test to use the exact live question. The final live run retrieved only `medication-safety` and `routine-consistency`.

## How I collaborated with AI

I used Codex as a coding partner to inspect the original PawPal project, propose a small RAG design, draft code and documentation, and help set up tests and GitHub Actions. I reviewed the file changes, kept the project at a level I could explain, and used the automated results to decide what needed correction. I did not treat generated code or text as automatically correct.

### One helpful AI suggestion

A helpful suggestion was to keep scheduling deterministic and use the model only to explain the plan with retrieved context. That design made the important time and priority behavior repeatable while still adding a meaningful AI feature. It also gave me clear places to test retrieval, safety checks, and model failure separately.

### One flawed AI suggestion

The first AI-generated retriever design added a species match as a bonus but did not exclude passages for the wrong species. The first AI-generated evaluation also accepted the cat case when the correct source appeared anywhere in the results, even though a dog source appeared too. The code technically passed its test, but the output was not good enough. I corrected both the retrieval rule and the evaluation assertion after reading the detailed result.

## Current evaluation status

- Unit tests: 48 passed in GitHub Actions
- Deterministic reliability evaluation: 7 of 7 passed
- Live Claude response evaluation: successful; final run retrieved only the two relevant passages and cited both
- Human veterinary review: not performed

The measured CI evidence is included in `README.md`, and the evaluation can be reproduced with:

```bash
python -m pytest -q
python evaluate.py --output evaluation_results.json
```
