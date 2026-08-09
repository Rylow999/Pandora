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
        # V_grafo: vitalidad global = media de vitalidades nodales.
        # Es la medida de "vida" del sistema (cuerpo del player = cuerpo del grafo).
        self.V_grafo = 1.0
        # Homeostasis: ultimo valor de food visto, para detectar mejora.
        self.ultimo_food = None
        # INSTINTO DE ESPECIE (0120): reflejo incorporado del sustrato.
        # En carencia (V_grafo baja), el sistema siente inclinacion a PROBAR la
        # accion de alimentacion. AUTOLIMITATIVO: la fuerza crece con la carencia
        # y se apaga al saciarse (V_grafo restaurado) -> no se obsesiona.
        # NO pre-juzga si comer es bueno: eso lo aprende la experiencia.
        self.instinto_alimentacion = 16      # accion 'eat' (el reflejo de esta especie/cuerpo)
        self.instinto_umbral_carencia = 0.3  # V_grafo bajo este -> el instinto se activa
        self.instinto_fuerza_base = 0.5      # fuerza base del impulso (modulada por carencia)
        # INSTINTO DE EXPLORACION (0121): curiosidad como instinto, NO reward.
        # El decoder aprende el modelo del mundo (estado->estado). Alta incertidumbre
        # (prediction error) genera inclinacion a MOVERSE hacia lo desconocido.
        # Autolimitativo: al explorar (modelo aprende), PE baja y el impulso se apaga.
        self.modelo_mundo = {}               # (estado_q, accion) -> {siguiente_q: count}
        self.incertidumbre_acum = 0.0        # predicciones fallidas recientes
        self.instinto_explorar_umbral = 3    # incertidumbre acumulada para activar
        self.instinto_explorar_fuerza = 0.4  # empuje a moverse
        self.acciones_movimiento = {1,2,3,4} # move_left/right/up/down
        self.ultimo_estado_q = None
        # INSTINTO DE DESPLAZAMIENTO (0122): el movimiento es la accion con RAZON.
        # Se activa cuando la necesidad NO se satisface donde el cuerpo esta.
        self.necesidad_insatisfecha = False
        self.instinto_desplazar_fuerza = 0.6
        self.devaluar_umbral = 0.35       # V_grafo bajo este => hay carencia real
        self.devaluar_fuerza = 0.4        # castigo a acciones locales que no resuelven

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
        # INSTINTO DE ESPECIE (0120): fuerza modulada por la carencia real.
        # Si V_grafo < umbral, la accion de alimentacion recibe un empuje proporcional
        # a que tan degradado esta el cuerpo. Autolimitativo: al saciarse (V_grafo sube),
        # la fuerza cae y el sistema puede volver a explorar (no se obsesiona).
        en_carencia = self.V_grafo < self.instinto_umbral_carencia
        fuerza_instinto = 0.0
        if en_carencia:
            fuerza_instinto = self.instinto_fuerza_base * (self.instinto_umbral_carencia - self.V_grafo)
        # INSTINTO DE EXPLORACION (0121): cuando hay incertidumbre (el modelo del mundo
        # no sabe predecir), el sistema se inclina a MOVERSE hacia lo desconocido.
        # Autolimitativo: al explorar, el modelo aprende y la incertidumbre baja.
        quiere_explorar = self.incertidumbre_acum >= self.instinto_explorar_umbral
        fuerza_explorar = 0.0
        if quiere_explorar:
            fuerza_explorar = self.instinto_explorar_fuerza
        # INSTINTO DE DESPLAZAMIENTO (0122): el movimiento es la accion con RAZON.
        # Si la necesidad no se satisface localmente (carecia con alimento/amenaza),
        # las acciones locales que NO resuelven se devaluan y el movimiento gana peso.
        # El cuerpo se MUEVE porque quedarse no funciona (busca/escapa).
        en_carencia_grave = self.V_grafo < self.devaluar_umbral
        necesidad_insat = en_carencia_grave and (self.ultima_accion == self.instinto_alimentacion)
        self.necesidad_insatisfecha = necesidad_insat
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                # Empuje instintivo solo sobre la accion de alimentacion y solo en carencia.
                # NO es veredicto (eso lo da la experiencia); es inclinacion a probar.
                if en_carencia and a == self.instinto_alimentacion:
                    score += fuerza_instinto
                # Instinto de exploracion: empuja a MOVERSE cuando el mundo es desconocido.
                if quiere_explorar and a in self.acciones_movimiento:
                    score += fuerza_explorar
                # Desplazamiento con razon: si la necesidad no se satisface localmente
                # (hambre y comer no funciona), devalua las acciones locales que no
                # resuelven y empuja el movimiento (el cuerpo busca donde si hay recurso).
                if necesidad_insat:
                    if a not in self.acciones_movimiento:
                        score -= self.devaluar_fuerza
                    elif a in self.acciones_movimiento:
                        score += self.instinto_desplazar_fuerza
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

    def actualizar_homeostasis(self, food, health=None):
        """MONISMO GRAFO-CUERPO (0119): acople DIRECTO.
        La vitalidad del grafo ES la salud del player. factor_cuerpo = health/10.
        Si health baja -> V_grafo baja (el grafo se degrada porque ES el cuerpo).
        Si health=0 -> V_grafo->0 (no hay grafo sin cuerpo).
        Cuando la homeostasis MEJORA (food sube) y la ultima accion la revirtio,
        reforzar conexion accion->nodo0 (supervivencia). Sin reward externo.
        """
        food = float(food)
        health = 10.0 if health is None else float(health)
        # Acople directo: la salud del player (0-10) multiplica la vitalidad del grafo.
        factor_cuerpo = max(0.05, health / 10.0)
        self.V_grafo = (sum(self.vitalidad) / max(1, len(self.vitalidad))) * factor_cuerpo
        if self.ultimo_food is None:
            self.ultimo_food = food
            return
        mejoro_homeostasis = food > self.ultimo_food
        # Si la ultima accion fue la que revirtio la carencia, reforzar supervivencia.
        if mejoro_homeostasis and self.ultima_accion >= 0:
            self.aprender_conexion(self.ultima_accion, 0)
        self.ultimo_food = food

    def cuantizar_estado(self, state_semantic):
        """Cuantiza el estado sensorial a un bucket simple para el modelo del mundo."""
        if not state_semantic:
            return 0
        clave = 0
        for i, v in enumerate(state_semantic[:16]):
            clave = clave * 2 + (1 if v > 0.5 else 0)
        return clave

    def actualizar_modelo_mundo(self, estado_q, accion, siguiente_q):
        """El decoder aprende transiciones (estado, accion) -> siguiente_estado.
        Si la prediccion de esta transicion FALLA (nunca vista o predice mal),
        acumula incertidumbre -> genera inclinacion a explorar lo desconocido.
        Autolimitativo: al ver la transicion y aprenderla, la incertidumbre del
        sistema baja (el modelo ya sabe) -> el impulso se apaga."""
        clave = (estado_q, accion)
        if clave not in self.modelo_mundo:
            self.modelo_mundo[clave] = {}
            # primera vez: no sabia esta transicion -> incertidumbre
            self.incertidumbre_acum += 1.0
        if siguiente_q not in self.modelo_mundo[clave]:
            self.modelo_mundo[clave][siguiente_q] = 0
            # transicion nueva a estado nuevo -> incertidumbre (no la habia visto)
            self.incertidumbre_acum += 1.0
        self.modelo_mundo[clave][siguiente_q] += 1
        # Al acumular evidencia, recocemos la transicion y el factor de incertidumbre
        # se diluye (la conocemos mejor). Decaimiento de incertidumbre por familiaridad.
        total = sum(self.modelo_mundo[clave].values())
        if total > 1:
            self.incertidumbre_acum = max(0.0, self.incertidumbre_acum - 0.2)

# 6. Anidado profundo (0059g)
def build_nested_K3(hrr, parent_vec, child_fact, role_parent, role_child):
    packed = [0.0] * hrr.D
    for j in range(hrr.D):
        packed[j] = parent_vec[j] + child_fact[j] * 0.5
    return hrr._normlist(packed)