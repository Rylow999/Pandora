# -*- coding: utf-8 -*-
"""sgm_core.py — SGM: Synthetic Graph Mind (Motor Cognitivo).

Core modularizado con TODOS los mecanismos integrados.
"""
import math, random, os, sys
import numpy as np

# Fix path para importar módulos del proyecto
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path: sys.path.insert(0, _RAIZ)

from sgm.core.sgm_hdc import HDC, SensorBridge
from sgm.core.sgm_hrr import HRR
from sgm.core.sgm_ppr import ppr_route, ppr_inverso
from sgm.core.sgm_kuramoto import interferencia, campo_interferencia
from sgm.core.sgm_grafo import SGMAgent as SGMAgentGrafo
from sgm.core.sgm_lang import ID2TOKEN, TOKEN2ID
from sgm.core.minecraft_actions import ACCIONES_MOVIMIENTO, ACCIONES_INTERACCION, NOMBRE

# Mapeo acción de Minecraft → token semántico (para entrenar L2)
ACCION2TOKEN = {
    0:  TOKEN2ID.get('quieto', 0),
    1:  TOKEN2ID.get('adelante', 0),
    2:  TOKEN2ID.get('atras', 0),
    3:  TOKEN2ID.get('izquierda', 0),
    4:  TOKEN2ID.get('derecha', 0),
    5:  TOKEN2ID.get('saltar', 0),
    6:  TOKEN2ID.get('agacharse', 0),
    7:  TOKEN2ID.get('atacar', 0),
    8:  TOKEN2ID.get('usar', 0),
    9:  TOKEN2ID.get('craftear', 0),
    10: TOKEN2ID.get('equipar', 0),
    11: TOKEN2ID.get('minar', 0),
    12: TOKEN2ID.get('colocar', 0),
}


class SGMAgentCore(SGMAgentGrafo):
    def __init__(self, rng=None, D=128, n_nodes=64, gamma=0.01):
        super().__init__(rng, D, n_nodes)
        self.rng = rng or random.Random(42)
        self.D = D; self.gamma = gamma
        self.hdc = HDC(self.rng, D)
        self.hrr = HRR(D, self.rng, n_nodes)
        self.sensor = SensorBridge(D)
        self._arbitro = None
        # Homeostasis
        self.gamma_nodo = gamma
        self.E = 0.0; self.E_acumulado = 0.0
        self._hambre_real = 0.0; self._amenaza = 0.0; self._algo_enfrente = 0
        self._posicion_actual = None; self._hay_gradiente = False; self._gradiente_dir = (0, 0)
        self._config_grad = {"activo": False, "fuerza": 0.0}; self._config_curio = {"activo": False, "fuerza": 0.0}
        self._inc_dirs = {}; self._seed = 0; self.objetos = {}; self.meta_recordada = None
        # Kuramoto
        self.phi_root = 0.0; self.eta_phase = 0.15; self.theta_interf = 0.70
        self.consolidadas = set(); self.theta_emerg_critico = 0.5
        # Pulsiones
        self.instinto_alimentacion = None; self.incertidumbre_acum = 0.0
        self.instinto_explorar_umbral = 0.5; self.instinto_umbral_carencia = 0.3
        self.instinto_interaccion_fuerza = 0.7; self.beta_supervivencia = 2.0
        self.beta_otras_compo = 0.3; self.reencare_fuerza = 0.8
        self.drive_noop = 0.0; self.drive_noop_umbral = 1.5; self.drive_noop_fuerza = 1.0
        self.drive_noop_tasa = 0.1; self.drive_noop_descarga = 0.5
        self.conteo_noop = 0
        self.stagnation_ticks = 0; self.doubt_cooldown = 0; self.status = "ACTIVA"
        self.necesidad_insatisfecha = False
        self.acciones_movimiento = ACCIONES_MOVIMIENTO
        self.acciones_interaccion = ACCIONES_INTERACCION
        self.theta_emerg_critico = 0.5
        self.auto_registrar_place = True; self.auto_navegar_meta = True
        self.place_bucket = 16  # un chunk de Minecraft (16x16x16 bloques)
        self.mutacion_tasa = 0.05
        self.modo = "BASE"; self.modo_ticks = 0; self.ultima_accion = -1; self.conteo_repeticion = 0
        self._ultima_accion_ejec = -1; self.historial_acciones = []
        # L2 + modelo mundo + self-mod
        self.l2_decoder = None; self.historial_campos = []; self.historial_acciones_l2 = []
        self.historial_metas_l2 = []  # metas (razon->token) por paso, para L2
        self._meta_pendiente = None  # meta a asociar en el proximo step
        self.modelo_mundo = {}; self.ultimo_estado_q = None
        self.ultimo_food = None; self.conteo_induccion = {}

    # ============ DECAIMIENTO DE VITALIDAD (Eq.5) ============
    def decaer_vitalidad(self, k=3):
        # Recompensar los k nodos más cercanos a la percepción actual (top-k),
        # no solo el seed exacto (evita el 'parpadeo' cuando la percepción varía
        # y el seed salta entre nodos)
        distancias = [(i, math.sqrt(sum((a - b) ** 2 for a, b in zip(self.omega[i], self.omega[self._seed]))))
                      for i in range(len(self.omega)) if i != self._seed]
        distancias.sort(key=lambda x: x[1])
        top_k = {self._seed} | {i for i, _ in distancias[:k]}

        for i in range(len(self.vitalidad)):
            A = 1.0 if i in top_k else 0.0
            self.vitalidad[i] = self.vitalidad[i] * math.exp(-self.gamma_nodo) + A * (1 - math.exp(-self.gamma_nodo))

    # ============ AISLAMIENTO DE NODOS ============
    def isolate_node(self, concept: str):
        """Aísla un nodo del grafo temporalmente para proteger la identidad."""
        # Buscar el nodo por place_cells
        node_idx = None
        for ctx, pid in self.place_cells.items():
            if concept in ctx:
                node_idx = pid
                break
        
        if node_idx is None:
            return False
        
        # Reducir vitalidad drásticamente
        self.vitalidad[node_idx] *= 0.1
        
        # Eliminar conexiones temporales
        if node_idx in self.edges:
            self.edges[node_idx] = set()
        
        # Eliminar conexiones entrantes
        for src in list(self.edges.keys()):
            if node_idx in self.edges[src]:
                self.edges[src].remove(node_idx)
        
        # Marcar como aislado
        if not hasattr(self, 'isolated_nodes'):
            self.isolated_nodes = set()
        self.isolated_nodes.add(node_idx)
        
        return True

    # ============ PODA DE ARISTAS ============
    def podar_aristas(self, umbral=0.01):
        a_eliminar = []
        for clave, datos in list(self.conn_type.items()):
            if clave not in self.consolidadas:
                datos["age"] += 1; datos["strength"] *= 0.999
                if datos["strength"] < umbral and datos["age"] > 100: a_eliminar.append(clave)
        for clave in a_eliminar:
            if clave in self.conn_type:
                del self.conn_type[clave]; a, b = clave
                if b in self.edges.get(a, []): self.edges[a].remove(b)
                if a in self.edges.get(b, []): self.edges[b].remove(a)

    # ============ KURAMOTO (Eq.3) ============
    def actualizar_kuramoto(self):
        for i in range(len(self.phi)):
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(self.omega[i], self.omega[0]))) if self.omega else 0.0
            R = 1.0 / (1.0 + dist); delta = math.sin(self.phi_root - self.phi[i])
            self.phi[i] = (self.phi[i] + self.eta_phase * R * delta) % (2 * math.pi)
            I = interferencia(self.omega[i], self.phi[i], self.phi_root)
            if I > self.theta_interf:
                for j in self.edges.get(i, []):
                    clave = (i, j)
                    strength = self.conn_type.get(clave, {}).get("strength", 0)
                    if strength > 0.2:  # solo consolidar aristas con uso real
                        self.consolidadas.add(clave)
                        self.consolidadas.add((j, i))

    # ============ HEBB EN HOMEOSTASIS ============
    def hebb_homeostasis(self, food, health):
        if self.ultimo_food is not None:
            delta_food = food - self.ultimo_food
            if delta_food > 0 and self.instinto_alimentacion is not None:
                self.reforzar_arista(self.instinto_alimentacion, 0, 0.05)
                # Recordar dónde se comió SOLO si la acción previa fue comer
                # (no sobreescribir por regeneración natural de comida en MC)
                if (self._posicion_actual is not None
                        and self.ultima_accion == self.instinto_alimentacion):
                    self.meta_recordada = self._posicion_actual
        self.ultimo_food = food

    # ============ HOMEOSTASIS ============
    def actualizar_homeostasis(self, food, health):
        food = float(food); health = float(health) if health is not None else 20.0
        factor_cuerpo = max(0.05, health / 20.0)
        # V_grafo: promedio de los nodos ACTIVOS (vitalidad > umbral).
        # Promediar TODOS los nodos colapsa V_grafo a piso porque los conceptos
        # dormidos decaen naturalmente a 0, arrastrando la homeostasis -> dispara
        # 'comer' infinitamente aunque el agente tenga comida.
        activos = [v for v in self.vitalidad if v > 0.1]
        if activos:
            self.V_grafo = (sum(activos) / len(activos)) * factor_cuerpo
        else:
            self.V_grafo = factor_cuerpo  # nada activo: solo cuerpo
        self._hambre_real = max(0.0, 1.0 - food / 20.0)
        self._amenaza = max(0.0, (20.0 - health) / 20.0) if health < 15 else 0.0
        self.E = max(0.0, self._hambre_real + self._amenaza)
        self.E_acumulado = self.E_acumulado * 0.95 + self.E
        self.hebb_homeostasis(food, health); self.verificar_trauma()

    # ============ TRAUMA ============
    def verificar_trauma(self):
        trauma = False
        for i in range(len(self.vitalidad)):
            if self.vitalidad[i] > 0.9 and i < len(self.phi):
                trauma = True
                for vecino in self.edges.get(i, []): self.consolidadas.discard((i, vecino))
        return trauma

    # ============ SUEÑO ============
    def reconciliar(self):
        for i in range(len(self.phi)): self.phi[i] = self.rng.uniform(0, 2 * math.pi)
        for i in range(len(self.vitalidad)):
            if self.vitalidad[i] < 0.05: self.vitalidad[i] = 0.0

    # ============ RAZONAMIENTO ============
    def inducir(self, a, b):
        clave = (a, b); self.conteo_induccion[clave] = self.conteo_induccion.get(clave, 0) + 1
        if self.conteo_induccion[clave] >= 3:
            self.reforzar_arista(a, b, 0.15); return {"evidencia": self.conteo_induccion[clave], "consolidada": True}
        return {"evidencia": self.conteo_induccion[clave], "consolidada": False}

    def deducir(self, a, b):
        if b not in self.edges.get(a, []): return False, []
        for vecino in self.edges.get(b, []):
            if vecino in self.edges.get(a, []): return True, [a, b, vecino]
        return False, []

    def abducir(self, resultado, topk=5): return ppr_inverso(self.edges, resultado, alpha=0.15, iters=30)

    # ============ MODELO DE MUNDO ============
    def actualizar_modelo_mundo(self, estado_q, accion, siguiente_q):
        clave = (estado_q, accion)
        if clave not in self.modelo_mundo: self.modelo_mundo[clave] = {}
        self.modelo_mundo[clave][siguiente_q] = self.modelo_mundo[clave].get(siguiente_q, 0) + 1

    def predecir_transicion(self, estado_q, accion):
        clave = (estado_q, accion)
        if clave in self.modelo_mundo and self.modelo_mundo[clave]:
            return max(self.modelo_mundo[clave], key=self.modelo_mundo[clave].get)
        return None

    # ============ SELF-MOD ============
    def auto_modificar(self, accion, resultado):
        self.vitalidad[accion] = max(0.0, min(1.0, self.vitalidad[accion] + resultado * 0.1))

    # ============ PERSISTENCIA ============
    def guardar(self, ruta):
        np.save(ruta, {
            "omega": self.omega, "phi": self.phi, "vitalidad": self.vitalidad,
            "es_place_cell": self.es_place_cell, "edges": self.edges,
            "conn_type": {str(k): v for k, v in self.conn_type.items()},
            "scope_depth": self.scope_depth, "place_cells": self.place_cells,
            "place_pos": self.place_pos, "V_grafo": self.V_grafo,
            "E_acumulado": self.E_acumulado, "historial_campos": self.historial_campos[-1000:],
            "historial_acciones_l2": self.historial_acciones_l2[-1000:],
            "historial_metas_l2": self.historial_metas_l2[-1000:]})

    def cargar(self, ruta):
        if not os.path.exists(ruta): return False
        d = np.load(ruta, allow_pickle=True).item()
        for k in ["omega","phi","vitalidad","es_place_cell","edges","scope_depth","place_cells","place_pos","V_grafo","E_acumulado","historial_campos","historial_acciones_l2","historial_metas_l2"]:
            if k in d: setattr(self, k, d[k])
        self.conn_type = {eval(k): v for k, v in d.get("conn_type", {}).items()}
        return True

    # ============ L2 ============
    def set_l2_decoder(self, decoder): self.l2_decoder = decoder

    def generar_texto(self):
        if self.l2_decoder is None: return "..."
        zona = campo_interferencia(self.omega, self.phi, self.phi_root, self.vitalidad)
        if not zona: return "..."
        palabras = []
        for _, omega, I in zona[:5]:
            top = self.l2_decoder.decodificar(np.array(omega) * I, topk=1)
            if top: palabras.append(ID2TOKEN.get(top[0][0], "?"))
        return " ".join(palabras) if palabras else "..."

    def procesar_l2(self, epochs=50, lr=0.05):
        if len(self.historial_campos) < 10: return None
        try:
            from sklearn.manifold import TSNE; from sklearn.cluster import KMeans
            usar_sklearn = True
        except ImportError: usar_sklearn = False
        C = self._construir_coocurrencia(); n = C.shape[0]
        PMI = self._computar_pmi(C)
        U, S, _ = np.linalg.svd(PMI, full_matrices=False); vv = U[:, :min(32, n)] * S[:min(32, n)]
        if usar_sklearn:
            import inspect
            kwargs = {"n_components": 2, "perplexity": min(30, n-1), "random_state": 42}
            # Compatibilidad: n_iter (sklearn<1.1) vs max_iter (sklearn>=1.1)
            tsne_params = inspect.signature(TSNE.__init__).parameters
            if "max_iter" in tsne_params: kwargs["max_iter"] = 500
            else: kwargs["n_iter"] = 500
            Y = TSNE(**kwargs).fit_transform(vv)
            labels = KMeans(n_clusters=min(10, n), random_state=42, n_init=10).fit_predict(Y)
        else:
            Y = self._tsne_puro(vv, perplexity=min(30, n-1)); labels = self._kmeans(Y, k=min(10, n))
        cluster_tokens = {}
        for c in range(len(set(labels))):
            acciones_c = [a for z, a in zip(self.historial_campos, self.historial_acciones_l2)
                          if z for nid, _, _ in z if nid < len(labels) and labels[nid] == c]
            if acciones_c:
                accion_mas_comun = max(set(acciones_c), key=acciones_c.count)
                cluster_tokens[c] = ACCION2TOKEN.get(accion_mas_comun, TOKEN2ID.get('explorar', 0))
        from experiments.sgm_l2_system import L2Decoder
        dec = L2Decoder(128, lr)
        pares = [(omega, cluster_tokens.get(labels[nid], TOKEN2ID.get('explorar', 0)))
                 for z, a in zip(self.historial_campos, self.historial_acciones_l2)
                 for nid, omega, _ in z if nid < len(labels)]
        if not pares: return None
        for _ in range(epochs):
            random.shuffle(pares)
            for omega, tid in pares: dec.entrenar(omega, tid)
        self.l2_decoder = dec; return dec

    def _construir_coocurrencia(self):
        n = len(self.omega); C = np.zeros((n, n))
        for zona in self.historial_campos:
            if not zona: continue
            nodos = [nid for nid, _, _ in zona if nid < n]
            for i in nodos:
                for j in nodos: C[i, j] += 1
        return C

    def _computar_pmi(self, C, eps=1e-10):
        total = C.sum()
        if total == 0: return np.zeros_like(C)
        P = C / total; Pi = C.sum(axis=1) / total; Pj = C.sum(axis=0) / total
        ratio = P / (Pi[:, None] * Pj[None, :] + eps)
        # PPMI: log del ratio, truncando a 0 los no-positivos
        # (log(ratio<=1) < 0 = ruido; PPMI los mapea a 0 exacto)
        with np.errstate(divide='ignore', invalid='ignore'):
            ppm = np.log(ratio + eps)
        ppm[ppm < 0] = 0.0
        return ppm

    def _tsne_puro(self, X, n_components=2, perplexity=30, n_iter=300, lr=200):
        n = X.shape[0]; Y = np.random.randn(n, n_components) * 0.01
        P = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j: P[i, j] = math.exp(-np.sum((X[i] - X[j]) ** 2) / (2 * perplexity ** 2))
        P = P / P.sum()
        for _ in range(n_iter):
            Q = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i != j: Q[i, j] = 1 / (1 + np.sum((Y[i] - Y[j]) ** 2))
            Q = Q / Q.sum()
            grad = np.zeros_like(Y)
            for i in range(n):
                for j in range(n):
                    if i != j: grad[i] += 4 * (P[i, j] - Q[i, j]) * (Y[i] - Y[j]) / (1 + np.sum((Y[i] - Y[j]) ** 2))
            Y -= lr * grad
        return Y

    def _kmeans(self, X, k=10, n_iter=50):
        centers = X[random.sample(range(X.shape[0]), min(k, X.shape[0]))]
        labels = np.zeros(X.shape[0], dtype=int)
        for _ in range(n_iter):
            for i in range(X.shape[0]): labels[i] = int(np.argmin([np.sum((X[i] - c) ** 2) for c in centers]))
            new = np.zeros_like(centers); counts = np.zeros(k)
            for i in range(X.shape[0]): new[labels[i]] += X[i]; counts[labels[i]] += 1
            for j in range(k):
                if counts[j] > 0: new[j] /= counts[j]
            centers = new
        return labels

    # ============ NAVEGACIÓN ============
    def _navegacion_y_objetos(self):
        if self.auto_navegar_meta and self._hambre_real > 0.2 and self.meta_recordada is not None:
            mx, my, mz = self.meta_recordada[:3] if len(self.meta_recordada) == 3 else (*self.meta_recordada, 0)
            if self._posicion_actual is not None:
                cxp, cyp, czp = self._posicion_actual[:3] if len(self._posicion_actual) == 3 else (*self._posicion_actual, 0)
                if abs(mx - cxp) + abs(my - cyp) + abs(mz - czp) > 1:
                    dx = 1 if mx > cxp else (-1 if mx < cxp else 0)
                    dy = 1 if my > cyp else (-1 if my < cyp else 0)
                    dz = 1 if mz > czp else (-1 if mz < czp else 0)
                    self._accion_meta = self._direccion_a_accion(dx, dy, dz)
                else: self._accion_meta = None

    def _direccion_a_accion(self, dx, dy, dz=0):
        """
        Convierte direccion 3D a accion de movimiento de Minecraft.
        El eje Y (saltar/agacharse) SOLO prioriza cuando la diferencia
        vertical es clara (|dy| >= 2). Con |dy|=1, el movimiento horizontal
        predomina: en Minecraft avanzar horizontal sube escalones solos, y
        saltar con dy=1 de ruido provoca el bucle 'solo salta'.
        """
        abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)
        if abs_dy >= 2 and abs_dy >= abs_dx and abs_dy >= abs_dz:
            if dy > 0: return 5   # JUMP (subir)
            if dy < 0: return 6   # SNEAK (bajar/agacharse)
        # Plano horizontal (prioriza al no estar Y claro)
        if abs_dx >= abs_dz:
            if dx > 0: return 4   # RIGHT (este)
            if dx < 0: return 3   # LEFT (oeste)
        if abs_dz > 0:
            if dz > 0: return 1   # FORWARD (sur)
            if dz < 0: return 2   # BACK (norte)
        return 0  # NOOP

    def _elegir_accion_ppp(self, valid_actions):
        rank = ppr_route(self.edges, self._seed, self._aff, alpha=0.15, iters=30)
        best, bv = -1, -2.0
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                if score > bv: bv, best = score, a
        return best if best >= 0 else valid_actions[0]

    def aprender_conexion(self, a, b): self.reforzar_arista(a, b, 0.1)

    def registrar_meta(self, razon):
        """Registra la meta decidida (razon) para el proximo step.
        El L2 asocia cada estado percibido con la meta elegida (no una accion 0-16)."""
        tid = TOKEN2ID.get(razon, TOKEN2ID.get('explorar', 0))
        self._meta_pendiente = tid

    # ============ STEP COMPLETO ============
    def step(self, state_semantic, valid_actions, food=None, health=None):
        food_anterior = self.ultimo_food
        
        # 1. Proyección semántica
        om_r = self.hdc.project(state_semantic)
        self._seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        # 2. Homeostasis
        if food is not None and health is not None: self.actualizar_homeostasis(food, health)
        
        # 3. Modo (BASE/SUPERVIVENCIA)
        necesidad_critica = max(self._hambre_real, self._amenaza)
        self.modo = "SUPERVIVENCIA" if necesidad_critica > self.theta_emerg_critico else "BASE"
        self.modo_ticks += 1
        
        # 4. Place cells (3D)
        if self.auto_registrar_place and self._posicion_actual:
            px, py, pz = self._posicion_actual[:3] if len(self._posicion_actual) == 3 else (*self._posicion_actual, 0)
            bucket = (px // self.place_bucket, py // self.place_bucket, pz // self.place_bucket)
            # Incluir contexto para diferenciar lugares (bioma, hora, bloque enfrente)
            contexto = f"P{bucket[0]}_{bucket[1]}_{bucket[2]}|bioma={getattr(self, '_bioma', 'plains')}|hora={getattr(self, '_hora', 0)}|enf={self._algo_enfrente}"
            self.registrar_place_cell(contexto, (px, py, pz))
        
        # 5. Decaimiento + Kuramoto
        self.decaer_vitalidad(); self.actualizar_kuramoto()
        
        # 6. Navegación + objetos
        self._navegacion_y_objetos()
        
        # 7. Arbitro
        if self._arbitro is not None:
            accion = self._arbitro.elegir(self, valid_actions)
        else:
            accion = self._elegir_accion_ppp(valid_actions)
        
        # 8. Post-acción
        self._post_accion(accion)
        
        # 9. Auto-mod
        if food is not None:
            delta = food - (food_anterior or food)
            self.auto_modificar(accion, delta)
        
        # 10. Poda ocasional
        if len(self.historial_acciones) % 50 == 0: self.podar_aristas()
        
        # 11. Historial L2
        zona = campo_interferencia(self.omega, self.phi, self.phi_root, self.vitalidad)
        self.historial_campos.append(zona)
        self.historial_acciones_l2.append(accion)
        # meta: usar la ultima registrada o por defecto 'explorar'
        meta_id = getattr(self, '_meta_pendiente', None)
        if meta_id is None:
            meta_id = TOKEN2ID.get('explorar', 0)
        self.historial_metas_l2.append(meta_id)
        self._meta_pendiente = None
        
        # 12. Mutar place cell activo si se está en el mismo lugar un rato
        # (no solo si accion==noop; en MC puedes estar quieto cayendo, en agua, etc.)
        if self.place_activo >= 0:
            if not hasattr(self, '_place_ticks'): self._place_ticks = 0
            if getattr(self, '_ultimo_place_activo', -1) == self.place_activo:
                self._place_ticks += 1
            else:
                self._place_ticks = 0
                self._ultimo_place_activo = self.place_activo
            # Mutar solo si estuvimos en este lugar un rato (>= 3 pasos)
            if self._place_ticks >= 3:
                señal = max(0.0, min(1.0, self.V_grafo))
                self.mutar_omega_lugar(señal, tasa=self.mutacion_tasa)
        
        return accion

    def _post_accion(self, accion):
        self.historial_acciones.append(accion)
        # Drive noop (SEEKING): urgencia creciente con noops consecutivos.
        # Cada noop acumula mas (2x, 3x...), para que el empuje a moverse
        # supere al descanso aunque haya un 'adelante' ocasional que descargue.
        if accion == 0:
            self.conteo_noop = getattr(self, 'conteo_noop', 0) + 1
            incremento = self.drive_noop_tasa * min(3, self.conteo_noop)  # 0.1, 0.2, 0.3
            self.drive_noop = min(self.drive_noop_umbral * 3, self.drive_noop + incremento)
        else:
            self.conteo_noop = 0
            self.drive_noop = max(0.0, self.drive_noop - self.drive_noop_descarga)
        # Aprender conexión
        if self.ultima_accion >= 0 and accion != self.ultima_accion:
            self.aprender_conexion(self.ultima_accion, accion)
        # Necesidad insatisfecha
        self.necesidad_insatisfecha = self._hambre_real > 0.3 and self.ultima_accion == self.instinto_alimentacion
        # Repetición → stagnation
        if accion == self.ultima_accion:
            self.conteo_repeticion += 1
            self.stagnation_ticks += 1
        else:
            self.conteo_repeticion = 0
            self.stagnation_ticks = 0
        self.ultima_accion = accion
        # Duda + recuperación
        if self.doubt_cooldown > 0: self.doubt_cooldown -= 1
        if self.status == "INCONCLUSA" and self.stagnation_ticks < 5:
            self.status = "ACTIVA"  # recuperación
        elif self.status == "ACTIVA" and self.stagnation_ticks > 20:
            self.status = "INCONCLUSA"; self.doubt_cooldown = 10


SGMAgent = SGMAgentCore