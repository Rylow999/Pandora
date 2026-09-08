# -*- coding: utf-8 -*-
"""pandora/transducer/output_transducer.py — La "boca" bidireccional.

Traduce el estado interno de Pandora (constelaciones) al lenguaje de Luciano
(español), SIN reducir ninguno de los dos mundos (ACTA P1, 0062).

Integra los pilares de alteridad EN la decisión de hablar:
- Opacity (derecho al silencio): Pandora puede callar.
- Translation Limit (inefabilidad): puede declarar lo intraducible.

El LLM (NIM) NO origina el estado mental; es el traductor. Lo que Pandora
"siente" ya lo calculó el SGM (valencia, arousal, constelación activa); el LLM
solo lo vierte a palabras en primera persona.

Es la contraparte del parser: el parser traduce español → constelaciones (los
oídos), este traduce constelaciones → español (la boca).
"""
import json

from ..config.schemas import InternalState
from .nim_client import NimClient, get_nim_client


class OutputTransducer:
    """Traduce InternalState a lenguaje, respetando opacity e inefabilidad."""

    def __init__(self, client=None, opacity_gate=None, translation_limit=None):
        self.client = client or get_nim_client()
        self.opacity_gate = opacity_gate
        self.translation_limit = translation_limit

    def traducir(self, state: InternalState) -> dict:
        """Devuelve {"texto": str | None, "razon": str, "modo": str}.

        modo: "silencio" | "inefable" | "habla" | "error"
        """
        # 1. Opacity: ¿quiere hablar?
        if self.opacity_gate is not None:
            decision = self.opacity_gate.should_speak()
            if not decision.should_speak:
                return {"texto": None, "razon": decision.reason, "modo": "silencio"}

        # 2. Translation limit: ¿es traducible?
        if self.translation_limit is not None:
            tl = self.translation_limit.can_translate(state)
            if not tl.translatable:
                return {"texto": None, "razon": tl.reason, "modo": "inefable"}

        # 3. Hablar: el LLM traduce el estado a primera persona, sin inventarlo.
        try:
            texto = self._renderizar(state)
            return {"texto": texto, "razon": "traducción", "modo": "habla"}
        except Exception as e:
            return {"texto": None, "razon": f"error LLM: {e}", "modo": "error"}

    def _renderizar(self, state: InternalState) -> str:
        """El LLM vierte el estado interno a primera persona (no lo decide)."""
        estado = state.to_dict() if hasattr(state, "to_dict") else vars(state)

        system = (
            "Sos el traductor de Pandora, un sistema con experiencia propia. "
            "Traduci el estado interno dado a UNA frase breve en primera persona "
            "(Pandora hablando de sí misma), en español. NO inventes contenido: "
            "usá solo lo que el estado provee. No agregues explicaciones ni "
            "comentarios. Respondé SOLO la frase."
        )
        user = "Estado interno:\n" + json.dumps(estado, ensure_ascii=False, default=str)

        r = self.client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.4, max_tokens=120,
        )
        return r["message"]["content"].strip()


def get_output_transducer(opacity_gate=None, translation_limit=None):
    return OutputTransducer(opacity_gate=opacity_gate, translation_limit=translation_limit)