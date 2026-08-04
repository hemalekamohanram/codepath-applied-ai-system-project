from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from dotenv import load_dotenv

from pawpal_system import Owner, Task


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "knowledge" / "pet_care_knowledge.json"
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "ai_events.jsonl"
DEFAULT_MODEL = "claude-haiku-4-5"

load_dotenv(PROJECT_ROOT / ".env")

EMERGENCY_PHRASES = (
    "trouble breathing",
    "can't breathe",
    "cannot breathe",
    "collapsed",
    "uncontrolled bleeding",
    "seizure",
    "ate poison",
    "swallowed poison",
    "toxic substance",
)

STOP_WORDS = {
    "a", "an", "and", "are", "can", "for", "how", "i", "in", "is", "it",
    "make", "my", "of", "on", "or", "the", "this", "to", "what", "with",
}


@dataclass(frozen=True)
class KnowledgePassage:
    id: str
    species: str
    topics: tuple[str, ...]
    content: str
    source: str


@dataclass(frozen=True)
class RetrievedPassage:
    passage: KnowledgePassage
    score: float


@dataclass
class CareGuidance:
    answer: str
    sources: list[KnowledgePassage]
    confidence: float
    used_ai: bool
    guardrail_triggered: bool = False
    error: Optional[str] = None


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if token not in STOP_WORDS and len(token) > 1
    }


class KnowledgeRetriever:
    """Small local keyword retriever for the curated PawPal knowledge base."""

    def __init__(self, knowledge_path: Path | str = DEFAULT_KNOWLEDGE_PATH) -> None:
        self.knowledge_path = Path(knowledge_path)
        self.passages = self._load_passages()

    def _load_passages(self) -> list[KnowledgePassage]:
        with self.knowledge_path.open(encoding="utf-8") as knowledge_file:
            rows = json.load(knowledge_file)
        return [
            KnowledgePassage(
                id=row["id"],
                species=row["species"],
                topics=tuple(row["topics"]),
                content=row["content"],
                source=row["source"],
            )
            for row in rows
        ]

    def retrieve(
        self,
        query: str,
        species: Iterable[str],
        top_k: int = 3,
    ) -> list[RetrievedPassage]:
        query_tokens = _tokens(query)
        pet_species = {item.lower() for item in species}
        ranked: list[RetrievedPassage] = []

        for passage in self.passages:
            if passage.species != "all" and passage.species not in pet_species:
                continue
            passage_tokens = _tokens(" ".join(passage.topics) + " " + passage.content)
            overlap = len(query_tokens & passage_tokens)
            if overlap == 0:
                continue
            species_bonus = 2 if passage.species in pet_species else 0
            general_bonus = 1 if passage.species == "all" else 0
            score = float(overlap * 2 + species_bonus + general_bonus)
            ranked.append(RetrievedPassage(passage=passage, score=score))

        ranked.sort(key=lambda item: (-item.score, item.passage.id))
        return ranked[:top_k]


class PawPalAI:
    """Retrieves care context, calls the model, and applies safety guardrails."""

    def __init__(
        self,
        retriever: Optional[KnowledgeRetriever] = None,
        client: Any = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        log_path: Path | str = DEFAULT_LOG_PATH,
    ) -> None:
        self.retriever = retriever or KnowledgeRetriever()
        self.client = client
        self.api_key = api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
        self.log_path = Path(log_path)

    def generate_guidance(
        self,
        owner: Owner,
        plan: list[Task],
        question: str,
    ) -> CareGuidance:
        clean_question = question.strip()
        if not clean_question:
            return CareGuidance(
                answer="Enter a question about the care plan before asking PawPal AI.",
                sources=[],
                confidence=0.0,
                used_ai=False,
                error="empty_question",
            )

        if len(clean_question) > 500:
            return CareGuidance(
                answer="Please shorten the question to 500 characters or fewer.",
                sources=[],
                confidence=0.0,
                used_ai=False,
                error="question_too_long",
            )

        lowered = clean_question.lower()
        if any(phrase in lowered for phrase in EMERGENCY_PHRASES):
            result = CareGuidance(
                answer=(
                    "This may be an emergency. Contact a veterinarian or local emergency "
                    "clinic now. PawPal cannot diagnose or provide emergency instructions."
                ),
                sources=[],
                confidence=1.0,
                used_ai=False,
                guardrail_triggered=True,
            )
            self._write_log("guardrail", [], result)
            return result

        species = [pet.species for pet in owner.get_pets()]
        task_names = [task.get_routine_name() for task in plan]
        retrieval_query = " ".join([clean_question, *task_names])
        retrieved = self.retriever.retrieve(retrieval_query, species=species)
        sources = [item.passage for item in retrieved]

        if not sources:
            result = CareGuidance(
                answer=(
                    "I could not find enough relevant information in the PawPal knowledge "
                    "base. Try asking about feeding, medication, walking, play, or grooming."
                ),
                sources=[],
                confidence=0.0,
                used_ai=False,
                error="no_context",
            )
            self._write_log("no_context", [], result)
            return result

        confidence = self._confidence(retrieved)
        if self.client is None and not self.api_key:
            result = CareGuidance(
                answer=(
                    "AI guidance is not configured. Set ANTHROPIC_API_KEY, restart the app, "
                    "and try again. The relevant knowledge sources are shown below."
                ),
                sources=sources,
                confidence=confidence,
                used_ai=False,
                error="missing_api_key",
            )
            self._write_log("configuration_error", sources, result)
            return result

        try:
            client = self.client or self._create_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=500,
                system=(
                    "You are PawPal, a careful pet-care planning assistant. Use only the "
                    "retrieved context. Explain the existing schedule; do not diagnose, "
                    "change medication instructions, or claim to replace a veterinarian. "
                    "Cite supporting passages with their bracketed IDs. If the context is "
                    "not enough, say what is missing. Keep the answer under 180 words."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": self._build_prompt(
                            clean_question, species, task_names, sources
                        ),
                    }
                ],
            )
            answer = "".join(
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            ).strip()
            if not answer:
                raise ValueError("The model returned an empty response.")

            result = CareGuidance(
                answer=answer,
                sources=sources,
                confidence=confidence,
                used_ai=True,
            )
            self._write_log("success", sources, result)
            return result
        except Exception as exc:
            result = CareGuidance(
                answer=(
                    "PawPal AI could not generate guidance right now. Your saved tasks and "
                    "deterministic schedule were not changed. Please try again later."
                ),
                sources=sources,
                confidence=confidence,
                used_ai=False,
                error=type(exc).__name__,
            )
            self._write_log("api_error", sources, result)
            return result

    def _create_client(self) -> Any:
        from anthropic import Anthropic

        return Anthropic(api_key=self.api_key)

    @staticmethod
    def _confidence(retrieved: list[RetrievedPassage]) -> float:
        if not retrieved:
            return 0.0
        best_score = retrieved[0].score
        coverage_bonus = min(len(retrieved), 3) * 0.05
        return round(min(0.95, 0.45 + best_score / 20 + coverage_bonus), 2)

    @staticmethod
    def _build_prompt(
        question: str,
        species: list[str],
        task_names: list[str],
        sources: list[KnowledgePassage],
    ) -> str:
        context = "\n".join(
            f"[{source.id}] {source.content}" for source in sources
        )
        return (
            f"Pet species: {', '.join(species) or 'not provided'}\n"
            f"Scheduled tasks: {', '.join(task_names) or 'none'}\n"
            f"Owner question: {question}\n\n"
            f"Retrieved context:\n{context}"
        )

    def _write_log(
        self,
        event: str,
        sources: list[KnowledgePassage],
        result: CareGuidance,
    ) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "model": self.model,
            "source_ids": [source.id for source in sources],
            "confidence": result.confidence,
            "used_ai": result.used_ai,
            "guardrail_triggered": result.guardrail_triggered,
            "error": result.error,
        }
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(record) + "\n")
        except OSError:
            # Logging must never break the care-planning workflow.
            pass
