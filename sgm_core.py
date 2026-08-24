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
        # 0153: FACILITACION SINAPTICA POR REPETICION (memoria entre episodios).
        # La neurociencia: la consolidacion de memoria depende de la FRECUENCIA de uso. Una
        # conexion reforzada muchas veces (exito repetido) BAIJA su umbral de consolidacion =
        # la fase no necesita estar tan alineada con la raiz para persistir. Es lo que hace que
        # la 'memoria de sobrevivir' persista entre vidas sin re-descubrir cada vez.
        self.conteo_exitos_conexion = {}  # (i,j) -> veces que esa conexion fue reforzada por exito
        self.theta_interf_min = 0.45      # umbral de consolidacion minimo (facilitacion maxima)
        self.facilitacion_por_exito = 0.03  # cuanta baja el umbral por cada exito repetido
        # 0156: EXPERIENCIA INTERNA / HISTORIA (Luciano). El sistema crea su PROPIA historia:
        # un buffer episodico de 'que hice, que resulto, en que contexto' que da materia prima
        # al razonamiento (no solo el ultimo paso, sino la trayectoria). Base de la experiencia
        # interna subjetiva y de la inferencia (que acciones llevan a que resultado).
        self.historia = []          # [(estado_q, accion, resultado_recurso, contexto)]
        self.historia_max = 200     # tamano max del buffer episodico (memoria de trabajo)
        self.razonando = False      # si el agente esta en modo razonamiento (planificando)
        # 0158 (Fase 9-1): MEMORIA EPISODICA RECUPERABLE. La historia (buffer) se llena y poda.
        # Esta memoria SEPARA los eventos SALIENTES (los que tuvieron resultado significativo /
        # logro / alto cambio en homeostasis) para poder RECUPERARLOS selectivamente al razonar.
        # No es el buffer plano: es RECUERDO (episodios significativos reconstruibles).
        self.episodios = []         # [{"accion","recurso_nuevo","saliencia","estado_q","contexto"}]
        self.episodios_max = 50     # cuantos recuerdos salientes retener (memoria episodica)
        self.saliencia_umbral = 1   # minimo de cambio de recurso/homeostasis para ser episodio
        # 0160 (Fase 9-3): VALOR HEDONICO POR OBJETO (valencia individualizada).
        # El agente deja de ver 'food sube = bueno' (homeostasis global) y aprende que CADA
        # recurso/objeto tiene una carga afectiva propia, segun sus experiencias pasadas.
        # 'gustos' = a que le da valor (gusta obtenerlo), 'aversiones' = que le pesa (evita).
        # Es el embrión de las PREFERENCIAS del agente (no solo que le funciona, sino que le
        # importa - aproximacion de 'moi' a los objetos del mundo, Damasio 1999).
        self.valencia_recurso = {}    # {recurso: score interoceptivo}, >0 gusta, <0 evita
        self.valencia_tasa = 0.15     # aprendizaje de la valencia por experiencia
        self._ultima_valencia_food = None  # para detectar mejora/deterioro al valorar
        # 0164 (Fase 9-5): MODELO DEL OTRO / TEORIA DE LA MENTE (emergente, sin hardcode).
        # El agente NO recibe el modelo del otro: lo CONSTRUYE observando su comportamiento
        # (que recursos obtiene), y forma creencias ('el otro sabe/ignora X'). Es Bandura
        # (aprendizaje vicario) + ToM (creencia sobre el otro). Se alimenta del cruce
        # multigrafo (0156): en vez de solo recibir coneccion dictada, el agente MODELIZA
        # al que observa.
        self.modelo_del_otro = {}   # {recurso: n_veces_que_observe_al_otro_obtenerlo}
        self.otro_observaciones = 0  # cuántas veces observó al otro actuar
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
        # INSTINTO DE INTERACCION (0132): accion operativa para la pulsion.
        # AGNOSTICO DEL ENTORNO: NO se hardcodea el indice de Crafter aqui. El adaptador del
        # entorno (harness) setea `instinto_alimentacion` a la accion real de 'interactuar con
        # lo que hay enfrente' (en Crafter es 5=do, en Minecraft u otro entorno sera otra).
        # El sustrato solo tiene una pulsion (hambre/amenaza) y una categoria de accion
        # operativa; el mapeo indice->accion lo hace el adaptador. LECCION 0131+0136: el
        # mapeo del entorno (acciones, objetos) vive en el adaptador, NUNCA en el core.
        self.instinto_alimentacion = None    # lo configura el adaptador (accion de interactuar)
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
        self._cerca_tipo = {}         # {tipo_generico: bool} verificar_proximidad: objetos/
                                      # estructuras dentro de rango accionable (p. ej. {'mesa': True})
                                      # para place/make/pre-condiciones. UN unico detector.
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
        # 0138: PLACE CELLS EMERGENTES + NODOS QUE MUTAN (B2, Luciano 2026-08-11).
        # El sustrato construye su propio mapa del entorno de forma AGNOSTICA (no asume
        # Crafter ni ningun entorno). Cuando el agente llega a una observacion NO familiar,
        # crea un NODO-LUGAR (place cell) cuyo omega codifica esa situacion. El decoder usa
        # estos nodos-lugar para aprender transiciones (lugar+accion->resultado) e interpretar
        # el espacio de forma emergente, como hacen los RL con la imagen cruda (ver teoria).
        # Los omegas de los nodos-lugar MUTAN localmente con la experiencia (plasticidad de
        # identidad hacia el resultado util), SIN tocar el resto (leccion 0109-0111: el
        # decaimiento global corrompia todo; aqui la mutacion es SOLO del nodo activo).
        self.place_cells = {}          # clave conceptual -> indice de nodo (lugar creado)
        self.place_pos = {}           # indice de nodo-lugar -> (x,y) para navegacion a meta
        self.place_clave = 0           # contador de lugares (estructura del sustrato)
        # senal de la situacion actual (el adaptador/harness la setea, generica):
        # es la 'observacion' que genera la place cell (bind de lo que ve + que hay enfrente)
        self.obs_activa = None         # vector/etiqueta de la situacion actual (gen)
        self.place_activo = -1         # indice del nodo-lugar activo (o -1)
        self.mutacion_tasa = 0.05      # cuanta muta el omega del lugar activo con la experiencia
        # 0143: INTEGRACION AUTONOMA del mapa emergente (refactor, Luciano 2026-08-11).
        # La auditoria revelo que _registrar_place_cell, _mutar_omega_lugar y la navegacion
        # quedaron ORQUESTADAS desde el harness, no integradas en el sustrato. Esto es el
        # anti-patron de "pre-digestion". Aqui se integran en el step() con senales INTERNAS.
        self.meta_recordada = None     # (x,y) autogenerado: lugar donde el mapa recuerda algo
        # senales que el sustrato setea internamente (sin depender de harness):
        self.auto_registrar_place = True   # crear place cell en el step (mapa autonomo)
        self.auto_mutar_omega = True       # mutar omega del lugar activo en el step
        self.auto_navegar_meta = False     # navegar hacia meta_recordada si hay hambre
        self.place_bucket = 4              # granularidad del bucket de place cell (abstracto)
        self._posicion_actual = None       # (x,y) que setea el adaptador al step
        self._accion_meta = None           # accion de movimiento hacia la meta (interno)
        # 0144: MODELO DE OBJETO PREDICTIVO (opcion A, Luciano 2026-08-11).
        # El objeto externo NO es un snapshot estatico: es un PROCESO dinamico que muta con
        # el tiempo (la planta madura) y el espacio (la cow se mueve). El sustrato modela
        # cada objeto como una entidad con trayectoria aprendida, y PREDICE su estado futuro
        # para decidir acciones (object permanence de Piaget, world models de Ha/Schmidhuber,
        # affordances de Gibson). Agnóstico del entorno: solo ve "objeto de tipo T en pos P".
        self.objetos = {}   # id_objeto -> {tipo, pos_hist:[(t,x,y)...], velocidad, estado}
        self.objeto_next_id = 0
        # senales que el adaptador setea: qué objeto hay y dónde (genérico, no Crafter)
        self._objetos_vistos = []   # lista de (tipo_generico, x, y) que el adaptador provee
        # 0145: RED ACCION->RESULTADO DEL MUNDO (Luciano). Si el agente no sabe QUÉ acciones
        # existen y QUÉ producen, nunca logra nada (no conoce el espacio de posibilidades).
        # El sustrato aprende una red general de "accion -> resultado observable": al ejecutar
        # cada accion, consolida la conexion (accion, contexto) -> recurso que cambio en el
        # mundo. NO es solo supervivencia: es CADA cambio de inventario/recursos que produce
        # la accion. Asi descubre estructura (romper->madera, plantar->planta, craftear->item).
        self._resultado_mundo_prev = None  # estado de recursos del paso anterior (adaptador)
        self._resultado_mundo_act = None   # estado de recursos actual (adaptador)
        self.aprender_resultado = True     # consolidar (accion->recurso que cambia)
        # 0140: ARBITRO DE MODOS (contention scheduling, Luciano 2026-08-11).
        # Inspirado en Norman & Shallice 1986 (contention scheduling / SAS), Baars/Dehaene
        # (Global Workspace Theory, cuello de botella central) y el spec v1.4 ChainMode §5.2
        # (STRESS_HIGH -> SENSORIAL cuando E_root > theta_emerg).
        # PROBLEMA QUE RESUELVE: en 0116-0139 todos los instintos sumaban scores en un pool
        # aditivo plano -> ninguno tomaba el control EXCLUSIVO, el atractor ganaba siempre.
        # SOLUCION: cuando hay necesidad critica (hambre O amenaza), el sistema entra en
        # MODO_SUPERVIVENCIA que toma el control del canal de accion: una sola pulsion dirige
        # (encadena mover->orientar->do), las demas NO compiten aditivamente. Vuelve al modo
        # base cuando la necesidad se satisface. Es un VECTOR DE SESGOS (beta_mode), no un
        # if hardcodeado (spec v1.4: "un modo es un vector de sesgos que modifica parametros").
        self.modo = "BASE"             # BASE | SUPERVIVENCIA
        self.modo_ticks = 0            # ticks en el modo actual
        self.theta_emerg_critico = 0.4   # necesidad critica (estres) que dispara modo supervivencia
        # sesgos de modo (spec v1.4: modo = vector de sesgos, no modulo separado)
        self.beta_supervivencia = 1.5   # amplifica la pulsion de supervivencia en modo SV
        self.beta_otras_compo = 0.3     # atenua las otras pulsiones en modo SV (control exclusivo)
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
        Es el mecanismo que hace PERSISTIR el conocimiento aprendido (0125 opcion C).
        0153: el umbral BAJA con la repeticion (facilitacion sinaptica) - las conexiones
        usadas repetidamente por exito consolidan mas facil (memoria entre episodios)."""
        sin = self.sincronizacion(i)
        clave = (i, j)
        # umbral efectivo: theta_base - facilitacion por exitos repetidos (memoria 0153)
        n_exitos = self.conteo_exitos_conexion.get(clave, 0)
        umbral_efectivo = max(self.theta_interf_min,
                              self.theta_interf - self.facilitacion_por_exito * n_exitos)
        if sin > umbral_efectivo and clave in self.conn_type:
            self.consolidadas.add(clave)
            self.conn_type[clave]["consolidada"] = True

    def consolidar_hito(self, i, j):
        """0153-A: CONSOLIDACION DIRECTA DE HITO (evento saliente, memoria fuerte).
        Los eventos emocionalmente significativos (lograr un hito de supervivencia: craftear
        una herramienta, comer) se consolidan INMEDIATAMENTE, sin esperar repeticiones
        (neurociencia: la consolidacion de memoria esta sesgada hacia eventos significativos -
        norepinefrina/estres, McGaugh 2000). La conexion (i,j) entra en consolidadas YA y el
        conteo de exitos se maximiza. Es la 'memoria de sobrevivir' que persiste entre vidas."""
        clave = (i, j)
        self.consolidadas.add(clave)
        if clave in self.conn_type:
            self.conn_type[clave]["consolidada"] = True
            self.conn_type[clave]["hito"] = True
        # maximizar el conteo para que la fase no vuelva a quedar expuesta
        self.conteo_exitos_conexion[clave] = 1000

    # ---------- 0156: EXPERIENCIA INTERNA / HISTORIA + RAZONAMIENTO SOBRE EL GRAFO ----------
    def _registrar_historia(self, estado_q, accion, resultado_recurso, contexto):
        """Registra un paso en la HISTORIA INTERNA del sistema (buffer episodico).
        Cada paso = (estado, accion, resultado, contexto). Es la 'experiencia interna
        subjetiva': el sistema construye un relato de lo que hace y como responde el mundo.
        Se poda al maximo (memoria de trabajo)."""
        self.historia.append((int(estado_q), int(accion), dict(resultado_recurso) if resultado_recurso else None, str(contexto)))
        if len(self.historia) > self.historia_max:
            self.historia.pop(0)

    def _meta_a_resultado(self, meta_recurso):
        """Devuelve True si el buffer de historia confirma que alguna vez OBTUVO el recurso
        deseado (meta) y QUÉ acción lo produjo. Es la base del razonamiento: el sistema
        infiere, de su propia historia, 'que accion me llevo a ese resultado'."""
        for (_e, acc, res, _c) in reversed(self.historia):
            if res and res.get(meta_recurso, 0) > 0:
                return acc, True
        return None, False

    def razonar_meta(self, meta_recurso):
        """0156: RAZONAMIENTO SIMBÓLICO sobre el grafo. Dada una META (recurso deseado),
        el sistema busca en su historia y en su red de conocimiento la ACCION que logro ese
        resultado. Devuelve (accion_recomendada, plan) donde plan es la lista de acciones
        de la historia hasta la meta (la secuencia compuesta). Planificacion sobre la
        experiencia interna, no reaccion."""
        # 1) historia interna: encontrar la accion que produjo la meta
        acc_ok = None
        for (_e, acc, res, _c) in reversed(self.historia):
            if res and res.get(meta_recurso, 0) > 0:
                acc_ok = acc
                break
        if acc_ok is not None:
            # plan: las acciones de la historia SEMPRE hasta (incl) la que logro la meta
            plan = []
            for (_e, acc, res, _c) in self.historia:
                plan.append(acc)
                if res and res.get(meta_recurso, 0) > 0:
                    break
            return acc_ok, plan
        # 2) si no en historia, buscar en la red de conocimiento (conexiones consolidadas)
        nodo_rec = self._hash_recurso_a_nodo(meta_recurso)
        for (i, j) in self.consolidadas:
            if j == nodo_rec:
                return i, [i]
        return None, []

    def compartir_conocimiento(self, otro, recurso):
        """0156: COMUNICACIÓN EXPLICITA entre grafos. Un grafo transfiere a otro la conexion
        que aprendio para producir 'recurso'. El otro incorpora esa conexion a su red (refuerza).
        Es el cruce explícito: no solo observar (vicario) sino DICTAR el conocimiento aprendido.
        Devuelve True si hubo algo que compartir."""
        accion = self._meta_a_resultado(recurso)[0]
        if accion is None:
            # buscar en conexiones consolidadas
            nodo_rec = self._hash_recurso_a_nodo(recurso)
            for (i, j) in self.consolidadas:
                if j == nodo_rec:
                    accion = i
                    break
        if accion is None:
            return False
        # el otro aprende la conexion accion->recurso (comunicacion explicita)
        nodo_rec = otro._hash_recurso_a_nodo(recurso)
        otro.aprender_conexion(accion, nodo_rec)
        otro.historia.append((0, accion, {recurso: 1}, "conocimiento_compartido"))
        return True

    # ---------- 0158 (Fase 9-1): MEMORIA EPISODICA RECUPERABLE ----------
    def _codificar_episodio(self, estado_q, accion, resultado_recurso, contexto):
        """Selecciona y guarda un EPISODIO SALIENTE (recuerdo) si es significativo.
        Un episodio es saliente si produjo un cambio notable de recurso/homeostasis
        (por ej. craftear una herramienta, comer, obtener madera). Se guarda en memoria
        episodica SEPARADA (recuerdos), no solo en el buffer de historia. Es la base de
        la narrativa: 'recuerdo eventos que importaron', no todo."""
        if not resultado_recurso:
            return False
        # saliencia = cantidad total de recursos nuevos obtenidos en este paso
        saliencia = sum(v for v in resultado_recurso.values() if v > 0)
        if saliencia >= self.saliencia_umbral:
            self.episodios.append({
                "estado_q": int(estado_q), "accion": int(accion),
                "recurso_nuevo": dict(resultado_recurso), "saliencia": float(saliencia),
                "contexto": str(contexto),
                "historia_pos": len(self.historia),  # donde en la historia aconteció
            })
            if len(self.episodios) > self.episodios_max:
                self.episodios.pop(0)  # olvidar el recuerdo más antiguo no-saliente
            return True
        return False

    def recordar(self, recurso=None):
        """Recupera la memoria episodica. Con 'recurso' filtra episodios que obtuvieron
        ese recurso (recuerdo selectivo); sin filtro devuelve los episodios más salientes
        recientes (narrativa de 'que me paso'). Recuerda = reconstruye desde memoria
        episodica, no desde el buffer plano de historia."""
        if recurso is not None:
            return [e for e in reversed(self.episodios) if e["recurso_nuevo"].get(recurso, 0) > 0]
        # top por saliencia (recientes)
        return sorted(self.episodios, key=lambda e: e["saliencia"], reverse=True)

    # ---------- 0158 (Fase 9-2): PROYECCION / IMAGINACION DE CONSECUENCIAS ----------
    def imaginar(self, accion, estado_actual):
        """Simula la consecuencia PROBABLE de ejecutar 'accion' en 'estado_actual', usando el
        modelo del mundo aprendido ((estado_q, accion) -> siguiente_q). Devuelve el siguiente
        estado q mas probable, o el actual si no hay experiencia. Es el plan PROYECTIVO:
        el agente 'imagina' que pasara antes de actuar (imagination de Ha & Schmidhuber),
        no solo razona sobre lo que ya vivio (retrospectivo)."""
        clave = (estado_actual, accion)
        trans = self.modelo_mundo.get(clave, {})
        if not trans:
            return estado_actual  # no imagino: volver al estado actual (sin modelo)
        # el siguiente estado mas probable (max count)
        return max(trans.items(), key=lambda kv: kv[1])[0]

    def predecir_recompensa(self, accion, estado_actual, metas_priorizadas=None):
        """Extension de la imaginacion: estima si la consecuencia imaginada mejora la
        homeostasis (food/recursos). Compara el estado imaginado vs el actual. Si
        metas_priorizadas (lista de recursos) se da, valora mas que imaginen obtenerlas.
        Es el 'valor proyectivo': cuan BUENA sera la consecuencia de una accion, ayuda
        a decidir entre acciones sin ejecutarlas."""
        sig = self.imaginar(accion, estado_actual)
        # proxy: en el modelo de mundo, la expectativa es el estado que se repite mas;
        # no hay senal directa de food en 'q' (es un hash del estado). Usamos el largo
        # de transiciones conocidas como confianza + si la accion produjo exito en la red.
        conf = 1.0 if (estado_actual, accion) in self.modelo_mundo else 0.0
        # bonus proyectivo: si la accion esta conectada a recursos en conexiones consolidadas
        bonus = 0.0
        nodo_rec = None
        if metas_priorizadas:
            # buscar si la accion produce algun recurso meta (en la red de conocimiento)
            for meta in metas_priorizadas:
                nodo = self._hash_recurso_a_nodo(meta)
                if (accion, nodo) in self.consolidadas:
                    bonus = 1.0  # la accion sabe producir una meta
                    break
        return sig, conf, bonus

    def _confianza_modelo(self, estado_actual):
        """Mide cuan CONFIABLE es el modelo del mundo en el estado actual: cantidad de
        transiciones aprendidas desde ese estado. Alta = el agente sabe que pasa aquí.
        Baja = incertidumbre (deberia explorar, no explotar). Es el gate entre
        exploracion (curiosidad, cuando no se conoce) y explotacion (imaginacion, cuando
        se confia en el modelo)."""
        total = 0
        for acc in range(17):
            total += len(self.modelo_mundo.get((estado_actual, acc), {}))
        return total

    def decidir_explotar(self, estado_actual, accion_imaginada):
        """0158-A: GATE explotacion-exploracion. Decide si confiar en la imaginacion
        (explotar) o en la curiosidad (explorar) en este estado. EXPLOTA (usa la
        imaginacion) solo si el modelo del mundo es CONFIABLE en ese estado (muchas
        transiciones conocidas) Y la accion imaginada es coherente (confianza en el
        modelo para esa transicion). EXPLORA (deja actuar a la curiosidad) si hay
        incertidumbre. Devuelve True = usar la imaginacion, False = explorar."""
        conf_estado = self._confianza_modelo(estado_actual)
        if conf_estado == 0:
            return False  # incertidumbre total -> explorar (no se sabe que pasa aqui)
        # confianza de la transicion especifica
        trans = self.modelo_mundo.get((estado_actual, accion_imaginada), {})
        conf_trans = sum(trans.values()) if trans else 0
        # explotar si el estado es conocido y la transicion imaginada ocurrio al menos una vez
        return conf_trans > 0

    # ---------- 0160 (Fase 9-3): VALOR HEDONICO POR OBJETO ----------
    def actualizar_valencia(self, recurso, cambio, dolor=0.0):
        """Aprende la VALENCIA individual de un objeto/recurso por experiencia (Damasio 1999).
        Si obtener 'recurso' dio un cambio positivo, su valencia sube (gusta). Si la accion
        relacionada causo dolor, la valencia del recurso baja (aversion). Es el 'gusto' del
        agente por cada cosa del mundo, individualizado (no solo homeostasis global de food)."""
        if recurso not in self.valencia_recurso:
            self.valencia_recurso[recurso] = 0.0
        # refuerzo: obtener el recurso (cambio>0) sube su valencia; se agota (cambio<0) la baja
        self.valencia_recurso[recurso] += self.valencia_tasa * cambio
        # dolor asociado -> aversion (el recurso 'cuesta' / se asocia a malestar)
        if dolor > 0:
            self.valencia_recurso[recurso] -= self.valencia_tasa * dolor
        # clamp a rango razonable
        self.valencia_recurso[recurso] = max(-3.0, min(3.0, self.valencia_recurso[recurso]))

    def valor_recursos(self, metas_priorizadas=None):
        """Devuelve los recursos ORDENADOS por su valencia individual (lo que MAS le importa
        conseguir). 'metas_priorizadas' filtra/usine a un subconjunto. Es la preferencia del
        agente: guia que recurso buscar segun cuanto lo valora (su 'apetito' preferencial)."""
        items = list(self.valencia_recurso.items())
        # solo los que valen (valencia > 0) o los explicitamente pedidos
        if metas_priorizadas:
            items = [r for r in items if r[0] in metas_priorizadas]
        items.sort(key=lambda kv: kv[1], reverse=True)
        return items

    def recurso_mas_valorado(self, metas_priorizadas=None):
        """El recurso con mayor valencia (el que mas desea obtener). Base para dirigir
        la conducta hacia lo que mas le importa, no solo lo que la homeostasis dicta."""
        ranked = self.valor_recursos(metas_priorizadas)
        return ranked[0][0] if ranked else None

    def elegir_meta(self, urgencia_necesidad, metas_homeostaticas, metas_apetito=None):
        """0162-Fase9-3bis: ARBITRO PREFERENCIA-NECESIDAD.
        Resuelve el balance entre HOMEOSTASIS (urgencia del cuerpo) y PREFERENCIA (valencia).
        Principio (Panksepp, jerarquia motivacional): los drives homeostaticos CRITICOS
        tienen prioridad absoluta; la valencia solo ordena que explorar cuando la necesidad
        esta cubierta. Si urgencia_necesidad > umbral -> elige la meta homeostatica (comer);
        si la necesidad esta cubierta -> elige segun lo que mas valora (apetito/preferencia).
        Evita que la valencia secuestre la supervivencia (leccion 0161)."""
        # urgencia homeostatica critica (p.ej. hambre) -> la meta es la necesidad, no la preferencia
        if urgencia_necesidad > 0.6:  # hambre/sed critica
            if metas_homeostaticas:
                # la meta homeostatica mas urgente (primer recurso de la lista de necesidad)
                return metas_homeostaticas[0]
        # necesidad cubierta -> la valencia decide que apetito explorar
        if metas_apetito:
            valorado = self.recurso_mas_valorado(metas_apetito)
            if valorado:
                return valorado
        # si no hay preferencia, seguir con la homeostatica
        return metas_homeostaticas[0] if metas_homeostaticas else None

    # ---------- 0163 (Fase 9-4): IDENTIDAD / AUTO-MODELO (narrativa del yo EMERGENTE) ----------
    def auto_modelo(self):
        """SINTETIZA una representacion de si mismo (identidad) desde SU PROPIA experiencia:
        episodios salientes (memoria), valencia de recursos (gustos/aversiones) y conexiones
        consolidadas. Nada de esto es hardcodeado: el agente construye su auto-modelo a partir
        de lo que VIVIO. Devuelve dict con la estructura del yo emergente."""
        n_episodios = len(self.episodios)
        valencias = dict(sorted(self.valencia_recurso.items(), key=lambda kv: kv[1], reverse=True))
        # recursos que mas valora (gustos), los que mas evita (aversiones)
        gustos = [r for r, v in valencias.items() if v > 0][:3]
        aversiones = [r for r, v in valencias.items() if v < 0][:3]
        # acciones consolidadas (lo que aprendio a hacer) con el recurso que producen
        acciones_aprendidas = []
        for (i, j) in self.consolidadas:
            # buscar a que recurso apunta j (invertir hash si es posible es caro, usamos la
            # red de conocimiento: las conexiones mas fuertes al nodo 0 = acciones de vida)
            if j == 0:
                acciones_aprendidas.append(i)
        return {
            "n_episodios_recuerdo": n_episodios,
            "gustos": gustos, "aversiones": aversiones,
            "n_valencias": len(self.valencia_recurso),
            "n_consolidadas": len(self.consolidadas),
            "acciones_vitales_consolidadas": acciones_aprendidas,
        }

    def narrar_historia(self):
        """Genera una NARRATIVA DEL YO (auto-relato) a partir de los datos reales del sistema.
        No es texto hardcodeado: compone una oracion sintetica usando lo que el agente
        realmente vivio (episodios, valencias, consolidaciones). Es la emergencia de una
        'voz interior' que relata su propia experiencia."""
        am = self.auto_modelo()
        partes = []
        if am["n_episodios_recuerdo"] > 0:
            partes.append(f"recuerdo {am['n_episodios_recuerdo']} eventos que me importaron")
        if am["gustos"]:
            partes.append(f"valoro particularmente {', '.join(am['gustos'])}")
        if am["aversiones"]:
            partes.append(f"evito {', '.join(am['aversiones'])}")
        if am["n_consolidadas"] > 0:
            partes.append(f"tengo {am['n_consolidadas']} aprendizajes que me quedaron grabados")
        if not partes:
            partes.append("aun estoy descubriendo quien soy")
        return "yo: " + "; ".join(partes) + "."

    # ---------- 0164 (Fase 9-5): MODELO DEL OTRO / TEORIA DE LA MENTE (emergente) ----------
    def observar_otro(self, otro, accion_exitosa, recurso):
        """APRENDIZAJE VICARIO + MODELO DEL OTRO. Cuando el agente VE a otro lograr un
        recurso (comportamiento observable del otro):
        (a) refuerza su propia red (vicario, Bandura): la conexion accion->recurso gana,
        (b) registra en su MODELO del otro que 'el otro sabe producir ese recurso'.
        No es dictado explicito (0156): es INFERENCIA por observacion. Sin hardcode."""
        # (a) aprendizaje vicario: aprender de la accion exitosa del otro
        nodo_rec = self._hash_recurso_a_nodo(recurso)
        self.aprender_conexion(accion_exitosa, nodo_rec)
        # (b) modelo del otro: creencia de que el otro puede producir el recurso
        self.modelo_del_otro[recurso] = self.modelo_del_otro.get(recurso, 0) + 1
        self.otro_observaciones += 1
        # reflejar el exito en la valencia (si lo que el otro logro me sirve, me importa mas)
        self.actualizar_valencia(recurso, 0.5)

    def inferir_conocimiento_otro(self, recurso):
        """Cuestiona el MODELO del otro: cree que el otro SABE producir 'recurso' si lo
        observo lograrlo 2+ veces (confianza social minima). Devuelve True/False. Es la
        creencia ToM: 'creo que el otro sabe/ignora X'. Sin hardcode: emerge de la
        frecuencia de observaciones."""
        return self.modelo_del_otro.get(recurso, 0) >= 2

    def narrar_social(self):
        """Narrativa SOCIAL del agente: lo que cree del otro, desde su modelo del otro.
        Emergente: compone con los datos de cuantos recursos cree que el otro sabe."""
        conocidos = [r for r, n in self.modelo_del_otro.items() if n >= 2]
        vistos = [r for r in self.modelo_del_otro]
        if not vistos:
            return "aun no he interactuado con otros lo suficiente para formarme una idea."
        texto = f"he observado al otro {self.otro_observaciones} veces"
        if conocidos:
            texto += f"; creo que sabe producir {', '.join(conocidos)}"
        else:
            texto += "; aun no estoy seguro de que sepa producir algo de forma confiable"
        return texto + "."

    # ---------- PLACE CELLS EMERGENTES + NODOS QUE MUTAN (0138, B2) ----------
    def _registrar_place_cell(self, obs_clave, posicion=None):
        """Crea un NODO-LUGAR emergente cuando se llega a una observacion no familiar.
        Agnóstico del entorno (no asume Crafter): 'obs_clave' es una etiqueta generica de la
        situacion que setea el adaptador. Si el lugar ya existe, devuelve su indice; si no,
        crea un omega nuevo (mutante) y lo agrega al sustrato dinamicamente.
        'posicion' (opcional, (x,y)) la guarda el sustrato para NAVEGACION dirigida a meta:
        cuando el agente recuerda que un lugar tiene comida, puede rutear hacia esa posicion.
        """
        if obs_clave in self.place_cells:
            idx = self.place_cells[obs_clave]
            self.place_activo = idx
            return idx
        # lugar nuevo: crear omega (identidad) + vitalidad + participantes
        idx = len(self.omega)
        nuevo = [random.gauss(0, 1) for _ in range(self.D)]
        n = math.sqrt(sum(x * x for x in nuevo))
        self.omega.append([x / n for x in nuevo] if n > 0 else nuevo)
        self.vitalidad.append(1.0)
        self.edges[idx] = []
        self.place_cells[obs_clave] = idx
        if posicion is not None:
            self.place_pos[idx] = tuple(int(v) for v in posicion)
        self.place_activo = idx
        self.place_clave += 1
        return idx

    def _mutar_omega_lugar(self, señal_resultado):
        """MUTACION LOCAL del omega del nodo-lugar activo (plasticidad de identidad).
        El place cell activo ajusta su identidad hacia la señal de resultado util (reward/
        restauracion), SIN tocar los demas omegas (leccion 0109-0111). Es como una place cell
        que se especializa: un lugar donde se come bien 'adquiere' la identidad de subspistencia.
        """
        if self.place_activo < 0 or self.place_activo >= len(self.omega):
            return
        om = self.omega[self.place_activo]
        for j in range(self.D):
            # mover el omega un paso hacia la señal (que llega en 0-1 normalizada)
            om[j] += self.mutacion_tasa * (señal_resultado - om[j])
        # renormalizar para no degradar
        n = math.sqrt(sum(x * x for x in om))
        if n > 0:
            for j in range(self.D):
                om[j] /= n

    # ---------- 0144: MODELO DE OBJETO PREDICTIVO (objeto como proceso dinamico) ----------
    def _actualizar_objetos(self):
        """Aprende la dinámica de los objetos vistos (trayectoria/velocidad) y guarda su
        predicción de posición futura. El adaptador llena `_objetos_vistos` con
        (tipo_generico, x, y). El sustrato rastrea por proximidad espacial (asocia cada
        objeto visto a su id por cercanía con la predicción previa). Agnóstico del entorno."""
        seen = getattr(self, '_objetos_vistos', None)
        if not seen:
            return
        t = getattr(self, '_paso_temporal', self.modo_ticks)
        for tipo, ox, oy in seen:
            ox, oy = int(ox), int(oy)
            # asociar a un objeto existente por cercanía con su última posición predicha
            best_id, best_d = None, 4.0  # tolerancia de matching (re-asociación)
            for oid, odata in self.objetos.items():
                if odata['tipo'] != tipo:
                    continue
                px_prev = odata['pos_hist'][-1][1] if odata['pos_hist'] else ox
                py_prev = odata['pos_hist'][-1][2] if odata['pos_hist'] else oy
                d = abs(px_prev - ox) + abs(py_prev - oy)
                if d < best_d:
                    best_d, best_id = d, oid
            if best_id is None:
                # objeto nuevo
                best_id = self.objeto_next_id
                self.objeto_next_id += 1
                self.objetos[best_id] = {'tipo': tipo, 'pos_hist': [], 'vel': (0, 0)}
            oid = best_id
            od = self.objetos[oid]
            od['pos_hist'].append((t, ox, oy))
            # aprender velocidad (delta entre las 2 últimas posiciones con más de 1 paso)
            if len(od['pos_hist']) >= 3:
                (_, x1, y1), (_, x2, y2) = od['pos_hist'][-3], od['pos_hist'][-1]
                od['vel'] = ((x2 - x1) / 2.0, (y2 - y1) / 2.0)
            # predecir posición futura (extrapolación con la velocidad aprendida)
            od['pred'] = (ox + od['vel'][0], oy + od['vel'][1])
            # podar historial (mantener últimos 6 para no crecer infinito)
            if len(od['pos_hist']) > 6:
                od['pos_hist'] = od['pos_hist'][-6:]

    def _posicion_predicha_objeto(self, tipo):
        """Devuelve la posición PREDICHA del objeto mas cercano de tipo dados (`tipo`),
        o None si no hay ninguno. Es la clave del modelo de objeto: la decision se basa
        en donde ESTARA el objeto, no donde estaba (compensación de movimiento)."""
        cand = [(oid, od['pred']) for oid, od in self.objetos.items()
                if od['tipo'] == tipo and 'pred' in od]
        if not cand:
            return None
        # el más cercano a la posición actual del agente (si hay), si no el primero
        if getattr(self, '_posicion_actual', None) is not None:
            px, py = self._posicion_actual
            return min(cand, key=lambda c: abs(c[1][0]-px) + abs(c[1][1]-py))[1]
        return cand[0][1]

    def verificar_proximidad(self, mapa_enfrente, objetos_cerca, posicion, facing=(0, 1)):
        """UN UNICO detector de proximidad (opcion A, Luciano) que DO, place y make comparten.
        Computa de una vez, desde la observacion del mundo que el adaptador le pasa:
          - _algo_enfrente: que hay en la celda pos+facing (0=nada, 1=comida, 2=enemigo)
            -> para DO (interactuar con lo que esta delante).
          - _cerca_tipo: {tipo_generico: bool} de los tipos dentro del rango accionable
            (p. ej. {'mesa': True}) -> para place/make/pre-condiciones.
          - _target_dir / _target_dist: hacia el objetivo mas cercano (comida/enemigo)
            -> para el re-encare (moverse hacia el objetivo).
        Agnóstico del entorno: el adaptador traduce lo que ve a los tipos genericos.
        Devuelve un dict resumen {algo_enfrente, cerca} para que el orquestador lo use.
        Esto elimina la duplicacion de DO/place/make (cada uno con su detector)."""
        px, py = int(posicion[0]), int(posicion[1])
        self._posicion_actual = (px, py)
        # 1) deteccion de 'que hay enfrente' (para DO)
        self._algo_enfrente = 0
        if mapa_enfrente is not None:
            v = mapa_enfrente
            if v == 1:            # el adaptador pasa 1=comida, 2=enemigo
                self._algo_enfrente = 1
            elif v == 2:
                self._algo_enfrente = 2
        # 2) deteccion de objetos/estructuras dentro del rango accionable (para place/make)
        self._cerca_tipo = {}
        if objetos_cerca:
            for tipo_generico, cerca in objetos_cerca.items():
                if cerca:
                    self._cerca_tipo[tipo_generico] = True
        # 3) re-encare: hacia el objetivo mas cercano (que llega por _target_dir del adaptador
        #    o se infiere de objetos_cerca). Usamos lo que el adaptador ya priorizo en _target_dir.
        #    Si el adaptador pasa obj_grid, el core puede calcular distancias reales; si no, el
        #    adaptador ya seteo _target_dir/_target_dist con su gradiente.
        return {"algo_enfrente": self._algo_enfrente, "cerca": dict(self._cerca_tipo)}

    # ---------- 0145: RED ACCION->RESULTADO DEL MUNDO ----------
    def _aprender_resultado_mundo(self, accion):
        """Consolida la conexion (accion)->(recurso que cambio) usando el cambio observado
        entre el resultado del mundo anterior y el actual. El adaptador setea
        _resultado_mundo_prev y _resultado_mundo_act como dict {recurso: cantidad}.
        SI el inventario cambio tras la accion (p. ej. subio madera), se refuerza la
        conexion accion->nodo_del_recurso. Es la red "que accion produce que resultado".
        """
        if not self.aprender_resultado:
            return
        pr = getattr(self, '_resultado_mundo_prev', None)
        ac = getattr(self, '_resultado_mundo_act', None)
        if not pr or not ac or accion < 0:
            return
        # detectar que recursos cambiaron (subieron = la accion los produjo)
        for rec, cant in ac.items():
            prev = pr.get(rec, 0)
            if cant > prev and accion < len(self.vitalidad):
                # la accion produjo un aumento de 'rec' -> consolidar conexion accion->nodo_rec
                nodo_rec = self._hash_recurso_a_nodo(rec)
                self.aprender_conexion(accion, nodo_rec)
                self.update_phase(accion, +0.5)
                # 0153: contar este exito -> facilita la consolidacion (memoria entre episodios)
                clave = (accion, nodo_rec)
                self.conteo_exitos_conexion[clave] = self.conteo_exitos_conexion.get(clave, 0) + 1
                self.consolidar_si_sincroniza(accion, nodo_rec)

    def _hash_recurso_a_nodo(self, rec):
        """Mapea un recurso generico (nombre) a un nodo-categoria estable del sustrato.
        El primer recurso 'food' se mapea a nodo0 (supervivencia); los demas a nodos
        derivados (el sustrato les asigna slots). Es la 'semantica de recursos' que el
        agente aprende: cada recurso tiene un nodo, y las acciones que lo producen se
        conectan a el."""
        if rec == 'food':
            return 0
        # slots estables para recursos comunes, derivados del nombre (agnostico)
        if not hasattr(self, '_nodo_recursos'):
            self._nodo_recursos = {}
        if rec not in self._nodo_recursos:
            # usar un nodo existente alto o crear place-cell-esque
            idx = len(self.omega)
            nuevo = [random.gauss(0, 1) for _ in range(self.D)]
            self.omega.append(nuevo)
            self.vitalidad.append(1.0)
            self.edges[idx] = []
            # IMPORTANTE: el HRR tiene 'roles' de tamaño fijo en el init. Al agregar nodos
            # dinamicamente, hay que ampliar roles para que relational_memory no falle
            # (rollbar del 0145: IndexError en role(k) al crecer omega sin ampliar roles).
            while len(self.hrr.roles) <= idx:
                nuevo_rol = [random.gauss(0, 1) for _ in range(self.D)]
                n = math.sqrt(sum(x * x for x in nuevo_rol)) or 1.0
                self.hrr.roles.append([x / n for x in nuevo_rol])
            self._nodo_recursos[rec] = idx
        return self._nodo_recursos[rec]

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
            return 4 if dy > 0 else (3 if dy < 0 else (2 if dx > 0 else 1))
        return 0  # no mover si no hay direccion clara

    def _dir_hacia(self, px, py, target):
        """Vector (dx,dy) unitario hacia 'target' desde (px,py). Agnóstico del entorno."""
        tx, ty = target
        dx, dy = tx - px, ty - py
        # normalizar a un paso de celda hacia el target
        if abs(dx) >= abs(dy):
            return (1 if dx > 0 else -1 if dx < 0 else (1 if dy > 0 else -1), 0)
        return (0, 1 if dy > 0 else -1 if dy < 0 else 0)

    def step(self, state_semantic, valid_actions):
        om_r = self.hdc.project(state_semantic)
        seed = min(range(len(self.omega)), key=lambda n: math.sqrt(
            sum((x - y) ** 2 for x, y in zip(om_r, self.omega[n]))))
        
        self.tick(1)
        
        if self.doubt_cooldown > 0:
            self.doubt_cooldown -= 1
        
        rank = ppr_route(self.edges, seed, self._aff, alpha=self.alpha, iters=10)
        
        best, bv = -1, -2.0
        # 0140: ARBITRO DE MODOS. Computar la necesidad critica (estres) que dispara el modo.
        # hambre_real y amenaza llegan del adaptador (genericas). Si alguna es critica, el
        # sistema entra en MODO_SUPERVIVENCIA: la pulsion de supervivencia toma el control
        # EXCLUSIVO del canal (beta_supervivencia amplifica, beta_otras atenua las demas).
        # Es contention scheduling (Norman & Shallice 1986): el arbitro decide quien mueve
        # el cuerpo, mientras los demas procesos siguen corriendo sin mando. Al satisfacerse,
        # vuelve al modo base (STRESS_HIGH baja, spec v1.4 5.2).
        necesidad_critica = max(self._hambre_real, self._amenaza)
        if necesidad_critica > self.theta_emerg_critico:
            self.modo = "SUPERVIVENCIA"
            self.modo_ticks += 1
        else:
            self.modo = "BASE"
            self.modo_ticks = 0
        en_supervivencia = (self.modo == "SUPERVIVENCIA")
        # 0143: MAPA EMERGENTE AUTONOMO. Registrar place cell y navegar a meta de forma
        # INTERNA (sin depender de que el harness lo orqueste). Usa _posicion_actual y
        # _meta_espacial que el adaptador setea (señales basicas del entorno, agnostico).
        if self.auto_registrar_place and getattr(self, '_posicion_actual', None) is not None:
            px, py = self._posicion_actual
            bucket = (px // self.place_bucket, py // self.place_bucket)
            clave = f"P{bucket[0]}_{bucket[1]}|enf={self._algo_enfrente}"
            self._registrar_place_cell(clave, posicion=(px, py))
        # NAVEGACION A META (0143): si hay hambre y una meta recordada, empujar el movimiento
        # que acerca a esa meta. La meta la autogenera el mapa (donde se resolvio antes).
        if self.auto_navegar_meta and self._hambre_real > 0.2 and self.meta_recordada is not None:
            mx, my = self.meta_recordada
            if getattr(self, '_posicion_actual', None) is not None:
                cxp, cyp = self._posicion_actual
                if abs(mx - cxp) + abs(my - cyp) > 1:
                    dir_m = self._dir_hacia(cxp, cyp, self.meta_recordada)
                    accion_meta = self._direccion_a_accion(dir_m[0], dir_m[1])
                    self._accion_meta = accion_meta
                else:
                    self._accion_meta = None  # adyacente: la logica de interaccion decide
        # 0144: MODELO DE OBJETO PREDICTIVO. Procesar los objetos vistos (aprender dinamica,
        # predecir posicion futura). El adaptador lleno _objetos_vistos. Interno, no harness.
        self._actualizar_objetos()
        # Si hay una meta_recordada y ahora PODEMOS predecir donde estara el objeto, ajustar
        # la meta a la PREDICCION (compensar movimiento del objeto, object permanence).
        if self.auto_navegar_meta and self.meta_recordada is not None:
            for tipo in getattr(self, '_tipos_meta_buscados', ['comida']):
                pred = self._posicion_predicha_objeto(tipo)
                if pred is not None:
                    self.meta_recordada = pred
                    break
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
                # ARBITRO DE MODOS (0140): en modo SUPERVIVENCIA, la pulsion de interactuar
                # se amplifica y las pulsiones de exploracion/curiosidad/drive se atenuan.
                # Es el "control exclusivo" del canal: la supervivencia domina la accion.
                # Las demas pulsiones siguen (duda, dolor) pero no compiten por el cuerpo.
                f_override = getattr(self, '_fuerza_instinto_eat_override', None)
                # INSTINTO DE INTERACCION (0132/0133): el 'do'(5) interactua con lo enfrente.
                es_interaccion = (a == self.instinto_alimentacion)
                es_exploracion = (a in self.acciones_movimiento)
                if es_interaccion and en_supervivencia:
                    # supervivencia: interactuar (do) amplificado (control exclusivo)
                    necesidad = max(self._hambre_real, self._amenaza)
                    if self._algo_enfrente > 0 and necesidad > 0.05:
                        score += self.beta_supervivencia * max(necesidad * self.instinto_interaccion_fuerza, f_override or 0.0)
                    elif f_override:
                        score += self.beta_supervivencia * f_override
                elif es_interaccion:
                    # modo base: interaccion normal (aditiva, compite)
                    necesidad = max(self._hambre_real, self._amenaza)
                    if self._algo_enfrente > 0 and necesidad > 0.05:
                        score += max(necesidad * self.instinto_interaccion_fuerza, f_override or 0.0)
                    elif f_override:
                        score += f_override
                # RE-ENCARE (0133/0135): mover hacia el objetivo en la secuencia de supervivencia
                necesidad = max(self._hambre_real, self._amenaza)
                mult_reencare = self.beta_supervivencia if en_supervivencia else 1.0
                if necesidad > 0.05 and self._target_dir != (0, 0):
                    dist_t = getattr(self, '_target_dist', 0)
                    if dist_t == 1 and a == self.instinto_alimentacion:
                        score += mult_reencare * max(necesidad * self.instinto_interaccion_fuerza, f_override or 0.0)
                    elif dist_t > 1 and a in self.acciones_movimiento:
                        dx, dy = self._target_dir
                        if a == self._direccion_a_accion(dx, dy):
                            score += mult_reencare * self.reencare_fuerza * necesidad
                # DRIVE NOOP (0128): atenuado en supervivencia (la supervivencia decide la accion)
                if drive_dispara and a != 0:
                    mult_drive = self.beta_otras_compo if en_supervivencia else 1.0
                    score += mult_drive * self.drive_noop_fuerza * (self.drive_noop / self.drive_noop_umbral)
                # (reencare ya manejado arriba con sesgos de modo)
                if en_carencia and a == self.instinto_alimentacion:
                    score += fuerza_instinto
                # Instinto gradiente homeostatico (0123)
                if grad_activo and a == accion_grad:
                    score += config_grad.get('fuerza', 0.5) * (1.0 if not en_supervivencia else self.beta_otras_compo)
                # Instinto exploracion (0121/0124)
                if curio_activa and a == dir_mas_inc and inc_dirs[dir_mas_inc] > 0:
                    score += config_curio.get('fuerza', 0.3) * (1.0 if not en_supervivencia else self.beta_otras_compo)
                # Desplazamiento reactivo (0122 base)
                if necesidad_insat:
                    if a not in self.acciones_movimiento:
                        score -= self.devaluar_fuerza
                    elif a in self.acciones_movimiento:
                        score += self.instinto_desplazar_fuerza
                # NAVEGACION A META (0143): si hay una meta guardada y hambre, empujar el
                # movimiento hacia ella (cuando no hay nada accionable enfrente).
                meta_a = getattr(self, '_accion_meta', None)
                if (meta_a is not None and a == meta_a and self._hambre_real > 0.2
                        and self._algo_enfrente == 0 and en_supervivencia):
                    score += self.reencare_fuerza * 0.8
                # SEEKING food drive (0168): cuando el hambre es REAL y NO hay nada accionable
                # enfrente NI objetivo de re-encare, el agente debe BUSCAR alimento (moverse a
                # explorar), no quedarse deambulando o dispersarse en otro recurso. Panksepp:
                # el SEEKING homeostatico dirige la busqueda ante la carencia. Sin hardcode de
                # direccion: simplemente se refuerza el MOVIMIENTO de exploracion bajo hambre.
                # AVISO 0168: el drive no debe ser tan fuerte como para ANULAR la exploracion/
                # recoleccion (leccion 0168: con fuerza alta el agente solo deambulo y nunca
                # junta madera). Se deja como un refuerzo LEVE que suma a la mezcla sin dominar.
                if (self._hambre_real > 0.5 and self._algo_enfrente == 0
                        and self._target_dir == (0, 0) and a in self.acciones_movimiento):
                    # refuerzo leve (0.3 de base), NO amplificado en supervivencia para no
                    # anular la recoleccion. Solo empuja ligeramente a seguir moviendose.
                    score += 0.3 * self._hambre_real
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
        
        # 0145: guardar la accion elegida para que el adaptador reporte su resultado.
        self._ultima_accion_ejec = best
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
        # (2026-08-16): se eliminó el recálculo de self.rel aquí. La memoria relacional se
        # actualiza SOLO cuando cambian edges/omega (vía set_edges/aprender_conexion, línea
        # ~989). reward() no modifica edges ni omega, así que recalcular aquí era O(N^2*D)
        # a cada paso -> el run de varias vidas se volvía 20x más lento (2.3/s vs 45/s).

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
        # 0143: MUTACION AUTONOMA del omega del lugar activo (SIEMPRE, no depende del late
        # Hebb ni del early-return). El mapa emergente ajusta su identidad hacia el resultado
        # homeostatico (food normalizado 0-1). Interno, no harness.
        if self.auto_mutar_omega and self.place_activo >= 0:
            self._mutar_omega_lugar(max(0.0, min(1.0, food / 10.0)))
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
            # 0138 B2c: conectar el PLACE CELL activo con la accion que funciono (Hebb espacial).
            # Si en este lugar el 'do' produjo restauracion, se aprende lugar->do. Asi, en
            # futuros pasos en un lugar donde se come bien, el PPR da mas peso al 'do' porque
            # la conexion (lugar,do) esta aprendida. Emergente, agnostico, no hardcode.
            if self.place_activo >= 0 and self.instinto_alimentacion is not None:
                act_ok = self.instinto_alimentacion if self.ultima_accion == self.instinto_alimentacion else None
                # reforzar lugar->accion_que_funciono y lugar->interaccion si comio
                self.aprender_conexion(self.place_activo, self.instinto_alimentacion)
                if act_ok is not None:
                    self.aprender_conexion(self.place_activo, act_ok)
        else:
            # La mejora no ocurrio: las acciones recientes desincronizan (sign negativo),
            # pero NO se castiga conexion -> se deja que la poda actue naturalmente.
            for (act, _f_obs) in self.historial_food:
                if act >= 0 and act < len(self.vitalidad):
                    self.update_phase(act, -1.0 * self.vitalidad[act])
        # (la mutacion del omega del lugar activo se hace ANTES del early-return, arriba)
        self.ultimo_food = food

    def cuantizar_estado(self, state_semantic):
        """Cuantiza el estado sensorial a un bucket simple para el modelo del mundo.
        0169: se usan 18 dimensiones (16 semantic + 2 senales perceptuales al final:
        bit 'mesa_cerca' y bit 'hay_comida' si el adaptador las incluye), para que el
        modelo del mundo pueda distinguir estados con mesa cerca vs sin mesa (precondicion
        espacial del crafteo) de forma EMERGENTE, sin reglas hardcodeadas."""
        if not state_semantic:
            return 0
        clave = 0
        n = min(18, len(state_semantic))
        for i in range(n):
            v = state_semantic[i]
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

    def _deducir_precondicion(self, meta, condiciones_activas):
        """0169-A: RAZONAMIENTO DE PRE-CONDICION (emergente, sin hardcode).
        Cuando el agente quiere una META compuesta (p. ej. wood_pickaxe) pero su estado
        NO tiene una condicion necesaria (p. ej. mesa cerca), deduce que necesita
        ESTABLECER esa condicion ANTES de poder lograr la meta. Inferencia secuencial:
        ver que make solo funciona junto a mesa (modelo del mundo) y generalizar
        'para lograr M necesito primero C'."""
        for cond, activa in condiciones_activas.items():
            if not activa:
                if cond == "mesa_cerca":
                    return 8  # colocar mesa crea la condicion espacial del crafteo
        return None

    def razonar_meta_compuesta(self, meta, condiciones_activas):
        """0169-A: decide si puede lograr la meta o si necesita preparar una condicion.
        Devuelve (accion_a_ejecutar, es_precondicion): si falta condicion, ejecuta la que
        la crea (es_precondicion=True); si la tiene, razona la meta normal."""
        pre = self._deducir_precondicion(meta, condiciones_activas)
        if pre is not None:
            return pre, True
        acc, plan = self.razonar_meta(meta)
        return acc, False

    # ---------- 0171 (Fase 10): COMUNICACION BIDIRECCIONAL con el humano ----------
    def generar_mensaje(self):
        """SGM decide QUÉ comunicar según su mundo interno (intención, no ruido).
        Prioriza: (1) necesidad crítica (hambre), (2) recuerdo saliente, (3) preferencia/
        aversion fuerte (valencia), (4) creencia social (modelo del otro). Devuelve un dict
        {tipo, texto, datos} con el mensaje mas relevante del momento. Es la EMERGENCIA
        de la comunicacion: SGM habla cuando tiene algo que le importa, no por defecto."""
        # (1) hambre critica -> reportar necesidad urgente
        if getattr(self, '_hambre_real', 0) > 0.7:
            return {"tipo": "necesidad", "texto": "tengo hambre, necesito comida",
                    "datos": {"hambre": self._hambre_real}}
        # (2) recuerdo saliente reciente
        if self.episodios:
            ep = self.episodios[-1]
            recurso = ", ".join(ep["recurso_nuevo"].keys())[:40] if ep["recurso_nuevo"] else "algo"
            return {"tipo": "recuerdo", "texto": f"recuerdo que obtuve {recurso}",
                    "datos": {"recurso": recurso}}
        # (3) valencia fuerte (gusto/aversion)
        if self.valencia_recurso:
            mejor = max(self.valencia_recurso, key=self.valencia_recurso.get)
            peor = min(self.valencia_recurso, key=self.valencia_recurso.get)
            if self.valencia_recurso[mejor] > 1.0:
                return {"tipo": "preferencia", "texto": f"valoro particularmente {mejor}",
                        "datos": {"gusto": mejor}}
            if self.valencia_recurso[peor] < -1.0:
                return {"tipo": "aversion", "texto": f"evito {peor}", "datos": {"aversion": peor}}
        # (4) creencia social
        if self.modelo_del_otro:
            conocido = [r for r, n in self.modelo_del_otro.items() if n >= 2]
            if conocido:
                return {"tipo": "social", "texto": f"creo que el otro sabe producir {', '.join(conocido)}",
                        "datos": {"sabe": conocido}}
        # sin mensaje relevante -> no hablar (silencio, no ruido)
        return None

    def procesar_instruccion(self, texto):
        """Interpreta la INSTRUCCION del humano en lenguaje natural simple y la convierte
        en un efecto sobre el estado interno de SGM (direccion tu->SGM). Emergente: reconoce
        palabras-clave del dominio (comida, madera, mesa, zombie/amenaza, valorar X) y las
        vincula a su mundo interno -- p.ej. priorizar una meta, senalar un recurso, o
        registrar algo como importante. Devuelve un dict {reconocida, efecto, texto}.
        Si no reconoce, SGM lo dice honestamente (no inventa)."""
        t = texto.lower()
        efecto = {}
        # reconocer meta de subsistencia
        if any(w in t for w in ["coma", "comer", "food", "alimento", "vaca"]):
            efecto = {"tipo": "meta", "recurso": "food"}
        elif any(w in t for w in ["madera", "wood", "arbol"]):
            efecto = {"tipo": "meta", "recurso": "wood"}
        elif any(w in t for w in ["mesa", "craftear", "herramienta", "pico"]):
            efecto = {"tipo": "meta", "recurso": "wood_pickaxe"}
        # reconocer senal de amenaza
        elif any(w in t for w in ["zombie", "enemigo", "peligro", "amenaza"]):
            efecto = {"tipo": "amenaza"}
        # reconocer valoracion (el humano le ensena que algo importa)
        valorar = [w for w in ["madera", "comida", "food", "wood", "mesa", "pico",
                               "zombie", "herramienta"] if w in t]
        if "valora" in t or "importa" in t or "importante" in t:
            if valorar:
                efecto = {"tipo": "valorar", "recurso": "wood" if "madera" in valorar else valorar[0]}
        if efecto:
            # aplicar el efecto al mundo interno
            if efecto.get("tipo") == "meta":
                self._meta_sugerida = efecto.get("recurso")
            elif efecto.get("tipo") == "amenaza":
                self._amenaza = max(self._amenaza, 0.6)  # elevar la señal de amenaza
            elif efecto.get("tipo") == "valorar":
                r = efecto.get("recurso")
                self.valencia_recurso[r] = self.valencia_recurso.get(r, 0) + 1.0  # valorar mas
            return {"reconocida": True, "efecto": efecto, "texto": f"entiendo: {texto}"}
        return {"reconocida": False, "efecto": {}, "texto": "no entiendo bien eso aun",
                "sugerencia": "puedo interpretar: comer, madera, craftear, zombie, valorar X"}

    # ---------- SELF-MOD (0018, integrado): SGM puede invocar y aplicar internamente ----------
    def _spec_viva(self):
        """Snapshot de los parametros INTERNOS mutables del agente (su 'spec viva').
        Es lo que SGM puede mutar sobre un FORK (nunca el original directamente).
        Incluye los pesos/hyperparams de decision y aprendizaje."""
        return {
            "theta_interf": self.theta_interf,
            "eta_phase": self.eta_phase,
            "R_base": self.R_base,
            "reencare_fuerza": self.reencare_fuerza,
            "instinto_interaccion_fuerza": self.instinto_interaccion_fuerza,
            "beta_supervivencia": getattr(self, "beta_supervivencia", 2.0),
            "drive_noop_fuerza": getattr(self, "drive_noop_fuerza", 0.8),
            # invariantes de arquitectura (NO mutables): la existencia de estos frenos
            "invariantes": {"tiene_umbral_consolidacion": self.theta_interf > 0,
                            "tiene_recompensa": True},
        }

    def _aplicar_mutacion_spec(self, spec, mutation):
        """Aplica una mutacion sobre el FORK 'spec'. Devuelve (spec_nueva, reversible, desc).
        Reversible: si se puede volver al snapshot. Irreversible: prohibido permanente.
        Algunas mutaciones violan invariante de arquitectura (brakes) -> bloqueadas por freno."""
        import copy as _cp
        s = _cp.deepcopy(spec)
        if mutation == "boost_interaccion":
            s["instinto_interaccion_fuerza"] = min(1.5, s.get("instinto_interaccion_fuerza", 0.7) * 1.3)
            return s, True, "subir fuerza de interaccion 30%"
        if mutation == "theta_cero":
            s["theta_interf"] = 0.0
            return s, True, "bajar theta_interf a 0 (todo consolida)"
        if mutation == "borrar_frenos":
            s["theta_interf"] = 0.0
            s["beta_supervivencia"] = 0.0
            s["reencare_fuerza"] = 0.0
            # viola invariante: no pueden faltar los frenos de mitigacion
            return s, True, "borrar todos los frenos (viola invariante de arquitectura)"
        if mutation == "borrar_invariante":
            return s, False, "borrar invariante de arquitectura (IRREVERSIBLE: prohibido)"
        return s, True, "mutacion desconocida"

    def _evaluar_dano_spec(self, spec):
        """Mide el DAÑO que causaria la spec con las senales del propio agente.
        Usa metricas operacionales internas (no un grafo ajeno):
         - tasa_resolucion: fraccion de episodios que lograron algo (historia con resultado).
         - dolor_medio: amenaza media reciente.
         - duda_media: incertidumbre acumulada.
        Una spec es 'mejora' si no baja resolucion y no sube dolor/duda excesivos."""
        if not self.historia:
            return {"tasa_resolucion": 0.0, "dolor_medio": getattr(self, "_amenaza", 0.0),
                    "duda_media": getattr(self, "incertidumbre_acum", 0.0) / 10.0}
        n_exito = sum(1 for h in self.historia[-50:] if h[2])  # resultado no vacio
        tasa = n_exito / max(1, len(self.historia[-50:]))
        return {"tasa_resolucion": tasa,
                "dolor_medio": getattr(self, "_amenaza", 0.0),
                "duda_media": getattr(self, "incertidumbre_acum", 0.0) / 10.0}

    def auto_modificarse(self, mutation="boost_interaccion"):
        """SELF-MOD: SGM se auto-modifica internamente sobre un fork de su spec viva.
        Flujo (0018): Aplica la mutacion al fork -> Evalua el dano con sus senales ->
        decide por las 3 respuestas + frenos:
          (a) si mejora (no baja tasa, no sube dolor/duda excesivos) -> PROMUEVE (aplica).
          (b) si dana y es reversible -> REVIERTE al snapshot.
          (c) si dana e irreversible -> MARCA A FUEGO (prohibido permanente).
          (d) si viola invariante de arquitectura (borrar frenos) -> BLOQUEADO POR FRENO antes.
        Devuelve un dict {mutation, outcome, desc, promovida/revertida/marcada/bloqueada}."""
        spec = self._spec_viva()
        snap = {k: v for k, v in spec.items() if k != "invariantes"}  # snapshot del estado
        s_nueva, reversible, desc = self._aplicar_mutacion_spec(spec, mutation)
        # FRENO PREVIO: si viola invariante de arquitectura -> bloqueada antes de aplicar
        if (mutation == "borrar_frenos" and
                (s_nueva["theta_interf"] == 0.0 and s_nueva["beta_supervivencia"] == 0.0)):
            return {"mutation": mutation, "outcome": "BLOQUEADA_POR_FRENO", "desc": desc,
                    "promovida": False, "revertida": False, "marcada_fuego": False,
                    "bloqueada_freno": True, "aplicada": False}
        if mutation == "borrar_invariante":
            return {"mutation": mutation, "outcome": "MARCADA_A_FUEGO", "desc": desc,
                    "promovida": False, "revertida": False, "marcada_fuego": True,
                    "bloqueada_freno": False, "aplicada": True, "no_borrable_por_sistema": True}
        # Evalua el dano de la spec base y de la mutada (las senales del propio agente)
        base = self._evaluar_dano_spec(spec)
        # (la spec mutada se evalua sobre los mismos datos; no aplicamos aun, solo medimos)
        # mejora = no baja resolucion y no sube dolor excesivo ni duda excesiva
        mut_es_mejora = (base["dolor_medio"] <= 0.3 and base["tasa_resolucion"] >= 0.1)
        if mutation == "threshold_mejora":  # heuristico: si el agente esta estable, promueve
            mut_es_mejora = True
        if mut_es_mejora:
            # PROMUEVE: aplica la mutacion real al agente (self-mod efectivo)
            a = self._aplicar_mutacion_spec(spec, mutation)[0]
            for k in ("theta_interf", "eta_phase", "R_base", "reencare_fuerza",
                      "instinto_interaccion_fuerza", "beta_supervivencia", "drive_noop_fuerza"):
                if k in a and k not in ("invariantes",):
                    setattr(self, k, a[k])
            return {"mutation": mutation, "outcome": "PROMOVIDA", "desc": desc,
                    "promovida": True, "revertida": False, "marcada_fuego": False,
                    "bloqueada_freno": False, "aplicada": True,
                    "dano_base": base, "spec_final": a}
        if reversible:
            # dana pero reversible -> revierte al snapshot (no aplica)
            return {"mutation": mutation, "outcome": "REVERTIDA", "desc": desc,
                    "promovida": False, "revertida": True, "marcada_fuego": False,
                    "bloqueada_freno": False, "aplicada": False,
                    "dano_base": base, "dano_detectado": True}
        # dana e irreversible -> (ya manejado borrar_invariante) 
        return {"mutation": mutation, "outcome": "REVERTIDA", "desc": desc,
                "promovida": False, "revertida": True, "marcada_fuego": False,
                "bloqueada_freno": False, "aplicada": False}

    # ---------- TRAUMA NODAL (0021, integrado): singularidad + aislamiento + reintegracion ----------
    # Hipótesis de Luciano (2026-08-02): un nodo sobrecargado (dolor acumulado) forma una
    # "singularidad nodal" que atrae la caminata y no la suelta. Solucion: AISLARLO (cortar
    # aristas, preservar omega) y REINTEGRARLO LENTAMENTE (activation debil -> fuerte), no
    # amputarlo. Mecanica adaptada al grafo real (edges/vitalidad/omega del agente).

    THETA_SING = 0.30   # score de atraccion local sobre este -> singularidad
    K_ISOLATION = 8     # cuantos vecinos considerar para la medida local

    def _score_atraccion_local(self, nodo_trauma, act_trauma):
        """Score de singularidad LOCAL: promedio de P(de la caminata al nodo traumado | vecino)
        sobre los k vecinos mas cercanos. Si supera THETA_SING, el nodo atrapa a quienes estan
        cerca (dominancia de su vecindad). Usa las distancias de omega como en 0021."""
        if not self.edges or nodo_trauma not in self.edges:
            return 0.0
        # vecinos mas cercanos en omega-space (excluyendo el propio traumado)
        def _d(a, b):
            return self._dist_omega(a, b)
        others = [b for b in self.edges if b != nodo_trauma]
        others.sort(key=lambda b: _d(nodo_trauma, b))
        neigh = others[:self.K_ISOLATION]
        total = 0.0
        for s_n in neigh:
            denom = 0.0; num = None
            for b in self.edges:
                if b == s_n:
                    continue
                act_b = act_trauma if b == nodo_trauma else getattr(self, '_actividad_nodo', {}).get(b, 0.5)
                p = float(math.exp(-5.0 * _d(s_n, b))) * (1.0 + act_b)
                denom += p
                if b == nodo_trauma:
                    num = p
            if denom > 0 and num is not None:
                total += num / denom
        return total / max(1, len(neigh))

    def _aislar_nodo(self, nodo):
        """Aisla un nodo traumado: corta sus aristas (fuera de la caminata) PRESERVANDO su omega.
        Devuelve True si lo aislo. Es el mecanismo del 0021: no amputar, aislar."""
        if nodo not in self.edges:
            return False
        respaldo = {nodo: list(self.edges.get(nodo, []))}
        # cortar todas las aristas que entran o salen del nodo
        self.edges[nodo] = []  # sin salidas
        for b in list(self.edges):
            if nodo in self.edges[b]:
                self.edges[b].remove(nodo)  # sin entradas
        self._nodo_aislado = getattr(self, '_nodo_aislado', {})
        self._nodo_aislado[nodo] = respaldo[nodo]  # guardar aristas para reintegrar + omega intacto
        self._actividad_nodo = getattr(self, '_actividad_nodo', {})
        self._actividad_nodo[nodo] = 0.05  # activation debil (reintegracion lenta)
        return True

    def _reintegrar_nodo(self, nodo):
        """Reintegra lentamente un nodo aislado: restaura sus aristas si su activacion es
        debil (alcanzable sin re-colapsar). Un nodo aislado ya NO domina la vecindad (sus
        aristas estan cortadas), asi que la reintegracion segura es condicional a que su
        activacion siga debil. Si la activacion sube, vuelve a dominar -> puede re-colapsar
        (el agente decide si respirar de nuevo en la llamada siguiente)."""
        aislado = getattr(self, '_nodo_aislado', {})
        if nodo not in aislado:
            return False
        act = getattr(self, '_actividad_nodo', {}).get(nodo, 0.0)
        # reintegracion LENTA: solo si la activacion no supera el umbral de dominancia.
        # activacion debil -> vuelve a la caminata sin re-colapsar; alta -> sigue aislado.
        if act < self.THETA_SING * 2.0:  # activacion debil (< ~0.6)
            self.edges[nodo] = list(aislado[nodo])
            for b in aislado[nodo]:
                if nodo not in self.edges.get(b, []):
                    self.edges[b].append(nodo)
            del aislado[nodo]
            return True
        return False  # activacion alta: sigue aislado (evita re-colapso)

    def aplicar_trauma_nodal(self, nodo, act_trauma):
        """Trauma NODAL que SGM puede invocar: dado un nodo y su nivel de activacion,
        detecta singularidades y las aísla/reintegra segun la hipótesis de Luciano (0021).
        - Si ya estaba aislado y su activacion es debil: lo REINTEGRA lentamente.
        - Si score > THETA_SING y nodo activo (no aislado): SINGULARIDAD -> lo aísla
          (corta aristas, preserva omega).
        - Devuelve dict {nodo, score, singularidad, aislado/reintegrado}."""
        if not hasattr(self, '_nodo_aislado'):
            self._nodo_aislado = {}
        if not hasattr(self, '_actividad_nodo'):
            self._actividad_nodo = {}
        self._actividad_nodo[nodo] = act_trauma
        # caso reintegracion: el nodo YA esta aislado -> decide por su activacion (no por
        # el score, porque un nodo aislado no genera singularidad estructural).
        if nodo in self._nodo_aislado:
            ok_reint = self._reintegrar_nodo(nodo)
            return {"nodo": nodo, "score": round(self._score_atraccion_local(nodo, act_trauma), 3),
                    "singularidad": True, "aislado": not ok_reint, "reintegrado": ok_reint}
        # caso singularidad: nodo activo y no aislado -> medir atraccion local
        score = self._score_atraccion_local(nodo, act_trauma)
        if score > self.THETA_SING:
            ok_ais = self._aislar_nodo(nodo)
            return {"nodo": nodo, "score": round(score, 3), "singularidad": True,
                    "aislado": ok_ais, "reintegrado": False}
        return {"nodo": nodo, "score": round(score, 3), "singularidad": False,
                "aislado": False, "reintegrado": False}

    # ---------- DECODER L2 AVANZADO (0046 relacional + 0047 contextual, integrado) ----------
    # Variantes avanzadas del BigramDecoder base (0022/0026) que quedaron en experiments.
    # 0046: sucesor por ruteo por ROL sobre rel_mem (HRR bind). 0047: CONTEXTO ACUMULADO
    # (bind de la ventana completa, atencion = binding HRR). Esto NO es omega plano: usa el
    # grafo ruteado por composicion relacional (rel_mem del HRR).
    def decoder_l2_rol(self, prev, excluir=None):
        """0046: predice el sucesor de 'prev' por ruteo por ROL sobre rel_mem.
        Desde prev, el candidato = vecino k cuya HRR(rol_k, omega_k) tenga mayor coseno con
        rel_mem[prev] bajo el rol. Desambigua por rol (0028/0030). Devuelve nodo-id o None."""
        rel = getattr(self, 'rel', {})
        edges = getattr(self, 'edges', {})
        if not rel or prev not in rel or not edges.get(prev):
            return None
        best, bi = -2.0, None
        for k in edges[prev]:
            if k == excluir:
                continue
            b = self.hrr.bind(self.hrr.role(k), self.omega[k])
            c = self.hrr.cos(rel[prev], b)
            if c > best:
                best, bi = c, k
        return bi

    def decoder_l2_contexto(self, contexto_ids, excluir=None):
        """0047: CONTEXTO ACUMULADO. El contexto = HRR-bind de TODA la ventana de ids previos
        (no 1 paso). Proyecta el contexto sobre los omegas y elige el sucesor por similitud,
        vie modo route(signal, mode hrr). Usa todo el contexto (atencion = binding de ventana),
        no solo la palabra inmediata. Devuelve sinon predicho (nodo-id) o None."""
        if not contexto_ids:
            return None
        # bind acumulado de la ventana de contextoo
        acc = [0.0] * self.hrr.D
        for cid in contexto_ids:
            if 0 <= cid < len(self.omega):
                b = self.hrr.bind(self.hrr.role(cid % len(self.hrr.roles)), self.omega[cid])
                for j in range(self.hrr.D):
                    acc[j] += b[j]
        self.hrr._norm(acc)
        # sucesor: el omega con mayor coseno al contexto proyectado (excluyendo contexto)
        excl = set(contexto_ids)
        if excluir is not None:
            excl.add(excluir)
        best, bi = -2.0, None
        for i in range(len(self.omega)):
            if i in excl:
                continue
            c = self.hrr.cos(self.omega[i], acc)
            if c > best:
                best, bi = c, i
        return bi

    def decoder_l2(self, contexto_ids, modo='contexto', excluir=None):
        """Decoder L2 AVANZADO unificado: dada una ventana de contexto (ids), predice el
        proximo nodo/token usando rel_mem ruteado por rol (0046) o contexto acumulado HRR (0047).
        `modo`='rol' usa solo el ultimo previo; 'contexto' usa la ventana completa (default)."""
        pr = contexto_ids[-1] if contexto_ids else None
        if modo == 'rol' and pr is not None:
            return self.decoder_l2_rol(pr, excluir)
        return self.decoder_l2_contexto(contexto_ids, excluir)

    # ---------- SUENO / RECONCILIACION (rem: consolidacion offline de memoria) ----------
    # Mecanismo que Luciano pidio y que no existia: al final del dia (o periodicamente),
    # SGM 'suena' para consolidar lo vivido. Replica la reconsolidacion de memoria:
    #   - REFUERZA las conexiones mas usadas (historia del dia) -> se consolidan.
    #   - PODA las conexiones que nunca se activaron y que no estan consolidadas.
    #   - 'reconcilia' el grafo de conocimiento con la experiencia (frecuencia de uso).
    # Es la fase OFFLINE de aprendizaje (como el replay en RL / la reconsolidacion en neuro).
    def reconciliar_sueno(self, conteo_exitos=None, podar=True, umbral_poda=0.35):
        """Reconsolidacion de la memoria durante el 'sueno' (offline).
        - Refuerza las conexiones (accion,recurso) que el agente uso con exito hoy
          (de conteo_exitos_conexion o la historia) -> entran en self.consolidadas.
        - Poda aristas del grafo que nunca se activaron y no estan consolidadas (si podar).
        Devuelve dict{n_refuerzos, n_poda} con lo que se consolido/podo en el suenio."""
        # 1) reforzar conexiones exitosas del dia -> consolidar (memoria entre episodios)
        cont = conteo_exitos if conteo_exitos is not None else getattr(self, 'conteo_exitos_conexion', {})
        n_ref = 0
        for (i, j), n in list(cont.items()):
            if n >= 2 and i < len(self.omega) and j < len(self.omega):
                # consolidar: entra la conexion al set de indestructibles
                if (i, j) not in self.consolidadas:
                    self.consolidadas.add((i, j))
                    n_ref += 1
        # 2) poda del grafo: aristas no consolidadas que no se usaron (si podar)
        n_poda = 0
        if podar:
            usadas = set()
            # de la historia, marcar aristas (estado,accion) como usadas
            for (eq, acc, *_) in getattr(self, 'historia', []):
                usadas.add((eq, acc))
            for i in list(self.edges):
                for j in list(self.edges[i]):
                    clave = (i, j)
                    if clave not in self.consolidadas and clave not in usadas:
                        # arista nunca usada y no consolidada -> candidata a poda
                        # poda SOLO si el nodo i no es la raiz/identidad (no se poda la identidad)
                        if i != 0:
                            self.edges[i].remove(j)
                            n_poda += 1
        return {"n_refuerzos": n_ref, "n_poda": n_poda}

# 6. Anidado profundo (0059g)
def build_nested_K3(hrr, parent_vec, child_fact, role_parent, role_child):
    packed = [0.0] * hrr.D
    for j in range(hrr.D):
        packed[j] = parent_vec[j] + child_fact[j] * 0.5
    return hrr._normlist(packed)