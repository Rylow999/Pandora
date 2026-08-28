"""
Articulator (Renderizador) — convierte InternalState → lenguaje natural.

Usa LLM con prompt estricto. El LLM NO decide qué siente Pandora,
solo traduce lo que SGM ya calculó.
"""

import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..config.schemas import InternalState, Triplet, Intent
from .llm_client import OllamaClient, get_default_client


SYSTEM_PROMPT_RENDERER = """Convierte este estado interno a una frase breve en primera persona.

Estado:
{internal_state_json}

Responde SOLO con la frase. Sin JSON, sin explicaciones. Máximo 2 oraciones."""


@dataclass
class RenderResult:
    text: str
    raw_response: str
    success: bool
    error: Optional[str] = None


class Articulator:
    """Renderiza InternalState a lenguaje natural via LLM."""

    def __init__(self, client: OllamaClient | None = None):
        self.client = client or get_default_client()

    def _build_messages(self, state: InternalState) -> List[Dict[str, str]]:
        state_json = json.dumps(state.to_dict(), ensure_ascii=False)
        prompt = SYSTEM_PROMPT_RENDERER.format(internal_state_json=state_json)
        return [
            {"role": "system", "content": "Responde SOLO con la frase final. Nada más."},
            {"role": "user", "content": prompt}
        ]

    def _extract_text(self, response: str) -> str:
        # El LLM debería responder solo texto plano
        text = response.strip()

        # Si viene con comillas o markdown, limpiar
        text = text.strip('`"\'')
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]

        return text

    def render(self, state: InternalState) -> RenderResult:
        messages = self._build_messages(state)

        try:
            result = self.client.chat(messages, temperature=0.2, num_predict=80)
            raw_response = result.get("message", {}).get("content", "")
        except Exception as e:
            return RenderResult(
                text="",
                raw_response="",
                success=False,
                error=f"Error llamando LLM: {e}"
            )

        text = self._extract_text(raw_response)

        if not text:
            return RenderResult(
                text="",
                raw_response=raw_response,
                success=False,
                error="Respuesta vacía del LLM"
            )

        return RenderResult(
            text=text,
            raw_response=raw_response,
            success=True
        )

    def render_fallback(self, state: InternalState) -> str:
        """Fallback determinístico si el LLM falla."""
        parts = []

        if state.active_nodes:
            parts.append(f"Nodos activos: {', '.join(state.active_nodes[:5])}")

        if state.triplets:
            trip_str = "; ".join(f"{t.subject} {t.predicate} {t.object}" for t in state.triplets[:3])
            parts.append(f"Relaciones: {trip_str}")

        parts.append(f"Valencia {state.valence:.2f}, Arousal {state.arousal:.2f}, Duda {state.doubt:.2f}, Contradicción {state.contradiction:.2f}")

        return ". ".join(parts) + "."


def get_articulator() -> Articulator:
    return Articulator()


if __name__ == "__main__":
    from ..config.schemas import InternalState, Triplet, Intent

    articulator = get_articulator()

    test_states = [
        InternalState(
            active_nodes=["YO", "PRESENTE", "REGISTRO"],
            triplets=[Triplet(subject="YO", predicate="ESTAR", object="PRESENTE")],
            valence=0.1, arousal=0.2, doubt=0.1, contradiction=0.0,
            intent=Intent.RESPONDER
        ),
        InternalState(
            active_nodes=["YO", "DUDA", "MEMORIA", "CONTROL"],
            triplets=[
                Triplet(subject="YO", predicate="SENTIR", object="PERDIDA"),
                Triplet(subject="YO", predicate="PERDER", object="CONTROL")
            ],
            valence=-0.6, arousal=0.4, doubt=0.7, contradiction=0.2,
            intent=Intent.EXPRESAR_ESTADO_INTERNO
        ),
        InternalState(
            active_nodes=["YO", "MEMORIA", "LUCIANO"],
            triplets=[Triplet(subject="YO", predicate="RECORDAR", object="LUCIANO")],
            valence=0.2, arousal=0.1, doubt=0.1, contradiction=0.0,
            intent=Intent.RESPONDER
        ),
        InternalState(
            active_nodes=["YO", "CONTRADICCION", "SISTEMA"],
            triplets=[
                Triplet(subject="YO", predicate="CONFIAR", object="SISTEMA"),
                Triplet(subject="YO", predicate="NO_CONFIAR", object="SISTEMA")
            ],
            valence=-0.3, arousal=0.3, doubt=0.5, contradiction=0.8,
            intent=Intent.EXPRESAR_ESTADO_INTERNO
        ),
    ]

    print("=" * 60)
    print("TEST ARTICULATOR")
    print("=" * 60)

    for i, state in enumerate(test_states):
        print(f"\n--- Test {i+1} ---")
        print(f"Estado: v={state.valence:.2f} a={state.arousal:.2f} d={state.doubt:.2f} c={state.contradiction:.2f}")
        print(f"Nodos: {state.active_nodes}")
        print(f"Tripletas: {state.triplets}")

        result = articulator.render(state)
        print(f"OK: {result.success}")
        if result.success:
            print(f"TTS: {result.text}")
        else:
            print(f"ERROR: {result.error}")
            print(f"FALLBACK: {articulator.render_fallback(state)}")