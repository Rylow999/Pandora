"""
PandoraAgent — Orquestador principal.

Integra:
- SemanticParser: texto usuario → SemanticEvent
- SGMAgentCore: evento semántico → tick → estado dominante
- Articulator: estado dominante → lenguaje natural
- Journal: memoria episódica persistente
- Workspace: memoria de trabajo (buffer 7-9 items)
"""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from pandora.config.settings import get_config, PandoraConfig
from pandora.config.schemas import SemanticEvent, InternalState, Intent, Triplet, Affect
from pandora.transducer.semantic_parser import SemanticParser, get_parser
from pandora.transducer.articulator import Articulator, get_articulator
from sgm.core.sgm_core import SGMAgentCore


@dataclass
class Episode:
    """Episodio completo de interacción."""
    episode_id: str
    timestamp: str
    user_input: str
    semantic_event: Dict[str, Any]
    internal_state: Dict[str, Any]
    response: str
    parsing_success: bool
    processing_time_ms: float


class Workspace:
    """Memoria de trabajo — buffer de items recientes (capacidad ~7)."""

    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.items: List[Dict[str, Any]] = []

    def push(self, item: Dict[str, Any]):
        self.items.append(item)
        if len(self.items) > self.capacity:
            self.items.pop(0)

    def get_context(self) -> List[Dict[str, Any]]:
        return list(self.items)

    def clear(self):
        self.items.clear()


class Journal:
    """Journal episódico — append-only JSONL."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, episode: Episode):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(episode), ensure_ascii=False) + '\n')

    def last(self, n: int = 5) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return [json.loads(line) for line in lines[-n:]]

    def all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f]


class PandoraAgent:
    """
    Agente Pandora completo.

    Flujo por turno:
    1. Recibe texto del usuario
    2. Parser → SemanticEvent (tripletas, affect, intent)
    3. Codifica evento a vector HRR + inyecta en SGM
    4. SGM.step() → actualiza grafo, homeostasis, kuramoto, arbitro
    5. Lee estado dominante (nodos activos, tripletas, métricas)
    6. Articulator → respuesta en lenguaje natural
    7. Guarda episodio en Journal + actualiza Workspace
    """

    def __init__(
        self,
        sgm: SGMAgentCore | None = None,
        parser: SemanticParser | None = None,
        articulator: Articulator | None = None,
        journal_path: str = "pandora/journal/episodes.jsonl",
        checkpoint_path: str = "pandora/checkpoints/sgm_state.npy",
        workspace_capacity: int = 7,
        load_checkpoint: bool = True,
        config: PandoraConfig | None = None
    ):
        # Configuración centralizada
        self.config = config or get_config()
        
        # Componentes
        self.sgm = sgm or self._create_default_sgm()
        self.parser = parser or get_parser()
        self.articulator = articulator or get_articulator()

        # Memoria
        self.journal = Journal(self.config.journal_path)
        self.workspace = Workspace(self.config.workspace_capacity)

        # Checkpoint
        self.checkpoint_path = Path(self.config.checkpoint_path)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        # Estado
        self.turn_count = 0
        self.session_id = str(uuid.uuid4())[:8]

        # Cargar checkpoint si existe y se solicita
        if load_checkpoint and self.checkpoint_path.exists():
            self.sgm.cargar(str(self.checkpoint_path))
            print(f"[Pandora] Checkpoint cargado: {self.checkpoint_path}")

    def _create_default_sgm(self) -> SGMAgentCore:
        """Crea SGM con configuración base."""
        import random
        sgm = SGMAgentCore(random.Random(42), D=128, n_nodes=64, gamma=0.01)
        sgm.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
        sgm.instinto_alimentacion = 5  # acción 'do' en Crafter
        return sgm

    def _encode_semantic_event(self, event: SemanticEvent) -> List[float]:
        """
        Codifica SemanticEvent a vector semántico para inyectar en SGM.
        Usa HRR binding: subject + predicate + object → vector compuesto.
        """
        # Generar vector basado en tripletas usando place cells y omega
        vec = [0.0] * self.sgm.D
        
        for t in event.triplets:
            for concept in [t.subject, t.predicate, t.object]:
                # Buscar place cell para el concepto
                for ctx, pid in self.sgm.place_cells.items():
                    if concept in ctx:
                        # Sumar omega del nodo
                        for d in range(self.sgm.D):
                            vec[d] += self.sgm.omega[pid][d]
                        break
        
        # Si no hay tripletas, usar vector aleatorio pequeño
        if all(v == 0.0 for v in vec):
            import random, math
            rng = random.Random(hash(str(event.triplets)) % 10000)
            vec = [rng.gauss(0, 0.1) for _ in range(self.sgm.D)]
        
        # Normalizar
        import math
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        
        return vec

    def _inject_event_to_sgm(self, event: SemanticEvent):
        """Inyecta evento semántico en el SGM."""
        # El SGM espera state_semantic (vector denso) para HDC.project
        # Simplificado: activamos nodos por nombre via place cells / omega
        for t in event.triplets:
            for concept in [t.subject, t.predicate, t.object]:
                # Buscar nodo con ese concepto (via place_cells o índice)
                self._activate_concept(concept)

        # Inyectar affect como señal homeostática
        # valence: -1 (negativo) a 1 (positivo) -> _hambre_real: 1 (hambre) a 0 (saciado)
        # arousal: 0 (calma) a 1 (alta activación) -> _amenaza: 0 a 1
        self.sgm._hambre_real = max(0.0, 1.0 - event.affect.valence)  # valence 1.0 -> 0.0, valence -1.0 -> 2.0 (clamped)
        self.sgm._amenaza = event.affect.arousal  # 0.0 a 1.0

    def _activate_concept(self, concept: str):
        """Activa un concepto en el grafo (busca place cell o crea activación)."""
        # Place cells tienen contexto; buscar match parcial
        for ctx, pid in self.sgm.place_cells.items():
            if concept in ctx:
                self.sgm.place_activo = pid
                return

        # Fallback: activar por similitud omega (buscar nodo más cercano semánticamente)
        # Por ahora: no-op, el SGM usa HDC.project sobre state_semantic

    def _read_dominant_state(self, semantic_event=None) -> InternalState:
        """Lee estado dominante del SGM para articulator."""
        # Nodos con mayor vitalidad
        vitality_items = [(i, self.sgm.vitalidad[i]) for i in range(len(self.sgm.vitalidad))]
        vitality_items.sort(key=lambda x: x[1], reverse=True)
        top_nodes = [f"NODO_{i}" for i, v in vitality_items[:5] if v > 0.1]

        # Place cell activo
        if self.sgm.place_activo >= 0:
            ctx = list(self.sgm.place_cells.keys())[self.sgm.place_activo] if self.sgm.place_activo < len(self.sgm.place_cells) else ""
            top_nodes.append(f"PLACE_{ctx[:20]}")

        # Construir tripletas: del evento semántico si existe, sino desde conn_type
        triplets = []
        if semantic_event and semantic_event.triplets:
            for t in semantic_event.triplets:
                triplets.append(Triplet(subject=t.subject, predicate=t.predicate, object=t.object))
        else:
            # Fallback: desde conn_type (aristas con tipo)
            for (src, tgt), ctype in list(self.sgm.conn_type.items())[:10]:
                triplets.append(Triplet(subject=f"NODO_{src}", predicate=ctype, object=f"NODO_{tgt}"))

        # Métricas homeostáticas — del estado REAL del grafo, no de constantes
        # valence/arousal: del afecto inyectado (ya en _hambre_real/_amenaza)
        valence = 1.0 - self.sgm._hambre_real * 2  # hambre alto => valence negativo
        arousal = self.sgm._amenaza
        # doubt: inversa de la integridad topológica (self fragmentado => duda alta)
        integridad = self.sgm.integridad_topologica()
        doubt = 1.0 - integridad if integridad is not None else 0.0
        # contradiction: del status del SGM (ACTIVA / INCONCLUSA / CONTRADICTORIA)
        status = getattr(self.sgm, 'status', 'ACTIVA')
        contradiction = 0.8 if status == 'CONTRADICTORIA' else (0.3 if status == 'INCONCLUSA' else 0.0)

        return InternalState(
            active_nodes=top_nodes or ["YO", "ENTORNO"],
            triplets=triplets,
            valence=valence,
            arousal=arousal,
            doubt=doubt,
            contradiction=contradiction,
            intent=Intent.RESPONDER
        )

    def receive(self, user_text: str) -> str:
        """
        Procesa un turno completo: input → respuesta.
        """
        start_time = time.time()
        self.turn_count += 1

        # 1. Parse
        parse_result = self.parser.parse(user_text)

        if not parse_result.success:
            # Fallback: evento mínimo
            from ..config.schemas import Affect
            semantic_event = SemanticEvent(
                raw=user_text,
                triplets=[],
                affect=Affect(valence=0.0, arousal=0.1, uncertainty=0.8),
                intent=Intent.DESCONOCIDO,
                metadata={"parse_error": parse_result.error}
            )
        else:
            semantic_event = parse_result.event

        # 2. Inyectar en SGM
        self._inject_event_to_sgm(semantic_event)

        # 3. State para step - usar codificación HRR real del evento semántico
        assert semantic_event is not None
        state_semantic = self._encode_semantic_event(semantic_event)

        # 4. Tick SGM (sin food/health: la homeostasis del loop conversacional es
        #  la integridad topológica del grafo, no un metabolismo corporal)
        action = self.sgm.step(state_semantic, list(range(self.config.env_valid_actions)))

        # 5. Leer estado dominante
        internal_state = self._read_dominant_state()

        # 6. Articular respuesta
        render_result = self.articulator.render(internal_state)
        if not render_result.success:
            response = self.articulator.render_fallback(internal_state)
        else:
            response = render_result.text

        # 7. Guardar episodio
        episode = Episode(
            episode_id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            user_input=user_text,
            semantic_event=semantic_event.to_dict() if hasattr(semantic_event, 'to_dict') else {},
            internal_state=internal_state.to_dict(),
            response=response,
            parsing_success=parse_result.success,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        self.journal.append(episode)

        # 8. Actualizar workspace
        self.workspace.push({
            "turn": self.turn_count,
            "input": user_text,
            "state": internal_state.to_dict(),
            "response": response
        })

        # 9. Checkpoint periódico
        if self.turn_count % 10 == 0:
            self.save_checkpoint()

        return response

    def save_checkpoint(self):
        """Guarda estado del SGM."""
        self.sgm.guardar(str(self.checkpoint_path))
        print(f"[Pandora] Checkpoint guardado (turno {self.turn_count})")

    def get_status(self) -> Dict[str, Any]:
        """Estado actual para debugging."""
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "sgm_nodes": len(self.sgm.omega),
            "sgm_edges": sum(len(v) for v in self.sgm.edges.values()) // 2,
            "sgm_place_cells": len(self.sgm.place_cells),
            "sgm_v_grafo": getattr(self.sgm, 'V_grafo', 0),
            "sgm_modo": getattr(self.sgm, 'modo', 'UNKNOWN'),
            "journal_entries": len(self.journal.all()),
            "workspace_items": len(self.workspace.items)
        }

    def self_perceive(self):
        """Auto-percepción: leer journal reciente y re-inyectar."""
        recent = self.journal.last(5)
        for ep in recent:
            if ep.get("semantic_event"):
                # Re-inyectar eventos recientes para consolidación
                pass


def get_pandora_agent(**kwargs) -> PandoraAgent:
    return PandoraAgent(**kwargs)


if __name__ == "__main__":
    # Test rápido del agente completo
    print("=" * 60)
    print("TEST PANDORA AGENT")
    print("=" * 60)

    agent = get_pandora_agent(load_checkpoint=False)

    test_inputs = [
        "Hola, quiero registrar este inicio.",
        "Mi nombre es Luciano.",
        "¿Cuál es mi nombre?",
        "Siento que pierdo el control.",
    ]

    for text in test_inputs:
        print(f"\n>>> {text}")
        response = agent.receive(text)
        print(f"<<< {response}")

    print(f"\n--- STATUS ---")
    print(json.dumps(agent.get_status(), indent=2, ensure_ascii=False))