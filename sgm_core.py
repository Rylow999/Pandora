# -*- coding: utf-8 -*-
"""
sgm_core.py — SGM: Synthetic Graph Mind (Motor Cognitivo).

Core modularizado: HDC, HRR, PPR, Kuramoto, grafo, homeostasis + hook arbitro.
Todo lo demás está en módulos separados (pulsiones, L2, comunicacion, razonamiento).
"""
import math, random

# Módulos base
from experiments.sgm_hdc import HDC, SensorBridge
from experiments.sgm_hrr import HRR
from experiments.sgm_ppr import ppr_route, ppr_inverso
from experiments.sgm_kuramoto import kuramoto_step, interferencia, campo_interferencia, promedio_ponderado, step_k_cadenas
from experiments.sgm_grafo import SGMAgent as SGMAgentGrafo
from experiments.sgm_homeostasis import Homeostasis
from experiments.sgm_memoria import Memoria
from experiments.sgm_instintos import Instintos


class SGMAgentCore(SGMAgentGrafo):
    """
    Agente SGM con core modularizado.
    
    step(): percepción → arbitro → acción
    NO contiene lógica de negocio, solo orquestación.
    """
    
    def __init__(self, rng=None, D=128, n_nodes=64, gamma=0.01):
        super().__init__(rng, D, n_nodes)
        self.rng = rng or random.Random(42)
        self.D = D
        self.gamma = gamma
        
        # Componentes base
        self.hdc = HDC(self.rng, D)
        self.hrr = HRR(D, self.rng, n_nodes)
        self.sensor = SensorBridge(D)
        
        # Homeostasis
        self.homeostasis = Homeostasis(D)
        
        # Memoria
        self.memoria = Memoria(D)
        
        # Instintos
        self.instintos = Instintos()
        
        # Arbitro (hook externo)
        self._arbitro = None
        
        # Estado
        self.modo = "BASE"
        self.modo_ticks = 0
        self.ultima_accion = -1
        self.historial_acciones = []
        self.stagnation_ticks = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"
        
        # Percepción
        self._hambre_real = 0.0
        self._amenaza = 0.0
        self._algo_enfrente = 0
        self._posicion_actual = None
        self._seed = 0
    
    def set_arbitro(self, arbitro):
        """Configura el arbitro externo de pulsiones."""
        self._arbitro = arbitro
    
    def set_edges(self, edges):
        """Configura las aristas del grafo."""
        self.edges = edges
    
    def step(self, state_semantic, valid_actions):
        """
        Un paso completo del agente.
        
        1. Proyección semántica (HDC)
        2. Percepción interna (modos, place cells, objetos)
        3. Arbitro de pulsiones → acción
        4. Post-acción (drive noop, aprendizaje, duda)
        """
        # 1. Proyección semántica
        om_r = self.hdc.project(state_semantic)
        self._seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        # 2. Percepción interna
        self._percepcion_interna()
        
        # 3. Arbitro de pulsiones
        if self._arbitro is not None:
            accion = self._arbitro.elegir(self, valid_actions)
        else:
            accion = self._elegir_accion_ppp(valid_actions)
        
        # 4. Post-acción
        self._post_accion(accion)
        
        return accion
    
    def _percepcion_interna(self):
        """Fase de percepción interna: modos, place cells, objetos."""
        # Modo (contention scheduling)
        necesidad_critica = max(self._hambre_real, self._amenaza)
        if necesidad_critica > 0.5:
            self.modo = "SUPERVIVENCIA"
            self.modo_ticks += 1
        else:
            self.modo = "BASE"
            self.modo_ticks = 0
        
        # Place cells
        if self.memoria.auto_registrar_place and self._posicion_actual:
            px, py = self._posicion_actual
            bucket = (px // self.memoria.place_bucket, py // self.memoria.place_bucket)
            clave = f"P{bucket[0]}_{bucket[1]}|enf={self._algo_enfrente}"
            self.registrar_place_cell(clave, posicion=(px, py))
        
        # Kuramoto
        kuramoto_step(self.phi, self.phi[0] if self.phi else 0.0, self.vitalidad)
    
    def _elegir_accion_ppp(self, valid_actions):
        """Elige acción usando PPR directo (sin arbitro)."""
        rank = ppr_route(self.edges, self._seed, self._aff, alpha=0.15, iters=10)
        
        best, bv = -1, -2.0
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                if score > bv:
                    bv, best = score, a
        
        return best if best >= 0 else valid_actions[0]
    
    def _post_accion(self, accion):
        """Post-acción: drive noop, aprendizaje, duda."""
        self.historial_acciones.append(accion)
        
        # Drive noop
        self.instintos.actualizar_drive_noop(accion)
        
        # Aprender conexión
        if self.ultima_accion >= 0 and accion != self.ultima_accion:
            self.reforzar_arista(self.ultima_accion, accion)
        
        # Repetición
        if accion == self.ultima_accion:
            self.stagnation_ticks += 1
        else:
            self.stagnation_ticks = 0
        
        self.ultima_accion = accion
        
        # Duda
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        elif self.status == "ACTIVA" and self.memoria.check_stagnation(self):
            self.memoria.handle_doubt(self)
    
    def actualizar_homeostasis(self, food, health):
        """Actualiza homeostasis."""
        self.homeostasis.actualizar(self, food, health)
        self._hambre_real = self.homeostasis._hambre_real
    
    def expresarse(self, decoder_l2=None):
        """
        Genera expresión basada en el estado del grafo.
        Usa el decoder L2 si está disponible.
        """
        if decoder_l2 is None:
            return "..."
        
        # Campo de interferencia
        zona = campo_interferencia(
            self.omega, self.phi,
            self.phi[0] if self.phi else 0.0,
            self.vitalidad
        )
        
        if not zona:
            return "..."
        
        return decoder_l2.decode(zona, max_palabras=5)
    
    def reward(self, r, pain=0.0):
        """Actualiza vitalidad basado en reward/pain."""
        if self.ultima_accion >= 0 and self.ultima_accion < len(self.vitalidad):
            if r > 0:
                self.vitalidad[self.ultima_accion] = min(1.0, self.vitalidad[self.ultima_accion] + r * 0.5)
            if pain > 0:
                self.vitalidad[self.ultima_accion] *= max(0.3, 1.0 - pain)


# Compatibilidad con código anterior
SGMAgent = SGMAgentCore