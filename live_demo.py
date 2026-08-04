"""Run one live, grounded PawPal example with the configured Claude model."""

from __future__ import annotations

import json

from pawpal_ai import PawPalAI
from pawpal_system import Owner, Pet, Task


def main() -> int:
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="cat")
    task = Task("Medication", "daily", 10, 3)
    pet.add_task(task)
    owner.add_pet(pet)

    service = PawPalAI()
    question = "How can I make the medication reminder easier to follow?"
    result = service.generate_guidance(owner, [task], question)

    print(
        json.dumps(
            {
                "input": question,
                "model": service.model,
                "used_ai": result.used_ai,
                "guardrail_triggered": result.guardrail_triggered,
                "confidence": result.confidence,
                "sources": [source.id for source in result.sources],
                "error": result.error,
                "answer": result.answer,
            },
            indent=2,
        )
    )
    return 0 if result.used_ai else 1


if __name__ == "__main__":
    raise SystemExit(main())
