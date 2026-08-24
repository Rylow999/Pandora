# -*- coding: utf-8 -*-
"""
sgm_core.py — SGM: Synthetic Graph Mind (Motor Cognitivo).

Core modularizado con TODOS los mecanismos integrados:
- HDC, HRR, PPR, Kuramoto
- Grafo con omega inmutable (conceptos) / mutable (place cells)
- Decaimiento de vitalidad (gamma_nodo, Eq.5)
- Poda de aristas (strength < umbral)
- Consolidación Kuramoto (phi, Eq.3)
- Hebb en homeostasis (co-ocurrencia acciones que mejoran)
- Modelo de mundo (predictivo)
- Razonamiento (inducir, deducir, abducir)
- Trauma nodal (sobrecarga → aislar)
- Comunicación (texto desde estado)
- Self-mod (frenos operacionales)
- Sueño/reconciliación
"""
import math, random, os
import numpy as np

from experiments.sgm_hdc import HDC, SensorBridge
from experiments.sgm_hrr import HRR
from experiments.sgm_ppr import ppr_route, ppr_inverso
from experiments.sgm_kuramoto import kuramoto_step, interferencia, campo_interferencia, promedio_ponderado, step_k_cadenas
from experiments.sgm_grafo import SGMAgent as SGMAgentGrafo


class SGMAgentCore(SGMAgentGrafo):
    """Agente SGM con core modularizado y flujo completo."""
    
    def __init__(self, rng=None, D=128, n_nodes=64, gamma=0.01):
        super().__init__(rng, D, n_nodes)
        self.rng = rng or random.Random(42)
        self.D = D
        self.gamma = gamma
        
        # Componentes base
        self.hdc = HDC(self.rng, D)
        self.hrr = HRR(D, self.rng, n_nodes)
        self.sensor = SensorBridge(D)
        
        # Arbitro
        self._arbitro = None
        
        # Homeostasis (decaimiento + Hebb)
        self.gamma_nodo = gamma
        self.gamma_conocimiento = 0.001
        self.E = 0.0
        self.E_acumulado = 0.0
        self._hambre_real = 0.0
        self._amenaza = 0.0
        self._algo_enfrente = 0
        self._posicion_actual = None
        self._hay_gradiente = False
        self._gradiente_dir = (0, 0)
        self._config_grad = {"activo": False, "fuerza": 0.0}
        self._config_curio = {"activo": False, "fuerza": 0.0}
        self._inc_dirs = {}
        self._target_dir = (0, 0)
        self._target_dist = 0
        self._accion_meta = None
        self._seed = 0
        self.objetos = {}
        self.meta_recordada = None
        
        # Kuramoto (consolidación)
        self.phi_root = 0.0
        self.eta_phase = 0.05
        self.R_base = 1.0
        self.theta_interf = 0.70
        self.consolidadas = set()
        self.conteo_exitos_conexion = {}
        
        # Atributos para pulsiones
        self.instinto_alimentacion = None
        self.incertidumbre_acum = 0.0
        self.instinto_explorar_umbral = 3
        self.instinto_umbral_carencia = 0.3
        self.instinto_interaccion_fuerza = 0.7
        self.beta_supervivencia = 2.0
        self.beta_otras_compo = 0.3
        self.reencare_fuerza = 0.8
        self.acciones_movimiento = {1, 2, 3, 4}
        self.drive_noop = 0.0
        self.drive_noop_umbral = 1.5
        self.drive_noop_fuerza = 1.0
        self.drive_noop_tasa = 0.1
        self.drive_noop_descarga = 0.5
        self.stagnation_ticks = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"
        
        # Modelo de mundo
        self.modelo_mundo = {}  # (estado_q, accion) -> {siguiente_q: count}
        self.ultimo_estado_q = None
        
        # Memoria episódica
        self.episodios = []
        self.episodios_max = 50
        self.context_window = []
        self.W_base = 50
        self.kappa_W = 2.0
        self.current_density = 0.0
        self.effective_learning_rate = 0.10
        self.parent_of = {}
        self.scope_depth = [0] * n_nodes
        
        # Trauma nodal
        self.theta_emerg_critico = 0.5
        
        # Self-mod
        self.historial_food = []
        self.ultimo_food = None
        
        # L2 decoder
        self.l2_decoder = None
        self.historial_campos = []
        self.historial_acciones_l2 = []
        
        # Comunicación
        self.valencia_recurso = {}
        self.valencia_tasa = 0.15
        self._ultima_valencia_food = None
        self.modelo_del_otro = {}
        self.otro_observaciones = 0
        self.obs_activa = None
        self.auto_registrar_place = True
        self.auto_navegar_meta = True
        self.auto_mutar_omega = True
        self.place_bucket = 4
        self.mutacion_tasa = 0.05
        self.acciones_movimiento = {1, 2, 3, 4}
        
        # Estado del ciclo
        self.modo = "BASE"
        self.modo_ticks = 0
        self.ultima_accion = -1
        self.conteo_repeticion = 0
        self.stagnation_ticks = 0
        self._ultima_accion_ejec = -1
    
    def set_arbitro(self, arbitro):
        self._arbitro = arbitro
    
    def set_edges(self, edges):
        self.edges = edges
    
    # ============ DECAIMIENTO DE VITALIDAD (Eq.5) ============
    
    def decaer_vitalidad(self):
        """V_i(t+1) = V_i·e^(-γ) + A_i·(1-e^(-γ)). A_i = 1 si fue visitado, si no 0."""
        for i in range(len(self.vitalidad)):
            A = 1.0 if self.historial_acciones and self.historial_acciones[-1] == i else 0.0
            self.vitalidad[i] = self.vitalidad[i] * math.exp(-self.gamma_nodo) + A * (1 - math.exp(-self.gamma_nodo))
    
    # ============ PODA DE ARISTAS ============
    
    def podar_aristas(self, umbral=0.01):
        """Elimina aristas con strength < umbral (no consolidadas)."""
        a_eliminar = []
        for clave, datos in self.conn_type.items():
            if clave not in self.consolidadas:
                datos["age"] += 1
                datos["strength"] *= 0.999  # decaimiento lento
                if datos["strength"] < umbral and datos["age"] > 100:
                    a_eliminar.append(clave)
        
        for clave in a_eliminar:
            del self.conn_type[clave]
            a, b = clave
            if b in self.edges.get(a, []):
                self.edges[a].remove(b)
            if a in self.edges.get(b, []):
                self.edges[b].remove(a)
    
    # ============ KURAMOTO (Eq.3) ============
    
    def actualizar_kuramoto(self):
        """φ(t+1) = [φ(t) + η·R·sin(φ_root - φ)] mod 2π."""
        for i in range(len(self.phi)):
            R = 1.0 / (1.0 + math.sqrt(sum((a - b) ** 2 for a, b in zip(self.omega[i], self.omega[0])))) if self.omega else 1.0
            delta = math.sin(self.phi_root - self.phi[i])
            signo = 1 if self.E > 0 else -1
            self.phi[i] = (self.phi[i] + self.eta_phase * R * signo * delta) % (2 * math.pi)
            
            # Consolidación por interferencia > umbral
            I = interferencia(self.omega[i], self.phi[i], self.phi_root)
            if I > self.theta_interf:
                for j in range(len(self.omega)):
                    if i != j and j < len(self.consolidadas):
                        self.consolidadas.add((i, j))
                        self.consolidadas.add((j, i))
    
    # ============ HEBB EN HOMEOSTASIS ============
    
    def hebb_homeostasis(self, food, health):
        """Refuerza conexiones entre acciones que co-ocurren con mejora de homeostasis."""
        if self.ultimo_food is not None:
            delta_food = food - self.ultimo_food
            if delta_food > 0:
                # Refuerzar conexiones entre últimas acciones
                for i in range(min(5, len(self.historial_acciones))):
                    a = self.historial_acciones[-(i+1)]
                    for j in range(min(5, len(self.historial_acciones))):
                        b = self.historial_acciones[-(j+1)]
                        if a != b:
                            clave = (a, b)
                            if clave not in self.conn_type:
                                self.conn_type[clave] = {"count": 0, "tipo": 0, "strength": 1.0, "age": 0}
                            self.conn_type[clave]["count"] += 1
                            self.conn_type[clave]["strength"] = min(1.0, self.conn_type[clave]["strength"] + 0.05)
        self.ultimo_food = food
    
    # ============ MODELO DE MUNDO ============
    
    def actualizar_modelo_mundo(self, estado_q, accion, siguiente_q):
        """Aprende transiciones estado→acción→estado."""
        clave = (estado_q, accion)
        if clave not in self.modelo_mundo:
            self.modelo_mundo[clave] = {}
        self.modelo_mundo[clave][siguiente_q] = self.modelo_mundo[clave].get(siguiente_q, 0) + 1
    
    def predecir_transicion(self, estado_q, accion):
        """Predice siguiente estado según modelo del mundo."""
        clave = (estado_q, accion)
        if clave in self.modelo_mundo:
            transiciones = self.modelo_mundo[clave]
            if transiciones:
                return max(transiciones, key=transiciones.get)
        return None
    
    def incertidumbre(self):
        """Calcula incertidumbre basada en predicciones fallidas."""
        total = sum(sum(v.values()) for v in self.modelo_mundo.values())
        if total == 0: return 1.0
        known = sum(1 for v in self.modelo_mundo.values() if len(v) == 1)
        return 1.0 - (known / max(1, len(self.modelo_mundo)))
    
    # ============ RAZONAMIENTO ============
    
    def inducir(self, a, b):
        """Inducción: observar A→B repetidas veces → generalizar."""
        clave = (a, b)
        if clave not in self.conteo_induccion:
            self.conteo_induccion[clave] = 0
        self.conteo_induccion[clave] += 1
        if self.conteo_induccion[clave] >= 3:  # umbral
            self.reforzar_arista(a, b, 0.15)
            return {"evidencia": self.conteo_induccion[clave], "consolidada": True, "fuerza": 0.15}
        return {"evidencia": self.conteo_induccion[clave], "consolidada": False, "fuerza": 0.0}
    
    def deducir(self, a, b):
        """Deducción: A→B y B→C → verificar A→C (transitividad)."""
        if b not in self.edges.get(a, []):
            return False, []
        for vecino in self.edges.get(b, []):
            if vecino in self.edges.get(a, []):
                return True, [a, b, vecino]
        return False, []
    
    def abducir(self, resultado, topk=5):
        """Abducción: dado un resultado, encontrar causas más plausibles."""
        return ppr_inverso(self.edges, resultado, alpha=0.15, iters=30)
    
    # ============ TRAUMA NODAL ============
    
    def verificar_trauma(self):
        """Verifica si hay nodos con sobrecarga (dolor)."""
        for i in range(len(self.vitalidad)):
            if self.vitalidad[i] > 0.9 and i < len(self.phi):
                # Aislar nodo: reducir vitalidad de vecinos
                for vecino in self.edges.get(i, []):
                    if vecino < len(self.vitalidad):
                        self.vitalidad[vecino] *= 0.95
                return True
        return False
    
    # ============ SELF-MOD ============
    
    def auto_modificar(self, accion, resultado):
        """Auto-modificación: ajustar comportamiento basado en resultado."""
        if resultado > 0:
            self.vitalidad[accion] = min(1.0, self.vitalidad[accion] + resultado * 0.1)
        elif resultado < 0:
            self.vitalidad[accion] = max(0.0, self.vitalidad[accion] + resultado * 0.1)
    
    # ============ SUEÑO/RECONCILIACIÓN ============
    
    def reconciliar(self):
        """Sueño: consolidar memoria, resetear fases, limpiar ruido."""
        # Reset de fases
        for i in range(len(self.phi)):
            self.phi[i] = self.rng.uniform(0, 2 * math.pi)
        # Limpiar nodos con vitalidad muy baja
        for i in range(len(self.vitalidad)):
            if self.vitalidad[i] < 0.05:
                self.vitalidad[i] = 0.0
    
    # ============ COMUNICACIÓN ============
    
    def generar_texto(self):
        """Genera texto basado en estado interno usando L2."""
        if self.l2_decoder is None:
            return "..."
        
        zona = campo_interferencia(self.omega, self.phi, self.phi_root, self.vitalidad)
        if not zona:
            return "..."
        
        palabras = []
        for nid, omega, I in zona[:5]:
            omega_full = self.omega[nid] if nid < len(self.omega) else omega
            top = self.l2_decoder.decode(np.array(omega_full) * I, topk=1)
            if top:
                palabras.append(ID2TOKEN.get(top[0][0], "?"))
        
        return " ".join(palabras) if palabras else "..."
    
    # ============ HOMEOSTASIS ============
    
    def actualizar_homeostasis(self, food, health):
        """Actualiza homeostasis (food: 0-20, health: 0-20)."""
        food = float(food)
        health = float(health) if health is not None else 20.0
        
        factor_cuerpo = max(0.05, health / 20.0)
        if self.omega:
            self.V_grafo = (sum(self.vitalidad) / len(self.vitalidad)) * factor_cuerpo
        else:
            self.V_grafo = factor_cuerpo
        
        self._hambre_real = max(0.0, 1.0 - food / 20.0)
        self._amenaza = max(0.0, (20.0 - health) / 20.0) if health < 15 else 0.0
        self.E = max(0.0, self._hambre_real + self._amenaza)
        self.E_acumulado = self.E_acumulado * 0.95 + self.E
        
        # Hebb
        self.hebb_homeostasis(food, health)
        
        # Trauma
        self.verificar_trauma()
    
    # ============ STEP COMPLETO ============
    
    def step(self, state_semantic, valid_actions, food=None, health=None):
        """Un paso completo del agente."""
        # 1. Proyección
        om_r = self.hdc.project(state_semantic)
        self._seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        # 2. Homeostasis
        if food is not None and health is not None:
            self.actualizar_homeostasis(food, health)
        
        # 3. Percepción interna
        self._percepcion_interna()
        
        # 4. Decaimiento + Kuramoto
        self.decaer_vitalidad()
        self.actualizar_kuramoto()
        
        # 5. Navegación
        self._navegacion_y_objetos()
        
        # 6. Arbitro
        if self._arbitro is not None:
            accion = self._arbitro.elegir(self, valid_actions)
        else:
            accion = self._elegir_accion_ppp(valid_actions)
        
        # 7. Post-acción
        self._post_accion(accion)
        
        # 8. Auto-mod
        if food is not None:
            delta = food - (self.ultimo_food or food)
            self.auto_modificar(accion, delta)
        
        # 9. Guardar historial L2
        zona = campo_interferencia(self.omega, self.phi, self.phi_root, self.vitalidad)
        self.historial_campos.append(zona)
        self.historial_acciones_l2.append(accion)
        
        return accion
    
    def _percepcion_interna(self):
        necesidad_critica = max(self._hambre_real, self._amenaza)
        if necesidad_critica > self.theta_emerg_critico:
            self.modo = "SUPERVIVENCIA"
            self.modo_ticks += 1
        else:
            self.modo = "BASE"
            self.modo_ticks = 0
        
        if self.auto_registrar_place and self._posicion_actual:
            px, py = self._posicion_actual
            bucket = (px // self.place_bucket, py // self.place_bucket)
            clave = f"P{bucket[0]}_{bucket[1]}|enf={self._algo_enfrente}"
            self.registrar_place_cell(clave, posicion=(px, py))
        
        kuramoto_step(self.phi, self.phi[0] if self.phi else 0.0, self.vitalidad)
    
    def _navegacion_y_objetos(self):
        if self.auto_navegar_meta and self._hambre_real > 0.2 and self.meta_recordada is not None:
            mx, my = self.meta_recordada
            if self._posicion_actual is not None:
                cxp, cyp = self._posicion_actual
                if abs(mx - cxp) + abs(my - cyp) > 1:
                    dx = 1 if mx > cxp else (-1 if mx < cxp else 0)
                    dy = 1 if my > cyp else (-1 if my < cyp else 0)
                    if abs(dx) >= abs(dy):
                        self._accion_meta = self._direccion_a_accion(dx, 0)
                    else:
                        self._accion_meta = self._direccion_a_accion(0, dy)
                else:
                    self._accion_meta = None
    
    def _direccion_a_accion(self, dx, dy):
        if dy < 0 and dx == 0: return 1
        if dy > 0 and dx == 0: return 2
        if dx > 0 and dy == 0: return 4
        if dx < 0 and dy == 0: return 3
        return 0
    
    def _elegir_accion_ppp(self, valid_actions):
        rank = ppr_route(self.edges, self._seed, self._aff, alpha=0.15, iters=10)
        best, bv = -1, -2.0
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                if score > bv:
                    bv, best = score, a
        return best if best >= 0 else valid_actions[0]
    
    def _post_accion(self, accion):
        self.historial_acciones.append(accion)
        
        # Drive noop
        if accion == 0:
            self.drive_noop = min(self.drive_noop_umbral * 3, self.drive_noop + self.drive_noop_tasa)
        else:
            self.drive_noop = max(0.0, self.drive_noop - self.drive_noop_descarga)
        
        # Aprender conexión
        if self.ultima_accion >= 0 and accion != self.ultima_accion:
            self.aprender_conexion(self.ultima_accion, accion)
        
        # Repetición
        if accion == self.ultima_accion:
            self.conteo_repeticion += 1
        else:
            self.conteo_repeticion = 0
        
        self.ultima_accion = accion
        
        # Duda
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        elif self.status == "ACTIVA" and self.stagnation_ticks > 20:
            self.status = "INCONCLUSA"
            self.doubt_cooldown = 10
    
    def aprender_conexion(self, a, b):
        self.reforzar_arista(a, b, 0.1)
    
    # ============ PERSISTENCIA ============
    
    def guardar(self, ruta):
        data = {
            "omega": self.omega, "phi": self.phi, "vitalidad": self.vitalidad,
            "es_place_cell": self.es_place_cell, "edges": self.edges,
            "conn_type": self.conn_type, "scope_depth": self.scope_depth,
            "place_cells": self.place_cells, "place_pos": self.place_pos,
            "V_grafo": self.V_grafo, "E_acumulado": self.E_acumulado,
            "historial_campos": self.historial_campos[-1000:],
            "historial_acciones_l2": self.historial_acciones_l2[-1000:],
        }
        np.save(ruta, data)
    
    def cargar(self, ruta):
        if not os.path.exists(ruta): return False
        data = np.load(ruta, allow_pickle=True).item()
        self.omega = data.get("omega", self.omega)
        self.phi = data.get("phi", self.phi)
        self.vitalidad = data.get("vitalidad", self.vitalidad)
        self.es_place_cell = data.get("es_place_cell", self.es_place_cell)
        self.edges = data.get("edges", self.edges)
        self.conn_type = data.get("conn_type", self.conn_type)
        self.scope_depth = data.get("scope_depth", self.scope_depth)
        self.place_cells = data.get("place_cells", self.place_cells)
        self.place_pos = data.get("place_pos", self.place_pos)
        self.V_grafo = data.get("V_grafo", self.V_grafo)
        self.E_acumulado = data.get("E_acumulado", self.E_acumulado)
        self.historial_campos = data.get("historial_campos", [])
        self.historial_acciones_l2 = data.get("historial_acciones_l2", [])
        return True
    
    def set_l2_decoder(self, decoder):
        self.l2_decoder = decoder


SGMAgent = SGMAgentCore