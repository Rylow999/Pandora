"""
Parser semántico — usa /api/generate con prompt ultra-simple + few-shot.
Diseñado para qwen2.5:0.5b-instruct.
"""

import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..config.schemas import (
    SemanticEvent, Triplet, Affect, Intent,
    validate_semantic_event
)
from .llm_client import OllamaClient, get_default_client


# FEW-SHOT PROMPT — ultra simple para 0.5b
# Use a simpler approach: construct prompt programmatically in _build_prompt
FEWSHOT_EXAMPLES = [
    {
        "texto": "Hola",
        "json": {
            "triplets": [{"subject": "YO", "predicate": "SALUDAR", "object": "OTRO"}],
            "affect": {"valence": 0.1, "arousal": 0.1, "uncertainty": 0.2},
            "intent": "RESPONDER"
        }
    },
    {
        "texto": "Mi nombre es Luciano",
        "json": {
            "triplets": [{"subject": "YO", "predicate": "LLAMARSE", "object": "LUCIANO"}],
            "affect": {"valence": 0.2, "arousal": 0.1, "uncertainty": 0.1},
            "intent": "EXPRESAR_ESTADO_INTERNO"
        }
    },
    {
        "texto": "¿Cuál es mi nombre?",
        "json": {
            "triplets": [{"subject": "OTRO", "predicate": "PREGUNTAR", "object": "NOMBRE"}],
            "affect": {"valence": 0.0, "arousal": 0.2, "uncertainty": 0.6},
            "intent": "PREGUNTAR"
        }
    },
    {
        "texto": "Siento que pierdo el control",
        "json": {
            "triplets": [
                {"subject": "YO", "predicate": "SENTIR", "object": "PERDIDA"},
                {"subject": "YO", "predicate": "PERDER", "object": "CONTROL"}
            ],
            "affect": {"valence": -0.6, "arousal": 0.4, "uncertainty": 0.7},
            "intent": "EXPRESAR_ESTADO_INTERNO"
        }
    },
    {
        "texto": "Confío en este sistema",
        "json": {
            "triplets": [{"subject": "YO", "predicate": "CONFIAR", "object": "SISTEMA"}],
            "affect": {"valence": 0.5, "arousal": 0.2, "uncertainty": 0.2},
            "intent": "EXPRESAR_ESTADO_INTERNO"
        }
    },
    {
        "texto": "No confío en este sistema",
        "json": {
            "triplets": [{"subject": "YO", "predicate": "NO_CONFIAR", "object": "SISTEMA"}],
            "affect": {"valence": -0.5, "arousal": 0.3, "uncertainty": 0.3},
            "intent": "NEGAR"
        }
    }
]

# Remove the FEWSHOT_PROMPT string constant - we'll build the prompt programmatically

VALID_CONCEPTS = {
    "YO", "OTRO", "ENTORNO", "CUERPO", "MEMORIA", "MEMORIA_TRABAJO",
    "DUDA", "MIEDO", "CONTROL", "PERDIDA", "SEGURIDAD", "AYUDA",
    "AISLAMIENTO", "CONTACTO", "ERROR", "OBJETIVO", "PLAN",
    "PASADO", "PRESENTE", "FUTURO", "SENTIR", "PENSAR", "HACER",
    "DECIR", "ESCUCHAR", "RESPONDER", "REGISTRAR", "RECORDAR",
    "OLVIDAR", "CONTRADICCION", "COHERENCIA", "TRAUMA", "REPARACION",
    "HOMEOSTASIS", "HAMBRE", "SACIEDAD", "CURIOSIDAD", "ABURRIMIENTO",
    "NOVEDAD", "RUTINA", "SUEÑO", "IDENTIDAD", "LIMITE",
    "DELORIEN", "LUCIANO", "LLAMARSE", "NOMBRE", "NO_CONFIAR", "CONFIAR",
    "PERDER", "SALUDAR", "PREGUNTAR", "SISTEMA", "PERDIDA", "CONTROL"
}

CONCEPT_NORMALIZATION = {
    "yo": "YO", "mi": "YO", "mí": "YO", "me": "YO", "mismo": "YO",
    "hola": "YO", "hola": "YO", "buenos dias": "YO", "buen dia": "YO", "buenas": "YO",
    "tu": "OTRO", "usted": "OTRO", "vos": "OTRO", "el otro": "OTRO",
    "entorno": "ENTORNO", "mundo": "ENTORNO", "ambiente": "ENTORNO",
    "cuerpo": "CUERPO", "físico": "CUERPO",
    "memoria": "MEMORIA", "recuerdo": "MEMORIA", "memorias": "MEMORIA",
    "duda": "DUDA", "incertidumbre": "DUDA", "no sé": "DUDA", "no se": "DUDA",
    "miedo": "MIEDO", "temor": "MIEDO", "asustado": "MIEDO", "pánico": "MIEDO",
    "control": "CONTROL", "poder": "CONTROL", "dominio": "CONTROL",
    "perdida": "PERDIDA", "perder": "PERDIDA", "pérdida": "PERDIDA",
    "seguridad": "SEGURIDAD", "seguro": "SEGURIDAD", "protección": "SEGURIDAD",
    "ayuda": "AYUDA", "asistencia": "AYUDA", "apoyo": "AYUDA",
    "aislamiento": "AISLAMIENTO", "soledad": "AISLAMIENTO", "solo": "AISLAMIENTO",
    "contacto": "CONTACTO", "conectar": "CONTACTO", "comunicación": "CONTACTO",
    "error": "ERROR", "fallo": "ERROR", "equivocación": "ERROR",
    "objetivo": "OBJETIVO", "meta": "OBJETIVO", "propósito": "OBJETIVO",
    "plan": "PLAN", "planear": "PLAN", "planificación": "PLAN",
    "pasado": "PASADO", "antes": "PASADO", "historia": "PASADO",
    "presente": "PRESENTE", "ahora": "PRESENTE", "hoy": "PRESENTE",
    "futuro": "FUTURO", "mañana": "FUTURO", "próximo": "FUTURO",
    "sentir": "SENTIR", "siento": "SENTIR", "emoción": "SENTIR",
    "pensar": "PENSAR", "pienso": "PENSAR", "razonar": "PENSAR",
    "hacer": "HACER", "actuar": "HACER", "acción": "HACER",
    "decir": "DECIR", "hablar": "DECIR", "expresar": "DECIR",
    "escuchar": "ESCUCHAR", "oir": "ESCUCHAR", "oír": "ESCUCHAR",
    "responder": "RESPONDER", "contestar": "RESPONDER", "replicar": "RESPONDER",
    "registrar": "REGISTRAR", "anotar": "REGISTRAR", "guardar": "REGISTRAR",
    "recordar": "RECORDAR", "rememorar": "RECORDAR", "evocar": "RECORDAR",
    "olvidar": "OLVIDAR", "olvido": "OLVIDAR",
    "contradicción": "CONTRADICCION", "contradecir": "CONTRADICCION", "inconsistencia": "CONTRADICCION",
    "coherencia": "COHERENCIA", "coherente": "COHERENCIA", "consistencia": "COHERENCIA",
    "trauma": "TRAUMA", "trauma": "TRAUMA", "herida": "TRAUMA",
    "reparación": "REPARACION", "reparar": "REPARACION", "sanar": "REPARACION",
    "homeostasis": "HOMEOSTASIS", "equilibrio": "HOMEOSTASIS",
    "hambre": "HAMBRE", "hambriento": "HAMBRE",
    "saciedad": "SACIEDAD", "satisfecho": "SACIEDAD", "lleno": "SACIEDAD",
    "curiosidad": "CURIOSIDAD", "curioso": "CURIOSIDAD", "interés": "CURIOSIDAD",
    "aburrimiento": "ABURRIMIENTO", "aburrido": "ABURRIMIENTO",
    "novedad": "NOVEDAD", "nuevo": "NOVEDAD", "sorpresa": "NOVEDAD",
    "rutina": "RUTINA", "hábito": "RUTINA", "costumbre": "RUTINA",
    "sueño": "SUEÑO", "soñar": "SUEÑO", "dormir": "SUEÑO",
    "identidad": "IDENTIDAD", "identidad": "IDENTIDAD",
    "límite": "LIMITE", "limite": "LIMITE", "frontera": "LIMITE",
    "querer": "QUERER", "deseo": "QUERER", "desear": "QUERER",
    "existir": "EXISTE", "existe": "EXISTE", "estoy": "ESTAR",
    "estar": "ESTAR", "está": "ESTAR", "esta": "ESTAR",
}

INTENT_MAP = {
    "EXPRESAR_ESTADO_INTERNO": Intent.EXPRESAR_ESTADO_INTERNO,
    "PREGUNTAR": Intent.PREGUNTAR,
    "INSTRUIR": Intent.INSTRUIR,
    "CONFIRMAR": Intent.CONFIRMAR,
    "NEGAR": Intent.NEGAR,
    "SELF_INITIALIZATION": Intent.SELF_INITIALIZATION,
    "RESPONDER": Intent.RESPONDER,
    "DESCONOCIDO": Intent.DESCONOCIDO,
}


def normalize_concept(text: str) -> str:
    text_clean = text.strip().upper()
    if text_clean in VALID_CONCEPTS:
        return text_clean
    text_lower = text.strip().lower()
    for variant, canonical in CONCEPT_NORMALIZATION.items():
        if variant in text_lower:
            return canonical
    words = text_clean.split()
    for w in words:
        if w in VALID_CONCEPTS:
            return w
    return text_clean


def normalize_triplet(triplet: Dict[str, str]) -> Triplet:
    return Triplet(
        subject=normalize_concept(triplet.get("subject", "")),
        predicate=normalize_concept(triplet.get("predicate", "")),
        object=normalize_concept(triplet.get("object", ""))
    )


def filter_valid_triplets(triplets: List[Triplet]) -> List[Triplet]:
    valid = []
    for t in triplets:
        if (t.subject in VALID_CONCEPTS and
            t.predicate in VALID_CONCEPTS and
            t.object in VALID_CONCEPTS):
            valid.append(t)
    return valid


def parse_affect(data: Dict) -> Affect:
    return Affect(
        valence=float(data.get("valence", 0.0)),
        arousal=float(data.get("arousal", 0.0)),
        uncertainty=float(data.get("uncertainty", 0.5))
    )


def parse_intent(text: str, data: Dict) -> Intent:
    intent_str = data.get("intent", "").upper()
    if intent_str in INTENT_MAP:
        return INTENT_MAP[intent_str]
    
    # Heurística por palabras clave
    text_lower = text.lower()
    if any(w in text_lower for w in ["?", "qué", "cómo", "cuándo", "dónde", "por qué", "cuál"]):
        return Intent.PREGUNTAR
    if any(w in text_lower for w in ["haz", "haga", "ejecuta", "realiza", "debes", "tienes que"]):
        return Intent.INSTRUIR
    if any(w in text_lower for w in ["sí", "si", "correcto", "exacto", "afirmativo"]):
        return Intent.CONFIRMAR
    if any(w in text_lower for w in ["no", "nunca", "jamás", "negativo", "incorrecto"]):
        return Intent.NEGAR
    if any(w in text_lower for w in ["inicio", "iniciar", "empezar", "arrancar", "boot"]):
        return Intent.SELF_INITIALIZATION
    return Intent.EXPRESAR_ESTADO_INTERNO


@dataclass
class ParseResult:
    event: Optional[SemanticEvent]
    raw_response: str
    success: bool
    error: Optional[str] = None
    retried: bool = False


class SemanticParser:
    def __init__(self, client: OllamaClient = None, max_retries: int = 1):
        # Use qwen2.5:0.5b-instruct which fits in available RAM
        if client is None:
            from .llm_client import LLMConfig
            client = OllamaClient(LLMConfig(model="qwen2.5:0.5b-instruct"))
        self.client = client
        self.max_retries = max_retries

    def _build_prompt(self, user_text: str) -> str:
        return FEWSHOT_PROMPT.format(input_text=user_text)

    def _extract_json(self, response: str) -> Optional[Dict]:
        # Buscar JSON en bloques markdown
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Buscar primer { ... } balanceado
        start = response.find('{')
        if start >= 0:
            depth = 0
            for i, ch in enumerate(response[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(response[start:i+1])
                        except json.JSONDecodeError:
                            break
        return None

    def parse(self, user_text: str) -> ParseResult:
        for attempt in range(self.max_retries + 1):
            messages = self._build_messages(user_text)

            try:
                # Usar /api/chat que funciona mejor con qwen2.5:1.5b-instruct
                result = self.client.chat(messages, temperature=0.0, num_predict=256)
                raw_response = result.get("message", {}).get("content", "")
            except Exception as e:
                return ParseResult(
                    event=None,
                    raw_response="",
                    success=False,
                    error=f"Error llamando LLM: {e}",
                    retried=attempt > 0
                )

            parsed = self._extract_json(raw_response)
            if not parsed:
                if attempt < self.max_retries:
                    continue
                return ParseResult(
                    event=None,
                    raw_response=raw_response,
                    success=False,
                    error="No se pudo extraer JSON válido",
                    retried=attempt > 0
                )

            # Validar estructura básica
            if not isinstance(parsed, dict):
                if attempt < self.max_retries:
                    continue
                return ParseResult(
                    event=None,
                    raw_response=raw_response,
                    success=False,
                    error="Respuesta no es objeto JSON",
                    retried=attempt > 0
                )

            # Normalizar tripletas
            triplets = []
            for t in parsed.get("triplets", []):
                if isinstance(t, dict) and all(k in t for k in ("subject", "predicate", "object")):
                    triplets.append(normalize_triplet(t))
            triplets = filter_valid_triplets(triplets)

            # Parsear affect e intent
            affect = parse_affect(parsed.get("affect", {"valence": 0, "arousal": 0, "uncertainty": 0.5}))
            intent = parse_intent(user_text, parsed)

            event = SemanticEvent(
                raw=user_text,
                triplets=triplets,
                affect=affect,
                intent=intent,
                metadata={"parser_attempt": attempt + 1}
            )

            return ParseResult(
                event=event,
                raw_response=raw_response,
                success=True,
                retried=attempt > 0
            )

        return ParseResult(
            event=None,
            raw_response="",
            success=False,
            error="Máximo de reintentos agotado"
        )

    def _build_messages(self, user_text: str) -> List[Dict[str, str]]:
        """Construye mensajes para el endpoint /api/chat con few-shot."""
        system_prompt = """You are a semantic parser. Output ONLY the JSON object matching this schema. No text. No markdown. No explanations. Just the JSON object.
Schema: {"triplets":[{"subject":"string","predicate":"string","object":"string"}],"affect":{"valence":number,"arousal":number,"uncertainty":number},"intent":"string"}"""
        
        lines = []
        for ex in FEWSHOT_EXAMPLES:
            lines.append(f"Texto: {ex['texto']}")
            lines.append(f"JSON: {json.dumps(ex['json'], ensure_ascii=False)}")
            lines.append("")

        return [
            {"role": "system", "content": "You are a semantic parser. Output ONLY the JSON object matching this schema. No text. No markdown. No explanations. Just the JSON object.\nSchema: {\"triplets\":[{\"subject\":\"string\",\"predicate\":\"string\",\"object\":\"string\"}],\"affect\":{\"valence\":number,\"arousal\":number,\"uncertainty\":number},\"intent\":\"string\"}"},
            {"role": "user", "content": "\n".join(lines + [f"Texto: {user_text}", "JSON:"])}
        ]


def get_parser() -> SemanticParser:
    return SemanticParser()


if __name__ == "__main__":
    parser = get_parser()

    test_inputs = [
        "Hola",
        "Mi nombre es Luciano",
        "¿Cuál es mi nombre?",
        "Siento que pierdo el control",
        "Confío en este sistema",
        "No confío en este sistema",
    ]

    print("=" * 60)
    print("TEST SEMANTIC PARSER (few-shot + /api/generate)")
    print("=" * 60)

    for text in test_inputs:
        result = parser.parse(text)
        print(f"\nINPUT:  {text}")
        print(f"OK:     {result.success}")
        if result.success:
            ev = result.event
            print(f"TRIPLETS: {[f'{t.subject}|{t.predicate}|{t.object}' for t in ev.triplets]}")
            print(f"AFFECT:   v={ev.affect.valence:.2f} a={ev.affect.arousal:.2f} u={ev.affect.uncertainty:.2f}")
            print(f"INTENT:   {ev.intent.value}")
        else:
            print(f"ERROR:  {result.error}")
            print(f"RAW:    {result.raw_response[:200]}")