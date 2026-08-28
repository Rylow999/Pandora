"""
Schemas JSON — Contrato estricto entre LLM (transductor) y SGM (sustrato).

No se usa texto libre como representación final.
El LLM devuelve símbolos normalizados → SGM opera sobre HRR/omega.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Literal
from enum import Enum
import json


class Intent(str, Enum):
    """Intenciones reconocidas en el intercambio."""
    EXPRESAR_ESTADO_INTERNO = "EXPRESAR_ESTADO_INTERNO"
    PREGUNTAR = "PREGUNTAR"
    INSTRUIR = "INSTRUIR"
    CONFIRMAR = "CONFIRMAR"
    NEGAR = "NEGAR"
    SELF_INITIALIZATION = "SELF_INITIALIZATION"
    RESPONDER = "RESPONDER"
    DESCONOCIDO = "DESCONOCIDO"


@dataclass
class Affect:
    """Valencia, activación e incertidumbre del evento."""
    valence: float      # -1.0 (muy negativo) a 1.0 (muy positivo)
    arousal: float      # 0.0 (calma) a 1.0 (alta activación)
    uncertainty: float  # 0.0 (certeza) a 1.0 (máxima incertidumbre)

    def __post_init__(self):
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.uncertainty = max(0.0, min(1.0, self.uncertainty))

    def to_dict(self):
        return asdict(self)


@dataclass
class Triplet:
    """Tripleta semántica normalizada: sujeto - predicado - objeto."""
    subject: str
    predicate: str
    object: str

    def to_dict(self):
        return asdict(self)

    def normalized_key(self) -> str:
        """Clave normalizada para deduplicación/índice."""
        return f"{self.subject.upper()}|{self.predicate.upper()}|{self.object.upper()}"


@dataclass
class SemanticEvent:
    """
    Evento semántico parseado desde texto humano.
    Entrada canónica al SGM.
    """
    raw: str                    # Texto original del usuario
    triplets: List[Triplet]     # Tripletas extraídas y normalizadas
    affect: Affect              # Estado afectivo estimado
    intent: Intent              # Intención clasificada
    metadata: dict = field(default_factory=dict)  # Extensible

    def to_dict(self):
        return {
            "raw": self.raw,
            "triplets": [t.to_dict() for t in self.triplets],
            "affect": self.affect.to_dict(),
            "intent": self.intent.value,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SemanticEvent':
        return cls(
            raw=data["raw"],
            triplets=[Triplet(**t) for t in data["triplets"]],
            affect=Affect(**data["affect"]),
            intent=Intent(data["intent"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class InternalState:
    """
    Estado dominante del SGM tras un tick.
    Salida canónica hacia el articulador LLM.
    """
    active_nodes: List[str]         # Nodos con mayor activación/vitalidad
    triplets: List[Triplet]         # Relaciones dominantes en el grafo
    valence: float                  # Valencia media del sistema
    arousal: float                  # Arousal medio
    doubt: float                    # Nivel de duda (0-1)
    contradiction: float            # Nivel de contradicción (0-1)
    intent: Intent = Intent.RESPONDER
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "active_nodes": self.active_nodes,
            "triplets": [t.to_dict() for t in self.triplets],
            "valence": self.valence,
            "arousal": self.arousal,
            "doubt": self.doubt,
            "contradiction": self.contradiction,
            "intent": self.intent.value,
            "metadata": self.metadata
        }


# --- Utilidades de validación ---

REQUIRED_EVENT_FIELDS = {"raw", "triplets", "affect", "intent"}
REQUIRED_STATE_FIELDS = {"active_nodes", "triplets", "valence", "arousal", "doubt", "contradiction"}


def validate_semantic_event(data: dict) -> tuple[bool, Optional[str]]:
    """Valida que un dict tenga la estructura de SemanticEvent."""
    if not isinstance(data, dict):
        return False, "No es un dict"
    missing = REQUIRED_EVENT_FIELDS - set(data.keys())
    if missing:
        return False, f"Campos faltantes: {missing}"
    # Validar triplets
    for t in data.get("triplets", []):
        if not all(k in t for k in ("subject", "predicate", "object")):
            return False, f"Triplet inválido: {t}"
    # Validar affect
    aff = data.get("affect", {})
    if not all(k in aff for k in ("valence", "arousal", "uncertainty")):
        return False, f"Affect incompleto: {aff}"
    # Validar intent
    if data.get("intent") not in [i.value for i in Intent]:
        return False, f"Intent desconocido: {data.get('intent')}"
    return True, None


def validate_internal_state(data: dict) -> tuple[bool, Optional[str]]:
    """Valida que un dict tenga la estructura de InternalState."""
    if not isinstance(data, dict):
        return False, "No es un dict"
    missing = REQUIRED_STATE_FIELDS - set(data.keys())
    if missing:
        return False, f"Campos faltantes: {missing}"
    return True, None


# --- Prompts canónicos (para referencia) ---

PARSER_PROMPT = """Sos un parser semántico para un sistema cognitivo llamado SGM.

Tu tarea NO es conversar.
Tu tarea es convertir el texto del usuario en una representación simbólica estricta.

Devuelve SOLO JSON válido con esta estructura exacta:

{{
  "triplets": [
    {{"subject": "string", "predicate": "string", "object": "string"}}
  ],
  "affect": {{
    "valence": float entre -1 y 1,
    "arousal": float entre 0 y 1,
    "uncertainty": float entre 0 y 1
  }},
  "intent": "string (uno de: EXPRESAR_ESTADO_INTERNO, PREGUNTAR, INSTRUIR, CONFIRMAR, NEGAR, SELF_INITIALIZATION, RESPONDER, DESCONOCIDO)"
}}

Reglas:
- No inventes conceptos si no aparecen en el texto.
- Normaliza los conceptos: mayúsculas, formas simples y estables (YO, MEMORIA, DUDA, ENTORNO, etc.).
- Si el texto es ambiguo, asigna uncertainty alta.
- valence: negativo = malestar/amenaza, positivo = satisfacción/seguridad.
- arousal: qué tan activado está el sistema ante el input.
- intent: clasifica la función pragmática del mensaje.

Texto del usuario:
{input_text}
"""

RENDERER_PROMPT = """Sos la capa de articulación verbal de un sistema cognitivo.

No inventes estados internos que no estén en el JSON.
No hagas terapia si no se especifica intención terapéutica.
Convertí el estado interno en lenguaje natural breve, directo, sin florituras.

Estado interno:
{internal_state_json}

Responde solo con la frase final.
"""


if __name__ == "__main__":
    # Test rápido de serialización
    ev = SemanticEvent(
        raw="Hola, quiero registrar este inicio.",
        triplets=[
            Triplet(subject="YO", predicate="QUERER", object="REGISTRAR"),
            Triplet(subject="YO", predicate="EXISTE", object="PRESENTE"),
        ],
        affect=Affect(valence=0.1, arousal=0.2, uncertainty=0.3),
        intent=Intent.SELF_INITIALIZATION
    )
    print(json.dumps(ev.to_dict(), indent=2, ensure_ascii=False))

    st = InternalState(
        active_nodes=["YO", "PRESENTE", "REGISTRO"],
        triplets=[Triplet(subject="YO", predicate="ESTAR", object="PRESENTE")],
        valence=0.1, arousal=0.2, doubt=0.1, contradiction=0.0
    )
    print(json.dumps(st.to_dict(), indent=2, ensure_ascii=False))