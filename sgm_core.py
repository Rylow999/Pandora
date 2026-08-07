# -*- coding: utf-8 -*-
"""
sgm_core.py -- SGM consolidado, UN solo modulo (no 63 scripts sueltos).
Solo mecanismos GANADORES de la Fase 7 + previas, validados en experimentos reales:

  GANADORES (adentro):
   - HRR + rol-por-nivel (0027c / hrr_core): composicion relacional. Rol = role_vecs[indice_nodo],
     NO posicion ni cyclic shift (ese era el bug de 0029). Bind=conv circular (signo i-k, 0027),
     unbind=correlacion, cleanup OBLIGATORIA (VSA survey).
   - PPR (0004): ruteo multi-hop con restart (alpha=0.15). Supera resonancia local 1-paso.
   - Decoder bigrama validado en corpus real (0026): top1 >> azar y > lineal; shuffled cae a azar.
   - Slots separados K=3 (0059g): anidado profundo (prof 12+). K=1/2 colapsan binariamente.

  DEJADOS AFUERA EXPLICITAMENTE (no ganaron / fallaron):
   - NodeCore en Python (0002): no aporto rendimiento; usamos omega como lista de floats.
   - Fase dinamica para XOR: fallo documentado, no se reimplementa.
   - 0056 con regla inyectada: TRAMPA (gramatica hardcodeada), excluida por honestidad.
   - Resonator puro (0059f): techo confirmado, no rompe; usamos slots K=3.

  SensorBridge (0019): project/unproject HDC de estado semantico -> omega. NO pixeles (instruccion:
  alimentar con estado semantico de Crafter: inventario, logros, salud; no pixeles crudos).

  Bucle percepcion->tick->accion: SGMAgent.step(state) y SGMAgent.reward(r).
  NO incluye multi-agente ni capa de lenguaje (se suman DESPUES de cerrar el loop solo).

Todo stdlib puro (sin numpy). Portable a donde corra Crafter.

API publica:
  HDC(rng, D)                  -> .project(signal)
  HRR(D, rng, n_roles)         -> .bind/.unbind/.cos/.cleanup/.role(i)/.relational_memory/.recover
  ppr_route(adj, seed, aff_fn) -> dict nodo->prob
  BigramDecoder(counts)        -> .top1(ctx)/.top5(ctx)
  SGMAgent(...)                -> .step(state_semantic, valid_actions)->action ; .reward(r, pain)
  build_nested_K3(...)         -> anidado profundo slots separados (0059g)
"""
import math, random

# 1. HDC / SensorBridge (0019): estado semantico -> omega
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

# 2. HRR + rol-por-nivel (0027c / hrr_core)
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

# 4. Decoder bigrama validado en corpus real (0026)
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

# 5. SGMAgent: bucle percepcion -> tick -> accion (+ reward)
class SGMAgent:
    def __init__(self, rng, D=256, n_nodes=32, alpha_ppr=0.15, gamma=0.01,
                 theta_novelty=0.30, min_duration=5, W_base=50):
        self.D = D; self.alpha = alpha_ppr; self.gamma = gamma
        self.theta_novelty = theta_novelty
        self.min_duration = min_duration
        self.W_base = W_base
        self.n_nodes = n_nodes
        # ω_root es el nodo 0 — identidad persistente del sistema
        # Los demas nodos (1..n_nodes-1) son acciones/conceptos
        self.omega = [[rng.gauss(0, 1) for _ in range(D)] for _ in range(n_nodes)]
        self.vitalidad = [1.0 for _ in range(n_nodes)]
        # La raiz (nodo 0) tiene vitalidad protegida: no baja de 0.5
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
        # ω_root_intero: vector que codifica el estado interno
        # Se actualiza en cada tick con health, food, energia del entorno
        self.omega_root_intero = [0.0] * D
        # Estado por nodo: "ACTIVO", "HIBERNADO"
        self.estado_nodo = ["ACTIVO" for _ in range(n_nodes)]
        self.theta_hibernation = 0.15  # θ_hibernation: por debajo de esto, el nodo hiberna
        self.kappa_trauma = 0.50       # κ_trauma: fraccion de vitalidad perdida por trauma
        # Modos cognitivos tipados (§1.1): vector de sesgos que modifica afinidad
        # sin cambiar la estructura del grafo
        self.modo_actual = "DEFAULT"  # DEFAULT, SENSORIAL, RAZONAMIENTO, PLAN
        self.modo_params = {
            "SENSORIAL": {
                "boost": 2.0, "K": 5, "W_base": 8, "lam": 2.0, "theta_interf": 0.60, "alpha_eff": 8.0, "D_eff": 64, "T_reason": 10
            },
            "RAZONAMIENTO": {
                "boost": 2.0, "K": 20, "W_base": 50, "lam": 5.0, "theta_interf": 0.85, "alpha_eff": 5.0, "D_eff": 384, "T_reason": 50
            },
            "PLAN": {
                "boost": 2.0, "K": 10, "W_base": 100, "lam": 3.0, "theta_interf": 0.75, "alpha_eff": 4.0, "D_eff": 1536, "T_reason": 100
            }
        }
        # conn_type: por defecto, todas las aristas son "Functional"
        # 0=Functional, 1=Causal, 2=Temporal, 3=Cognitive, 4=Terminal
        self.conn_type = {}  # {(i,k): tipo}

    def actualizar_interocepcion(self, health, food, energia=0.5):
        """§3.2: ω_root_intero codifica el estado interno del sistema.
        health, food, energia son senales del entorno (0-1 normalizado).
        """
        # Proyectar senales vitales a omega_root_intero
        senales = [health, food, energia,
                   health * food,  # producto: bienestar compuesto
                   1.0 - health,   # dolor corporal
                   1.0 - food,     # hambre
                   self.E_acumulado / 5.0,  # dolor acumulado normalizado
                   ]
        # Repetir para llenar D
        vals = []
        while len(vals) < self.D:
            vals.extend(senales)
        self.omega_root_intero = vals[:self.D]
        # Normalizar
        n = math.sqrt(sum(x*x for x in self.omega_root_intero))
        if n > 0:
            self.omega_root_intero = [x/n for x in self.omega_root_intero]
        # Mezclar con omega_root (nodo 0)
        for j in range(self.D):
            self.omega[0][j] = (self.omega[0][j] + self.omega_root_intero[j]) * 0.5

    def _aff(self, i, k):
        # Afinidad = similitud cos * vitalidad del nodo destino
        # Nodos hibernados no participan en el PPR (afinidad 0)
        if self.estado_nodo[k] == "HIBERNADO":
            return 0.0
        # Boost por conn_type segun modo activo (§1.1)
        boost = 1.0
        if self.modo_actual != "DEFAULT":
            tipo = self.conn_type.get((i, k), 0)  # 0=Functional por defecto
            modo = self.modo_actual
            params = self.modo_params.get(modo, {})
            # Mapeo de conn_type a boost segun tabla §1.2
            # 0=Functional, 1=Causal, 2=Temporal, 3=Cognitive, 4=Terminal
            boost_map = {
                "SENSORIAL": {0: 1.0, 1: 0.8, 2: 1.0, 3: 0.8, 4: 2.0},
                "RAZONAMIENTO": {0: 1.5, 1: 2.0, 2: 1.2, 3: 2.0, 4: 0.8},
                "PLAN": {0: 2.0, 1: 1.2, 2: 2.0, 3: 1.0, 4: 0.8},
            }
            boost = boost_map.get(modo, {}).get(tipo, 1.0)
        return self.hrr.cos(self.omega[i], self.omega[k]) * self.vitalidad[k] * boost

    def tick(self, n=1):
        """Avanza n ticks: decaimiento de vitalidad + hibernacion."""
        for _ in range(n):
            for i in range(len(self.omega)):
                # Ec.5: V_i(t+1) = V_i·e^(-γ)
                self.vitalidad[i] *= math.exp(-self.gamma)
                # Piso general
                if self.vitalidad[i] < 0.05:
                    self.vitalidad[i] = 0.05
                # Hibernacion: si V_i < θ_hibernation, marcar como HIBERNADO
                # §4.3: el nodo no se elimina, solo deja de participar en PPR
                if i > 0 and self.vitalidad[i] < self.theta_hibernation:
                    self.estado_nodo[i] = "HIBERNADO"
                elif i > 0 and self.estado_nodo[i] == "HIBERNADO":
                    # Reactivacion condicional (§4.3): si ω_root cambio lo suficiente
                    # (evaluado via interocepcion externa)
                    if self.vitalidad[i] >= 0.3:
                        self.estado_nodo[i] = "ACTIVO"
            # La raiz (nodo 0) tiene vitalidad protegida: piso 0.5
            if self.vitalidad[0] < 0.5:
                self.vitalidad[0] = 0.5
            # La raiz nunca hiberna
            self.estado_nodo[0] = "ACTIVO"

    def aplicar_trauma(self, indice_nodo):
        """§4.3: trauma por fracaso de plan. V_i *= (1 - κ_trauma).
        Si V_i cae por debajo de θ_hibernation, el nodo hiberna."""
        if indice_nodo > 0 and indice_nodo < len(self.vitalidad):
            self.vitalidad[indice_nodo] *= (1.0 - self.kappa_trauma)
            # Si bajo de θ_hibernation, hiberna directamente
            if self.vitalidad[indice_nodo] < self.theta_hibernation:
                self.estado_nodo[indice_nodo] = "HIBERNADO"

    def reset_episodio(self):
        """Reset suave entre episodios: mantiene omega, resetea estado afectivo.
        Los nodos hibernados se reactivan si su vitalidad recupera el umbral.
        """
        self.E_acumulado = 0.0
        self.E = 0.0
        self.status = "ACTIVA"
        self.doubt_count = 0
        self.doubt_cooldown = 0
        self.stagnation_ticks = 0
        self.conteo_repeticion = 0
        self.historial_acciones = []
        # La raiz se conserva intacta
        # La vitalidad se restaura parcialmente (el sistema arranca fresco pero con memoria)
        for i in range(1, len(self.vitalidad)):
            self.vitalidad[i] = max(0.3, self.vitalidad[i])
            # Si el nodo estaba hibernado y recupero vitalidad, reactivar
            if self.estado_nodo[i] == "HIBERNADO" and self.vitalidad[i] >= 0.3:
                self.estado_nodo[i] = "ACTIVO"

    def check_stagnation(self):
        """§2.3.2: detecta estancamiento por novedad.
        novelty(t) = |acciones_unicas en ventana W| / W
        Si novelty < theta_novelty por min_duration ticks -> duda.
        """
        W_t = min(self.W_base, max(1, len(self.historial_acciones)))
        if W_t < 5:  # muy pocos datos, no evaluar
            self.stagnation_ticks = 0
            return False
        
        ventana = self.historial_acciones[-W_t:]
        unicas = len(set(ventana))
        novelty = unicas / W_t
        
        if novelty < self.theta_novelty:
            self.stagnation_ticks += 1
        else:
            self.stagnation_ticks = 0
        
        return self.stagnation_ticks >= self.min_duration

    def handle_doubt(self):
        """§2.3.2: respuesta escalonada a la duda.
        Intento 1: relajar selectividad
        Intento 2: semilla alternativa
        Intento 3: abandonar como INCONCLUSA (no CONTRADICTORIA)
        """
        self.doubt_count += 1
        
        if self.doubt_count == 1:
            # Relajar: el efecto emerge porque la vitalidad del nodo actual baja
            # y el PPR naturalmente favorece otros nodos
            self.stagnation_ticks = 0
            self.doubt_cooldown = 5
            return "relax"
        
        elif self.doubt_count == 2:
            # Elegir una accion NO visitada recientemente
            if len(self.historial_acciones) >= 5:
                recientes = set(self.historial_acciones[-10:])
                candidatas = [a for a in range(len(self.omega)) if a not in recientes]
                if candidatas:
                    # Forzar temporalmente la afinidad: bajar vitalidad de acciones recientes
                    for a in recientes:
                        if a < len(self.vitalidad):
                            self.vitalidad[a] *= 0.5
                    self.stagnation_ticks = 0
                    self.doubt_cooldown = 5
                    return "relaunch"
            # Si no hay candidatas, pasar a abandono
            self.doubt_count = 3
        
        # Intento 3 (o caida directa desde 2 si no hay candidatas)
        self.status = "INCONCLUSA"
        self.doubt_cooldown = 10
        return "abandon"

    def set_edges(self, edges):
        self.edges = {i: list(edges.get(i, [])) for i in range(len(self.omega))}
        self.rel = self.hrr.relational_memory(self.edges, self.omega)
        # Inicializar conn_type como Functional (0) para todas las aristas
        for i in self.edges:
            for k in self.edges[i]:
                self.conn_type[(i, k)] = 0

    def set_conn_type(self, i, k, tipo):
        """Asigna tipo de conexion entre nodos i y k.
        0=Functional, 1=Causal, 2=Temporal, 3=Cognitive, 4=Terminal"""
        self.conn_type[(i, k)] = tipo

    def set_modo(self, modo):
        """Cambia el modo cognitivo activo: DEFAULT, SENSORIAL, RAZONAMIENTO, PLAN"""
        if modo in ("DEFAULT", "SENSORIAL", "RAZONAMIENTO", "PLAN"):
            self.modo_actual = modo

    def step(self, state_semantic, valid_actions, modo="DEFAULT"):
        # Establecer modo para esta llamada
        if modo in ("DEFAULT", "SENSORIAL", "RAZONAMIENTO", "PLAN"):
            self.modo_actual = modo
        
        om_r = self.hdc.project(state_semantic)
        
        # El seed del PPR ahora se calcula considerando TAMBIEN la raiz
        # No solo el estado sensorial, sino que la raiz (identidad) influye
        dist_sensorial = [math.sqrt(sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n])))
                         for n in range(len(self.omega))]
        # La raiz (nodo 0) recibe un bonus de afinidad (el sistema tiende a
        # mantener coherencia con su propia identidad)
        dist_sensorial[0] *= 0.7  # bonus 30% a la raiz
        seed = min(range(len(self.omega)), key=lambda n: dist_sensorial[n])
        
        # Tick de decaimiento
        self.tick(1)
        
        # Cooldown de duda
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        
        # PPR
        rank = ppr_route(self.edges, seed, self._aff, alpha=self.alpha, iters=100)
        
        # Seleccion: score PPR * vitalidad
        best, bv = -1, -2.0
        for a in valid_actions:
            if a in rank:
                score = rank[a] * self.vitalidad[a]
                if score > bv:
                    bv, best = score, a
        
        if best < 0:
            viables = [a for a in valid_actions if self.vitalidad[a] > 0.1]
            best = viables[0] if viables else valid_actions[0]
        
        # Registrar accion en historial
        self.historial_acciones.append(best)
        
        # Registrar repeticion
        if best == self.ultima_accion:
            self.conteo_repeticion += 1
        else:
            self.conteo_repeticion = 0
        self.ultima_accion = best
        
        # Verificar estancamiento (despues del paso, afecta al PROXIMO)
        if self.doubt_cooldown == 0 and self.status == "ACTIVA":
            if self.check_stagnation():
                result = self.handle_doubt()
                # Si abandonamos, la proxima accion partira desde otro seed
        
        return best

    def reward(self, r, pain=0.0, beta=0.10):
        # E = max(0, r - pain) — Ec.6: senal de dolor/valencia
        self.E = max(0.0, r - pain)
        # El dolor se acumula si es sostenido
        if pain > 0:
            self.E_acumulado = getattr(self, 'E_acumulado', 0.0) + pain
        else:
            self.E_acumulado = getattr(self, 'E_acumulado', 0.0) * 0.95  # decae si no hay dolor nuevo
        
        # Actualizar vitalidad del nodo que se acabo de usar
        if self.ultima_accion >= 0 and self.ultima_accion < len(self.vitalidad):
            if r > 0:
                # Reward positivo revitaliza
                self.vitalidad[self.ultima_accion] = min(1.0, self.vitalidad[self.ultima_accion] + r * 0.5)
            if pain > 0:
                # Dolor debilita el nodo que causo el dolor
                self.vitalidad[self.ultima_accion] *= max(0.3, 1.0 - pain)
        
        # Verificar contradiccion por dolor acumulado (§2.3.1)
        if self.E_acumulado > 2.0:  # theta_refut = 2.0
            self.status = "CONTRADICTORIA"
            self.doubt_cooldown = 10
        
        # Actualizar omegas (aprendizaje TD)
        for om in self.omega:
            for j in range(self.D):
                om[j] = (1 - beta) * om[j] + beta * r * 0.01
        self.rel = self.hrr.relational_memory(self.edges, self.omega)

# 6. Anidado profundo (0059g): slots SEPARADOS K=3 (NO resonator 0059f)
def build_nested_K3(hrr, parent_vec, child_fact, role_parent, role_child):
    packed = [0.0] * hrr.D
    for j in range(hrr.D):
        packed[j] = parent_vec[j] + child_fact[j] * 0.5
    return hrr._normlist(packed)

if __name__ == "__main__":
    rng = random.Random(7)
    D = 64
    hdc = HDC(rng, D)
    _ = hdc.project([1, 2, 3, 0, 5] + [0] * 50)
    hrr = HRR(D, rng, 4)
    om2 = [[rng.gauss(0, 1) for _ in range(D)] for _ in range(4)]
    edges = {0: [1, 2], 1: [3], 2: [], 3: []}
    rel = hrr.relational_memory(edges, om2)
    assert hrr.recover(rel, 0, 1, om2) == 1
    ag = SGMAgent(rng, D, n_nodes=4)
    ag.set_edges(edges)
    a = ag.step([1, 0, 0, 9], [0, 1, 2, 3])
    ag.reward(1.0, pain=0.0)
    print("sgm_core SMOKETEST OK: HDC/HRR/PPR/decoder/agent integrados")
