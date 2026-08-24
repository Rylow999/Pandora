# -*- coding: utf-8 -*-
"""sgm_grafo.py — Grafo SGM: nodos, aristas, place cells, herencia conceptual.

Omega inmutable para conceptos, mutable para place cells.
"""
import math, random


class SGMAgent:
    """Agente SGM con grafo de conceptos."""
    
    def __init__(self, rng, D=128, n_nodes=32):
        self.D = D
        self.rng = rng
        
        # Estructuras del grafo
        self.omega = [[rng.gauss(0, 1) for _ in range(D)] for _ in range(n_nodes)]
        self.vitalidad = [1.0 for _ in range(n_nodes)]
        self.es_place_cell = [False for _ in range(n_nodes)]
        self.edges = {i: [] for i in range(n_nodes)}
        
        # Place cells
        self.place_cells = {}
        self.place_pos = {}
        self.place_activo = -1
        self.place_clave = 0
        
        # Resolución
        self.resolucion_nivel = [0] * n_nodes
        self.scope_depth = [0] * n_nodes
        self.parent_of = {}
        
        # Estado
        self.phi = [rng.uniform(0, 2 * math.pi) for _ in range(n_nodes)]
        self.modo = "BASE"
        self.modo_ticks = 0
        self.ultima_accion = -1
        self.conteo_repeticion = 0
        self.historial_acciones = []
        
        # Homeostasis
        self.V_grafo = 1.0
        
        # Percepción interna
        self._hambre_real = 0.0
        self._amenaza = 0.0
        self._algo_enfrente = 0
        self._posicion_actual = None
        self._hay_gradiente = False
        self._gradiente_dir = (0, 0)
        self._config_grad = {"activo": False, "fuerza": 0.0}
        self._config_curio = {"activo": False, "fuerza": 0.0}
        self._inc_dirs = {}
        
        # Arbitro (hook externo)
        self._arbitro = None
        self.conn_type = {}  # {(nodo, vecino): {"count", "tipo", "strength", "age"}}
    
    def set_edges(self, edges):
        """Configura las aristas del grafo."""
        self.edges = edges
    
    def crear_nodo(self, es_place_cell=False):
        """Crea un nuevo nodo en el grafo."""
        idx = len(self.omega)
        nuevo = [self.rng.gauss(0, 1) for _ in range(self.D)]
        norm = math.sqrt(sum(x*x for x in nuevo)) or 1.0
        self.omega.append([x/norm for x in nuevo])
        self.vitalidad.append(0.5)
        self.es_place_cell.append(es_place_cell)
        self.edges[idx] = []
        self.phi.append(self.rng.uniform(0, 2 * math.pi))
        self.scope_depth.append(0)
        self.resolucion_nivel.append(0)
        return idx
    
    def crear_arista(self, a, b):
        """Crea una arista entre dos nodos."""
        if a == b:
            return
        if a not in self.edges:
            self.edges[a] = []
        if b not in self.edges:
            self.edges[b] = []
        if b not in self.edges[a]:
            self.edges[a].append(b)
        if a not in self.edges[b]:
            self.edges[b].append(a)
    
    def reforzar_arista(self, a, b, fuerza=0.1):
        """
        Refuerza una arista: crea si no existe, incrementa strength y tipo.
        Lógica de conn_type: Functional (0) → Causal (1) por uso repetido.
        """
        if a >= len(self.omega) or b >= len(self.omega):
            return
        
        # Crear arista si no existe
        self.crear_arista(a, b)
        
        # Reforzar vitalidad
        self.vitalidad[a] = min(1, self.vitalidad[a] + fuerza)
        self.vitalidad[b] = min(1, self.vitalidad[b] + fuerza)
        
        # Lógica de conn_type
        clave = (a, b)
        if clave not in self.conn_type:
            self.conn_type[clave] = {"count": 0, "tipo": 0, "strength": 1.0, "age": 0}
        
        self.conn_type[clave]["count"] += 1
        c = self.conn_type[clave]["count"]
        
        if c > 5:
            self.conn_type[clave]["tipo"] = 1  # Causal
        elif c > 2:
            self.conn_type[clave]["tipo"] = 0  # Functional
        
        self.conn_type[clave]["strength"] = min(1.0, self.conn_type[clave]["strength"] + fuerza)
        self.conn_type[clave]["age"] = 0
    
    def aprender_conexion(self, a, b):
        """Aprende conexión entre acción a y accion b (co-ocurrencia)."""
        self.reforzar_arista(a, b, 0.1)
    
    def _mutar_omega(self, nuevo, idx, es_place_cell=False):
        """Mutar omega de forma segura. Solo place cells pueden mutar."""
        if idx >= len(self.omega):
            return
        if es_place_cell or (idx < len(self.es_place_cell) and self.es_place_cell[idx]):
            self.omega[idx] = nuevo
    
    # ============ PLACE CELLS ============
    
    def registrar_place_cell(self, obs_clave, posicion=None):
        """Registra o recupera un place cell."""
        if obs_clave in self.place_cells:
            self.place_activo = self.place_cells[obs_clave]
            return self.place_activo
        
        idx = self.crear_nodo(es_place_cell=True)
        self.place_cells[obs_clave] = idx
        if posicion:
            self.place_pos[idx] = tuple(int(v) for v in posicion)
        self.place_activo = idx
        self.place_clave += 1
        return idx
    
    def mutar_omega_lugar(self, señal_resultado, tasa=0.05):
        """Muta el omega del place cell activo."""
        if self.place_activo < 0 or self.place_activo >= len(self.omega):
            return
        if not self.es_place_cell[self.place_activo]:
            return
        
        om = self.omega[self.place_activo]
        for j in range(self.D):
            om[j] += tasa * (señal_resultado - om[j])
        norm = math.sqrt(sum(x*x for x in om)) or 1.0
        for j in range(self.D):
            om[j] /= norm
    
    # ============ HERENCIA ============
    
    def heredar_concepto(self, padre, nombre_hijo=None):
        """Crea un nodo hijo como especialización del padre."""
        hijo_id = len(self.omega)
        padre_vec = self.omega[padre] if padre < len(self.omega) else [0.0] * self.D
        delta = [self.rng.gauss(0, 0.10) for _ in range(self.D)]
        hijo_vec = [padre_vec[i] + delta[i] for i in range(self.D)]
        norm = math.sqrt(sum(x*x for x in hijo_vec)) or 1.0
        hijo_vec = [x/norm for x in hijo_vec]
        
        self.crear_nodo(es_place_cell=False)
        self.omega[hijo_id] = hijo_vec
        self.es_place_cell[hijo_id] = False
        self.scope_depth[hijo_id] = self.scope_depth[padre] + 1
        self.parent_of[hijo_id] = padre
        return hijo_id
    
    # ============ ARBITRO ============
    
    def set_arbitro(self, arbitro):
        """Configura el arbitro externo."""
        self._arbitro = arbitro
    
    def elegir_accion(self, valid_actions):
        """Elige acción usando el arbitro o PPR directo."""
        if self._arbitro is not None:
            return self._arbitro.elegir(self, valid_actions)
        
        # Fallback: PPR directo desde nodo 0
        from sgm_ppr import ppr_route
        rank = ppr_route(self.edges, 0, self._aff, alpha=0.15, iters=10)
        
        best, bv = -1, -2.0
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                if score > bv:
                    bv, best = score, a
        
        return best if best >= 0 else valid_actions[0]
    
    def _aff(self, a, b):
        """Afinidad entre nodos (para PPR). No colapsa a 0 ante vitalidad baja."""
        if a >= len(self.omega) or b >= len(self.omega):
            return 0.0
        dist = math.sqrt(sum((x - y) ** 2 for x, y in zip(self.omega[a], self.omega[b])))
        # Afinidad semántica + mínimo piso de vitalidad para que PPR no colapse
        return math.exp(-5.0 * dist) * max(self.vitalidad[b], 0.1)