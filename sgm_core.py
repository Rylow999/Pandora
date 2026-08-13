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
        # ONTOLOGIA TEMPORAL DE LA VITALIDAD (0125):
        # - vitalidad[i]: base de actividad del nodo, decae con gamma_nodo (efimero,
        #   relevancia operativa local). Ec.5 Kuramoto V_i = V_i*e^-g + A_i*(1-e^-g).
        # - V_grafo: estado homeostatico del CUERPO (acople directo con health/food).
        #   Es lo que sube/baja con el hambre. NO es la media de vitalidades nodales.
        # - strength de conexion aprendida: conocimiento, decae con gamma_conocimiento
        #   (persistente). Si se consolida por sincronizacion Kuramoto, deja de decaer.
        # Separar estas 3 hace que "tener hambre" (estado global) no arrastre
        # mecanicamente la vitalidad de cada nodo, y que el conocimiento aprendido
        # (eat->nodo0) persista mientras el estado homeostatico fluctua.
        self.gamma_nodo = gamma           # decaimiento de vitalidad[i] (efimero)
        self.gamma_conocimiento = 0.001   # decaimiento de strength aprendido (persistente)
        # KURAMOTO (0125): fases de sincronizacion de cada nodo con la raiz.
        # phi[i]: fase en [0, 2pi). La sincronizacion cos(phi_i - phi_root) > umbral
        # es proxy de 'nodo cognitivamente relevante AHORA' (Eq.7, theta_interf=0.70).
        # La relevancia sincronizada CONSOLIDA la conexion aprendida (la vuelve no-podable),
        # habilitando la habituacion: el instinto se apaga porque el conocimiento persiste.
        self.phi = [rng.uniform(0, 2 * math.pi) for _ in range(n_nodes)]
        self.phi_root = 0.0               # fase de la raiz / identidad (nodo 0)
        self.eta_phase = 0.05             # tasa de aprendizaje de fase (Kuramoto Eq.3)
        self.R_base = 1.0                 # radio de acople base
        self.theta_interf = 0.70          # umbral de interferencia (Eq.7) -> consolida
        # conexiones consolidadas por sincronizacion: {(i,k)} no se podan
        self.consolidadas = set()
        # Homeostasis: ultimo valor de food visto, para detectar mejora.
        self.ultimo_food = None
        # Ventana reciente de (accion, food) para consolidacion Hebbiana (0126):
        # cuando food sube, se refuerza/consolida la conexion action->nodo0 de las
        # acciones que co-ocurrieron con la mejora, ponderadas por actividad.
        # NO hardcode de "comer es bueno": es Hebb (co-ocurrencia actividad-resultado).
        self.historial_food = []
        # INSTINTO DE ESPECIE (0120): reflejo incorporado del sustrato.
        # En carencia (V_grafo baja), el sistema siente inclinacion a PROBAR la
        # accion de alimentacion. AUTOLIMITATIVO: la fuerza crece con la carencia
        # y se apaga al saciarse (V_grafo restaurado) -> no se obsesiona.
        # NO pre-juzga si comer es bueno: eso lo aprende la experiencia.
        self.instinto_alimentacion = 5       # accion 'do' (CRITICO: en Crafter COMER = accion 5 'do', que procesa cow/plant ENFRENTE. Antes estaba en 16 = make_iron_sword (fabricar espada), lo que hacia que el instinto empujara a fabricar, no a comer. FIX 0131.)
        self.instinto_umbral_carencia = 0.3  # V_grafo bajo este -> el instinto se activa (DEPRECATED 0127)
        self.instinto_fuerza_base = 0.5      # fuerza base del impulso (modulada por hambre)
        # 0127: el instinto de alimentacion se ancla a HAMBRE REAL de food (no a V_grafo).
        # food va en percepcion en escala 0-10 (food/10 en sv) -> umbral en esa escala.
        self.umbral_hambre_food = 3.0   # food < este => hambre especifica -> pulsion a comer
        # 0128: DRIVE DE ACCION (SEEEKING, energia acumulada anti-noop).
        # El noop deja de ser gratis: cada paso en noop acumula energia libre (entropia)
        # que se libera presionando a ejecutar una accion no-noop del repertorio. Es el
        # SEEKING basado en Panksepp 1998: energia basal que empuja a ACTUAR (sin drive no
        # se hace nada aunque haya hambre) + Friston active inference: quedarse quieto sin
        # reducir incertidumbre = alta energia libre esperada que el sistema evita.
        # Autolimitativo: al ejecutar una accion no-noop, el drive se descarga.
        self.drive_noop = 0.0            # energia libre acumulada por inaccion
        self.drive_noop_umbral = 1.5     # entropia que dispara el empuje (se sobrepasa)
        self.drive_noop_fuerza = 1.0     # fuerza del empuje cuando se activa
        self.drive_noop_tasa = 0.1       # acumulacion por paso en noop (0.1/step)
        self.drive_noop_descarga = 0.5   # descarga al ejecutar una accion no-noop
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
        # 0132: INSTINTO DE INTERACCION (mecanismo multiaccion independiente, Luciano 2026-08-11).
        # El 'do'(5) es la accion de interactuar con lo que el cuerpo tiene ENFRENTE: come si
        # hay comida, ataca si hay enemigo. Es UN mecanismo operante general. La pulsion a 'do'
        # sube cuando hay UNA necesidad bio-insatisfecha del cuerpo (hambre real de food, o dolor/
        # amenaza/daño) Y hay algo accionable enfrente. Autolimitativo: al resolver (comer o
        # neutralizar amenaza) la necesidad cesa y la pulsion cae. Compuerta de habituacion:
        # la conexion do->nodo0 que protege la homeostasis se consolida (come por prediccion).
        # Senales (el harness setea estas en cada step):
        self._hambre_real = 0.0       # 0-1, hambre real de food (escala normalizada)
        self._amenaza = 0.0           # 0-1, dolor/hp bajo reciente + enemigo en vista
        self._algo_enfrente = 0       # 0=nada, 1=comida, 2=enemigo (lo que hay en pos+facing)
        # umbrales de las pulsiones
        self.umbral_amenaza_dolor = 0.5  # fraccion de hp perdida que dispara defensa
        self.instinto_interaccion_fuerza = 0.7  # fuerza base del impulso a 'do'
        # 0133: RE-ENCARE EMERGENTE (opcion A, Luciano). El sustrato aprende a POSICIONARSE
        # para que el objetivo quede ENFRENTE antes de interactuar. Senal: el harness setea
        # _target_dir (dx,dy) hacia el objetivo mas cercano (comida o enemigo). Si el objetivo
        # NO esta en pos+facing (no accionable ya), el instinto empuja a MOVERSE hacia el
        # (lo reorienta); al quedar enfrente (algo_enfrente>0), empuja 'do'. Asi emerge la
        # secuencia acercar -> reorientar -> interactuar, sin hardcodearla. Acto fallido no
        # crea nodo-referencia (leccion 0129): solo el 'do' efectivo consolida.
        self._target_dir = (0, 0)     # direccion (dx,dy) al objetivo mas cercano, o (0,0)
        self._target_dist = 0         # distancia manhattan al objetivo (0=enfrente, 1=adyacente, >1 lejos)
        self.reencare_fuerza = 0.8    # fuerza del empuje a moverse hacia el objetivo para reencarar
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
                # Preservar strength/age/consolidada si ya existian (fix integridad 0126):
                # antes se re-escribia la estructura sin esos campos -> KeyError: 'strength'
                existente = self.conn_type.get(clave, {})
                self.conn_type[clave] = {
                    "count": c,
                    "tipo": 1 if c > 3 else 0,
                    "strength": existente.get("strength", 1.0),
                    "age": existente.get("age", 0),
                    **({"consolidada": True} if clave in self.consolidadas else {}),
                }

    def update_phase(self, i, signo):
        """Kuramoto Eq.3 (0125): actualiza la fase del nodo i hacia la raiz.
        phi_i += eta * R_i * sign(o_i) * sin(phi_root - phi_i)  mod 2pi.
        sign(o_i) = +1 si la accion ayudo a la homeostasis (food subio), -1 si no.
        La sincronizacion resultante (cos(phi_i - phi_root)) es proxy de relevancia.
        """
        R_i = self.R_base / (1.0 + self._dist_omega(i, 0))
        delta = math.sin(self.phi_root - self.phi[i])
        self.phi[i] = (self.phi[i] + self.eta_phase * R_i * signo * delta) % (2 * math.pi)

    def _dist_omega(self, i, j):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(self.omega[i], self.omega[j])))

    def sincronizacion(self, i):
        """Eq.7 interferencia: I_i = cos(phi_i - phi_root). Proxy de relevancia sincronizada."""
        return math.cos(self.phi[i] - self.phi_root)

    def consolidar_si_sincroniza(self, i, j):
        """Si el nodo i esta sincronizado con la raiz (relevante), la conexion (i,j)
        se consolida: el strength deja de decaer con la poda (entra en self.consolidadas).
        Es el mecanismo que hace PERSISTIR el conocimiento aprendido (0125 opcion C)."""
        sin = self.sincronizacion(i)
        clave = (i, j)
        if sin > self.theta_interf and clave in self.conn_type:
            self.consolidadas.add(clave)
            self.conn_type[clave]["consolidada"] = True

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
                # Vitalidad nodo: decae con gamma_nodo (efimero, relevancia operativa)
                self.vitalidad[i] *= math.exp(-self.gamma_nodo)
                if self.vitalidad[i] < 0.05:
                    self.vitalidad[i] = 0.05
            # La raiz (nodo 0) tiene piso 0.5 para persistencia de identidad
            if self.vitalidad[0] < 0.5:
                self.vitalidad[0] = 0.5
            # Poda de aristas: las conexiones no usadas se debilitan.
            # El KNOWLEDGE (strength) decae con gamma_conocimiento (mucho mas lento que
            # la vitalidad), y las consolidadas por sincronizacion Kuramoto NO se podan.
            poda = []
            for clave, conn in self.conn_type.items():
                conn["age"] = conn.get("age", 0) + 1
                if clave in self.consolidadas:
                    # Consolidada: el strength persiste (sigma pegado, no decae)
                    conn["strength"] = min(2.0, conn.get("strength", 1.0))
                    continue
                conn["strength"] = conn.get("strength", 1.0) * math.exp(-self.gamma_conocimiento)
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

    def _direccion_a_accion(self, dx, dy):
        """Convierte un vector (dx, dy) en la accion de movimiento mas cercana.
        1=left, 2=right, 3=up, 4=down"""
        if abs(dx) >= abs(dy):
            return 2 if dx > 0 else (1 if dx < 0 else (4 if dy > 0 else 3))
        else:
            return 4 if dy > 0 else 3

    def step(self, state_semantic, valid_actions):
        om_r = self.hdc.project(state_semantic)
        seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        self.tick(1)
        
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        
        rank = ppr_route(self.edges, seed, self._aff, alpha=self.alpha, iters=10)
        
        best, bv = -1, -2.0
        # INSTINTO DE ESPECIE - ALIMENTACION (0120): fuerza modulada por la carencia real.
        en_carencia = self.V_grafo < self.instinto_umbral_carencia
        fuerza_instinto = 0.0
        if en_carencia:
            fuerza_instinto = self.instinto_fuerza_base * (self.instinto_umbral_carencia - self.V_grafo)
        # INSTINTO DE ESPECIE - GRADIENTE HOMEOSTATICO (0123): cuando hay hambre Y recurso visible,
        # las acciones de movimiento HACIA el recurso reciben un sesgo. Quimiotaxis simple.
        hay_gradiente = getattr(self, '_hay_gradiente', False)
        grad_dir = getattr(self, '_gradiente_dir', (0, 0))
        config_grad = getattr(self, '_config_grad', {})
        grad_activo = hay_gradiente and config_grad.get('activo', False) and en_carencia
        accion_grad = None
        if grad_activo:
            accion_grad = self._direccion_a_accion(grad_dir[0], grad_dir[1])
        # INSTINTO DE EXPLORACION (0121): curiosidad dirigida al mundo.
        quiere_explorar = self.incertidumbre_acum >= self.instinto_explorar_umbral
        fuerza_explorar = 0.0
        if quiere_explorar:
            fuerza_explorar = self.instinto_explorar_fuerza
        inc_dirs = getattr(self, '_inc_dirs', {})
        config_curio = getattr(self, '_config_curio', {})
        curio_activa = quiere_explorar and config_curio.get('activo', False)
        dir_mas_inc = None
        if inc_dirs:
            try:
                dir_mas_inc = max(inc_dirs, key=inc_dirs.get)
            except ValueError:
                dir_mas_inc = None
        # INSTINTO DE DESPLAZAMIENTO (0122): reactivo a necesidad insatisfecha local.
        en_carencia_grave = self.V_grafo < self.devaluar_umbral
        necesidad_insat = en_carencia_grave and (self.ultima_accion == self.instinto_alimentacion)
        self.necesidad_insatisfecha = necesidad_insat
        # 0128: DRIVE DE ACCION (SEEEKING). Si la energia libre acumulada por noop
        # supera el umbral, se activa un empuje que sesga CONTRA quedarse quieto
        # (noop=0): las acciones no-noop ganan fuerza. Es energia que se descarga al actuar.
        drive_dispara = self.drive_noop >= self.drive_noop_umbral
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                # DRIVE NOOP (0128): si el sistema acumulo mucha inaccion, empujar a
                # ejecutar CUALQUIER accion no-noop (salir del pozo de inercia).
                if drive_dispara and a != 0:
                    score += self.drive_noop_fuerza * (self.drive_noop / self.drive_noop_umbral)
                # INSTINTO DE INTERACCION (0132/0133 unificado: hambre + defensa via 'do').
                # El 'do'(5) interactua con lo que haya ENFRENTE. Con RE-ENCARE (0133):
                # - Si el objetivo (comida/enemigo) esta ENFRENTE (_algo_enfrente>0): pulsion a 'do'.
                # - Si hay necesidad real pero el objetivo NO se puede interactuar (no enfrente,
                #   _algo_enfrente==0 pero _target_dir!=0): pulsion a MOVERSE hacia el objetivo
                #   (lo reorienta para dejarlo enfrente). Emerge la secuencia sin hardcodearla.
                f_override = getattr(self, '_fuerza_instinto_eat_override', None)
                if a == self.instinto_alimentacion:
                    necesidad = max(self._hambre_real, self._amenaza)
                    if self._algo_enfrente > 0 and necesidad > 0.05:
                        # objetivo accionable enfrente -> interactuar (comer o atacar)
                        score += max(necesidad * self.instinto_interaccion_fuerza, f_override or 0.0)
                    elif f_override:
                        score += f_override
                # RE-ENCARE (0133/0135): acople fino al objetivo.
                # - Si hay necesidad y el objetivo esta a distancia 1 (adyacente), la pulsion
                #   a 'do' sube FUERTE (es la distancia de interaccion; el facing del harness
                #   puede estar mal calculado, el _target_dist es mas confiable que _algo_enfrente).
                # - Si el objetivo esta lejos (dist>1), empujar el MOVE hacia el (reorientarse).
                necesidad = max(self._hambre_real, self._amenaza)
                if necesidad > 0.05 and self._target_dir != (0, 0):
                    dist_t = getattr(self, '_target_dist', 0)
                    if dist_t == 1 and a == self.instinto_alimentacion:
                        # adyacente: interactuar (comer/atacar) con fuerza
                        score += max(necesidad * self.instinto_interaccion_fuerza, f_override or 0.0)
                    elif dist_t > 1 and a in self.acciones_movimiento:
                        # lejos: mover hacia el objetivo para reencarar
                        dx, dy = self._target_dir
                        if a == self._direccion_a_accion(dx, dy):
                            score += self.reencare_fuerza * necesidad
                elif en_carencia and a == self.instinto_alimentacion:
                    score += fuerza_instinto
                # Instinto gradiente homeostatico (0123)
                if grad_activo and a == accion_grad:
                    score += config_grad.get('fuerza', 0.5)
                # Instinto exploracion (0121/0124)
                if curio_activa and a == dir_mas_inc and inc_dirs[dir_mas_inc] > 0:
                    score += config_curio.get('fuerza', 0.3)
                # Desplazamiento reactivo (0122 base)
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

        # 0128: actualizar DRIVE NOOP. Si se ejecuto noop, la energia libre acumula
        # (noop deja de ser gratis); si se ejecuto una accion, se descarga. Autolimitativo.
        if best == 0:
            self.drive_noop = min(self.drive_noop_umbral * 3, self.drive_noop + self.drive_noop_tasa)
        else:
            self.drive_noop = max(0.0, self.drive_noop - self.drive_noop_descarga)

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
        # Registrar (accion, food) en la ventana Hebbiana
        if self.ultima_accion >= 0 and self.ultima_accion < len(self.vitalidad):
            self.historial_food.append((self.ultima_accion, food))
            if len(self.historial_food) > 6:
                self.historial_food.pop(0)
        if self.ultimo_food is None:
            self.ultimo_food = food
            return
        mejoro_homeostasis = food > self.ultimo_food
        # HEBBIANO (0126, fix del bug 0125): cuando la homeostasis MEJORA (food sube),
        # se refuerza/consolida la conexion accion->nodo0 de TODAS las acciones que
        # co-ocurrieron con la mejora en la ventana reciente, ponderadas por actividad.
        # Esto corrige el bug de 0125: `ultima_accion` era casi siempre MOVIMIENTO (por
        # el gradiente), asi que aprender_conexion(ultima_accion,0) reforzaba
        # movimiento->supervivencia en vez de comer->supervivencia. Con Hebb, el 'eat'
        # gana peso naturalmente si estuvo activo cerca de la mejora (co-ocurrencia),
        # sin hardcodear "comer es bueno".
        if mejoro_homeostasis:
            for (act, f_obs) in self.historial_food:
                if act >= 0 and act < len(self.vitalidad):
                    # Peso por actividad (= vitalidad del nodo) => co-ocurrencia real
                    self.aprender_conexion(act, 0)
                    self.update_phase(act, +1.0 * self.vitalidad[act])
                    self.consolidar_si_sincroniza(act, 0)
        else:
            # La mejora no ocurrio: las acciones recientes desincronizan (sign negativo),
            # pero NO se castiga conexion -> se deja que la poda actue naturalmente.
            for (act, _f_obs) in self.historial_food:
                if act >= 0 and act < len(self.vitalidad):
                    self.update_phase(act, -1.0 * self.vitalidad[act])
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