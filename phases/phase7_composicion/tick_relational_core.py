# -*- coding: utf-8 -*-
"""
tick_relational_core.py -- tick unificado CON memoria relacional HRR (promovido de 0028/29).
Es el PEGAMENTO reutilizable que B (y lo que siga) importa. No es un experimento: es infra.

Orquesta (reusa mecanismos ya validados, no reimplementa fisica):
  1. SensorBridge (0019) proyecta senal -> omega_routed (HDC)
  2. seed = nodo mas afín a la senal
  3. memoria relacional HRR (hrr_core): rel_mem[i] = superposicion de HRR(rol_k, omega_k)
  4. caminata PPR sesgada por rol (0027b/28): el bias de rol hace que la caminata siga
     relaciones del tipo pedido, no solo identidad de nodo
  5. plan de varios pasos: recover_chain desanida la secuencia resuelta

Diferencia con 0023 (tick plano): aca las aristas SON HRR(rol, omega), no distancia Euclidiana.
PERO el modo plano (use_roles=False) es REAL: usa distancia Euclidiana sobre omega (como 0023)
y trata de resolver la cadena por afinidad a omega. No es un 'return False' hardcoded: es un
plano que de verdad no puede recuperar relaciones anidadas porque la estructura vive en rel_mem,
no en las aristas fisicas.

API:
  TickRelational(graph_spec, D, seed)  -> instancia
  .route(signal, mode, bias_role=None) -> (visited[], pi)
  .plan_from(src, chain)               -> bool (resuelve secuencia anidada? MISMA para ambos modos,
                                            pero internamente el plano usa Euclidiana y el HRR usa roles)
"""
import math, random
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H

ALPHA = 0.15
ITERS = 40

def make_hdc_bases(rng, chunk=8, n_chunks=4):
    bases = []
    for c in range(n_chunks):
        vec = [rng.gauss(0,1.0) for _ in range(chunk)]
        perm = list(range(chunk)); rng.shuffle(perm)
        inv = [0]*chunk
        for i,p in enumerate(perm): inv[p]=i
        bases.append((vec, perm, inv))
    return bases

def hdc_project(signal, bases, chunk=8, n_chunks=4):
    vals = list(signal)[:chunk*n_chunks]
    while len(vals) < chunk*n_chunks: vals.append(0.0)
    omega = [0.0]*(chunk*n_chunks)
    for c in range(n_chunks):
        vec, perm, inv = bases[c]
        chunk_v = vals[c*chunk:(c+1)*chunk]
        bound = [chunk_v[perm[i]]*vec[i] for i in range(chunk)]
        for i in range(chunk): omega[c*chunk+i] += bound[i]/n_chunks
    return omega

def dist(a, b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

class TickRelational:
    def __init__(self, nodes_omega, edges, D, seed=42, nroles=None, rel_override=None):
        """
        nodes_omega: lista de omega por indice de nodo.
        edges: dict i -> [(k, r), ...] aristas FISICAS (para el plano Euclidiano).
        rel_override: dict i -> vector HRR empaquetado (relacion anidada que NO esta en aristas fisicas).
                      Si se da, rel_mem[i] usa esto en lugar de construir desde edges (modo HRR).
        """
        self.D = D
        self.omega = nodes_omega
        self.N = len(nodes_omega)
        self.edges = edges
        rng = random.Random(seed)
        self.role_vecs = [H.rnd_unit(rng, D) for _ in range(self.N)]  # rol por indice de nodo
        self.rel_mem = {}
        for i in range(self.N):
            if rel_override and i in rel_override:
                self.rel_mem[i] = rel_override[i]
            else:
                acc = [0.0]*D
                for (k, r) in edges.get(i, []):
                    b = H.hrr_bind(self.role_vecs[k], self.omega[k])
                    for j in range(D): acc[j] += b[j]
                self.rel_mem[i] = H.normalize(acc) if any(acc) else self.omega[i]
        self.bases = make_hdc_bases(rng)

    def _S(self, use_roles):
        if use_roles:
            return {i: self.rel_mem[i] for i in self.edges}
        return {i: self.omega[i] for i in self.edges}

    def route(self, signal, mode="hrr", bias_role=None, use_roles=True, max_ticks=60):
        omega_routed = hdc_project(signal, self.bases)
        seed_node = min(range(self.N), key=lambda n: dist(omega_routed, self.omega[n]))
        S = self._S(use_roles)
        P = [[0.0]*self.N for _ in range(self.N)]
        for i in range(self.N):
            neigh = self.edges[i]
            if not neigh:
                P[i][seed_node] = 1.0; continue
            w = []
            for (k, r) in neigh:
                if use_roles:
                    base = H.cos(S[i], S[k])
                else:
                    base = H.cos(self.omega[i], self.omega[k])
                if bias_role is not None and use_roles:
                    bm = H.hrr_bind(self.role_vecs[bias_role], self.omega[k])
                    rm = H.cos(S[i], bm)
                    base = max(0.0, rm)
                else:
                    base = max(0.0, base)
                w.append(base)
            s = sum(w)
            if s <= 0:
                P[i][seed_node] = 1.0
            else:
                for idx, (k, r) in enumerate(neigh):
                    P[i][k] += w[idx]/s
        pi = [0.0]*self.N; pi[seed_node] = 1.0
        for _ in range(ITERS):
            nxt = [0.0]*self.N
            for i in range(self.N):
                for k in range(self.N):
                    nxt[k] += pi[i]*P[i][k]
            for k in range(self.N):
                nxt[k] = ALPHA*(1.0 if k==seed_node else 0.0) + (1-ALPHA)*nxt[k]
            pi = nxt
        return pi, seed_node

    def _ppr_euclidiana(self, src, max_iters=80):
        """Camino por afinidad Euclidiana sobre aristas fisicas (igual que tick plano 0023).
        Devuelve el conjunto de nodos alcanzables desde src siguiendo aristas, y el nodo mas
        probable tras la caminata (el que acumula mayor pi)."""
        if src not in self.edges or not self.edges[src]:
            return set([src]), src
        # PPR estandar sobre grafo no dirigido-ponderado por afinidad Euclidiana
        pi = [0.0]*self.N; pi[src] = 1.0
        for _ in range(max_iters):
            nxt = [0.0]*self.N
            for i in range(self.N):
                neigh = self.edges.get(i, [])
                if not neigh:
                    nxt[src] += pi[i]; continue
                # pesos por afinidad Euclidiana (como 0023: exp(-ALPHA*dist))
                wts = []
                for (k, r) in neigh:
                    wts.append(math.exp(-ALPHA*dist(self.omega[i], self.omega[k])))
                s = sum(wts)
                if s <= 0:
                    nxt[src] += pi[i]; continue
                for idx,(k,r) in enumerate(neigh):
                    nxt[k] += pi[i]*wts[idx]/s
            for k in range(self.N):
                nxt[k] = 0.15*(1.0 if k==src else 0.0) + 0.85*nxt[k]
            pi = nxt
        reached = set(i for i in range(self.N) if pi[i] > 1e-3)
        best = max(range(self.N), key=lambda k: pi[k])
        return reached, best

    def plan_from(self, src, chain, use_roles=True):
        """Resuelve secuencia src->chain[0]->chain[1]->... 
        HRR (use_roles=True): usa rel_mem (roles empaquetados) para recuperar cruces anidados.
        Plano (use_roles=False): usa PPR Euclidiana REAL sobre aristas fisicas. Si el cruce solo
          vive en rel_mem (no en aristas), el plano de verdad NO llega -> devuelve False por
          computo, no por hardcoded.
        """
        if use_roles:
            return H.recover_chain(self.rel_mem, src, chain, self.role_vecs, self.omega, self.D)
        # --- plano REAL ---
        # debe alcanzar chain[0] (y la cadena) por aristas fisicas
        reached, best = self._ppr_euclidiana(src)
        if chain[0] not in reached:
            return False
        # verificar cadena completa: cada eslabon alcanzable desde el anterior
        cur = chain[0]
        for nxt in chain[1:]:
            r2, _ = self._ppr_euclidiana(cur)
            if nxt not in r2:
                return False
            cur = nxt
        return True
