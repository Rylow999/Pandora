# -*- coding: utf-8 -*-
"""
sgm_core_min.py — SGM core MINIMO (baseline verificado).
SOLO los mecanismos que demostraron funcionar en exp_SGM_0096 (v2):
- HDC, HRR, PPR, BigramDecoder, build_nested_K3
- Vitalidad V_i (gamma=0.01)
- check_stagnation(), handle_doubt()
- verify_contradiction() (E_acumulado > theta_refut)
- reset_episodio (reset suave entre episodios)

SIN omega_root_intero, SIN bonus de raiz, SIN modos, SIN conn_type,
SIN hibernacion, SIN trauma, SIN proteccion de raiz.

Este es el punto de partida para la auditoria parte por parte.
"""
import math, random

# 1. HDC / SensorBridge (0019)
class HDC:
    def __init__(self, rng, D=256, chunk=8):
        self.D = D; self.chunk = chunk; self.n_chunks = D // chunk; self.bases = []
        for _ in range(self.n_chunks):
            vec = [rng.gauss(0, 1.0) for _ in range(chunk)]
            perm = list(range(chunk)); rng.shuffle(perm)
            self.bases.append((vec, perm))

    def project(self, signal):
        vals = list(signal)[:self.n_chunks * self.chunk]
        while len(vals) < self.n_chunks * self.chunk: vals.append(0.0)
        om = [0.0] * self.D
        for c in range(self.n_chunks):
            vec, perm = self.bases[c]
            ch = vals[c * self.chunk:(c + 1) * self.chunk]
            b = [ch[perm[i]] * vec[i] for i in range(self.chunk)]
            for i in range(self.chunk): om[c * self.chunk + i] += b[i] / self.n_chunks
        n = math.sqrt(sum(x * x for x in om))
        return [x / n for x in om] if n > 0 else om

# 2. HRR
class HRR:
    def __init__(self, D, rng, n_roles):
        self.D = D
        self.roles = [[rng.gauss(0, 1) for _ in range(D)] for _ in range(n_roles)]
        for r in self.roles: self._norm(r)

    def _norm(self, v):
        n = math.sqrt(sum(x * x for x in v))
        if n > 0:
            for i in range(len(v)): v[i] /= n

    def role(self, i): return self.roles[i]

    def bind(self, a, b):
        D = self.D; c = [0.0] * D
        for k in range(D):
            s = 0.0
            for i in range(D): s += a[i] * b[(k - i) % D]
            c[k] = s
        return c

    def unbind(self, a, b):
        D = self.D; c = [0.0] * D
        for k in range(D):
            s = 0.0
            for i in range(D): s += a[i] * b[(i - k) % D]
            c[k] = s
        return c

    def cos(self, a, b):
        s = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
        return s / (na * nb) if na * nb > 0 else 0.0

    def cleanup(self, vec, mem):
        best, bi = -2.0, -1
        for i, m in enumerate(mem):
            c = self.cos(vec, m)
            if c > best: best, bi = c, i
        return bi

    def relational_memory(self, edges, omega):
        rel = {}
        for i in edges:
            acc = [0.0] * self.D
            for k in edges[i]:
                b = self.bind(self.role(k), omega[k])
                for j in range(self.D): acc[j] += b[j]
            rel[i] = self._normlist(acc)
        return rel

    def _normlist(self, v):
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v] if n > 0 else v

    def recover(self, rel_mem, src, tgt, omega):
        rec = self.unbind(rel_mem[src], self.role(tgt))
        return self.cleanup(rec, omega)

# 3. PPR (0004)
def ppr_route(adj, seed, aff_fn, alpha=0.15, iters=100):
    nodes = list(adj.keys())
    if seed not in nodes: return {}
    rank = {n: 0.0 for n in nodes}; rank[seed] = 1.0
    for _ in range(iters):
        nxt = {n: 0.0 for n in nodes}
        for n in nodes:
            if rank[n] == 0: continue
            nxt[seed] += alpha * rank[n]
            neigh = adj[n]
            if not neigh: continue
            w = [max(0.0, aff_fn(n, k)) for k in neigh]
            s = sum(w)
            if s <= 0: continue
            for idx, k in enumerate(neigh):
                nxt[k] += (1 - alpha) * (w[idx] / s) * rank[n]
        rank = nxt
    return rank

# 4. BigramDecoder (0026)
class BigramDecoder:
    def __init__(self, counts):
        self.counts = counts; self.V = len(counts)
        self.P = []
        for row in counts:
            s = sum(row)
            self.P.append([x / s if s > 0 else 0.0 for x in row])

    def top1(self, ctx):
        row = self.P[ctx]
        return max(range(self.V), key=lambda j: row[j]) if sum(row) > 0 else -1

    def top5(self, ctx):
        row = self.P[ctx]
        return sorted(range(self.V), key=lambda j: -row[j])[:5]

# 5. SGMAgent MINIMO
class SGMAgent:
    def __init__(self, rng, D=256, n_nodes=32, alpha_ppr=0.15, gamma=0.01,
                 theta_novelty=0.30, min_duration=5, W_base=50):
        self.D = D; self.alpha = alpha_ppr; self.gamma = gamma
        self.theta_novelty = theta_novelty
        self.min_duration = min_duration
        self.W_base = W_base
        self.omega = [[rng.gauss(0, 1) for _ in range(D)] for _ in range(n_nodes)]
        self.vitalidad = [1.0 for _ in range(n_nodes)]
        self.edges = {i: [] for i in range(n_nodes)}
        self.hdc = HDC(rng, D)
        self.hrr = HRR(D, rng, n_nodes)
        self.rel = {}
        self.E = 0.0
        self.E_acumulado = 0.0
        self.ultima_accion = -1
        self.conteo_repeticion = 0
        self.historial_acciones = []
        self.stagnation_ticks = 0
        self.doubt_count = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"
        # ω_root: nodo 0 como identidad persistente.
        # Piso de vitalidad 0.5 para que nunca desaparezca.
        # SIN bonus de afinidad.
        # conn_type: aristas tipadas que se aprenden del uso, no se asignan.
        self.conn_type = {}  # {(i,k): tipo}

    def aprender_conexion(self, a, b):
        """Refuerza la conexion entre accion a y accion b basado en co-ocurrencia.
        Si a y b ocurren juntos frecuentemente, la arista se vuelve Causal (1).
        Si ocurren pero no sistematicamente, Functional (0).
        Si casi nunca ocurren, la conexion se debilita.
        """
        clave = (a, b)
        if clave not in self.conn_type:
            self.conn_type[clave] = {"count": 0, "tipo": 0, "strength": 1.0, "age": 0}
        self.conn_type[clave]["count"] += 1
        # Si la transicion es muy frecuente, etiquetar como Causal
        c = self.conn_type[clave]["count"]
        if c > 5:
            self.conn_type[clave]["tipo"] = 1  # Causal
        elif c > 2:
            self.conn_type[clave]["tipo"] = 0  # Functional
        # Refrescar: la arista usada recupera strength y resetea age
        self.conn_type[clave]["strength"] = min(1.0, self.conn_type[clave]["strength"] + 0.2)
        self.conn_type[clave]["age"] = 0
        # Si no hay conexion en el grafo, crearla
        if b not in self.edges.get(a, []):
            if a < len(self.edges):
                self.edges[a].append(b)
                self.conn_type[clave] = {"count": c, "tipo": 1 if c > 3 else 0}

    def _aff(self, i, k):
        # Afinidad base: cos * vitalidad
        afinidad_base = self.hrr.cos(self.omega[i], self.omega[k]) * self.vitalidad[k]
        # Modulacion por conn_type aprendido (strength continuo, derivacion real del uso)
        # NOTA (2026-08-06): se elimino el boost Causal 1.5 — era hardcode arbitrario
        # que daba ventaja sistematica a aristas tipo Causal sin que nazca del sustrato.
        # Solo el strength (que crece con uso genuino y decae sin uso) modula.
        conn = self.conn_type.get((i, k))
        if conn:
            afinidad_base *= conn.get("strength", 1.0)
        return afinidad_base

    def tick(self, n=1):
        for _ in range(n):
            for i in range(len(self.omega)):
                self.vitalidad[i] *= math.exp(-self.gamma)
                if self.vitalidad[i] < 0.05:
                    self.vitalidad[i] = 0.05
            # La raiz (nodo 0) tiene piso 0.5 para persistencia de identidad
            if self.vitalidad[0] < 0.5:
                self.vitalidad[0] = 0.5
            # Poda de aristas: las conexiones no usadas se debilitan
            poda = []
            for clave, conn in self.conn_type.items():
                conn["age"] = conn.get("age", 0) + 1
                # Decaer strength si no se usa (ritmo lento: gamma, no gamma*2)
                conn["strength"] = conn.get("strength", 1.0) * math.exp(-self.gamma)
                if conn["strength"] < 0.05:
                    poda.append(clave)
            for clave in poda:
                a, b = clave
                self.conn_type.pop(clave, None)
                if b in self.edges.get(a, []):
                    self.edges[a].remove(b)

    def set_edges(self, edges):
        self.edges = {i: list(edges.get(i, [])) for i in range(len(self.omega))}
        self.rel = self.hrr.relational_memory(self.edges, self.omega)

    def _bigrama_predecibilidad(self, ventana):
        """Mide que tan predecible es la secuencia de acciones con un bigrama.
        Devuelve 1 - (proporcion de transiciones no triviales).
        Si casi todas las transiciones son la misma acción (a->a), alta predecibilidad, baja novedad secuencial.
        Si las transiciones varían, baja predecibilidad, alta novedad secuencial.
        """
        if len(ventana) < 4:
            return 0.0  # sin datos, neutro
        # Conteo de transiciones
        pares = {}
        for i in range(len(ventana) - 1):
            clave = (ventana[i], ventana[i+1])
            pares[clave] = pares.get(clave, 0) + 1
        # Si una transición domina (>70% de los items), la secuencia es predecible
        n_total = len(ventana) - 1
        max_freq = max(pares.values())
        return max_freq / max(1, n_total)

    def check_stagnation(self):
        W_t = min(self.W_base, max(1, len(self.historial_acciones)))
        if W_t < 5:
            self.stagnation_ticks = 0
            return False
        ventana = self.historial_acciones[-W_t:]
        novelty = len(set(ventana)) / len(ventana)
        # Novedad secuencial: si la secuencia es predecible (bigrama dominante), baja la novedad.
        predecibilidad = self._bigrama_predecibilidad(ventana)
        # El decoder informa a la duda: comportamiento predecible reduce la novedad efectiva
        novelty_efectiva = novelty * (1.0 - predecibilidad * 0.5)  # max 50% de reduccion
        if novelty_efectiva < self.theta_novelty:
            self.stagnation_ticks += 1
        else:
            self.stagnation_ticks = 0
        return self.stagnation_ticks >= self.min_duration

    def handle_doubt(self):
        self.doubt_count += 1
        if self.doubt_count == 1:
            self.stagnation_ticks = 0
            self.doubt_cooldown = 5
            return "relax"
        elif self.doubt_count == 2:
            if len(self.historial_acciones) >= 5:
                recientes = set(self.historial_acciones[-10:])
                candidatas = [a for a in range(len(self.omega)) if a not in recientes]
                if candidatas:
                    for a in recientes:
                        if a < len(self.vitalidad):
                            self.vitalidad[a] *= 0.5
                    self.stagnation_ticks = 0
                    self.doubt_cooldown = 5
                    return "relaunch"
            self.doubt_count = 3
        self.status = "INCONCLUSA"
        self.doubt_cooldown = 10
        return "abandon"

    def reset_episodio(self):
        """Reset suave: mantiene omega, resetea estado afectivo."""
        self.E_acumulado = 0.0
        self.E = 0.0
        self.status = "ACTIVA"
        self.doubt_count = 0
        self.doubt_cooldown = 0
        self.stagnation_ticks = 0
        self.conteo_repeticion = 0
        self.historial_acciones = []
        for i in range(1, len(self.vitalidad)):
            self.vitalidad[i] = max(0.7, self.vitalidad[i])

    def step(self, state_semantic, valid_actions):
        om_r = self.hdc.project(state_semantic)
        seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        self.tick(1)
        
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        
        rank = ppr_route(self.edges, seed, self._aff, alpha=self.alpha, iters=100)
        
        best, bv = -1, -2.0
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                if score > bv:
                    bv, best = score, a
        
        if best < 0:
            viables = [a for a in valid_actions if self.vitalidad[a] > 0.1]
            best = viables[0] if viables else valid_actions[0]
        
        self.historial_acciones.append(best)
        
        # Guardar anterior ANTES de pisar
        anterior = self.ultima_accion
        
        if best == self.ultima_accion:
            self.conteo_repeticion += 1
        else:
            self.conteo_repeticion = 0
        self.ultima_accion = best
        
        # Aprender conexion entre la accion anterior y la actual
        if anterior >= 0 and best != anterior:
            self.aprender_conexion(anterior, best)
        
        if self.doubt_cooldown == 0 and self.status == "ACTIVA":
            if self.check_stagnation():
                self.handle_doubt()
        
        return best

    def reward(self, r, pain=0.0, beta=0.10):
        self.E = max(0.0, r - pain)
        if pain > 0:
            self.E_acumulado = getattr(self, 'E_acumulado', 0.0) + pain
        else:
            self.E_acumulado = getattr(self, 'E_acumulado', 0.0) * 0.95
        
        if self.ultima_accion >= 0 and self.ultima_accion < len(self.vitalidad):
            if r > 0:
                self.vitalidad[self.ultima_accion] = min(1.0, self.vitalidad[self.ultima_accion] + r * 0.5)
            if pain > 0:
                self.vitalidad[self.ultima_accion] *= max(0.3, 1.0 - pain)
        
        if self.E_acumulado > 2.0:
            self.status = "CONTRADICTORIA"
            self.doubt_cooldown = 10
        
        # NOTA (2026-08-06): se eliminó el decaimiento global de omega en reward().
        # Antes: for om in self.omega: om[j] = (1-beta)*om[j] + beta*r*0.01
        # Eso contaminaba TODAS las identidades (omega) con ruido parejo, corrompiendo
        # la separación de conceptos y causando la degradación entre vidas (0109/0111).
        # FILOSOFIA: omega = identidad ESTABLE del concepto (no se toca).
        # El conocimiento vive en las CONEXIONES (aprender_conexion + strength), NO en omega.
        # Recalcular memoria relacional con los omega estables:
        self.rel = self.hrr.relational_memory(self.edges, self.omega)

# 6. Anidado profundo (0059g)
def build_nested_K3(hrr, parent_vec, child_fact, role_parent, role_child):
    packed = [0.0] * hrr.D
    for j in range(hrr.D):
        packed[j] = parent_vec[j] + child_fact[j] * 0.5
    return hrr._normlist(packed)