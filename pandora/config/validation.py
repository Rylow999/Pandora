"""
Input validation utilities for Pandora.
Validates HRR vectors, concepts, semantic events, and other inputs.
"""

from typing import List, Dict, Any, Optional, Set
import math
from ..config.schemas import SemanticEvent, Triplet, Affect, Intent


class ValidationError(Exception):
    """Error de validación de entrada."""
    pass


# Conceptos válidos según ontología
VALID_CONCEPTS: Set[str] = {
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


VALID_INTENTS: Set[str] = {
    "EXPRESAR_ESTADO_INTERNO", "PREGUNTAR", "INSTRUIR", "CONFIRMAR",
    "NEGAR", "SELF_INITIALIZATION", "RESPONDER", "DESCONOCIDO"
}


def validate_hrr_vector(vector: List[float], expected_dim: int = 128) -> bool:
    """
    Valida que un vector HRR sea válido.
    
    Args:
        vector: Vector a validar
        expected_dim: Dimensión esperada (default 128)
        
    Returns:
        True si es válido
        
    Raises:
        ValidationError: Si el vector no es válido
    """
    if not isinstance(vector, list):
        raise ValidationError(f"Vector debe ser lista, recibido {type(vector)}")
    
    if len(vector) != expected_dim:
        raise ValidationError(f"Vector dimensión {len(vector)} != esperada {expected_dim}")
    
    if not all(isinstance(x, (int, float)) for x in vector):
        raise ValidationError("Vector debe contener solo números")
    
    # Verificar que no sea todo ceros
    if all(x == 0.0 for x in vector):
        raise ValidationError("Vector no puede ser todo ceros")
    
    # Verificar que esté normalizado (aprox)
    norm = math.sqrt(sum(x * x for x in vector))
    if abs(norm - 1.0) > 0.2:
        raise ValidationError(f"Vector no normalizado: norm={norm:.4f}")
    
    return True


def validate_concept(concept: str) -> bool:
    """
    Valida que un concepto esté en la ontología.
    
    Args:
        concept: Concepto a validar
        
    Returns:
        True si es válido
        
    Raises:
        ValidationError: Si el concepto no es válido
    """
    if not isinstance(concept, str):
        raise ValidationError(f"Concepto debe ser string, recibido {type(concept)}")
    
    if not concept:
        raise ValidationError("Concepto no puede estar vacío")
    
    if concept not in VALID_CONCEPTS:
        raise ValidationError(f"Concepto '{concept}' no está en ontología válida")
    
    return True


def validate_triplet(triplet: Dict[str, str]) -> bool:
    """
    Valida una tripleta semántica.
    
    Args:
        triplet: Diccionario con subject, predicate, object
        
    Returns:
        True si es válido
        
    Raises:
        ValidationError: Si la tripleta no es válida
    """
    if not isinstance(triplet, dict):
        raise ValidationError(f"Triplet debe ser dict, recibido {type(triplet)}")
    
    required = {"subject", "predicate", "object"}
    missing = required - set(triplet.keys())
    if missing:
        raise ValidationError(f"Triplet faltan campos: {missing}")
    
    for key in required:
        validate_concept(triplet[key])
    
    return True


def validate_semantic_event(event: SemanticEvent) -> bool:
    """
    Valida un SemanticEvent completo.
    
    Args:
        event: Evento semántico a validar
        
    Returns:
        True si es válido
        
    Raises:
        ValidationError: Si el evento no es válido
    """
    if not isinstance(event, SemanticEvent):
        raise ValidationError(f"Event debe ser SemanticEvent, recibido {type(event)}")
    
    if not isinstance(event.raw, str):
        raise ValidationError("raw debe ser string")
    
    if not isinstance(event.triplets, list):
        raise ValidationError("triplets debe ser lista")
    
    for triplet in event.triplets:
        if not isinstance(triplet, Triplet):
            raise ValidationError(f"Cada triplet debe ser Triplet, recibido {type(triplet)}")
        validate_triplet({"subject": triplet.subject, "predicate": triplet.predicate, "object": triplet.object})
    
    if not isinstance(event.affect, Affect):
        raise ValidationError(f"Affect debe ser Affect, recibido {type(event.affect)}")
    
    # Validar rangos de affect
    if not -1.0 <= event.affect.valence <= 1.0:
        raise ValidationError(f"valence fuera de rango [-1,1]: {event.affect.valence}")
    if not 0.0 <= event.affect.arousal <= 1.0:
        raise ValidationError(f"arousal fuera de rango [0,1]: {event.affect.arousal}")
    if not 0.0 <= event.affect.uncertainty <= 1.0:
        raise ValidationError(f"uncertainty fuera de rango [0,1]: {event.affect.uncertainty}")
    
    if event.intent not in Intent:
        raise ValidationError(f"Intent '{event.intent}' no válido")
    
    return True


def validate_intent(intent: str) -> bool:
    """Valida que el intent sea válido."""
    if intent not in VALID_INTENTS:
        raise ValidationError(f"Intent '{intent}' no válido. Válidos: {VALID_INTENTS}")
    return True


if __name__ == "__main__":
    # Tests rápidos
    print("=== TEST VALIDACIÓN ===")
    
    # Test vector HRR
    try:
        validate_hrr_vector([0.1] * 128)
        print("✅ Vector HRR válido")
    except ValidationError as e:
        print(f"❌ Vector HRR: {e}")
    
    # Test concepto
    try:
        validate_concept("YO")
        print("✅ Concepto YO válido")
    except ValidationError as e:
        print(f"❌ Concepto: {e}")
    
    try:
        validate_concept("INVALIDO")
        print("✅ Concepto INVALIDO válido (inesperado)")
    except ValidationError as e:
        print(f"✅ Concepto INVALIDO rechazado correctamente: {e}")
    
    # Test triplet
    try:
        validate_triplet({"subject": "YO", "predicate": "SALUDAR", "object": "OTRO"})
        print("✅ Triplet válida")
    except ValidationError as e:
        print(f"❌ Triplet: {e}")
    
    print("\\n=== TESTS COMPLETADOS ===")