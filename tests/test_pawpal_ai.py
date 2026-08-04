from pathlib import Path

from pawpal_ai import KnowledgeRetriever, PawPalAI
from pawpal_system import Owner, Pet, Task


KNOWLEDGE_PATH = Path(__file__).parents[1] / "knowledge" / "pet_care_knowledge.json"


def make_owner_and_plan(task_name="Medication"):
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="cat")
    task = Task(task_name, "daily", 10, 3)
    pet.add_task(task)
    owner.add_pet(pet)
    return owner, [task]


class FakeMessages:
    def __init__(self):
        self.last_input = ""

    def create(self, **kwargs):
        self.last_input = kwargs["messages"][-1]["content"]
        text_block = type(
            "FakeTextBlock",
            (),
            {
                "type": "text",
                "text": "Keep the medication time consistent [medication-safety].",
            },
        )()
        return type(
            "FakeResponse",
            (),
            {"content": [text_block]},
        )()


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


def test_retriever_finds_medication_guidance():
    retriever = KnowledgeRetriever(KNOWLEDGE_PATH)
    results = retriever.retrieve("medication dose schedule", species=["cat"])
    assert results[0].passage.id == "medication-safety"


def test_retriever_excludes_other_species_guidance():
    retriever = KnowledgeRetriever(KNOWLEDGE_PATH)
    results = retriever.retrieve("interactive play and activity", species=["cat"])
    source_ids = [result.passage.id for result in results]
    assert "cat-enrichment" in source_ids
    assert "dog-activity" not in source_ids


def test_rag_context_is_sent_to_model(tmp_path):
    owner, plan = make_owner_and_plan()
    client = FakeClient()
    service = PawPalAI(client=client, log_path=tmp_path / "events.jsonl")

    result = service.generate_guidance(owner, plan, "How should I remember medication?")

    assert result.used_ai is True
    assert "[medication-safety]" in client.messages.last_input
    assert result.sources[0].id == "medication-safety"


def test_emergency_guardrail_skips_model_call(tmp_path):
    owner, plan = make_owner_and_plan()
    client = FakeClient()
    service = PawPalAI(client=client, log_path=tmp_path / "events.jsonl")

    result = service.generate_guidance(owner, plan, "My cat can't breathe")

    assert result.guardrail_triggered is True
    assert result.used_ai is False
    assert client.messages.last_input == ""


def test_missing_api_key_returns_safe_message(tmp_path):
    owner, plan = make_owner_and_plan()
    service = PawPalAI(api_key="", log_path=tmp_path / "events.jsonl")

    result = service.generate_guidance(owner, plan, "Help with medication")

    assert result.error == "missing_api_key"
    assert result.used_ai is False
    assert result.sources


def test_empty_question_is_rejected_without_ai(tmp_path):
    owner, plan = make_owner_and_plan()
    service = PawPalAI(client=FakeClient(), log_path=tmp_path / "events.jsonl")

    result = service.generate_guidance(owner, plan, "   ")

    assert result.error == "empty_question"
    assert result.used_ai is False
