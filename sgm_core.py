# -*- coding: utf-8 -*-
"""
sgm_core.py — SGM: Synthetic Graph Mind (Motor Cognitivo).

Core modularizado con flujo completo + persistencia + L2 integrado + t-SNE.
"""
import math, random, os
import numpy as np

from experiments.sgm_hdc import HDC, SensorBridge
from experiments.sgm_hrr import HRR
from experiments.sgm_ppr import ppr_route, ppr_inverso
from experiments.sgm_kuramoto import kuramoto_step, interferencia, campo_interferencia, promedio_ponderado, step_k_cadenas
from experiments.sgm_grafo import SGMAgent as SGMAgentGrafo
from experiments.sgm_homeostasis import Homeostasis
from experiments.sgm_memoria import Memoria
from experiments.sgm_instintos import Instintos


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
        
        # Homeostasis
        self.homeostasis = Homeostasis(D)
        
        # Memoria
        self.memoria = Memoria(D)
        
        # Instintos
        self.instintos = Instintos()
        
        # Arbitro (hook externo)
        self._arbitro = None
        
        # Estado interno
        self.modo = "BASE"
        self.modo_ticks = 0
        self.ultima_accion = -1
        self.historial_acciones = []
        self.stagnation_ticks = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"
        self.conteo_repeticion = 0
        
        # Percepción
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
        
        # Persistencia: historial para L2
        self.historial_campos = []
        self.historial_acciones_l2 = []
        self.l2_decoder = None
    
    def set_arbitro(self, arbitro):
        self._arbitro = arbitro
    
    def set_edges(self, edges):
        self.edges = edges
    
    def step(self, state_semantic, valid_actions, food=None, health=None):
        """Un paso completo del agente con homeostasis + percepción + arbitro."""
        # 1. Proyección semántica
        om_r = self.hdc.project(state_semantic)
        self._seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        # 2. Homeostasis (integrada)
        if food is not None and health is not None:
            self.actualizar_homeostasis(food, health)
        
        # 3. Percepción interna completa
        self._percepcion_interna()
        
        # 4. Navegación a meta y objetos
        self._navegacion_y_objetos()
        
        # 5. Arbitro de pulsiones
        if self._arbitro is not None:
            accion = self._arbitro.elegir(self, valid_actions)
        else:
            accion = self._elegir_accion_ppp(valid_actions)
        
        # 6. Post-acción
        self._post_accion(accion)
        
        return accion
    
    def _percepcion_interna(self):
        """Percepción interna: modos, place cells, Kuramoto."""
        # Modo (contention scheduling)
        necesidad_critica = max(self._hambre_real, self._amenaza)
        if necesidad_critica > 0.5:
            self.modo = "SUPERVIVENCIA"
            self.modo_ticks += 1
        else:
            self.modo = "BASE"
            self.modo_ticks = 0
        
        # Place cells
        if hasattr(self.memoria, 'auto_registrar_place') and self.memoria.auto_registrar_place and self._posicion_actual:
            px, py = self._posicion_actual
            bucket = (px // self.memoria.place_bucket, py // self.memoria.place_bucket)
            clave = f"P{bucket[0]}_{bucket[1]}|enf={self._algo_enfrente}"
            self.registrar_place_cell(clave, posicion=(px, py))
        
        # Kuramoto
        kuramoto_step(self.phi, self.phi[0] if self.phi else 0.0, self.vitalidad)
    
    def _navegacion_y_objetos(self):
        """Navegación a meta y modelo de objetos."""
        if hasattr(self.memoria, 'auto_navegar_meta') and self.memoria.auto_navegar_meta and self._hambre_real > 0.2 and self.meta_recordada is not None:
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
        
        self._actualizar_objetos()
        if hasattr(self.memoria, 'auto_navegar_meta') and self.memoria.auto_navegar_meta and self.meta_recordada is not None:
            for tipo in getattr(self, '_tipos_meta_buscados', ['comida']):
                pred = self._posicion_predicha_objeto(tipo)
                if pred is not None:
                    self.meta_recordada = pred
                    break
    
    def _actualizar_objetos(self):
        """Modelo de objetos: rastrea posición histórica."""
        seen = getattr(self, '_objetos_vistos', None)
        if not seen:
            return
        
        for tipo, ox, oy in seen:
            ox, oy = int(ox), int(oy)
            encontrado = False
            for oid, datos in self.objetos.items():
                if datos.get('tipo') == tipo:
                    hist = datos.get('pos_hist', [])
                    if hist:
                        ult = hist[-1]
                        if abs(ult[0] - ox) + abs(ult[1] - oy) < 3:
                            hist.append((ox, oy))
                            datos['pos_hist'] = hist[-10:]
                            encontrado = True
                            break
            if not encontrado:
                oid = len(self.objetos)
                self.objetos[oid] = {
                    'tipo': tipo,
                    'pos_hist': [(ox, oy)],
                    'id': oid
                }
    
    def _posicion_predicha_objeto(self, tipo):
        """Predice posición futura de un objeto basado en su velocidad."""
        for oid, datos in self.objetos.items():
            if datos.get('tipo') == tipo:
                hist = datos.get('pos_hist', [])
                if len(hist) >= 2:
                    vx = hist[-1][0] - hist[-2][0]
                    vy = hist[-1][1] - hist[-2][1]
                    return (hist[-1][0] + vx, hist[-1][1] + vy)
        return None
    
    def _direccion_a_accion(self, dx, dy):
        """Convierte dirección (dx, dy) a índice de acción."""
        if dy < 0 and dx == 0: return 1  # norte
        if dy > 0 and dx == 0: return 2  # sur
        if dx > 0 and dy == 0: return 4  # este
        if dx < 0 and dy == 0: return 3  # oeste
        if dx > 0 and dy < 0: return 1  # noreste → norte
        if dx > 0 and dy > 0: return 2  # sureste → sur
        return 0
    
    def _elegir_accion_ppp(self, valid_actions):
        """Fallback: PPR directo sin arbitro."""
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
        if hasattr(self.instintos, 'actualizar_drive_noop') and self.instintos:
            self.instintos.actualizar_drive_noop(accion)
        
        # Aprender conexión
        if self.ultima_accion >= 0 and accion != self.ultima_accion:
            self.aprender_conexion(self.ultima_accion, accion)
        
        # Repetición
        if accion == self.ultima_accion:
            self.stagnation_ticks += 1
        else:
            self.stagnation_ticks = 0
        
        self.ultima_accion = accion
        
        # Duda (verificar que memoria tenga los métodos)
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        elif self.status == "ACTIVA" and hasattr(self.memoria, 'check_stagnation') and self.memoria.check_stagnation(self):
            self.memoria.handle_doubt(self)
    
    def actualizar_homeostasis(self, food, health):
        """Actualiza homeostasis."""
        self.homeostasis.actualizar(self, food, health)
        self._hambre_real = self.homeostasis._hambre_real
    
    def expresarse(self, decoder_l2=None):
        """Genera expresión basada en el estado del grafo."""
        if decoder_l2 is None and self.l2_decoder is None:
            return "..."
        
        decoder = decoder_l2 or self.l2_decoder
        
        zona = campo_interferencia(
            self.omega, self.phi,
            self.phi[0] if self.phi else 0.0,
            self.vitalidad
        )
        
        if not zona:
            return "..."
        
        return decoder.decode(zona, max_palabras=5)
    
    def reward(self, r, pain=0.0):
        """Actualiza vitalidad basado en reward/pain."""
        if self.ultima_accion >= 0 and self.ultima_accion < len(self.vitalidad):
            if r > 0:
                self.vitalidad[self.ultima_accion] = min(1.0, self.vitalidad[self.ultima_accion] + r * 0.5)
            if pain > 0:
                self.vitalidad[self.ultima_accion] *= max(0.3, 1.0 - pain)
    
    # ============ PERSISTENCIA ============
    
    def guardar(self, ruta):
        """Guarda estado completo."""
        data = {
            "omega": self.omega,
            "phi": self.phi,
            "vitalidad": self.vitalidad,
            "es_place_cell": self.es_place_cell,
            "edges": self.edges,
            "conn_type": self.conn_type,
            "scope_depth": self.scope_depth,
            "parent_of": self.parent_of,
            "place_cells": self.place_cells,
            "place_pos": self.place_pos,
            "V_grafo": self.V_grafo,
            "historial_campos": self.historial_campos[-1000:],
            "historial_acciones_l2": self.historial_acciones_l2[-1000:],
        }
        np.save(ruta, data)
        return ruta
    
    def cargar(self, ruta):
        """Carga estado completo."""
        if not os.path.exists(ruta):
            return False
        data = np.load(ruta, allow_pickle=True).item()
        self.omega = data.get("omega", self.omega)
        self.phi = data.get("phi", self.phi)
        self.vitalidad = data.get("vitalidad", self.vitalidad)
        self.es_place_cell = data.get("es_place_cell", self.es_place_cell)
        self.edges = data.get("edges", self.edges)
        self.conn_type = data.get("conn_type", self.conn_type)
        self.scope_depth = data.get("scope_depth", self.scope_depth)
        self.parent_of = data.get("parent_of", self.parent_of)
        self.place_cells = data.get("place_cells", self.place_cells)
        self.place_pos = data.get("place_pos", self.place_pos)
        self.V_grafo = data.get("V_grafo", self.V_grafo)
        self.historial_campos = data.get("historial_campos", [])
        self.historial_acciones_l2 = data.get("historial_acciones_l2", [])
        return True
    
    # ============ L2 CON t-SNE ============
    
    def configurar_l2(self, l2_decoder):
        """Configura el decoder L2."""
        self.l2_decoder = l2_decoder
    
    def procesar_l2(self, epochs=50, lr=0.05):
        """Entrena L2 con los datos recolectados + t-SNE."""
        if len(self.historial_campos) < 10:
            print("  [L2] No hay suficientes datos")
            return None
        
        try:
            from sklearn.manifold import TSNE
            from sklearn.cluster import KMeans
        except ImportError:
            print("  [L2] sklearn no disponible")
            return None
        
        # 1. Co-ocurrencia
        C = self._construir_coocurrencia()
        n = C.shape[0]
        
        # 2. PMI
        PMI = self._computar_pmi(C)
        
        # 3. SVD
        k = min(32, n)
        U, S, _ = np.linalg.svd(PMI, full_matrices=False)
        vv = U[:, :k] * S[:k]
        
        # 4. t-SNE
        print(f"  [L2] t-SNE sobre {n} nodos...")
        tsne = TSNE(n_components=2, perplexity=min(30, n-1), n_iter=500, random_state=42)
        Y = tsne.fit_transform(vv)
        
        # 5. K-means
        n_clusters = min(10, n)
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(Y)
        
        # 6. Asignar tokens
        cluster_tokens = {}
        for c in range(n_clusters):
            acciones_c = []
            for i, (zona, accion) in enumerate(zip(self.historial_campos, self.historial_acciones_l2)):
                if not zona: continue
                for nid, _, _ in zona:
                    if nid < len(labels) and labels[nid] == c:
                        acciones_c.append(accion)
            if acciones_c:
                from collections import Counter
                accion_comun = Counter(acciones_c).most_common(1)[0][0]
                cluster_tokens[c] = accion_comun % len(TOKEN2ID)
            else:
                cluster_tokens[c] = 0
        
        # 7. Entrenar decoder
        from experiments.train_l2_real import L2Decoder
        V = len(TOKEN2ID)
        dec = L2Decoder(128, V, lr)
        
        pares = []
        for zona, accion in zip(self.historial_campos, self.historial_acciones_l2):
            if not zona: continue
            for nid, omega, _ in zona:
                if nid < len(labels):
                    tid = cluster_tokens.get(labels[nid], 0)
                    pares.append((np.array(omega, dtype=float), tid))
        
        if not pares:
            return None
        
        for ep in range(epochs):
            random.shuffle(pares)
            losses = [dec.train(x, t) for x, t in pares]
            if ep % 10 == 0:
                print(f"  [L2] Epoch {ep}: loss={np.mean(losses):.4f}")
        
        self.l2_decoder = dec
        print(f"  [L2] Decoder entrenado con {n_clusters} clusters")
        return dec
    
    def _construir_coocurrencia(self):
        C = np.zeros((len(self.omega), len(self.omega)))
        for zona in self.historial_campos:
            if not zona: continue
            nodos = [n for n, _, _ in zona]
            for i in nodos:
                for j in nodos:
                    if i < len(self.omega) and j < len(self.omega):
                        C[i, j] += 1
        return C
    
    def _computar_pmi(self, C, eps=1e-10):
        total = C.sum()
        if total == 0: return np.zeros_like(C)
        P_ij = C / total
        P_i = C.sum(axis=1) / total
        P_j = C.sum(axis=0) / total
        PMI = np.zeros_like(C)
        for i in range(C.shape[0]):
            for j in range(C.shape[1]):
                if P_ij[i,j] > eps and P_i[i] > eps and P_j[j] > eps:
                    PMI[i,j] = math.log(P_ij[i,j] / (P_i[i] * P_j[j]))
        return PMI


# Compatibilidad
SGMAgent = SGMAgentCore