# -*- coding: utf-8 -*-
"""
sgm_core.py — SGM: Synthetic Graph Mind (Motor Cognitivo).

Core modularizado con TODOS los mecanismos integrados.
"""
import math, random, os, sys
import numpy as np

# Asegurar que experiments/ pueda importar sgm_lang desde la raíz
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
# También experiments/ por si acaso
_EXP = os.path.dirname(os.path.abspath(__file__))
if _EXP not in sys.path:
    sys.path.insert(0, _EXP)

from experiments.sgm_hdc import HDC, SensorBridge
from experiments.sgm_hrr import HRR
from experiments.sgm_ppr import ppr_route, ppr_inverso
from experiments.sgm_kuramoto import kuramoto_step, interferencia, campo_interferencia, promedio_ponderado, step_k_cadenas
from experiments.sgm_grafo import SGMAgent as SGMAgentGrafo
from experiments.sgm_lang import ID2TOKEN


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
        self._seed = 0
        self.objetos = {}
        self.meta_recordada = None
        
        # Kuramoto (consolidación)
        self.phi_root = 0.0
        self.eta_phase = 0.05
        self.theta_interf = 0.70
        self.consolidadas = set()
        self.theta_emerg_critico = 0.5
        
        # Place cells / navegación
        self.auto_registrar_place = True
        self.auto_navegar_meta = True
        self.place_bucket = 4
        self.mutacion_tasa = 0.05
        
        # Atributos para pulsiones
        self.instinto_alimentacion = None
        self.incertidumbre_acum = 0.0
        self.instinto_explorar_umbral = 3
        self.instinto_umbral_carencia = 0.3
        self.instinto_interaccion_fuerza = 0.7
        self.beta_supervivencia = 2.0
        self.beta_otras_compo = 0.3
        self.reencare_fuerza = 0.8
        self.drive_noop = 0.0
        self.drive_noop_umbral = 1.5
        self.drive_noop_fuerza = 1.0
        self.drive_noop_tasa = 0.1
        self.drive_noop_descarga = 0.5
        self.stagnation_ticks = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"
        self.necesidad_insatisfecha = False
        self.modo = "BASE"
        self.modo_ticks = 0
        self.ultima_accion = -1
        self.conteo_repeticion = 0
        self._ultima_accion_ejec = -1
        self.historial_acciones = []
        
        # L2
        self.l2_decoder = None
        self.historial_campos = []
        self.historial_acciones_l2 = []
        
        # Modelo de mundo
        self.modelo_mundo = {}
        self.ultimo_estado_q = None
        
        # Self-mod
        self.ultimo_food = None
        self.conteo_induccion = {}
    
    def set_arbitro(self, arbitro):
        self._arbitro = arbitro
    
    def set_edges(self, edges):
        self.edges = edges
    
    # ============ DECAIMIENTO DE VITALIDAD (Eq.5) ============
    
    def decaer_vitalidad(self):
        for i in range(len(self.vitalidad)):
            A = 1.0 if self.historial_acciones and self.historial_acciones[-1] == i else 0.0
            self.vitalidad[i] = self.vitalidad[i] * math.exp(-self.gamma_nodo) + A * (1 - math.exp(-self.gamma_nodo))
    
    # ============ PODA DE ARISTAS ============
    
    def podar_aristas(self, umbral=0.01):
        a_eliminar = []
        for clave, datos in list(self.conn_type.items()):
            if clave not in self.consolidadas:
                datos["age"] += 1
                datos["strength"] *= 0.999
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
        for i in range(len(self.phi)):
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(self.omega[i], self.omega[0]))) if self.omega else 0.0
            R = 1.0 / (1.0 + dist)
            delta = math.sin(self.phi_root - self.phi[i])
            self.phi[i] = (self.phi[i] + self.eta_phase * R * delta) % (2 * math.pi)
            
            I = interferencia(self.omega[i], self.phi[i], self.phi_root)
            if I > self.theta_interf:
                for j in self.edges.get(i, []):
                    self.consolidadas.add((i, j))
                    self.consolidadas.add((j, i))
    # ============ HEBB EN HOMEOSTASIS ============
    
    def hebb_homeostasis(self, food, health):
        if self.ultimo_food is not None:
            delta_food = food - self.ultimo_food
            if delta_food > 0:
                # Refuerzar acción → nodo 0 (supervivencia), no acción → acción
                if self.instinto_alimentacion is not None:
                    self.reforzar_arista(self.instinto_alimentacion, 0, 0.05)
        self.ultimo_food = food
    
    # ============ MODELO DE MUNDO ============
    
    def actualizar_modelo_mundo(self, estado_q, accion, siguiente_q):
        clave = (estado_q, accion)
        if clave not in self.modelo_mundo:
            self.modelo_mundo[clave] = {}
        self.modelo_mundo[clave][siguiente_q] = self.modelo_mundo[clave].get(siguiente_q, 0) + 1
    
    def predecir_transicion(self, estado_q, accion):
        clave = (estado_q, accion)
        if clave in self.modelo_mundo:
            transiciones = self.modelo_mundo[clave]
            if transiciones:
                return max(transiciones, key=transiciones.get)
        return None
    
    # ============ RAZONAMIENTO ============
    
    def inducir(self, a, b):
        clave = (a, b)
        if clave not in self.conteo_induccion:
            self.conteo_induccion[clave] = 0
        self.conteo_induccion[clave] += 1
        if self.conteo_induccion[clave] >= 3:
            self.reforzar_arista(a, b, 0.15)
            return {"evidencia": self.conteo_induccion[clave], "consolidada": True}
        return {"evidencia": self.conteo_induccion[clave], "consolidada": False}
    
    def deducir(self, a, b):
        if b not in self.edges.get(a, []):
            return False, []
        for vecino in self.edges.get(b, []):
            if vecino in self.edges.get(a, []):
                return True, [a, b, vecino]
        return False, []
    
    def abducir(self, resultado, topk=5):
        return ppr_inverso(self.edges, resultado, alpha=0.15, iters=30)
    
    # ============ TRAUMA NODAL ============
    
    def verificar_trauma(self):
        trauma = False
        for i in range(len(self.vitalidad)):
            if self.vitalidad[i] > 0.9 and i < len(self.phi):
                trauma = True
                # Aislar: desconectar de vecinos temporalmente
                for vecino in self.edges.get(i, []):
                    if vecino < len(self.vitalidad):
                        clave = (i, vecino)
                        self.consolidadas.discard(clave)
        return trauma
    
    # ============ SELF-MOD ============
    
    def auto_modificar(self, accion, resultado):
        if resultado > 0:
            self.vitalidad[accion] = min(1.0, self.vitalidad[accion] + resultado * 0.1)
        elif resultado < 0:
            self.vitalidad[accion] = max(0.0, self.vitalidad[accion] + resultado * 0.1)
    
    # ============ SUEÑO/RECONCILIACIÓN ============
    
    def reconciliar(self):
        for i in range(len(self.phi)):
            self.phi[i] = self.rng.uniform(0, 2 * math.pi)
        for i in range(len(self.vitalidad)):
            if self.vitalidad[i] < 0.05:
                self.vitalidad[i] = 0.0
    
    # ============ COMUNICACIÓN ============
    
    def generar_texto(self):
        if self.l2_decoder is None:
            return "..."
        from sgm_lang import ID2TOKEN
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
        self.hebb_homeostasis(food, health)
        self.verificar_trauma()
    
    # ============ STEP COMPLETO ============
    
    def step(self, state_semantic, valid_actions, food=None, health=None):
        # 1. Proyección
        om_r = self.hdc.project(state_semantic)
        self._seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        # 2. Homeostasis
        if food is not None and health is not None:
            self.actualizar_homeostasis(food, health)
        
        # 3. Percepción interna (sin Kuramoto, va aparte)
        self._percepcion_interna()
        
        # 4. Decaimiento + Kuramoto (UNA sola vez)
        self.decaer_vitalidad()
        self.actualizar_kuramoto()
        
        # 5. Navegación + objetos
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
        
        # 9. Poda ocasional
        if len(self.historial_acciones) % 50 == 0:
            self.podar_aristas()
        
        # 10. Guardar historial L2
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
        
        # Place cells (sin Kuramoto, va aparte)
        if self.auto_registrar_place and self._posicion_actual:
            px, py = self._posicion_actual
            bucket = (px // self.place_bucket, py // self.place_bucket)
            clave = f"P{bucket[0]}_{bucket[1]}|enf={self._algo_enfrente}"
            self.registrar_place_cell(clave, posicion=(px, py))
    
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
        
        # Drive noop (inline, sin depender de sgm_instintos)
        if accion == 0:
            self.drive_noop = min(self.drive_noop_umbral * 3, self.drive_noop + self.drive_noop_tasa)
        else:
            self.drive_noop = max(0.0, self.drive_noop - self.drive_noop_descarga)
        
        # Aprender conexión
        if self.ultima_accion >= 0 and accion != self.ultima_accion:
            self.aprender_conexion(self.ultima_accion, accion)
        
        # Necesidad insatisfecha (para PulsionDesplazamiento)
        self.necesidad_insatisfecha = self._hambre_real > 0.3 and self.ultima_accion == self.instinto_alimentacion
        
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
            "conn_type": {str(k): v for k, v in self.conn_type.items()},
            "scope_depth": self.scope_depth,
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
        self.conn_type = {eval(k): v for k, v in data.get("conn_type", {}).items()}
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
    
    # ============ L2 CON t-SNE ============
    
    def procesar_l2(self, epochs=50, lr=0.05):
        """Entrena L2 con los datos recolectados + t-SNE."""
        if len(self.historial_campos) < 10:
            print("  [L2] No hay suficientes datos")
            return None
        
        try:
            from sklearn.manifold import TSNE
            from sklearn.cluster import KMeans
            usar_sklearn = True
        except ImportError:
            usar_sklearn = False
        
        from sgm_lang import TOKEN2ID
        
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
        print(f"  [L2] t-SNE sobre {n} nodos (sklearn={usar_sklearn})...")
        if usar_sklearn:
            tsne = TSNE(n_components=2, perplexity=min(30, n-1), n_iter=500, random_state=42)
            Y = tsne.fit_transform(vv)
            n_clusters = min(10, n)
            km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            labels = km.fit_predict(Y)
        else:
            Y = self._tsne_puro(vv, n_components=2, perplexity=min(30, n-1))
            n_clusters = min(10, n)
            labels = self._kmeans(Y, k=n_clusters)
        
        # 5. Asignar tokens
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
        
        # 6. Entrenar decoder
        from experiments.train_l2_real import L2Decoder
        V = len(TOKEN2ID)
        dec = L2Decoder(128, V, lr)
        
        pares = []
        for zona, accion in zip(self.historial_campos, self.historial_acciones_l2):
            if not zona: continue
            for nid, omega, _ in zona:
                if nid < len(labels):
                    tid = cluster_tokens.get(labels[nid], 0)
                    pares.append((omega, tid))
        
        if not pares:
            return None
        
        for ep in range(epochs):
            random.shuffle(pares)
            losses = [dec.train(x, t) for x, t in pares]
            if ep % 10 == 0:
                print(f"  [L2] Epoch {ep}: loss={np.mean(losses):.4f}")
        
        self.l2_decoder = dec
        return dec
    
    def _tsne_puro(self, X, n_components=2, perplexity=30, n_iter=300, lr=200):
        """t-SNE puro (sin sklearn)."""
        n = X.shape[0]
        if n < 2: return X[:, :n_components]
        Y = np.random.randn(n, n_components) * 0.01
        
        P = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    dist = np.sum((X[i] - X[j]) ** 2)
                    P[i, j] = math.exp(-dist / (2 * perplexity ** 2))
        P = P / P.sum()
        
        for it in range(n_iter):
            Q = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i != j:
                        dist = np.sum((Y[i] - Y[j]) ** 2)
                        Q[i, j] = 1 / (1 + dist)
            Q = Q / Q.sum()
            grad = np.zeros_like(Y)
            for i in range(n):
                for j in range(n):
                    if i != j:
                        dist_y = np.sum((Y[i] - Y[j]) ** 2)
                        grad[i] += 4 * (P[i, j] - Q[i, j]) * (Y[i] - Y[j]) / (1 + dist_y)
            Y -= lr * grad
        
        return Y
    
    def _kmeans(self, X, k=10, n_iter=50):
        """K-means simple."""
        n = X.shape[0]
        idx = random.sample(range(n), min(k, n))
        centers = X[idx]
        labels = np.zeros(n, dtype=int)
        
        for _ in range(n_iter):
            for i in range(n):
                dists = [np.sum((X[i] - c) ** 2) for c in centers]
                labels[i] = int(np.argmin(dists))
            new_centers = np.zeros_like(centers)
            counts = np.zeros(k)
            for i in range(n):
                new_centers[labels[i]] += X[i]
                counts[labels[i]] += 1
            for j in range(k):
                if counts[j] > 0:
                    new_centers[j] /= counts[j]
            centers = new_centers
        
        return labels


SGMAgent = SGMAgentCore