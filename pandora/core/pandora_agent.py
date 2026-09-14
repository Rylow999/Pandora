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

        # Transductor de salida (Fase 4): NIM como voz rica, con fallback al
        # articulator local (Ollama). El output_transducer integra opacity +
        # inefabilidad en la decisión de hablar; si NIM no está disponible, la
        # renderización cae al articulator (qwen2.5 local).
        from pandora.transducer.output_transducer import OutputTransducer
        from pandora.transducer.nim_client import NimClient
        self.output_transducer = OutputTransducer(client=NimClient(),
                                                  opacity_gate=None,
                                                  translation_limit=None)

        # Memoria
        self.journal = Journal(self.config.journal_path)
        self.workspace = Workspace(self.config.workspace_capacity)

        # Metacognición (Higher-Order Theory): razonar sobre el propio estado.
        # Antes estaba escrito pero sin cablear. Ahora el agente la instancia
        # y la expone para que el estado interno la refleje.
        from sgm.core.sgm_metacognicion import Metacognicion
        self.metacognicion = Metacognicion(self.sgm)

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

    def _articular_respuesta(self, internal_state) -> str:
        """Renderiza el estado interno a texto: NIM primero, fallback a Ollama.

        - Si NIM está disponible y traduce (modo 'habla'), usa su voz rica.
        - Si declara silencio/inefable o falla (sin key, sin red), cae al
          articulator local (Ollama) como respaldo.
        - Si ni NIM ni Ollama, fallback determinístico (nunca devuelve vacío).
        """
        # 1. Intentar NIM (voz rica)
        try:
            if self.output_transducer.client.disponible():
                r = self.output_transducer.traducir(internal_state)
                if r.get("modo") == "habla" and r.get("texto"):
                    return r["texto"]
        except Exception:
            pass  # NIM falló: caer al fallback local

        # 2. Fallback: articulator local (Ollama / qwen2.5)
        try:
            render_result = self.articulator.render(internal_state)
            if render_result.success and render_result.text:
                return render_result.text
        except Exception:
            pass

        # 3. Último recurso: texto determinístico (nunca vacío)
        return self.articulator.render_fallback(internal_state)

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
        for t in event.triplets:
            for concept in [t.subject, t.predicate, t.object]:
                self._activate_concept(concept)

        # Inyectar afecto como señal interna (sin metáfora corporal).
        # arousal (0=calma .. 1=activación) -> _amenaza: percepción de hostilidad.
        # La valencia negativa NO se traduce a "hambre"; la fragmentación del
        # grafo (aislamiento/desincronización) es lo que sube el deseo de
        # integración, vía integridad_topologica(). Ver _read_dominant_state.
        self.sgm._amenaza = event.affect.arousal  # 0.0 a 1.0

    def _deseo_integracion(self) -> float:
        """Déficit de coherencia: cuánto "desea" Pandora reintegrar su self.

        Reemplaza el _hambre_real corporal. Un self fragmentado (integridad
        baja) desea integrarse; un self coherente no. Emerge del grafo, no se
        inyecta desde fuera.
        """
        integridad = self.sgm.integridad_topologica()
        return max(0.0, min(1.0, 1.0 - integridad))

    def _duda_zona_ciega(self) -> float:
        """Duda REAL (NOTA 0072): fracción de zonas ciegas del grafo — nodos
        dormidos / de vitalidad baja que Pandora no explora. Desacoplada de la
        valencia (que mide integración): un grafo íntegro puede dudar mucho
        (mucho dormido), uno fragmentado puede no dudar (todo activo pero
        confuso). Emerge de la vitalidad real, no de deseo reciclado.
        """
        try:
            v = self.sgm.vitalidad
            if not v:
                return 0.0
            dormidos = sum(1 for x in v if x < 0.2)
            return max(0.0, min(1.0, dormidos / len(v)))
        except Exception:
            return 0.0

    def _contradiccion_fase(self) -> float:
        """Contradicción continua (NOTA 0072): dispersión de fase Kuramoto del
        grafo. 0 = fases alineadas (coherente), 1 = dispersión máxima. Reemplaza
        el semáforo de status (0/0.3/0.8) por un gradiente real de incoherencia.
        """
        try:
            import math
            phis = [p for p in self.sgm.phi if p is not None]
            if not phis:
                return 0.0
            # order parameter: |<e^{iφ}>| ; 1 = total coherencia. La contradicción
            # es el complemento de la coherencia de fase.
            cx = sum(math.cos(p) for p in phis) / len(phis)
            cy = sum(math.sin(p) for p in phis) / len(phis)
            coherencia = math.sqrt(cx * cx + cy * cy)
            return max(0.0, min(1.0, 1.0 - coherencia))
        except Exception:
            return 0.0

    def _arousal_kuramoto(self) -> float:
        """Activación propia (NOTA 0072): cuánto se está reacomodando el grafo
        AHORA — la velocidad de cambio de la coherencia de fase, no su nivel.
        Dado que no guardamos el orden de fase previo acá, usamos la relación
        entre dispersión y la traza reciente como proxy: muchos nodos en zona
        activa moviéndose = activación alta. Es fuente genuina de Pandora, no
        espejo del input.
        """
        try:
            # Proxy honesto de 'agitación': cuántos nodos están en zona activa
            # (I > theta_interf) AND vitalidad media — cuánto 'arde' el grafo.
            from sgm.core.sgm_kuramoto import interferencia
            activos = 0
            n = len(self.sgm.phi)
            for i in range(n):
                if i < len(self.sgm.vitalidad) and self.sgm.vitalidad[i] >= 0.1:
                    I = interferencia(self.sgm.omega[i], self.sgm.phi[i],
                                      getattr(self.sgm, 'phi_root', 0.0))
                    if I > getattr(self.sgm, 'theta_interf', 0.70):
                        activos += 1
            return max(0.0, min(1.0, activos / max(1, n)))
        except Exception:
            return 0.0

    def _activate_concept(self, concept: str):
        """Activa un concepto en el grafo (busca place cell)."""
        for ctx, pid in self.sgm.place_cells.items():
            if concept in ctx:
                self.sgm.place_activo = pid
                return

    def _nodos_activos_reales(self) -> list:
        """Descripción estructural real de lo que domina AHORA (NOTA 0072), sin
        etiquetas inventadas. Describe la FORMA de la constelación activa: cuántos
        nodos arden (vitalidad alta), cuántos dormidos, y las relaciones fuertes.
        El LLM puede decir 'un núcleo denso' sin que le inventemos nombres.
        """
        try:
            v = self.sgm.vitalidad
            activos = sum(1 for x in v if x > 0.5)
            dormidos = sum(1 for x in v if x < 0.2)
            total = len(v)
            cons = len(getattr(self.sgm, 'consolidadas', set())) // 2  # pares
            desc = [
                f"nucleo_activo({activos}/{total})",
                f"periferia_dormida({dormidos}/{total})",
                f"relaciones_consolidadas({cons})",
            ]
            # El presente emergente (phi_root) como un hecho, no una etiqueta
            phi = getattr(self.sgm, 'phi_root', 0.0)
            desc.append(f"presente_phi({phi:.2f})")
            return desc
        except Exception:
            return ["YO", "ENTORNO"]

    def _relaciones_reales(self) -> list:
        """Tripletas estructurales de las relaciones consolidadas más FUERTES del
        grafo (NOTA 0072). No inventa nombres: expresa la relación como hecho
        (estado_a ligado a estado_b con fuerza X). Es la matemática relacional
        real que Pandora consolidó — la 'realidad del grafo' que la boca debe
        poder expresar.
        """
        from ..config.schemas import Triplet
        rels = []
        try:
            # pares consolidados con su fuerza (de conn_type si existe)
            pares = list(getattr(self.sgm, 'consolidadas', set()))
            # ordenar por fuerza de conn_type (los más fuertes primero)
            def fuerza(par):
                return self.sgm.conn_type.get(par, {}).get("strength", 0.0)
            pares.sort(key=lambda p: fuerza(p), reverse=True)
            for (a, b) in pares[:6]:
                s = fuerza((a, b))
                if s > 0.0:
                    # relación estructural: 'estado_a' ↔ 'estado_b', con fuerza
                    rels.append(Triplet(
                        subject=f"estado_{a}",
                        predicate=f"ligado_a({s:.2f})",
                        object=f"estado_{b}",
                    ))
        except Exception:
            pass
        return rels

    def _read_dominant_state(self, semantic_event=None) -> InternalState:
        """Lee estado dominante del SGM para articulator.

        NOTA 0072: el transductor se alimenta de la MATEMÁTICA REAL del grafo —
        las RELACIONES (conn_type con fuerza/tipo, pares consolidadas, la
        constelación co-activada), no índices inventados como 'NODO_65'. Los
        nodos no tienen nombre (y no se lo inventamos); las relaciones SÍ son
        expresables como estructura. El LLM describe FORMA, no etiquetas.
        """
        # active_nodes: descripción estructural real, no 'NODO_65'
        active_nodes = self._nodos_activos_reales()

        # Construir tripletas REALES: las del evento entrante (conceptos del
        # oído) + las relaciones consolidadas más fuertes del grafo (estructura
        # relacional que Pandora consolidó).
        triplets = []
        if semantic_event and semantic_event.triplets:
            for t in semantic_event.triplets:
                triplets.append(Triplet(subject=t.subject, predicate=t.predicate, object=t.object))
        # Relaciones consolidadas: pares con mayor fuerza, como (estado_a, ligado, estado_b)
        triplets += self._relaciones_reales()

        # Métricas homeostáticas — del estado REAL del grafo, no de constantes
        # arousal: fuente propia (cambio de fase de Kuramoto = cuánto se reacomoda)
        # mezclada con la inyectada del mensaje (el tono del otro afecta, pero
        # Pandora tiene activación genuinamente suya).
        arousal_inherente = self._arousal_kuramoto()
        arousal = 0.5 * self.sgm._amenaza + 0.5 * arousal_inherente
        # deseo de integración: déficit de coherencia del self
        deseo = self._deseo_integracion()
        # valence: coherente con el deseo — integrado = positiva, fragmentado = negativa
        valence = 1.0 - deseo * 2
        # doubt: DESACOPLADA de valence (NOTA 0072). Ya no es 'deseo' reciclado:
        # es la fracción real de zonas ciegas (nodos dormidos/inexplorados) del
        # grafo — la incertidumbre que emerge de lo que Pandora NO conoce de sí.
        # Un grafo íntegro puede dudar (mucho dormido) y uno fragmentado puede
        # no dudar (todo activo pero confuso) — dejan de sonar idénticos.
        doubt = self._duda_zona_ciega()
        # contradiction: continua, de la dispersión de fase real (Kuramoto), no
        # el semáforo de status. 0 = fases alineadas, 1 = dispersión máxima.
        status = getattr(self.sgm, 'status', 'ACTIVA')
        contradiction = self._contradiccion_fase()

        # Metacognición (HOT): reflexionar sobre el propio estado, exponer
        # confianza/duda en el metadata para que el articulador la refleje.
        try:
            reflexion = self.metacognicion.reflexionar()
            confianza_global = reflexion.get("confianza_global", 0.5)
            meta_duda = reflexion.get("incertidumbre", 0.0)
        except Exception:
            confianza_global = 0.5
            meta_duda = 0.0

        return InternalState(
            active_nodes=active_nodes or ["YO", "ENTORNO"],
            triplets=triplets,
            valence=valence,
            arousal=arousal,
            doubt=doubt,
            contradiction=contradiction,
            intent=Intent.RESPONDER,
            metadata={
                "integracion": 1.0 - deseo,
                "deseo_integracion": deseo,
                "confianza_global": confianza_global,
                "duda_metacognitiva": meta_duda,
            }
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

        # 5. Leer estado dominante — pasando el evento semántico para que la boca
        #    reciba el CONTENIDO de lo que se dijo (no solo el afecto). Antes se
        #    llamaba sin el evento -> la boca caía al fallback conn_type (NODO_x)
        #    y repetía el afecto desnudo, sorda al contenido de la conversación.
        internal_state = self._read_dominant_state(semantic_event)

        # 6. Articular respuesta (NIM primero, fallback a Ollama local)
        response = self._articular_respuesta(internal_state)

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