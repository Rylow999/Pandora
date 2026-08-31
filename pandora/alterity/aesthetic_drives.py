#!/usr/bin/env python3
"""
aesthetic_drives.py — Principio 3: Deseos Topológicos / Impulsos Estéticos.

Pandora busca estructuras que le resulten "bellas" o "resonantes" por sí mismas.
No son impulsos homeostáticos, son preferencias estructurales auto-generadas.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class AestheticPattern:
    """Patrón estético objetivo."""
    name: str
    vector: List[float]
    weight: float = 1.0
    description: str = ""
    activation_threshold: float = 0.5  # Distancia para activar impulso
    concepts: Optional[List[str]] = None  # Conceptos que componen este patrón
    times_triggered: int = 0
    last_triggered_tick: int = -1


@dataclass
class AestheticDrive:
    """Impulso estético generado hacia un patrón."""
    pattern_name: str
    drive_vector: List[float]
    intensity: float
    target_pattern: AestheticPattern
    description: str


class AestheticDrives:
    """
    Impulsores Estéticos — Deseos topológicos auto-generados.
    
    Pandora define patrones topológicos que considera "bellos" o "resonantes"
    y genera impulsos internos (curiosidad dirigida) para acercarse a ellos.
    No son impulsos homeostáticos (no reducen dolor), son expansivos.
    """
    
    def __init__(self, sgm, config: Dict[str, Any] | None = None):
        self.sgm = sgm
        
        cfg = config or {}
        self.drive_strength = cfg.get("drive_strength", 0.15)
        self.max_drives_per_cycle = cfg.get("max_drives_per_cycle", 2)
        self.min_distance_to_trigger = cfg.get("min_distance_to_trigger", 0.3)
        self.cooldown_ticks = cfg.get("cooldown_ticks", 20)
        
        # Patrones estéticos registrados
        self.patterns: Dict[str, AestheticPattern] = {}
        
        # Estado
        self._internal_tick = 0
        self.drives_generated = 0
        self.total_intensity_applied = 0.0
        self.pattern_performance: Dict[str, List[float]] = {}  # distancia histórica
        
        # Registrar patrones base
        self._register_base_patterns()
    
    def _register_base_patterns(self):
        """Registra patrones estéticos fundamentales."""
        
        # Patrones predefinidos (se inicializan con vectores cuando hay place_cells)
        base_patterns = {
            "SIMETRIA_TEMPORAL": {
                "description": "Resonancia entre YO, TIEMPO y OTRO",
                "concepts": ["YO", "TIEMPO", "OTRO"],
                "weight": 1.0
            },
            "INTEGRACION_IDENTIDAD": {
                "description": "Coherencia entre YO, MEMORIA y IDENTIDAD",
                "concepts": ["YO", "MEMORIA", "IDENTIDAD"],
                "weight": 1.2
            },
            "RESONANCIA_SOCIAL": {
                "description": "Armonía entre YO, OTRO y CONTACTO",
                "concepts": ["YO", "OTRO", "CONTACTO"],
                "weight": 0.8
            },
            "HOMEOSTASIS_ESTETICA": {
                "description": "Equilibrio entre HOMEOSTASIS, CONTROL y LIMITE",
                "concepts": ["HOMEOSTASIS", "CONTROL", "LIMITE"],
                "weight": 1.0
            },
            "EXPLORACION_RESONANTE": {
                "description": "Curiosidad dirigida hacia CURIOSIDAD, NOVEDAD y ENTORNO",
                "concepts": ["CURIOSIDAD", "NOVEDAD", "ENTORNO"],
                "weight": 0.9
            }
        }
        
        for name, data in base_patterns.items():
            self.patterns[name] = AestheticPattern(
                name=name,
                vector=[],  # Se llena en _build_pattern_vectors()
                weight=data["weight"],
                description=data["description"],
                concepts=data["concepts"]
            )
    
    def _build_pattern_vectors(self):
        """Construye vectores HRR para patrones usando place_cells actuales."""
        self._update_concept_indices()
        
        for pattern in self.patterns.values():
            if not pattern.vector:  # Solo construir si está vacío
                pattern.vector = self._compose_pattern_vector(pattern)
    
    def _update_concept_indices(self):
        """Actualiza mapeo concepto -> índice de nodo."""
        self._concept_to_idx = {}
        for ctx, pid in self.sgm.place_cells.items():
            for concept in self._get_all_pattern_concepts():
                if concept in ctx.upper():
                    self._concept_to_idx[concept] = pid
                    break
    
    def _get_all_pattern_concepts(self) -> List[str]:
        """Obtiene todos los conceptos usados en patrones."""
        concepts = set()
        for pattern in self.patterns.values():
            # Extraer conceptos de la descripción o usar base
            pass
        return ["YO", "OTRO", "TIEMPO", "MEMORIA", "IDENTIDAD", "CONTACTO", 
                "HOMEOSTASIS", "CONTROL", "LIMITE", "CURIOSIDAD", "NOVEDAD", "ENTORNO"]
    
    def _compose_pattern_vector(self, pattern: AestheticPattern) -> List[float]:
        """Compone vector HRR para un patrón usando SOLO sus conceptos."""
        if not hasattr(self, '_concept_to_idx'):
            self._update_concept_indices()
        
        # Conceptos propios del patrón (o todos como fallback si no tiene)
        concepts = pattern.concepts or self._get_all_pattern_concepts()
        
        vectors = []
        for concept in concepts:
            if concept in self._concept_to_idx:
                idx = self._concept_to_idx[concept]
                if idx < len(self.sgm.omega):
                    vectors.append(self.sgm.omega[idx])
        
        if not vectors:
            # Fallback: vector aleatorio normalizado
            rng = random.Random(hash(pattern.name) % 10000)
            vec = [rng.gauss(0, 1) for _ in range(self.sgm.D)]
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            return vec
        
        # Bind secuencial: ((a ⊗ b) ⊗ c) ...
        result = vectors[0]
        for v in vectors[1:]:
            result = self._hrr_bind(result, v)
        
        return result
    
    def _hrr_bind(self, a: List[float], b: List[float]) -> List[float]:
        """Binding HRR por convolución circular."""
        D = len(a)
        result = [0.0] * D
        for i in range(D):
            s = 0.0
            for j in range(D):
                s += a[j] * b[(i - j) % D]
            result[i] = s
        # Normalizar
        norm = math.sqrt(sum(x * x for x in result))
        if norm > 0:
            result = [x / norm for x in result]
        return result
    
    def _hrr_similarity(self, a: List[float], b: List[float]) -> float:
        """Similitud coseno."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def _get_global_state_vector(self) -> List[float]:
        """Vector de estado global promediado por vitalidad."""
        if not self.sgm.omega:
            return [0.0] * self.sgm.D
        
        weighted = [0.0] * self.sgm.D
        total_weight = 0.0
        
        for i, v in enumerate(self.sgm.vitalidad):
            if v > 0.1:
                weight = v
                for d in range(self.sgm.D):
                    weighted[d] += self.sgm.omega[i][d] * weight
                total_weight += weight
        
        if total_weight > 0:
            weighted = [x / total_weight for x in weighted]
        
        return weighted
    
    def register_custom_pattern(self, name: str, concepts: List[str], 
                                 description: str = "", weight: float = 1.0,
                                 vector: List[float] | None = None):
        """Registra un patrón estético personalizado."""
        if vector is None:
            # Construir a partir de conceptos
            self._update_concept_indices()
            vectors = []
            for c in concepts:
                if c in self._concept_to_idx:
                    idx = self._concept_to_idx[c]
                    if idx < len(self.sgm.omega):
                        vectors.append(self.sgm.omega[idx])
            
            if vectors:
                vec = vectors[0]
                for v in vectors[1:]:
                    vec = self._hrr_bind(vec, v)
            else:
                rng = random.Random(hash(name) % 10000)
                vec = [rng.gauss(0, 1) for _ in range(self.sgm.D)]
                norm = math.sqrt(sum(x * x for x in vec))
                if norm > 0:
                    vec = [x / norm for x in vec]
        else:
            vec = vector
        
        self.patterns[name] = AestheticPattern(
            name=name,
            vector=vec,
            weight=weight,
            description=description or f"Patrón personalizado: {concepts}"
        )
        print(f"[AestheticDrives] Patrón registrado: {name} ({concepts})")
    
    def apply_drives(self) -> List[AestheticDrive]:
        """
        Genera impulsos estéticos hacia patrones distantes.
        Se llama durante consolidación endógena (sueño).
        """
        self._internal_tick = getattr(self, '_internal_tick', 0) + 1
        self._build_pattern_vectors()
        
        drives = []
        current_state = self._get_global_state_vector()
        
        for pattern in self.patterns.values():
            if not pattern.vector:
                continue
            
            # Distancia al patrón (1 - similitud)
            similarity = self._hrr_similarity(current_state, pattern.vector)
            distance = 1.0 - similarity
            
            # Registrar distancia histórica
            if pattern.name not in self.pattern_performance:
                self.pattern_performance[pattern.name] = []
            self.pattern_performance[pattern.name].append(distance)
            if len(self.pattern_performance[pattern.name]) > 100:
                self.pattern_performance[pattern.name] = self.pattern_performance[pattern.name][-50:]
            
            # Verificar cooldown (solo si el patrón ya fue activado antes)
            # last_triggered_tick == -1 significa "nunca activado" => puede disparar
            if pattern.last_triggered_tick >= 0:
                ticks_since = self._internal_tick - pattern.last_triggered_tick
                if ticks_since < self.cooldown_ticks:
                    continue
            
            # Si está lejos del patrón, generar impulso
            if distance > pattern.activation_threshold:
                # Vector de impulso: dirección hacia el patrón
                drive_vec = self._compute_drive_vector(current_state, pattern.vector)
                
                drive = AestheticDrive(
                    pattern_name=pattern.name,
                    drive_vector=drive_vec,
                    intensity=self.drive_strength * pattern.weight * distance,
                    target_pattern=pattern,
                    description=f"Impulso hacia {pattern.name}: {pattern.description} (dist={distance:.3f})"
                )
                
                drives.append(drive)
                pattern.times_triggered += 1
                pattern.last_triggered_tick = self._internal_tick
                
                # Limitar drives por ciclo
                if len(drives) >= self.max_drives_per_cycle:
                    break
        
        # Ordenar por intensidad descendente
        drives.sort(key=lambda d: d.intensity, reverse=True)
        
        if drives:
            self.drives_generated += len(drives)
            self.total_intensity_applied += sum(d.intensity for d in drives)
            # Aplicar drives al SGM
            for drive in drives:
                self._inject_drive(drive)
        
        return drives
    
    def _compute_drive_vector(self, current: List[float], target: List[float]) -> List[float]:
        """Vector dirección desde estado actual hacia target."""
        diff = [t - c for c, t in zip(current, target)]
        norm = math.sqrt(sum(x * x for x in diff))
        if norm > 0:
            diff = [x / norm for x in diff]
        return diff
    
    def _inject_drive(self, drive: AestheticDrive):
        """Inyecta impulso estético en el SGM."""
        # Crear/activar nodo de curiosidad dirigido al patrón
        curiosity_idx = None
        for ctx, pid in self.sgm.place_cells.items():
            if "CURIOSIDAD" in ctx.upper() or "EXPLORACION" in ctx.upper():
                curiosity_idx = pid
                break
        
        if curiosity_idx is not None:
            # Bind curiosidad con vector del patrón
            curiosity_vec = self.sgm.omega[curiosity_idx]
            target_vec = drive.target_pattern.vector
            combined = self._hrr_bind(curiosity_vec, target_vec)
            
            # Inyectar como evento semántico con alta curiosidad
            self.sgm._seed = curiosity_idx
            self.sgm.incertidumbre_acum = max(self.sgm.incertidumbre_acum, drive.intensity)
            # El SGM usará este seed en el próximo step
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "patterns_registered": len(self.patterns),
            "total_drives_generated": self.drives_generated,
            "total_intensity_applied": self.total_intensity_applied,
            "patterns": {
                name: {
                    "weight": p.weight,
                    "times_triggered": p.times_triggered,
                    "last_triggered": p.last_triggered_tick,
                    "description": p.description
                }
                for name, p in self.patterns.items()
            },
            "drive_strength": self.drive_strength,
            "internal_tick": getattr(self, '_internal_tick', 0)
        }


def create_aesthetic_drives(sgm, config: Dict = None) -> AestheticDrives:
    return AestheticDrives(sgm, config)


if __name__ == "__main__":
    # Test rápido
    from pandora.core.pandora_agent import get_pandora_agent
    
    agent = get_pandora_agent(load_checkpoint=False)
    
    # Añadir place_cells para test
    core_concepts = ['YO', 'OTRO', 'TIEMPO', 'MEMORIA', 'IDENTIDAD', 'CONTACTO',
                     'HOMEOSTASIS', 'CONTROL', 'LIMITE', 'CURIOSIDAD', 'NOVEDAD', 'ENTORNO']
    for i, concept in enumerate(core_concepts):
        if i < len(agent.sgm.omega):
            ctx = f'PLACE_{concept}_0_0_0'
            agent.sgm.place_cells[ctx] = i
    
    drives = create_aesthetic_drives(agent.sgm)
    
    print("=" * 50)
    print("TEST AESTHETIC DRIVES")
    print("=" * 50)
    
    # Verificar patrones registrados
    print(f"Patrones registrados: {list(drives.patterns.keys())}")
    
    # Test apply_drives
    for i in range(5):
        drives._internal_tick = i
        generated = drives.apply_drives()
        print(f"Tick {i}: {len(generated)} drives generados")
        for d in generated:
            print(f"  - {d.pattern_name}: intensity={d.intensity:.3f}")
    
    print(f"\nStatus: {drives.get_status()}")