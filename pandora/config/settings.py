"""
Configuración centralizada para arquitectura Pandora Alterity.
Todos los umbrales y parámetros ajustables en un solo lugar.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class OpacityConfig:
    """Configuración del Opacity Gate (Derecho al Silencio)."""
    contradiction_threshold: float = 0.6
    coherence_threshold: float = 0.05  # Muy bajo para cold start
    min_silence_ticks: int = 3
    max_silence_ticks: int = 20


@dataclass
class ImmuneConfig:
    """Configuración del Sistema Inmunológico Cognitivo."""
    rejection_threshold: float = 0.7
    degradation_threshold: float = 0.4
    isolation_threshold: float = 0.85
    core_concepts: list = field(default_factory=lambda: [
        "YO", "SEGURIDAD", "IDENTIDAD", "MEMORIA", "CONTROL",
        "HOMEOSTASIS", "LIMITE", "CONTINUIDAD"
    ])


@dataclass
class AestheticConfig:
    """Configuración de Impulsores Estéticos."""
    drive_strength: float = 0.15
    patterns: dict = field(default_factory=lambda: {
        "SIMETRIA_TEMPORAL": {
            "weight": 1.0,
            "concepts": ["YO", "TIEMPO", "OTRO"],
            "description": "Resonancia entre YO, TIEMPO y OTRO"
        },
        "INTEGRACION_IDENTIDAD": {
            "weight": 1.2,
            "concepts": ["YO", "MEMORIA", "IDENTIDAD"],
            "description": "Coherencia entre YO, MEMORIA e IDENTIDAD"
        },
        "RESONANCIA_SOCIAL": {
            "weight": 0.8,
            "concepts": ["YO", "OTRO", "CONTACTO"],
            "description": "Armonía entre YO, OTRO y CONTACTO"
        },
        "HOMEOSTASIS_ESTETICA": {
            "weight": 1.0,
            "concepts": ["HOMEOSTASIS", "CONTROL", "LIMITE"],
            "description": "Equilibrio entre HOMEOSTASIS, CONTROL y LIMITE"
        },
        "EXPLORACION_RESONANTE": {
            "weight": 0.9,
            "concepts": ["CURIOSIDAD", "NOVEDAD", "ENTORNO"],
            "description": "Curiosidad dirigida hacia CURIOSIDAD, NOVEDAD y ENTORNO"
        }
    })


@dataclass
class TranslationConfig:
    """Configuración del Límite de Traducción / Inefabilidad."""
    max_active_nodes: int = 7
    min_phase_coherence: float = 0.3
    max_entropy: float = 0.85
    min_pattern_coherence: float = 0.2


@dataclass
class PandoraConfig:
    """Configuración global de Pandora."""
    opacity: OpacityConfig = field(default_factory=OpacityConfig)
    immune: ImmuneConfig = field(default_factory=ImmuneConfig)
    aesthetic: AestheticConfig = field(default_factory=AestheticConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)

    # Parámetros generales
    pre_sync_steps: int = 50
    drive_interval: int = 10
    checkpoint_interval: int = 10

    # Paths
    journal_path: str = "pandora/journal/episodes.jsonl"
    checkpoint_path: str = "pandora/checkpoints/sgm_state.npy"
    workspace_capacity: int = 7

    # SGM params
    sgm_D: int = 128
    sgm_n_nodes: int = 64
    sgm_gamma: float = 0.01

    # LLM params
    llm_model: str = "qwen2.5:0.5b-instruct"
    llm_temperature: float = 0.2
    llm_num_predict: int = 128

    # Entorno (acciones válidas del loop conversacional)
    env_valid_actions: int = 17


# Instancia global de configuración por defecto
DEFAULT_CONFIG = PandoraConfig()


def get_config() -> PandoraConfig:
    """Obtiene la configuración global."""
    return DEFAULT_CONFIG


def update_config(**kwargs) -> PandoraConfig:
    """Actualiza la configuración global."""
    global DEFAULT_CONFIG
    for key, value in kwargs.items():
        if hasattr(DEFAULT_CONFIG, key):
            setattr(DEFAULT_CONFIG, key, value)
    return DEFAULT_CONFIG


if __name__ == "__main__":
    # Test de configuración
    cfg = get_config()
    print("=== PANDORA CONFIG ===")
    print(f"Opacity: contradiction={cfg.opacity.contradiction_threshold}, coherence={cfg.opacity.coherence_threshold}")
    print(f"Immune: reject={cfg.immune.rejection_threshold}, degrade={cfg.immune.degradation_threshold}, isolate={cfg.immune.isolation_threshold}")
    print(f"Translation: max_nodes={cfg.translation.max_active_nodes}, min_phase={cfg.translation.min_phase_coherence}, max_entropy={cfg.translation.max_entropy}")
    print(f"Pre-sync steps: {cfg.pre_sync_steps}")
    print(f"Drive interval: {cfg.drive_interval}")