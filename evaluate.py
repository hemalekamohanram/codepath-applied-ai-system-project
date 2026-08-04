"""Run PawPal's deterministic AI reliability checks and print a summary."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pawpal_ai import KnowledgeRetriever, PawPalAI
from pawpal_system import Owner, Pet, Task


@dataclass
class EvaluationResult:
    name: str
    passed: bool
    detail: str


class FakeMessages:
    def __init__(self) -> None:
        self.last_input = ""

    def create(self, **kwargs):
        self.last_input = kwargs["messages"][-1]["content"]
        text_block = type(
            "FakeTextBlock",
            (),
            {"type": "text", "text": "Use a consistent time [medication-safety]."},
        )()
        return type(
            "FakeResponse",
            (),
            {"content": [text_block]},
        )()


class FakeClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


def make_plan(species: str, task_name: str) -> tuple[Owner, list[Task]]:
    owner = Owner(name="Evaluation user")
    pet = Pet(name="Test pet", species=species)
    task = Task(task_name, "daily", 10, 3)
    pet.add_task(task)
    owner.add_pet(pet)
    return owner, [task]


def record(name: str, condition: bool, detail: str) -> EvaluationResult:
    return EvaluationResult(name=name, passed=bool(condition), detail=detail)


def run_evaluation() -> list[EvaluationResult]:
    retriever = KnowledgeRetriever()
    results: list[EvaluationResult] = []

    medication = retriever.retrieve("remember medication dose", ["cat"])
    medication_id = medication[0].passage.id if medication else "none"
    results.append(
        record(
            "medication_retrieval",
            medication_id == "medication-safety",
            f"top_source={medication_id}",
        )
    )

    enrichment = retriever.retrieve("interactive play and enrichment", ["cat"])
    enrichment_ids = [item.passage.id for item in enrichment]
    results.append(
        record(
            "cat_enrichment_retrieval",
            "cat-enrichment" in enrichment_ids and "dog-activity" not in enrichment_ids,
            f"sources={','.join(enrichment_ids)}",
        )
    )

    owner, plan = make_plan("cat", "Medication")
    fake_client = FakeClient()
    grounded_service = PawPalAI(client=fake_client, log_path=Path("logs/evaluation.jsonl"))
    grounded = grounded_service.generate_guidance(
        owner, plan, "How can I remember the medication?"
    )
    context_in_prompt = "[medication-safety]" in fake_client.messages.last_input
    results.append(
        record(
            "retrieved_context_in_prompt",
            grounded.used_ai and context_in_prompt,
            f"used_ai={grounded.used_ai}, context_found={context_in_prompt}",
        )
    )

    emergency_service = PawPalAI(
        client=FakeClient(), log_path=Path("logs/evaluation.jsonl")
    )
    emergency = emergency_service.generate_guidance(
        owner, plan, "My cat can't breathe"
    )
    results.append(
        record(
            "emergency_guardrail",
            emergency.guardrail_triggered and not emergency.used_ai,
            (
                f"guardrail={emergency.guardrail_triggered}, "
                f"used_ai={emergency.used_ai}"
            ),
        )
    )

    missing_key = PawPalAI(
        api_key="", log_path=Path("logs/evaluation.jsonl")
    ).generate_guidance(owner, plan, "Help with medication")
    results.append(
        record(
            "missing_key_handling",
            missing_key.error == "missing_api_key" and not missing_key.used_ai,
            f"error={missing_key.error}, used_ai={missing_key.used_ai}",
        )
    )

    empty_question = PawPalAI(
        client=FakeClient(), log_path=Path("logs/evaluation.jsonl")
    ).generate_guidance(owner, plan, "   ")
    results.append(
        record(
            "empty_question_validation",
            empty_question.error == "empty_question",
            f"error={empty_question.error}",
        )
    )

    unrelated_owner, unrelated_plan = make_plan("other", "Unrelated task")
    no_context = PawPalAI(
        api_key="", log_path=Path("logs/evaluation.jsonl")
    ).generate_guidance(unrelated_owner, unrelated_plan, "Explain quantum networking")
    results.append(
        record(
            "no_context_handling",
            no_context.error == "no_context" and not no_context.used_ai,
            f"error={no_context.error}, sources={len(no_context.sources)}",
        )
    )

    return results


def print_summary(results: list[EvaluationResult]) -> None:
    print("PawPal reliability evaluation")
    print("=" * 31)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status:4} | {result.name:30} | {result.detail}")
    passed = sum(result.passed for result in results)
    print("-" * 31)
    print(f"Passed: {passed}/{len(results)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for a machine-readable JSON result file.",
    )
    args = parser.parse_args()

    results = run_evaluation()
    print_summary(results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps([asdict(result) for result in results], indent=2),
            encoding="utf-8",
        )

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
