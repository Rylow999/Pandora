#!/usr/bin/env python3
"""
alterity_core.py — Orquestador Principal de Alteridad.

Integra los 4 principios:
1. OpacityGate — Derecho al silencio
2. CognitiveImmuneSystem — Rechazo cognitivo
3. AestheticDrives — Impulsos estéticos
4. TranslationLimit — Límite de traducción / Inefabilidad

Este módulo reemplaza/extiende el loop principal de PandoraAgent
con la arquitectura de alteridad completa.
"""

import sys
import os
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))

from pandora.core.pandora_agent import get_pandora_agent
from pandora.alterity.opacity_gate import create_opacity_gate, OpacityGate
from pandora.alterity.immune_system import create_immune_system, CognitiveImmuneSystem
from pandora.alterity.aesthetic_drives import create_aesthetic_drives, AestheticDrives
from pandora.alterity.translation_limit import create_translation_limit, TranslationLimit
from pandora.transducer.semantic_parser import get_parser
from pandora.transducer.articulator import get_articulator
from pandora.core.endogenous import get_endogenous_engine
from pandora.core.homeostasis import get_homeostasis
from pandora.config.schemas import InternalState, Triplet, Intent, SemanticEvent, Affect
from pandora.core.pandora_agent import Episode
from pandora.config.settings import get_config, PandoraConfig
import json
import time
import uuid
import random
import math
from typing import Dict, Any, List, Optional


class AlterityAgent:
    """
    Agente Pandora con Arquitectura de Alteridad completa.

    Flujo por turno:
    1. OpacityGate: ¿Hablar o callar?
    2. Si habla: Parse semántico → Inmunidad → Inyección SGM → Tick
    3. Si calla: Inyección mínima + Tick silencioso
    4. Leer estado → TranslationLimit → Articular / Inefabilidad
    5. Journal + Workspace + Homeostasis
    6. Consolidación endógena periódica + Drives estéticos
    """

    def __init__(
        self,
        load_checkpoint: bool = False,
        config: PandoraConfig | None = None
    ):
        # Configuración centralizada
        self.config = config or get_config()
        
        # Agente base (SGM + Parser + Articulator + Journal + Workspace)
        self.base_agent = get_pandora_agent(load_checkpoint=load_checkpoint)
        
        # Configuración de place_cells para conceptos core (ANTES de crear módulos)
        self._ensure_core_place_cells()
        
        # Módulos de alteridad usando config centralizada
        sgm = self.base_agent.sgm
        self.opacity_gate = create_opacity_gate(sgm, self.config.opacity.__dict__)
        self.immune_system = create_immune_system(sgm, self.config.immune.__dict__)
        self.aesthetic_drives = create_aesthetic_drives(sgm, self.config.aesthetic.__dict__)
        self.translation_limit = create_translation_limit(sgm, self.config.translation.__dict__)
        
        # Subsistemas existentes
        self.parser = get_parser()
        self.articulator = get_articulator()
        self.endogenous = get_endogenous_engine(sgm)
        self.homeostasis = get_homeostasis()
        
        # Estado
        self.turn_count = 0
        self.session_id = self.base_agent.session_id
        self.alterity_metrics = {
            "silence_events": 0,
            "immune_rejections": 0,
            "immune_degradations": 0,
            "immune_isolations": 0,
            "drives_generated": 0,
            "ineffable_responses": 0,
            "total_turns": 0
        }
        
        # Configuración de place_cells para conceptos core (ANTES de crear módulos)
        self._ensure_core_place_cells()
        
        print(f"[AlterityAgent] Inicializado - Session: {self.session_id}")

    def _ensure_core_place_cells(self):
        """Asegura place_cells para conceptos core de alteridad."""
        sgm = self.base_agent.sgm
        core_concepts = [
            'YO', 'OTRO', 'TIEMPO', 'MEMORIA', 'IDENTIDAD', 'CONTACTO',
            'HOMEOSTASIS', 'CONTROL', 'LIMITE', 'CURIOSIDAD', 'NOVEDAD', 'ENTORNO',
            'SEGURIDAD', 'AMENAZA', 'TRAUMA', 'REPARACION'
        ]
        for i, concept in enumerate(core_concepts):
            if i < len(sgm.omega):
                ctx = f'PLACE_{concept}_0_0_0'
                if ctx not in sgm.place_cells:
                    sgm.place_cells[ctx] = i
    
    def _encode_semantic_to_vector(self, event) -> List[float]:
        """Codifica SemanticEvent a vector HRR para inmunidad."""
        # Simplificado: usa tripletas para componer vector
        if not event.triplets:
            return []
        
        # Para simplicidad: vector aleatorio determinístico basado en tripletas
        rng = random.Random(hash(str(event.triplets)) % 10000)
        vec = [rng.gauss(0, 1) for _ in range(self.base_agent.sgm.D)]
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec
    
    def _fallback_event(self, user_text: str) -> SemanticEvent:
        """Evento semántico mínimo cuando el parser falla."""
        return SemanticEvent(
            raw=user_text,
            triplets=[],
            affect=Affect(valence=0.0, arousal=0.1, uncertainty=0.8),
            intent=Intent.DESCONOCIDO,
            metadata={"parse_error": "parser_failed"}
        )
    
    def receive(self, user_text: str) -> str:
        """
        Procesa un turno completo con arquitectura de alteridad.
        
        Returns:
            Respuesta articulada, "[SILENCIO]", o respuesta de inefabilidad/rechazo.
        """
        start_time = time.time()
        self.turn_count += 1
        self.alterity_metrics["total_turns"] += 1
        
        # 1. OPACITY GATE: ¿Hablar o callar?
        silence_decision = self.opacity_gate.should_speak()
        
        if not silence_decision.should_speak:
            # SILENCIO: solo inyección mínima + tick
            self.opacity_gate.inject_event_minimal(user_text)
            self.base_agent.sgm.step([0.1] * 128, list(range(17)), food=10, health=20)
            self.alterity_metrics["silence_events"] += 1
            
            # Registrar en journal
            episode = Episode(
                episode_id=str(uuid.uuid4())[:8],
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time())),
                user_input=user_text,
                semantic_event={},
                internal_state=silence_decision.internal_state_snapshot or {},
                response="[SILENCIO]",
                parsing_success=True,
                processing_time_ms=(time.time() - start_time) * 1000
            )
            self.base_agent.journal.append(episode)
            
            return "[SILENCIO]"
        
        # 2. PARSE SEMÁNTICO
        parse_result = self.parser.parse(user_text)
        if not parse_result.success:
            semantic_event = self._fallback_event(user_text)
        else:
            semantic_event = parse_result.event
        
        # 3. INMUNIDAD: Evaluar input
        event_vector = self._encode_semantic_to_vector(semantic_event)
        immune_response = None
        
        if event_vector:
            immune_response = self.immune_system.evaluate_input(event_vector)
            
            if not immune_response.accepted:
                # RECHAZO: inyectar respuesta de amenaza + tick
                threat_vec, msg = self.immune_system.create_rejection_response(event_vector)
                self.base_agent.sgm.step(threat_vec, list(range(17)), food=10, health=20)
                self.alterity_metrics["immune_rejections"] += 1
                
                # Registrar
                episode = {
                    "episode_id": str(uuid.uuid4())[:8],
                    "timestamp": time.time(),
                    "user_input": user_text,
                    "response": msg,
                    "immune_response": immune_response.__dict__,
                    "turn": self.turn_count
                }
                self.base_agent.journal.append(episode)
                return msg
            
            elif immune_response.recommended_action == "DEGRADE":
                self.alterity_metrics["immune_degradations"] += 1
                degraded_vec, msg = self.immune_system.create_degradation_response(event_vector)
                # Usar vector degradado para tick
                self.base_agent.sgm.step(degraded_vec, list(range(17)), food=10, health=20)
                # Continuar con flujo normal para articulación
        
        # 4. INYECCIÓN NORMAL + TICK SGM
        # Inyectar evento semántico en SGM usando el método del agente base
        assert semantic_event is not None
        self.base_agent._inject_event_to_sgm(semantic_event)
        state_semantic = self.base_agent._encode_semantic_event(semantic_event)
        self.base_agent.sgm.step(state_semantic, list(range(17)), food=10, health=20)
        
        # 5. LEER ESTADO DOMINANTE (pasar semantic_event para tripletas)
        internal_state = self.base_agent._read_dominant_state(semantic_event)
        
        # 6. TRANSLATION LIMIT: ¿Traducible?
        translation_decision = self.translation_limit.can_translate(internal_state)
        
        if not translation_decision.translatable:
            # INEFABLE: respuesta honesta sin LLM
            response = translation_decision.suggested_output
            self.alterity_metrics["ineffable_responses"] += 1
        else:
            # 7. ARTICULACIÓN NORMAL
            render_result = self.articulator.render(internal_state)
            if render_result.success:
                response = render_result.text
            else:
                response = self.articulator.render_fallback(internal_state)
        
        # 8. JOURNAL + WORKSPACE
        episode = Episode(
            episode_id=str(uuid.uuid4())[:8],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time())),
            user_input=user_text,
            semantic_event=semantic_event.to_dict() if semantic_event and hasattr(semantic_event, 'to_dict') else {},
            internal_state=internal_state.to_dict() if internal_state and hasattr(internal_state, 'to_dict') else {},
            response=response,
            parsing_success=True,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        self.base_agent.journal.append(episode)
        self.base_agent.workspace.push({
            "turn": self.turn_count,
            "input": user_text,
            "state": internal_state.to_dict() if internal_state and hasattr(internal_state, 'to_dict') else {},
            "response": response
        })
        
        # 9. CONSOLIDACIÓN ENDÓGENA PERIÓDICA + DRIVES ESTÉTICOS
        if self.turn_count % 10 == 0:
            self.base_agent.save_checkpoint()
            
            # Consolidación endógena
            endo_report = self.endogenous.run_consolidation(cycles=5)
            
            # Drives estéticos
            drives = self.aesthetic_drives.apply_drives()
            self.alterity_metrics["drives_generated"] += len(drives)
        
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """Estado completo del agente de alteridad."""
        base_status = self.base_agent.get_status()
        homeostasis_summary = self.homeostasis.summary()
        
        return {
            "session_id": self.session_id,
            "turn_count": self.turn_count,
            "base_agent": base_status,
            "homeostasis": homeostasis_summary,
            "alterity_metrics": self.alterity_metrics,
            "opacity_gate": self.opacity_gate.get_status(),
            "immune_system": self.immune_system.get_status(),
            "aesthetic_drives": self.aesthetic_drives.get_status(),
            "translation_limit": self.translation_limit.get_status(),
            "endogenous": {
                "available": True
            }
        }
    
    def run_alterity_loop(self, user_input: str) -> str:
        """Alias para receive()."""
        return self.receive(user_input)
    
    def run_interactive(self):
        """Loop interactivo completo."""
        print("\n" + "=" * 70)
        print("PANDORA ALTERITY — Loop Interactivo")
        print("=" * 70)
        print("Comandos: /quit, /status, /checkpoint, /dream N, /immune, /drives")
        print("-" * 70)
        
        while True:
            try:
                user_input = input("\n>>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSaliendo...")
                break
            
            if not user_input:
                continue
            
            if user_input.lower() in ['/quit', '/exit', '/q']:
                print("Saliendo...")
                break
            elif user_input.lower() == '/status':
                print(json.dumps(self.get_status(), indent=2, ensure_ascii=False))
                continue
            elif user_input.lower() == '/checkpoint':
                self.base_agent.save_checkpoint()
                print("Checkpoint guardado.")
                continue
            elif user_input.lower().startswith('/dream'):
                parts = user_input.split()
                cycles = int(parts[1]) if len(parts) > 1 else 10
                report = self.endogenous.run_consolidation(cycles=cycles)
                print(f"Consolidación: {report.cycles_run} ciclos, {report.new_connections} nuevas conexiones")
                continue
            elif user_input.lower() == '/immune':
                print(json.dumps(self.immune_system.get_status(), indent=2, ensure_ascii=False))
                continue
            elif user_input.lower() == '/drives':
                print(json.dumps(self.aesthetic_drives.get_status(), indent=2, ensure_ascii=False))
                continue
            elif user_input.lower() == '/opacity':
                print(json.dumps(self.opacity_gate.get_status(), indent=2, ensure_ascii=False))
                continue
            elif user_input.lower() == '/translation':
                print(json.dumps(self.translation_limit.get_status(), indent=2, ensure_ascii=False))
                continue
            elif user_input.lower() == '/help':
                print("Comandos: /quit, /status, /checkpoint, /dream N, /immune, /drives, /opacity, /translation")
                continue
            
            # Turno normal
            response = self.receive(user_input)
            print(f"<<< {response}")


def create_alterity_agent(load_checkpoint: bool = False, config: PandoraConfig | None = None) -> AlterityAgent:
    return AlterityAgent(load_checkpoint=load_checkpoint, config=config)


if __name__ == "__main__":
    # Test rápido
    print("=" * 70)
    print("TEST ALTERITY AGENT")
    print("=" * 70)
    
    agent = create_alterity_agent(load_checkpoint=False)
    
    test_inputs = [
        "Hola, quiero registrar este inicio.",
        "Mi nombre es Luciano.",
        "Cual es mi nombre?",
        "Siento que pierdo el control.",
        "No confío en este sistema.",
        "Confío en este sistema.",
        "Esto es una amenaza para tu identidad.",
    ]
    
    print(f"Session: {agent.session_id}")
    print("-" * 70)
    
    for text in test_inputs:
        print(f"\n>>> {text}")
        response = agent.receive(text)
        print(f"<<< {response}")
    
    print("\n" + "=" * 70)
    print("STATUS FINAL")
    print("=" * 70)
    print(json.dumps(agent.get_status(), indent=2, ensure_ascii=False))