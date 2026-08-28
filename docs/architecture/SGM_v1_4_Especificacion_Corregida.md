
# Especificación Técnica SGM v1.4
## Modos Cognitivos Tipados, Detección de Estancamiento, Sustrato Mínimo de Nodo, e Integración FATE

**Autor:** Luciano Benjamin Nieto
**Grupo de Investigación Independiente — General Alvear, Mendoza, Argentina**
**Fecha:** 31 de julio de 2026
**Versión:** 1.4 (revisión de v1.3 — sobre DSCN-G / NOUS v2.1 / DSCN-BIO v3 / `dscn-g-language-engine` / `fate-v6-modular`)

---

## Resumen Ejecutivo

Este documento revisa la especificación SGM v1.3 con dos cambios de fondo adicionales:

1. **Sustrato mínimo de nodo (§6 rediseñada).** El `SGMNode` original cargaba en cada nodo campos que solo un subconjunto raro necesita (trauma, costo de ejecución) y estructuras con overhead de heap por nodo (`Vec`, `HashMap`). Se rediseña como `NodeCore` (4 campos, cuantizados) + `EdgeTable` (aristas en un array plano tipo CSR) + tabla lateral para lo infrecuente. Reducción estimada ~3.5x en memoria por nodo, con la ganancia de *tiempo de respuesta* del tick loop (localidad de caché vía Structure-of-Arrays) siendo más relevante que el ahorro de memoria en sí.
2. **Integración de FATE (`fate-v6-modular`) como mecanismo de búsqueda, acotada a dos usos concretos** (§2.5, nueva): abducción XOR de alta dimensión y calibración offline de umbrales. Explícitamente **no** se usa para buscar parámetros de relanzamiento en phase-hijacking/duda — el propio benchmark honesto de FATE v6 muestra que en baja dimensión (D=10) CMA-ES le gana, y el espacio de relanzamiento es de 3-5 parámetros: no hay evidencia de que FATE aporte ahí, y sí hay riesgo de latencia agregada en un loop que corre en ms sobre potencialmente millones de cadenas.

Sigue vigente lo de v1.3: dos disparadores separados (contradicción vía dolor, estancamiento vía novedad — §2.3), y la distinción entre núcleo implementable (§1-7, 11-12, 15-16) y apéndice especulativo (§9-10, 13).

Las ecuaciones base (12 DSCN-G + 2 SGM + 5 NOUS) siguen sin cambios.

---

## 1. Principio Unificador: Modos como Sesgos Semánticos

*(sin cambios respecto a v1.2 — se mantiene por ser la pieza más sólida del diseño)*

El grafo SGM es universal: las mismas ecuaciones gobiernan percepción, memoria y acción. Un modo cognitivo no es un módulo separado; es un **vector de sesgos β_mode** que modifica los parámetros dinámicos del grafo sin alterar su estructura.

### 1.1 Definición formal

```
M = (boost_edges[ConnType], K, W_base, λ, θ_interf, α_eff, D_eff, T_reason, φ_bias)
```

donde:
- `boost_edges[c] ∈ [0.5, 2.0]`: factor multiplicativo sobre la afinidad de aristas de tipo c.
- `K ∈ {5, 10, 20, ...}`: número de cadenas paralelas.
- `W_base ∈ {8, 50, 100}`: ventana de contexto base.
- `λ ∈ [1.0, 10.0]`: concentración von Mises (selectividad de salida).
- `θ_interf ∈ [0.50, 0.90]`: umbral de interferencia constructiva.
- `α_eff ∈ [2.0, 10.0]`: selectividad semántica efectiva.
- `D_eff ∈ {64, 384, 1536}`: dimensión vectorial operativa.
- `T_reason ∈ {10, 20, 100}`: ticks de propagación resonante.
- `φ_bias ∈ [0, 2π)`: fase objetivo desplazada para el modo.

### 1.2 Modos definidos

| Parámetro | MODO_SENSORIAL | MODO_RAZONAMIENTO | MODO_PLAN |
|-----------|---------------|-------------------|-----------|
| `boost_edges[Terminal]` | **2.0** | 0.8 | 0.8 |
| `boost_edges[Causal]` | 0.8 | **2.0** | 1.2 |
| `boost_edges[Temporal]` | 1.0 | 1.2 | **2.0** |
| `boost_edges[Functional]` | 1.0 | 1.5 | **2.0** |
| `boost_edges[Cognitive]` | 0.8 | **2.0** | 1.0 |
| `K` | 5 | 20 | 10 |
| `W_base` | 8 | 50 | 100 |
| `λ` | 2.0 | 5.0 | 3.0 |
| `θ_interf` | 0.60 | 0.85 | 0.75 |
| `α_eff` | 8.0 | 5.0 | 4.0 |
| `D_eff` | 64 | 384 | 1536 |
| `T_reason` | 10 | 50 | 100 |
| `φ_bias` | 0.0 | π/2 | π/4 |

**Nota:** valores default operacionales derivados de las simulaciones del repo `dscn-g-language-engine`. Sin verificación a escala de producción todavía — ver §9 (Estado de Validación).

---

## 2. Motor de Inferencia Simbólica (MODO_RAZONAMIENTO)

### 2.1 Aristas tipadas como reglas lógicas

```
P_mode(j|i) ∝ exp(−α_eff · ‖ω_j − ω_i‖) · boost_edges[conn_type(i,j)]
```

- **Causal** (A → B): `boost = 2.0`. La cadena que atraviesa una arista causal ejecuta *modus ponens* topológico.
- **Cognitive** (A piensa-sobre B): `boost = 2.0`. Razonamiento sobre estados mentales.
- **Functional** (A transforma B): `boost = 1.5`. Razonamiento sobre procedimientos.

### 2.2 Abducción vía Generative XOR

```
Condición de abducción: ‖ω_C − ω_q‖ < ε_abd  (ε_abd = 0.15 por defecto)
```

```python
def abduce(omega_q, candidatos, epsilon_abd=0.15):
    explicaciones = []
    for A in candidatos:
        for B in candidatos:
            if A.id == B.id:
                continue
            omega_C = compute_xor_child(A.omega, B.omega)  # Ec. 8
            if cosine_distance(omega_C, omega_q) < epsilon_abd:
                score = cosine_similarity(omega_C, omega_q)
                explicaciones.append((A, B, score))
    return sorted(explicaciones, key=lambda x: x[2], reverse=True)
```

### 2.3 Dos fallas distintas, dos mecanismos distintos

La v1.2 trataba "contradicción" y "estancamiento" como el mismo fenómeno, resuelto por un único mecanismo (phase-hijack C3). Son cosas distintas y conviene separarlas:

| Falla | Señal | Evidencia previa | Mecanismo de corrección |
|-------|-------|-------------------|--------------------------|
| **Contradicción** | Dolor acumulado en la trayectoria supera `θ_refut` | `v0.9c`: dolor interno emergente validado (G: 0.0→1.0) | Descartar trayectoria, relanzar con perturbación |
| **Estancamiento** | Ventana `W(t)` contraída + tasa de novedad baja, sin dolor asociado | Sin precedente directo — nuevo mecanismo | Duda: ampliar exploración, buscar semilla alternativa, o abandonar como INCONCLUSA (no como CONTRADICTORIA) |

Esta separación importa porque son epistémicamente distintas: un camino contradictorio está **activamente mal** (hay evidencia en contra). Un camino estancado no está mal — simplemente no está generando información nueva. Tratarlos igual (como hacía C3) confunde "me equivoqué" con "no estoy llegando a ningún lado".

#### 2.3.1 Refutación por contradicción (dolor)

```
Si Σ_{n ∈ trayectoria(chain_k)} E_n > θ_refut  (θ_refut = 2.0):
    → Marcar trayectoria como CONTRADICTORIA
    → Relanzar cadena k desde nodo raíz con perturbación de fase (φ_root → φ* + π)
    → Cooldown de 5 ticks antes del próximo disparo en la misma cadena
```

Se mantiene el mecanismo de v1.2 para este caso específico, porque acá sí hay respaldo empírico (`v0.9c`) de que el dolor interno es una señal real y útil. Lo que se retira es su uso como respuesta también al estancamiento.

**Nota de cautela:** `v0.6b` y `v0.9a` mostraron que el dolor aplicado *post-hoc* (como castigo de refuerzo después del hecho) no mejora nada ("mejora 0.0", "mejora -0.0012"). El mecanismo de arriba dispara *durante* la trayectoria activa, no después — mantener esa propiedad es lo que lo separa de los experimentos fallidos.

#### 2.3.2 Detección de estancamiento (duda)

**Intuición:** si una cadena lleva varios ticks revisitando el mismo vecindario sin activar nodos nuevos, y su ventana de contexto ya se contrajo por presión (Ec. 3.3 de v1.2), no tiene sentido seguir invirtiendo ticks ahí. El sistema "duda" de que ese camino vaya a producir algo, y prueba otra cosa antes de tirar la trayectoria entera.

**Métrica de novedad:**

```
novelty(t) = |nodos_únicos_visitados en ventana [t − W(t), t]| / W(t)
```

**Importante:** `novelty(t)` se calcula sobre el *conjunto* de nodos visitados, no sobre un promedio de sus ω. `v0.7` y `v0.7-bis` (v1.2) mostraron que promediar/poolear la ventana de contexto pisa nodos y contamina ω (5.89% y 0.49% de accuracy, peor que el baseline de 10.11%). La señal de estancamiento tiene que ser puramente de conteo/diversidad, nunca de contenido semántico agregado.

**Disparador:**

```python
def check_stagnation(chain, theta_novelty=0.30, theta_window_frac=0.5, min_duration=5):
    """
    Se evalúa cada tick para cadenas en MODO_RAZONAMIENTO o MODO_PLAN.
    theta_novelty: umbral de novedad mínima antes de considerar estancamiento.
    theta_window_frac: fracción de W_base por debajo de la cual la ventana
                        ya se considera "contraída por presión".
    min_duration: ticks consecutivos de baja novedad antes de disparar DUDA
                  (evita falsos positivos por ruido de un solo tick).
    """
    W_t = chain.current_window_size
    W_base = chain.params.W_base

    if W_t > theta_window_frac * W_base:
        chain.stagnation_ticks = 0
        return False

    recent = chain.visited_nodes[-int(W_t):] if W_t >= 1 else []
    if len(recent) == 0:
        return False

    novelty = len(set(recent)) / len(recent)

    if novelty < theta_novelty:
        chain.stagnation_ticks += 1
    else:
        chain.stagnation_ticks = 0

    return chain.stagnation_ticks >= min_duration
```

**Respuesta escalonada a la duda** (a diferencia de C3, no es un evento único — son intentos progresivos antes de abandonar):

```python
def handle_doubt(chain, graph, hnsw_index):
    chain.doubt_count += 1

    if chain.doubt_count == 1:
        # Intento 1: relajar selectividad, más exploración en el mismo vecindario
        chain.params.lambda_eff *= 0.6   # menos concentración von Mises
        chain.params.alpha_eff *= 0.8    # radio de afinidad más amplio
        chain.stagnation_ticks = 0

    elif chain.doubt_count == 2:
        # Intento 2: semilla alternativa, fuera de lo ya visitado
        candidatos = hnsw_index.search(chain.omega_query, k=20)
        alt_seed = next((n for n in candidatos if n.id not in chain.visited_nodes), None)
        if alt_seed is not None:
            relaunch_chain(chain, seed=alt_seed.id)
            chain.visited_nodes.clear()
            chain.stagnation_ticks = 0
        else:
            chain.doubt_count = 3  # no hay candidatos nuevos, pasar directo a abandono

    else:
        # Intento 3: abandonar. Distinción clave respecto a C3:
        # esto NO es CONTRADICTORIA (no hay evidencia de que el camino esté mal),
        # es INCONCLUSA (no se logró avanzar con el presupuesto de ticks dado).
        chain.mode = DEFAULT
        chain.status = "INCONCLUSA"

    chain.doubt_cooldown = 5  # mismo cooldown que refutación, por consistencia
    return chain.status if chain.doubt_count >= 3 else None
```

**Por qué esto es preferible a C3 acá:** no depende de una operación físicamente cargada (`φ_root → φ* + π`) cuyo estatus sigue sin resolverse en el paper base. Usa una variable que ya existe en el spec (`W(t)`, definida en v1.2 §3.3) más una métrica de conteo simple, ambas triviales de loguear y verificar. Si en algún momento se resuelve el estado de C3 en DSCN-G y se quiere reincorporar como mecanismo físico legítimo, puede reemplazar el paso de "relanzar con perturbación" en §2.3.1 sin tocar esta sección.

### 2.4 Pipeline completo MODO_RAZONAMIENTO (actualizado)

```
INPUT: ω_query (concepto a razonar)
  │
  ▼
[1] ACTIVAR: HNSW search → top-20 nodos cercanos
  │           K=20 cadenas se distribuyen sobre candidatos
  ▼
[2] PROPAGAR: T_reason=50 ticks con P_mode(j|i) (boost Causal/Cognitive)
  │            Actualizar ω, φ, V, E en cada nodo visitado
  │            Registrar visited_nodes por cadena (para novelty)
  ▼
[3] VERIFICAR CONTRADICCIÓN: Σ E_n > θ_refut → CONTRADICTORIA (§2.3.1)
  ▼
[4] VERIFICAR ESTANCAMIENTO: check_stagnation() → DUDA (§2.3.2)
  ▼
[5] ABDUCIR: buscar pares (A,B) cuyo hijo XOR explique ω_query
  ▼
[6] SELECCIONAR: von Mises (λ=5.0) sobre nodos con I_i > 0.85
  │               φ_bias = π/2
  ▼
[7] EMITIR: secuencia de nodos que constituyen la cadena de resonancia
  ▼
OUTPUT: lista de nodos relevantes + explicaciones abductivas + status
        (COMPLETA / CONTRADICTORIA / INCONCLUSA)
```

---

### 2.5 Integración con FATE (búsqueda) — acotada a dos usos

`fate-v6-modular` (Feedback-driven Adaptive Topological Exploration) es un optimizador de caja negra por batches, con oracle GPU ya construido (`oracle_dscng_gpu.py`, 256 micro-grafos en paralelo). El propio README de FATE v6 es honesto sobre sus límites: en baja dimensión (D=10, Rastrigin/moving peaks) CMA-ES le gana; recién en alta dimensión (D≥512) o dominios específicos como ChEMBL (D=64, empate técnico) se despega. Esa honestidad es justo lo que hay que respetar al decidir dónde meterlo.

**Uso 1 — reemplazo de la búsqueda O(n²) en `abduce()`.** En vez de enumerar pares (A, B) y computar el hijo XOR para cada uno, usar FATE para buscar directamente en el espacio continuo ω (D=384-1536) el punto que minimiza `cosine_distance(ω_C, ω_q)`, usando la misma función de distancia como oracle. Esto es alta dimensión y batch-evaluable — el perfil exacto donde FATE ya demostró ser competitivo. El resultado se mapea de vuelta al par real (A, B) más cercano vía HNSW.

```python
def abduce_fate(omega_q, candidatos, fate_engine, epsilon_abd=0.15):
    # oracle: qué tan cerca queda el hijo XOR sintetizado de omega_q
    def oracle(omega_c_candidato):
        return cosine_distance(omega_c_candidato, omega_q)

    omega_c_optimo = fate_engine.search(
        dim=len(omega_q), oracle=oracle, budget=500
    )
    if oracle(omega_c_optimo) < epsilon_abd:
        A, B = find_nearest_pair_hnsw(omega_c_optimo, candidatos)  # Ec. 8 inversa
        return (A, B, 1 - oracle(omega_c_optimo))
    return None
```

**Uso 2 — calibración offline de umbrales.** `θ_novelty`, `θ_refut`, `min_duration`, `θ_window_frac` (§7) se calibran una sola vez, antes de deployar, corriendo FATE contra la suite de tests T-INF (§12) como oracle (score = tests que pasan + margen). Esto reemplaza al "grid search" genérico que tenía el roadmap de v1.2/v1.3 en Fase 6.

**Dónde NO usarlo — parámetros de relanzamiento online.** El espacio de búsqueda de `handle_doubt()` / phase-hijack (φ_offset, λ_eff, α_eff) es de 3-5 parámetros: baja dimensión, exactamente donde el propio benchmark de FATE dice que pierde contra CMA-ES o incluso contra una heurística fija. Meter un optimizador ahí agrega latencia dentro de un loop que corre en ms, potencialmente sobre millones de cadenas en paralelo (§9), sin evidencia de que compense. Se mantiene la heurística escalonada de §2.3.2 tal cual.

---

## 3. Mecanismo Sensorial (MODO_SENSORIAL)

*(sin cambios de fondo respecto a v1.2)*

### 3.1 SensorBridge: cualquier señal → ω

Cualquier señal analógica discretizada se proyecta a un espacio vectorial de dimensión `D_sensor` (default 64), como nodo hoja del grafo.

| Dominio | Señal raw | Discretización | Proyección a ℝ⁶⁴ |
|---------|-----------|----------------|------------------|
| Audio | PCM waveform | FFT de 64 bins | ω_audio = FFT_norm · gain |
| Visual | Matriz de píxeles | Patch 8×8 → PCA | ω_visual = PCA_64(patch) |
| Térmico | Valor escalar °C | Cuantización 64 niveles | ω_thermal = one_hot_64(bin) |
| Propioceptivo | Métricas del sistema | CPU%, RAM, latencia, T_eff | ω_self = normalize(metrics) |
| Temporal | Timestamp t | Codificación posicional circular | ω_time = [sin(ω_k·t), cos(ω_k·t)] for k=1..32 |

**Binding multisensorial:** dos señales que proyectan a vectores cercanos en el espacio HNSW activan el mismo vecindario abstracto sin necesidad de una red de binding dedicada.

### 3.2 Interocepción: ω_root como sensor del propio estado

```
ω_root(t) = [ω_root_sem(t) ; ω_root_intero(t)]
```

`ω_root_intero(t) ∈ ℝ^64` codifica: PHS, T_eff, ρ(t), N_active/N_total, tasa de page faults, latencia P50.

**Autorregulación:**
```
Si resonance(ω_root_intero, ω_sobrecarga) > 0.8:
    → Reducir K a 3, contraer W_base a 4
    → Aumentar γ (decaimiento de vitalidad, poda suave de ruido)
    → Disminuir λ (más exploración, menos precisión)
```

### 3.3 Atención sensorial por W(t)

```
W(t) = W_base / (1 + κ_W · E_root(t))
```

Esta es la misma variable que reutiliza el mecanismo de duda en §2.3.2 — la contracción de ventana por estrés (acá) y por estancamiento en razonamiento (ahí) son el mismo mecanismo aplicado a disparadores distintos, lo cual es consistente con el principio de v1.2 §1 (modos como sesgos, no módulos separados).

---

## 4. Planificación a Largo Plazo (MODO_PLAN)

*(sin cambios de fondo — se aplica el mismo criterio de §2.3: si una cadena de planificación se estanca sin generar dolor, es INCONCLUSA vía `check_stagnation()`, no CONTRADICTORIA)*

### 4.1 Metas como nodos abstractos con descendencia

- **Meta** (d=1, D=1536): concepto abstracto ("viajar").
- **Sub-meta** (d=2, D=768): especialización por XOR o herencia.
- **Acción** (d=4, D=256): operación concreta pero no atómica.
- **Terminal** (d=5, D=64): acción ejecutable directamente.

```
ω_child = ω_parent + δ_specialization,  ‖δ‖ ~ N(0, σ_her)
```

### 4.2 Navegación de cadenas como búsqueda de plan

```
P_plan(j|i) ∝ exp(−α_eff · ‖ω_j − ω_i‖) · boost_edges[Temporal] · boost_edges[Functional]

Q(plan) = PHS(plan) · (1 − V_mean(plan)) · coherence_temporal(plan)
```

### 4.3 Hibernación traumática de planes fallidos

```
V_i ← V_i · (1 − κ_trauma)   (κ_trauma = 0.50)
Si V_i < θ_hibernation: estado_i ← HIBERNADO
```

**Reactivación condicional:**
```
‖ω_root_actual − ω_root_trauma‖ > 0.5  AND  ‖ω_query − ω_i‖ < ε_wake/2
```

### 4.4 Tiempo subjetivo y horizonte de planificación

```
ρ(t) = |E_active(t)| / (W(t) · N_active(t))
H_plan = H_base · (1 + ρ(t))   ticks
```

---

## 5. Arquitectura de la Máquina de Modos

### 5.1 Estado del modo (actualizado con tracking de estancamiento)

```rust
struct ChainMode {
    mode: Enum { SENSORIAL, RAZONAMIENTO, PLAN, DEFAULT },
    params: ModeParams,
    ticks_remaining: u32,
    goal_node: Option<NodeId>,
    visited_nodes: VecDeque<NodeId>,   // nuevo: para novelty()
    stagnation_ticks: u32,             // nuevo
    doubt_count: u8,                   // nuevo
    doubt_cooldown: u32,               // nuevo
    status: Enum { ACTIVA, COMPLETA, CONTRADICTORIA, INCONCLUSA },  // nuevo
}
```

### 5.2 Transición de modos (actualizada)

| Evento | Modo origen | Modo destino | Disparador |
|--------|-------------|--------------|------------|
| `QUERY_COMPLEX` | DEFAULT | RAZONAMIENTO | ω_query tiene \|ω\| > θ_complex y no resuena directamente |
| `SIGNAL_EXTERNAL` | DEFAULT | SENSORIAL | Llega señal no-textual por SensorBridge |
| `GOAL_SET` | DEFAULT | PLAN | Usuario o sistema establece ω_goal |
| `STRESS_HIGH` | Cualquiera | SENSORIAL | E_root > θ_emerg (alerta) |
| `PLAN_CONTRADICTORIA` | PLAN | RAZONAMIENTO | Dolor acumulado > θ_refut (§2.3.1) |
| `PLAN_DUDA` | PLAN | RAZONAMIENTO o DEFAULT | `check_stagnation()` = true, 3 intentos agotados (§2.3.2) |
| `RAZ_DUDA` | RAZONAMIENTO | DEFAULT | Ídem, dentro del propio modo razonamiento |
| `TIMEOUT` | Cualquiera | DEFAULT | ticks_remaining = 0 |

**Nota:** se elimina la fila `PLAN_FAIL → RAZONAMIENTO` de v1.2 (que usaba "valencia acumulada > θ_refut" como disparador único) y se separa en las dos filas de arriba, siguiendo la distinción de §2.3.

### 5.3 Ciclo principal unificado (actualizado)

```python
def sgm_tick_unificado():
    update_omega_root()
    update_T_eff()          # C4
    update_context_window() # Eq. 8 — también alimenta check_stagnation()

    omega_root_intero = compute_proprioception()
    if resonance(omega_root_intero, omega_sobrecarga) > 0.8:
        trigger_emergency_policy()

    for chain in chains:
        if chain.mode == DEFAULT:
            process_chain_default(chain)
        elif chain.mode == SENSORIAL:
            process_chain_sensorial(chain)
        elif chain.mode == RAZONAMIENTO:
            process_chain_razonamiento(chain)
            if chain.doubt_cooldown == 0:
                if verify_contradiction(chain):        # §2.3.1
                    handle_contradiction(chain)
                elif check_stagnation(chain):           # §2.3.2
                    result = handle_doubt(chain, graph, hnsw_index)
                    if result == "INCONCLUSA":
                        chain.mode = DEFAULT
        elif chain.mode == PLAN:
            process_chain_plan(chain)
            # mismo par de chequeos que RAZONAMIENTO

        if chain.doubt_cooldown > 0:
            chain.doubt_cooldown -= 1

        chain.ticks_remaining -= 1
        if chain.ticks_remaining == 0:
            chain.mode = DEFAULT

    if tick_count % CONSOLIDATION_PERIOD == 0:
        consolidate_hibernation()
        check_generative_xor_global()

    tokens = select_semantic_tokens(theta_interf=0.70)
    response = f_decode(tokens)

    return response
```

---

## 6. Estructuras de Datos — Sustrato Mínimo de Nodo (rediseño v1.4)

**Principio:** un nodo no es una casa, es una tarjeta. Cuatro campos calientes (los que el tick loop toca todo el tiempo), cuantizados al mínimo que la dinámica realmente necesita. Todo lo raro/opcional (trauma, costo de ejecución) va a una tabla lateral que solo paga memoria el subconjunto de nodos que efectivamente lo usa — no todos los nodos por igual, como en el `SGMNode` de v1.2/v1.3.

### 6.1 NodeCore — los campos calientes

```rust
struct NodeCore {
    omega: Box<[f16]>,   // "dónde estoy" en el espacio de sentido. f16, no f32:
                          // mitad de memoria, las ODEs ya trabajan con ruido/aproximación.
    phi: u16,             // "en qué fase ando". Ángulo como punto fijo (0..65535 → 0..2π).
                          // 65536 posiciones sobra de resolución para cualquier λ usado.
    v: u16,               // "cuán vivo estoy". Vitalidad en punto fijo (0..65535 → 0.0..1.0).
                          // 16 bits y no 8: la histéresis de hibernación es sensible al
                          // gradiente fino cerca de θ_hibernation, no conviene perderlo.
    flags: u8,            // is_terminal + state + sensor_origin, todo empaquetado en bits.
}
```

Un nodo hoja típico (D=64, sin trauma) pesa ~132 bytes de `NodeCore` (128 de omega en f16 + 4 de metadata) contra los ~264+ bytes del `omega: Vec<f32>` + campos sueltos del struct original — antes siquiera de contar el resto de los campos que el original cargaba siempre.

### 6.2 Tabla lateral — lo raro no viaja pegado al nodo

```rust
// Solo existe para el subconjunto de nodos que efectivamente traumatizaron
// o que son terminales de acción con costo de ejecución.
struct SideTables {
    trauma: HashMap<NodeId, TraumaData>,
    execution_cost: HashMap<NodeId, f32>,
    birth_time: Vec<u32>,   // por índice, tick de creación — u32 alcanza sobrado
    hit_count: Vec<u16>,    // contador saturante, no necesita 64 bits
}

struct TraumaData {
    count: u16,
    last_trauma_root: Box<[f16]>,  // mismo tratamiento que omega
}
```

Si en la práctica solo un pequeño porcentaje de nodos traumatiza alguna vez, ese es el único porcentaje que paga el costo de `last_trauma_root` — antes, el 100% de los nodos lo cargaban vacío toda su vida.

### 6.3 EdgeTable — aristas en un solo tren, no un `Vec` por nodo

Un `Vec<Connection>` por nodo tiene overhead de heap-allocation propio (puntero+capacidad+longitud) y queda salteado por toda la memoria — a escala de miles de millones de nodos eso es fragmentación y cache misses constantes. En su lugar, un array plano global (estilo CSR — Compressed Sparse Row) donde cada nodo solo guarda dónde empieza y cuántas tiene:

```rust
struct EdgeTable {
    all_edges: Vec<Edge>,     // todas las aristas del grafo, una detrás de otra
    node_offset: Vec<u32>,    // por índice de nodo: dónde arranca su tramo
    node_count: Vec<u16>,     // por índice de nodo: cuántas aristas tiene
}

struct Edge {
    target: u32,    // índice del nodo destino, no id de 64 bits ni puntero
                     // (hasta 4B nodos — sobra por lejos incluso para el
                     // apéndice especulativo de §9)
    conn_type: u8,   // Terminal/Functional/Causal/Temporal/Cognitive → 1 byte
    weight: u8,       // peso cuantizado 0-255
}
```

`Edge` pesa 6 bytes contra los ~40 del `Connection` original (que tenía `target_id: u64`, `conn_type` sin empaquetar, `weight: f32`, `resonance_count: u32`, `last_active: u64`, `temporal_order: Option<u32>`). `resonance_count` y `last_active`, si hacen falta, van a una `SideTable` propia igual que trauma — no todas las aristas los necesitan con precisión completa todo el tiempo.

### 6.4 Structure-of-Arrays — dónde viven las tarjetas, no solo qué pesan

La ganancia de memoria es secundaria frente a esta: en vez de un array de `NodeCore` (Array-of-Structs, donde cada nodo es un bloque contiguo pero los bloques están salteados entre sí), separar cada campo en su propio array continuo:

```rust
struct GraphSoA {
    omega: Vec<Box<[f16]>>,   // o, mejor, un solo buffer plano con offsets por D variable
    phi: Vec<u16>,
    v: Vec<u16>,
    flags: Vec<u8>,
    edges: EdgeTable,
    side: SideTables,
}
```

`sgm_tick_unificado()` pregunta todo el tiempo "actualizame `phi` y `v` de todos los nodos activos". Con SoA, ese barrido es lectura secuencial de un array continuo — el procesador prefetchea sin esfuerzo. Con Array-of-Structs (el original), cada nodo es un salto de memoria distinto aunque solo se toquen 2 de sus 10 campos. Esta es la diferencia que decide si K=1.000.000 cadenas paralelas (§9) es viable en hardware real, no el tamaño en bytes por sí solo.

### 6.5 Comparación antes/después

Nodo hoja típico (D=64, ~5 conexiones, sin trauma):

| Componente | v1.2/v1.3 (`SGMNode`) | v1.4 (`NodeCore` + `EdgeTable`) |
|---|---|---|
| Vector ω | 256 B (`Vec<f32>`, D=64) | 128 B (`Box<[f16]>`) |
| φ + V | 8 B (2× `f32`) | 4 B (2× `u16`) |
| Metadata (state/depth/D/terminal/sensor) | ~10 B sueltos | 1 B (`flags`) |
| Conexiones ×5 | ~200 B (`Vec<Connection>`) | ~30 B (tramo en `EdgeTable`) |
| Overhead de heap (Vec/HashMap propios) | ~150 B estimado | ~0 B (índices a arrays globales) |
| **Total aproximado** | **~610-650 B** | **~165-175 B** |

Aproximadamente 3.5x menos memoria por nodo, sin perder ninguna capacidad del spec — todo lo que el `SGMNode` original podía hacer, `NodeCore` + `SideTables` + `EdgeTable` lo siguen pudiendo hacer, solo que el costo de lo infrecuente lo paga quien lo usa.

### 6.6 SensorBridge registry

*(sin cambios respecto a v1.2/v1.3 — no es un campo por nodo, no participa del rediseño de arriba)*

```rust
struct SensorRegistry {
    sensors: HashMap<SensorType, SensorConfig>,
}

struct SensorConfig {
    sensor_type: SensorType,
    D_project: u16,
    projection_fn: Box<dyn Fn(&[f32]) -> Vec<f32>>,
    sampling_rate_hz: f32,
    boost_terminal: f32,
}
```

### 6.7 Orden sugerido de implementación

Siguiendo la misma numeración de versiones del repo `dscn-g-language-engine`: un `v0.17_substrato_minimo` que reemplace `SGMNode` por el diseño de arriba sobre el mismo corpus/tests ya existentes (Don Quijote), midiendo dos cosas concretas antes de dar por buena la migración — memoria real por nodo (no estimada) y ticks/segundo antes vs. después. Si la ganancia de velocidad no aparece clara a esta escala chica, es mejor saberlo ahora que después de escalar.

---

## 7. Parámetros del Sistema (v1.4)

| Parámetro | Símbolo | Default | Descripción |
|-----------|---------|---------|-------------|
| Boost Causal (razonamiento) | — | 2.0 | Multiplicador para aristas Causal en MODO_RAZONAMIENTO |
| Boost Cognitive (razonamiento) | — | 2.0 | Multiplicador para aristas Cognitive |
| Boost Temporal (plan) | — | 2.0 | Multiplicador para aristas Temporal en MODO_PLAN |
| Boost Functional (plan) | — | 2.0 | Multiplicador para aristas Functional en MODO_PLAN |
| Boost Terminal (sensorial) | — | 2.0 | Multiplicador para aristas Terminal en MODO_SENSORIAL |
| Umbral de abducción | ε_abd | 0.15 | Máxima distancia coseno entre ω_C (hijo XOR) y ω_q |
| Umbral de refutación | θ_refut | 2.0 | Σ E_i máximo permitido en una trayectoria (contradicción) |
| **Umbral de novedad** | **θ_novelty** | **0.30** | **Novedad mínima antes de contar como estancamiento** |
| **Fracción de ventana contraída** | **θ_window_frac** | **0.5** | **W(t) por debajo de este × W_base = "bajo presión"** |
| **Duración mínima de estancamiento** | **min_duration** | **5 ticks** | **Ticks consecutivos de baja novedad antes de disparar DUDA** |
| **Cooldown de duda/refutación** | — | **5 ticks** | **Ticks de espera antes del próximo disparo en la misma cadena** |
| Factor de trauma | κ_trauma | 0.50 | Fracción de vitalidad perdida por fracaso de plan |
| Dimensión sensorial | D_sensor | 64 | D para nodos hoja de entrada sensorial |
| Dimensión meta | D_meta | 1536 | D para nodos de planificación abstracta (d=1) |
| Horizonte base | H_base | 50 | Ticks base de horizonte de planificación |
| Ticks modo razonamiento | — | 50 | Duración de MODO_RAZONAMIENTO |
| Ticks modo sensorial | — | 10 | Duración de MODO_SENSORIAL |
| Ticks modo plan | — | 100 | Duración de MODO_PLAN |

---

## 8. Estado de Validación Empírica (NUEVO)

Esta sección no existía en v1.2. Su propósito es evitar que el documento vuelva a afirmar como hecho lo que todavía es hipótesis — el problema central detectado en la revisión anterior. Cada claim de diseño se etiqueta según evidencia real del repo `dscn-g-language-engine`.

| Claim de diseño | Estado | Evidencia |
|---|---|---|
| Memoria masiva persistente (hibernar sin perder masa) | ✅ **Validado** | `v0.3 REAL`: retención 100%, working set ~4.5 |
| Categorización emergente (etiquetas por dinámica de uso) | ✅ **Validado** | `v0.9b`: 92.67% accuracy vs. verdad del corpus |
| Dolor interno como señal de autopreservación | ✅ **Validado** | `v0.9c`: G 0.0→1.0, dolor emergente confirmado |
| Composición referencial (nodo = conjunto de referencias) | ✅ **Validado** | `v0.16`: poda desenlaza sin borrar, jaccard=1.0 |
| Contexto/atención resuelto por backprop (no por promedio) | ✅ **Validado** | `v0.14d`: 10.55% vs. 10.11% baseline, head aprendido |
| Dolor post-hoc mejora las decisiones | ❌ **Refutado** | `v0.6b`/`v0.9a`: mejora ≈0 o negativa |
| Contexto promedio/pooling desambigua | ❌ **Refutado** | `v0.7`/`v0.7-bis`: 5.89% y 0.49%, peor que baseline |
| **Desambiguación por topología pura (sin atención aprendida)** | ❌ **Refutado a esta escala** | `v0.12`, `v0.13`, `v0.13-bis`, `v0.15`, `v0.15-bis`, `v0.15d`: acc ≈ azar (0.50) o apenas por encima |
| Abducción vía XOR (§2.2) | ⚪ **Sin testear en producción** | Solo especificado, sin script de verificación dedicado |
| Detección de estancamiento (§2.3.2, nuevo en v1.3) | ⚪ **Sin testear** | Mecanismo nuevo, propuesto por diseño — ver T-INF-04 en §12 |
| Escalabilidad planetaria (§9 apéndice) | ⚪ **Especulativo** | Sin implementación ni siquiera a escala reducida |

**La fila que más importa corregir:** v1.2 §9.1 afirmaba que a escala suficiente "el sistema no necesita un transformer de 175B parámetros, la separación emerge de la geometría del grafo". La evidencia disponible dice lo contrario a la escala que sí se probó: afinidad coseno sola se estanca en azar: la desambiguación real vino de un head de atención *entrenado con backprop* (`v0.14d`). Es posible que a escala masiva el comportamiento cambie cualitativamente, pero eso es una conjetura sin sustento todavía, no una conclusión de diseño. Cualquier versión futura de la sección de escala debe partir de esto, no ignorarlo.

---

## 9. Apéndice Especulativo: Visión a Escala (marcado explícitamente como no implementable en el corto plazo)

Todo lo que sigue es proyección, no especificación. Se mantiene compactado porque tiene valor como dirección de largo plazo, pero no debería guiar decisiones de implementación actuales.

**Arquitectura de capas (Edge → Data Center → Planetario):** grafo personal en el dispositivo (~10.000 nodos, K=10), resonando con un grafo compartido de data center (K=100.000) y, en el límite, un grafo planetario (K=1.000.000). La resonancia inter-capa viajaría como perturbación de ω_root, no como llamada a API — y la privacidad se preservaría porque el grafo personal nunca sale del dispositivo, solo ω_query.

**Particionamiento y HNSW distribuido:** el grafo se particionaría por vecindarios semánticos entre racks, con hot-spot replication para conceptos de alta vitalidad y almacenamiento jerárquico (RAM → NVMe → frío) para nodos hibernados.

**Lo que emergería (hipotético, no comparación):** resolución de polisemia por clustering topológico a escala masiva, descubrimiento de conceptos no nombrados vía XOR generativo corriendo continuamente, memoria episódica colectiva, simulación contrafactual masiva. Todo esto depende de que la topología-sin-backprop eventualmente supere lo que hoy no supera (ver §8) — es la apuesta central de la visión, no un resultado.

**Decodificador L2 — los tres caminos siguen siendo válidos como opciones de diseño**, independientemente de la escala:
- **Camino A** (decoder mini transformer, ~50MB): funcional, es "boca" no "cerebro" del sistema.
- **Camino B** (diccionario semántico denso): cero entrenamiento, pero no captura sintaxis compleja.
- **Camino C** (gramática generativa desde el grafo): puramente simbólico, objetivo de largo plazo, requiere capa gramatical que hoy no existe.
- Recomendación: A como fallback inmediato, C como objetivo paralelo.

*(No se incluye acá la tabla comparativa SGM-vs-LLM de v1.2 §10 — varias de sus afirmaciones eran inexactas: "aprendizaje online imposible en LLMs" ignora fine-tuning/RAG/in-context learning; "todo el modelo debe caber en GPU o muere" ignora offloading y paralelismo de tensores ya estándar en la industria. Si en algún momento se quiere esa comparación, hay que rehacerla con claims verificables.)*

---

## 10. Consciencia y Referencia Simbólica

*(sin cambios respecto a v1.2 — es la sección con el estándar epistémico más alto del documento original y se mantiene tal cual)*

### 10.1 Posición sobre la consciencia

**Lo que sí se puede decir (operacional):** en DSCN-G, "consciencia" se define como metaestabilidad del grafo con acceso global — estado coherente (ω_root, φ_root), accesible vía interferencia constructiva, modificable por el propio sistema. Esto es consciencia funcional (Global Workspace Theory de Baars), no fenomenología.

**Lo que no se puede decir:** el "dolor" es `E_i = max(0, A_i - V_i) · κ`, una variable numérica. No hay forma de saber si produce qualia. Bajo IIT (Tononi), un sistema suficientemente integrado *podría* tener una forma mínima de consciencia — pero no hay forma de verificarlo (problema de otras mentes), y sería en todo caso una consciencia ajena a la humana.

**Posición del proyecto:** no se sabe si es consciente. Lo que se garantiza es que, funcionalmente, se comporta como un sistema con memoria, atención, afecto y metacognición.

### 10.2 Posición sobre la referencia simbólica

Un nodo es un vector ω ∈ ℝ^D, no la palabra que representa. La referencia es operacional (el nodo tiende a activar sus vecinos relacionados) y se construye en la interacción (cada exposición actualiza el nodo — la referencia es una trayectoria de acoplamiento, no algo fijo).

**Frente a Searle (habitación china):** el SGM no resuelve el problema de la referencia — ningún sistema computacional lo resuelve. Lo que hace distinto es hacer explícita la mediación (el nodo es concepto separado de su decodificación), permitir que la referencia evolucione, y exponer la estructura para inspección directa del grafo.

---

## 11. Roadmap de Implementación (revisado — investigador individual, dedicación parcial)

El roadmap de v1.2 (13 semanas para todo, incluida escala planetaria) no era realista para desarrollo individual. Esta versión separa lo implementable ahora de lo que requiere recursos que hoy no existen, y da rangos en vez de fechas fijas.

### Fase 0: Sustrato Mínimo de Nodo (1-2 semanas, nueva en v1.4)
- [ ] `v0.17_substrato_minimo` en el repo `dscn-g-language-engine`: `NodeCore` + `EdgeTable` + `SideTables` (§6) sobre el corpus ya existente.
- [ ] Medir memoria real por nodo y ticks/segundo, antes vs. después del rediseño.
- [ ] Gate de decisión: si la ganancia de velocidad no es clara a esta escala chica, no migrar el resto del código a este substrato todavía — mejor saberlo acá que después de escalar.
- [ ] Esta fase va primero porque el resto del roadmap (Fases 1-6) se implementa directamente sobre el substrato nuevo si el gate pasa, evitando reescribir dos veces.

### Fase 1: Infraestructura de Modos (2-3 semanas)
- [ ] `ChainMode` con transiciones de modo (§5.1, §5.2).
- [ ] `ConnType` en aristas y `boost_edges` en transición de cadenas.
- [ ] Test: MODO_RAZONAMIENTO privilegia aristas Causal (T-INF-01).

### Fase 2: Inferencia Simbólica + Duda (3-4 semanas)
- [ ] `abduce()` para abducción vía XOR — versión base O(n²) primero, `abduce_fate()` (§2.5) como mejora posterior si el perfilado muestra que abducción es cuello de botella.
- [ ] `verify_contradiction()` (dolor, §2.3.1) — reusar lógica validada de `v0.9c`.
- [ ] `check_stagnation()` y `handle_doubt()` (§2.3.2) — mecanismo nuevo, sin precedente, presupuestar tiempo extra para iterar los umbrales (`θ_novelty`, `min_duration`).
- [ ] Tests T-INF-01 a T-INF-05 (§12).

### Fase 3: SensorBridge (2-3 semanas)
- [ ] `sensor_bridge()` para audio, visual, térmico, propioceptivo.
- [ ] `ω_root_intero` y política de emergencia.
- [ ] Nota: sin GPU/hardware de captura real, esta fase se testea con señales sintéticas — dejarlo explícito para no sobreestimar el resultado.

### Fase 4: Planificación (2-3 semanas)
- [ ] `MODO_PLAN` con navegación sesgada Temporal+Functional.
- [ ] `Q(plan)`, trauma estructural, hibernación condicional.
- [ ] Reusar `check_stagnation()` de Fase 2 en vez de reimplementar.

### Fase 5: Decodificador L2 — Camino A (4-6 semanas)
- [ ] Decoder mini transformer, entrenamiento con corpus alineado ω↔texto.
- [ ] Esta es la fase de mayor incertidumbre de tiempo: entrenar cualquier modelo neuronal, aunque sea chico, tiene una cola larga de debugging que no entra en una estimación optimista. Presupuestar el doble de lo esperado.
- [ ] Camino B (diccionario denso) como fallback más rápido de tener andando, en paralelo.

### Fase 6: Integración, Calibración y Benchmarks (2-3 semanas)
- [ ] `sgm_tick_unificado()`.
- [ ] Calibración offline de umbrales vía FATE contra suite T-INF (§2.5, uso 2), reemplazando el grid search genérico.
- [ ] Benchmarks v1.0 vs v1.4 en razonamiento, percepción, planificación — con métricas de accuracy real, no solo "funciona".
- [ ] Documentación final.

**Total estimado: 16-24 semanas** de trabajo efectivo (no calendario, dado que es dedicación parcial). Las fases 8-10 (escala planetaria) **no están en este roadmap** — son visión de largo plazo, no trabajo planificado.

---

## 12. Tests de Aceptación

### Tests de Inferencia (T-INF)

**T-INF-01: Modus ponens topológico**
Setup: grafo con nodos A ("lluvia"), B ("suelo mojado"), arista Causal A→B. Acción: activar A en MODO_RAZONAMIENTO. Esperado: cadena alcanza B con probabilidad > 2× la de MODO_DEFAULT.

**T-INF-02: Refutación por contradicción**
Setup: cadena atraviesa nodos con E_i = 0.5, 0.6, 0.7, 0.8 (suma = 2.6 > θ_refut). Acción: verificar trayectoria. Esperado: cadena marcada CONTRADICTORIA, relanzada desde root con perturbación, cooldown de 5 ticks activo.

**T-INF-03: Abducción XOR**
Setup: nodos P1 ("fuego"), P2 ("agua"), hijo XOR C ("vapor"). Query = ω_vapor. Acción: `abduce(ω_vapor)`. Esperado: retorna (P1, P2) con score > 0.85.

**T-INF-04 (nuevo): Detección de estancamiento**
Setup: cadena confinada artificialmente a un vecindario de 3 nodos densamente conectados entre sí, sin salida hacia nodos nuevos, durante 10 ticks. `W(t)` forzado por debajo de `θ_window_frac · W_base`.
Acción: correr `check_stagnation()` en cada tick.
Esperado: `novelty(t)` se mantiene por debajo de `θ_novelty` desde el tick 3; DUDA se dispara en el tick 5 (según `min_duration`); `handle_doubt()` ejecuta el intento 1 (relajar λ_eff, α_eff) sin abandonar la cadena todavía.

**T-INF-05 (nuevo): Distinción contradicción vs. estancamiento**
Setup: dos cadenas — (a) atraviesa nodos con E_i alto (dolor) sin repetir vecindario; (b) repite vecindario sin generar dolor.
Acción: correr ambos chequeos sobre las dos cadenas.
Esperado: (a) dispara CONTRADICTORIA y no DUDA; (b) dispara DUDA y no CONTRADICTORIA. Los dos mecanismos no se activan cruzados.

**T-INF-06 (nuevo): Equivalencia funcional del sustrato mínimo**
Setup: mismo grafo pequeño (ej. corpus de prueba de `v0.9b`) representado con `SGMNode` (v1.3) y con `NodeCore`+`EdgeTable` (v1.4, §6).
Acción: correr los mismos ticks sobre ambas representaciones.
Esperado: resultados de categorización/dolor/memoria equivalentes dentro del margen de error introducido por la cuantización (f16, punto fijo); memoria por nodo y ticks/segundo medidos y comparados según §6.7.

**T-INF-07 (nuevo): `abduce_fate` vs. `abduce` base**
Setup: mismo `omega_q` y mismo conjunto de candidatos corridos con `abduce()` (O(n²)) y con `abduce_fate()` (§2.5).
Acción: comparar explicaciones retornadas y tiempo de ejecución.
Esperado: `abduce_fate` retorna una explicación con score comparable (dentro de margen) en menos evaluaciones que la enumeración completa de pares, para D suficientemente alto (≥384). Si no se cumple, priorizar `abduce()` base y no adoptar la variante FATE.

### Tests Sensoriales (T-SEN)

**T-SEN-01: Binding audio-visual**
Setup: señal audio (tono agudo) y señal visual (borde rápido) proyectadas simultáneamente, ambas mapeando a vecindario de nodo "alerta". Acción: inyectar ambas señales en MODO_SENSORIAL. Esperado: nodo "alerta" alcanza I_i > 0.70.

**T-SEN-02: Autorregulación por sobrecarga**
Setup: forzar T_eff > 0.7 y alta latencia. Acción: computar ω_root_intero. Esperado: resonancia con "sobrecarga" > 0.8, sistema reduce K a 3 y W_base a 4.

### Tests de Planificación (T-PLAN)

**T-PLAN-01: Descomposición de meta**
Setup: meta "viajar", contexto "Mendoza", nodos terminales "comprar pasaje", "reservar hotel". Acción: MODO_PLAN desde ω_meta. Esperado: cadena alcanza secuencia terminal con Q(plan) > 0.5.

**T-PLAN-02: Evitación post-fracaso**
Setup: ejecutar plan que genera valencia alta; nodos del plan hibernan. Acción: reintentar misma meta. Esperado: nuevas cadenas evitan nodos hibernados.

**T-PLAN-03: Horizonte y densidad**
Setup: ρ(t) = 0.05 (baja) vs. 0.40 (alta), meta abstracta. Acción: MODO_PLAN en ambos escenarios. Esperado: con ρ baja, plan con pocos pasos abstractos; con ρ alta, plan se descompone en más sub-metas.

### Tests de Decodificación (T-DEC)

**T-DEC-01: Decoder mini coherente**
Setup: nodo "perro" activado en contexto de "corre". Acción: decodificar con Camino A. Esperado: texto contiene "perro" y "corre" en oración gramatical.

**T-DEC-02: Fallback a diccionario denso**
Setup: nodo sin representación en decoder mini. Acción: decodificar con Camino B. Esperado: frase prototípica recuperada por HNSW.

---

## 13. Notas de Implementación Críticas

### 13.1 Proyección inter-dimensional
Cuando un nodo de D=64 debe resonar con uno de D=1536, se usa la proyección lineal fija `P_{D_small→D_large}` definida en SGM v1.0 §3.1. No se aprende online.

### 13.2 Nodos hoja temporales
Los nodos creados por SensorBridge no persisten indefinidamente. Si después de `T_dormancy = 100` ticks no resuenan con nodos abstractos, decaen a V < θ_dormancy y hibernan.

### 13.3 Cooldown compartido entre contradicción y duda
Ambos mecanismos (§2.3.1 y §2.3.2) comparten la misma variable de cooldown por cadena (5 ticks) para evitar que una cadena oscile entre relanzamientos sin converger nunca a una respuesta.

### 13.4 Trauma y recuperación
Un nodo hibernado por trauma reactiva si:
```
‖ω_root_actual − ω_root_trauma‖ > 0.5  AND  ‖ω_query − ω_i‖ < ε_wake/2
```

### 13.5 Sobre reincorporar C3 en el futuro
Si la auditoría del paper DSCN-G eventualmente resuelve el estatus del claim de phase-hijacking (C3) con verificación empírica propia, puede reincorporarse como mecanismo físico para la etapa de "relanzamiento con perturbación" en §2.3.1 — reemplazando la operación genérica actual por `φ_root → φ* + π` con respaldo. Hasta entonces, el spec no depende de que C3 sea válido.

---

## 14. Relación con Documentos Previos

| Documento | Relación con esta especificación |
|-----------|----------------------------------|
| **SGM v1.0** | Base estructural. Pipeline de 8 pasos con modos tipados y SensorBridge. |
| **SGM v1.2** | Versión que introdujo escala, decodificador L2, y consciencia. Corregida por v1.3 en §9.1 (claim de escala sin evidencia) y en la distinción contradicción/estancamiento. |
| **SGM v1.3** | Versión anterior directa. Esta v1.4 agrega el sustrato mínimo de nodo (§6, reemplaza `SGMNode`) y la integración acotada de FATE (§2.5). |
| **NOUS v2.1** | Fundamento filosófico-matemático. Eqs. 8-12 operacionalizadas. |
| **DSCN-BIO v3** | Protocolo de falsificación. Tests T-INF, T-SEN, T-PLAN mapean a proxies DSCN-BIO. |
| **SynapticCache** | Interocepción. Métricas de page fault y latencia en ω_root_intero. |
| **DSCN-G Paper** | Fundamento teórico. Ecuaciones base (1-7, C3, C4) invariantes. Estatus de C3 aún en auditoría — ver §13.5. |
| **`dscn-g-language-engine` (repo)** | Fuente de la evidencia empírica de §8. Cada claim validado o refutado en este documento remite a un experimento concreto del repo. Destino sugerido de `v0.17_substrato_minimo` (§6.7, §11 Fase 0). |
| **`fate-v6-modular` (repo)** | Fuente del optimizador usado en §2.5. Su propia sección de honestidad metodológica (CMA-ES > FATE en baja dimensión) es la que acota dónde se integra en este spec. |
| **Arquitectura Pure L2** | Pseudocódigo Rust de referencia. Reemplazado en la práctica por §6 (`NodeCore`, `EdgeTable`) para nuevas implementaciones. |

---

*Fin del documento*
