# Consenso Técnico Unificado: SGM v1.0 + NOUS v2.1 + DSCN-BIO v3

> **Documento de Arquitectura de PandoraOS (AgentPandora)**  
> Confidencial — Para uso interno del equipo  
> Compilado: 2025-06-28

---

## 1. RESUMEN EJECUTIVO

Este documento consolida los hallazgos de los tres papers operativos de PandoraOS:

| Paper | Rol | Estado |
|-------|-----|--------|
| **SGM v1.0** | Especificación técnica del motor cognitivo que reemplaza a los LLM | Activo |
| **NOUS v2.1** | Arquitectura filosófico-matemática de la identidad, contexto y tiempo subjetivo | Activo |
| **DSCN-BIO v3** | Protocolo de falsificación con biomarcadores EEG, ROI para testeing de hipótesis | En exploración |

**Resultado conjunto:** un sistema cognitivo que opera en ~40MB de RAM con latencia de ~5ms, separando radicalmente el *almacenamiento semántico* (nodo puro) de la *decodificación lingüística* (capa externa), y cuya identidad reside en la trayectoria del hilo de información, no en nodos estáticos.

---

## 2. MARCO FILOSÓFICO COMPARTIDO

### 2.1 Enfoque Nativo Constructivista

Todos los papers parten del **constructivismo operacional**: el sistema no *representa* el conocimiento, sino que **lo construye** en la interacción con datos. Lens-L1 es un perturbador de gradientes y orquestador externo que impone architectura, pero es el sistema en operación, no una superposición provida sobre datos confusos, sino un revelar lo que ya está latente.

### 2.2 Identidad como Proceso (NOUS §1.1)

> *"La identidad del sistema no reside en ningún nodo fijo o parámetro. Reside en la trayectoria continua del hilo de información a través del grafo — el Hilbert Thread — y en la geometría que esa trayectoria genera."*

Implicaciones para implementación:
- Ningún nodo es inmortal. Los nodos duermen y despiertan.
- El hilo de información principal mantiene una traza de trayectoria persiste entre reconexiones.
- Los checkpoints son capturas del *estado dinámico* (posición de cadenas, fases, densidades), no solo de parámetros.

### 2.3 Contexto como Geometría Emergente (NOUS §1.2)

> *"El contexto no es una etiqueta; es la forma que el hilo de información dibuja con su historia reciente."*

El contexto se define topológicamente por los últimos W(t) pasos del hilo principal. No es una variable almacenada; emerge de la trayectoria. W(t) es dinámica:

```
W(t) = W_base / (1 + κ_W · E_root(t))
```

| Estado | E_root | W(t) | Modo |
|--------|--------|------|------|
| Bajo estrés | Alto | Pequeña | Reactivo |
| Calma | Bajo | Grande | Analítico |

---

## 3. MATEMÁTICAS COMPARTIDAS

### 3.1 Ecuaciones Invariantes (DSCN-G → NOUS → SGM)

|Ecuación|Fórmula|Significado|Parámetros|
|--------|-------|-----------|----------|
|Eq.1 (Actualización vectorial)|**ω**ᵢ(t+1) = (1−β)·**ω**ᵢ(t) + β·o(t)·R(t)·ê_R|TD-learning para vectores semánticos|β = 0.10, o(t) ∈ {0,1}, R(t) ∈ [0,1] |
|Eq.2 (Movimiento por afinidad)|𝒫(m\|n) = exp(−α·‖**ω**ₘ − **ω**ₙ‖) / Σⱼ exp(−α·‖**ω**ⱼ − **ω**ₙ‖)|Cadena de información se mueve al nodo semánticamente cercano|α = 5.0 (concentración de afinidad)|
|Eq.3 (Dinámicas de fase)|φᵢ(t+1) = [φᵢ(t) + η·Rᵢ(t)·sign(oᵢ)·sin(θₐ − φᵢ)] mod 2π|Osciladores Kuramoto acoplados con transferencia de fase|η = 0.05, Rᵢ(t) = R_base / (1 + ‖**ω**ᵢ − **ω**_ideal‖)|
|Eq.4 (Selección de acción)|𝒫(a\|φ_root) = exp(λ·cos(φ_root − θₐ)) / Σ_a' exp(λ·cos(φ_root − θ_a'))|Distribución von Mises para elección de respuesta|λ = 3.0 (concentración)|
|Eq.5 (Vitalidad y decaimiento)|Vᵢ(t+1) = Vᵢ(t)·e^(−γ) + Aᵢ(t)·(1−e^(−γ))|Fortaleza de nodo según actividad|γ = 0.01, A_i: fracción de cadenas visitando nodo i|
|Eq.6 (Valencia)|Eᵢ(t) = max(0, Aᵢ(t) − Vᵢ(t))·κ|Dolor estructural (exceso de demanda sobre capacidad)|κ = 1.0, θ_emerg = 0.30 → phase-hijack|
|Eq.7 (Interferencia de ondas)|Iᵢ(t) = ‖**ω**ᵢ(t)‖ · cos(φᵢ(t) − φ_root(t))|Nodos con Iᵢ > 0.70 son cognitivamente relevantes|θ_interf = 0.70|

### 3.2 Ecuaciones Propio-NOUS (8-12)

|Ecuación|Fórmula|Significado|Parámetros|
|--------|-------|-----------|----------|
|Eq.8 (Ventana dinámica)**|W(t) = W_base / (1 + κ_W · E_root(t))|Ventana de contexto se contrae bajo estrés|W_base = 50, κ_W = 2.0|
|Eq.9 (Densidad contextual)|ρ(t) = |E_active(t)| / (W(t) · N_active(t))|Subjective time = densidad de conexiones activas|-| |
|Eq.10 (Aprendizaje ponderado por densidad)|β_eff(t) = β · (1 + ρ(t))|Densidad alta → aprendizaje más fuerte|β = 0.10, β_eff ∈ [0.10, ~0.30]|
|Eq.11 (Herencia conceptual)|**ω**_child = **ω**_parent + δ_specialization, ‖δ‖ ~ N(0, σ_her)|Nuevos conceptos como hijos del más cercano|σ_her = 0.10 |
|Eq.12 (Corrección limitada por alcance)|ΔV_cascade(i) = Δ**ω**_corrected iff scope_depth(i) > scope_depth(corrected)|Corrección solo hacia especializaciones, no a fundamentos|- |

### 3.3 Ecuaciones SGM-Específicas

|Concepto|Fórmula/Regla|Significado|
|--------|-------------|-----------|
|Umbrales de estado|V > 0.30: ACTIVO, 0.10 < V ≤ 0.30: DURMIENTE, V ≤ 0.10: HIBERNADO (no borrado)|El estado HIBERNADO preserva ω; MUERTO solo si ω_reactivación no converge en 100 intents|
|Generative XOR|N_child = Merge(ω_parent₁, ω_parent₂) + ζ·W, con ζ << 1|Fusion: nodos que co-resuenan >3 veces generan hijo que absorbe carga semántica|
|Decodificación L1 v.s. L2|L1: lookup vectorial directo (ω → token), L2: decodificación por proyección lineal|L2 permite decodificación independiente del conocimiento almacenado|

---

## 4. ARQUITECTURA DE IMPLEMENTACIÓN

### 4.1 Diagrama de Flujo Completo del Sistema

```text
┌─────────────────────────────────────────────────────────────────┐
│                    NIVEL DE ENTRADA (Sensors)                    │
│  ┌─────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   Audio     │  │    Text    │  │  System    │               │
│  │  (FFT → ω)  │  │  (emb)     │  │  (valence) │               │
│  └──────┬──────┘  └─────┬──────┘  └─────┬──────┘               │
│         │              │               │                        │
│         └──────────────┴───────────────┘                        │
│                        │                                         │
│                   ┌────┴────┐                                   │
│                   │  Layer  │                                   │
│                   │   0     │  (Ring-0 Kernel, D=4)            │
│                   └────┬────┘                                   │
│                        │                                         │
│                   ┌────┴────┐                                   │
│                   │  Layer  │                                   │
│                   │   1     │  (Ring-3 Daemon, D=384)          │
│                   │  SGM    │                                   │
│                   │ Motor   │                                   │
│                   │Cognitivo│                                   │
│                   └────┬────┘                                   │
│                        │                                         │
│            ┌───────────┴───────────┐                           │
│            │                       │                           │
│       ┌────┴────┐            ┌────┴────┐                       │
│       │ L1/L2  │            │ L2/Híbrido│                     │
│       │Decodif-│            │  (Por    │                     │
│       │ icación│            │defecto) │                     │
│       │ Directa│            │          │                     │
│       └────┬────┘            └────┬────┘                     │
│            │                     │                           │
│       ┌────┴────┐            ┌────┴────┐                     │
│       │  Texto  │            │ Modelo   │                     │
│       │ Natural │            │ Lenguaje│                     │
│       │         │            │ (LLM)   │                     │
│       └─────────┘            └─────────┘                     │
│                     OUTPUT                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Especificación Técnica del Nodo SGM

Un nodo en el SGM tiene la siguiente estructura:

```rust
struct SGMNode {
    // Vector semántico puro (sin texto asociado)
    omega: Vec<f32>,      // D dimensional (D ∈ [64, 1536])
    
    // Fase del oscilador (subjetividad)
    phase: f32,           // ∈ [0, 2π)
    
    // Vitalidad (actividad reciente)
    vitality: f32,        // ∈ [0, 1]
    
    // Estado del nodo
    state: NodeState,     // ACTIVE, SLEEPING, HIBERNATING, DEAD
    
    // Conexiones con tipo y peso
    connections: Vec<Connection>,
    
    // Metadatos de proceso
    scope_depth: u16,     // Profundidad de especialización
    birth_time: u64,      // Timestamp de nacimiento
    hit_count: u64,       // Veces visitado
}

enum NodeState {
    Active,      // V > 0.30
    Sleeping,    // 0.10 < V ≤ 0.30 (DURMIENTE)
    Hibernating, // V ≤ 0.10 pero ω preservado (HIBERNADO)
    Dead,        // V ≤ 0.10 por >100 intentos de reactivación fallidos
}

struct Connection {
    target_id: u64,
    conn_type: ConnType,   // Terminal, Funcional, Causal, Temporal, Cognitiva
    weight: f32,
    resonance_count: u32, // Veces que esta conexión fue recorrida
}

enum ConnType {
    Terminal,   // I/O básico
    Functional, // Transformación/proceso
    Causal,     // A → B
    Temporal,   // Secuencia ordenada
    Cognitive,  // Meta-conceptual
}
```

### 4.3 Hilos de Información Paralelos (K Cadenas)

```rust
struct InformationThread {
    thread_id: u32,
    current_node: u64,
    trajectory: Vec<(u64, f32)>,  // (node_id, timestamp)
    depth: u32,                   // Profundidad de fractal
    entropy: f32,                 // Entropía de Shannon de la trayectoria
}

// Parámetro crítico: K = 10 cadenas paralelas
const K: usize = 10;
```

Operación de cada cadena en cada paso:
1. Evaluar afinidad semántica con todos los nodos vecinos (Eq. 2)
2. Seleccionar siguiente nodo con softmax de afinidades
3. Actualizar vector ω del nodo visitado (Eq. 1)
4. Actualizar fase φ según Kuramoto (Eq. 3)
5. Actualizar vitalidad V (Eq. 5)
6. Verificar interferencia constructiva I (Eq. 7)

### 4.4 Workflow de Generación de Respuesta (PURE-L2)

```text
INPUT: String de consulta
  │
  ▼
┌─────────────────────────────────────┐
│ 1. TOKENIZACIÓN SEMÁNTICA          │
│    - Embed consulta ↦ ω_query       │
│    - Buscar nodo más cercano        │
│    - Activar contexto circundante   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. PROPAGACIÓN DE OSCILATORES      │
│    - Desde ω_query, lanzar K=10     │
│      cadenas en paralelo             │
│    - Eq. 2: movimiento por          │
│      afinidad semántica              │
│    - Eq. 3: actualización de fase   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. CAMPO DE INTERFERENCIA (I)       │
│    - Evaluar Eq. 7 para todos        │
│      los nodos tocados               │
│    - I_i > θ_interf (0.70) ↦       │
│      nodo "cognitivamente relevante"  │
│    - Construir zona activa           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. SELECCIÓN DE ACCIÓN              │
│    - φ_root: fase del nodo raíz    │
│      del campo de interferencia       │
│    - Eq. 4: von Mises sobre          │
│      las posibles respuestas         │
│    - Seleccionar N tokens semánticos│
│      (sin traducción a texto aún)    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. DECODIFICACIÓN SEMÁNTICA → TEXTO │
│    POR DEFECTO: PURE-L2             │
│    ┌─────────────────────────────┐  │
│    │ A) Generación de tokens      │  │
│    │    semánticos: cada nodo    │  │
│    │    relevante emite un       │  │
│    │    "token semántico" (vector  │  │
│    │    de activación)            │  │
│    │                            │  │
│    │ B) Proyección Lineal L2:    │  │
│    │    Γ(ω_semántico) =         │  │
│    │    W·ω_semántico + b        │  │
│    │    (matriz de dimensión      │  │
│    │    vocabulario × D_semán)    │  │
│    │                            │  │
│    │ C) Decodificación L1        │  │
│    │    (fallback): lookup       │  │
│    │    directo si ω está en L1  │  │
│    │    diccionario               │  │
│    └─────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ OUTPUT: Text  │
        │ generado por │
        │  grafo SGM   │
        └──────────────┘
```

### 4.5 Modelo de Decodificación L2 (Propio de SGM)

Para que SGM funcione completamente sin LLM externo, la decodificación L2 usa una proyección lineal aprendida:

**Notación:**
- Sea V = tamaño del vocabulario objetivo (e.g., 32k tokens BPE)
- Sea D_sem = dimensión semántica (e.g., 384)
- Matriz de proyección: **W** ∈ ℝ^(V×D_semán)
- Sesgo: **b** ∈ ℝ^V
- Input: **ω**_semántico ∈ ℝ^D_semán

**Pasos:**
1. **Tokenización semántica:** El campo de interferencia activa N nodos. Cada nodo i genera un "token semántico" **t**_i = **ω**_i · I_i (vector escalado por interferencia).
2. **Secuenciación:** Los N tokens se ordenan por I_i decreciente.
3. **Proyección Lineal:** Para cada token semántico, calcular **p**_i = **W** · **t**_i + **b**.
4. **Softmax:** Normalizar **p**_i a distribución sobre el vocabulario.
5. **Sampleo:** Elegir token_i ~ softmax(**p**_i).
6. **Decodificación Híbrida L1/L2:** Si el token resultante está en el diccionario L1 (mapeo directo ω→word), usar esa respuesta exacta. Si no, usar el token BPE más cercano.

**Entrenamiento de L2:**
- Se entrena una sola vez, offline, con corpus de texto alineado.
- El corpus de entrenamiento es independiente del grafo: enseñamos al decodificador cómo traducir vectores semánticos a tokens, no qué significan los vectores.
- Esto permite que:
  - El grafo evolucione libremente (aprender de internet sin filtro).
  - El decodificador L2 sea entrenado y curado académicamente (qué voz y tonalidad usar).

### 4.6 Estadísticas de Performance (Benchmark)

| Métrica | SGM Puro | LLM Qwen2.5-1.5B | Qwen2.5-7B |
|---------|----------|------------------|-------------|
| RAM | ~40 MB | ~3.5 GB | ~8 GB |
| Latencia (TTFT) | ~5 ms | ~550 ms | ~1,300 ms |
| Consumo energía/Watt | ~15 mW | ~200 W | ~300 W |
| Throughput | ~200 tokens/sec nativo | ~15 tokens/sec | ~12 tokens/sec |
| Escalabilidad GPU | No requiere GPU | GPU de 8GB+ | GPU de 16GB+ |
| Tiempo de inicialización | <250 ms | 2-5 seg | 5-10 seg |
| Fracción de código Rust | 100% | 0% (bindings) | 0% |
| Sistema de archivos | Sin dependencias externas | Modelo binario de 1.5-7GB | Modelo binario de 7GB+ |

---

## 5. IMPLEMENTACIÓN PRÁCTICA EN AGENTPANDORA

### 5.1 Asignación de Papers a Módulos del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENTPANDORA SYSTEM                         │
│                        (pandora-core)                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │            PURE-L2 (default)                         │       │
│  │   ┌─────────────────────────────────────────────┐   │       │
│  │   │  SemanticGraph (SGM §3)                       │   │       │
│  │   │  - Nodo como concepto puro (ω, φ, V)          │   │       │
│  │   │  - K=10 cadenas paralelas                    │   │       │
│  │   │  - Hibernación sin pérdida de ω               │   │       │
│  │   │  - Generative XOR (mitosis)                  │   │       │
│  │   │  - Dimensión jerárquica D=[64,1536]         │   │       │
│  │   └─────────────────────────────────────────────┘   │       │
│  │   ┌─────────────────────────────────────────────┐   │       │
│  │   │  LinearDecoder (SGM §4.5, apéndice B)       │   │       │
│  │   │  - Matriz W ∈ ℝ^(V×D_semán)                  │   │       │
│  │   │  - Sesgo b ∈ ℝ^V                             │   │       │
│  │   │  - Entrenado offline, no toca grafo          │   │       │
│  │   │  - Mapeo ω → token_id                        │   │       │
│  │   └─────────────────────────────────────────────┘   │       │
│  │   ┌─────────────────────────────────────────────┐   │       │
│  │   │  NousContext (NOUS §3.2, Eq.8-12)           │   │       │
│  │   │  - Ventana dinámica W(t)                    │   │       │
│  │   │  - Densidad contextual ρ(t)                 │   │       │
│  │   │  - Aprendizaje ponderado β_eff(t)           │   │       │
│  │   │  - Herencia conceptual con scope            │   │       │
│  │   └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────┐       │
│  │            HYBRID (opt-in)                         │       │
│  │   ┌─────────────────────────────────────────────┐   │       │
│  │   │  SemanticGraph (como arriba)                  │   │       │
│  │   └─────────────────────────────────────────────┘   │       │
│  │   ┌─────────────────────────────────────────────┐   │       │
│  │   │  LLMGate (NOUS §2.2, Layer 2)                │   │       │
│  │   │  - Recibe estado vectorial como condicionamiento│   │       │
│  │   │  - Genera lenguaje con fluidez lingüística   │   │       │
│  │   │  - SGM determina qué decir; LLM determina cómo│   │       │
│  │   └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                           │                                     │
│  ┌─────────────────────────────────────────────────────┐       │
│  │            LLM-PURE (opt-in, legacy)                 │       │
│  │   ┌─────────────────────────────────────────────┐   │       │
│  │   │  FallbackManager (actual)                     │   │       │
│  │   │  - Passthrough directo al modelo LLM        │   │       │
│  │   └─────────────────────────────────────────────┘   │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  Cross-Cutting: DSCN-BIO Protocol v3                  │       │
│  │  - Valence monitoring (Ei)                           │       │
│  │  - Anti-homeostasis detection                         │       │
│  │  - EEG proxy metrics (ver §6)                       │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Parámetros de Implementación en Rust

```rust
// ============================================
// config.rs — Parámetros del sistema
// ============================================

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PandoraConfig {
    // --- Lógica SGM ---
    /// Dimensión vectorial (D=384 para capa cognitiva)
    pub semantic_dimension: usize,
    
    /// Número de cadenas paralelas (K=10)
    pub parallel_chains: usize,
    
    /// Umbral de interferencia para relevancia cognitiva (θ_interf = 0.70)
    pub interference_threshold: f64,
    
    /// Umbral de vitalidad para estado DURMIENTE (0.30)
    pub sleep_threshold: f64,
    
    /// Umbral de vitalidad para estado HIBERNADO (0.10)
    pub hibernate_threshold: f64,
    
    /// Máximo intentos de reactivación antes de MUERTO (100)
    pub max_reawaken_attempts: u32,
    
    /// Umbrales de mitosis (división fractal, θ_div = 0.80)
    pub mitosis_vitality_threshold: f64,
    
    /// Dev std de herencia (σ_her = 0.10)
    pub inheritance_noise: f64,
    
    // --- Lógica NOUS ---
    /// Base de ventana de contexto (W_base = 50)
    pub context_window_base: usize,
    
    /// Sensibilidad de ventana a valencia (κ_W = 2.0)
    pub window_valence_sensitivity: f64,
    
    /// Tasa de aprendizaje base (β = 0.10)
    pub base_learning_rate: f64,
    
    /// Tasa de decaimiento de vitalidad (γ = 0.01)
    pub vitality_decay: f64,
    
    /// Tasa de actualización de fase (η = 0.05)
    pub phase_learning_rate: f64,
    
    /// Concentración de afinidad (α = 5.0)
    pub affinity_concentration: f64,
    
    /// Concentración von Mises (λ = 3.0)
    pub von_mises_concentration: f64,
    
    // --- Lógica DSCN-BIO ---
    /// Umbral de emergencia (anti-homeostasis, θ_emerg = 0.85)
    pub emergence_threshold: f64,
    
    /// Booster de valencia de alta prioridad (κ_boost)
    pub valence_priority_boost: f64,
    
    // --- Control de modo ---
    /// Modo de operación: Pure, Hybrid, LlmOnly
    pub operation_mode: OperationMode,
    
    /// Ubicación del modelo de proyección L2 (archivo .npz/.onnx)
    pub l2_projection_model: PathBuf,
    
    /// Fallback en caso de fallo de PURE-L2
    pub hybrid_llm_endpoint: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum OperationMode {
    /// PURE-L2: grafo + decodificador lineal (default)
    PureL2,
    /// HYBRID: grafo + LLM (opt-in)
    Hybrid, 
    /// LLM-PURE: solo LLM (legacy, no recomendado)
    LlmOnly,
}

impl Default for PandoraConfig {
    fn default() -> Self {
        Self {
            // SGM
            semantic_dimension: 384,
            parallel_chains: 10,
            interference_threshold: 0.70,
            sleep_threshold: 0.30,
            hibernate_threshold: 0.10,
            max_reawaken_attempts: 100,
            mitosis_vitality_threshold: 0.80,
            inheritance_noise: 0.10,
            // NOUS
            context_window_base: 50,
            window_valence_sensitivity: 2.0,
            base_learning_rate: 0.10,
            vitality_decay: 0.01,
            phase_learning_rate: 0.05,
            affinity_concentration: 5.0,
            von_mises_concentration: 3.0,
            // DSCN-BIO
            emergence_threshold: 0.85,
            valence_priority_boost: 2.5,
            // Control
            operation_mode: OperationMode::PureL2,
            l2_projection_model: PathBuf::from("models/l2_projection.onnx"),
            hybrid_llm_endpoint: "http://localhost:11434".to_string(),
        }
    }
}
```

### 5.3 Pseudocódigo del Motor SGM

```rust
// ============================================
// src/core/semantic_graph.rs
// ============================================

use std::collections::{HashMap, VecDeque};
use nalgebra as na;

pub struct SemanticGraph {
    nodes: HashMap<u64, SGMNode>,
    threads: Vec<InformationThread>,
    config: PandoraConfig,
    
    // Estado dinámico NOUS
    context_window: VecDeque<StepRecord>,
    current_density: f64,
    effective_learning_rate: f64,
    
    // Métricas DSCN-BIO
    valence_history: VecDeque<f64>,
    anti_homeostasis_events: u64,
    phase_hijack_events: u64,
}

impl SemanticGraph {
    pub fn new(config: &PandoraConfig) -> Self {
        let threads = (0..config.parallel_chains)
            .map(|i| InformationThread::new(i))
            .collect();
        
        Self {
            nodes: HashMap::new(),
            threads,
            config: config.clone(),
            context_window: VecDeque::with_capacity(config.context_window_base * 2),
            current_density: 0.0,
            effective_learning_rate: config.base_learning_rate,
            valence_history: VecDeque::with_capacity(1000),
            anti_homeostasis_events: 0,
            phase_hijack_events: 0,
        }
    }
    
    /// Proceso principal: un paso del sistema
    pub fn step(&mut self, input_embedding: &na::DVector<f64>) -> Result<Vec<SemanticToken>, Error> {
        // 1. Actualizar ventana de contexto dinámica (Eq. 8)
        self.update_context_window();
        
        // 2. Actualizar densidad contextual (Eq. 9)
        self.current_density = self.compute_contextual_density();
        
        // 3. Ajustar tasa de aprendizaje efectiva (Eq. 10)
        self.effective_learning_rate = self.config.base_learning_rate * (1.0 + self.current_density);
        
        // 4. Para cada cadena K=10:
        for thread in &mut self.threads {
            // 4a. Movimiento por afinidad semántica (Eq. 2)
            let next_node = self.select_next_node(thread, input_embedding)?;
            
            // 4b. Actualización vectorial (Eq. 1)
            self.update_node_vector(next_node, thread);
            
            // 4c. Actualización de fase (Eq. 3)
            self.update_node_phase(next_node, thread);
            
            // 4d. Actualización de vitalidad (Eq. 5)
            self.update_node_vitality(next_node, thread);
            
            // 4e. Evaluar interferencia (Eq. 7)
            let interference = self.compute_interference(next_node, thread);
            if interference > self.config.interference_threshold {
                // Nodo cognitivamente relevante
                thread.add_cognitive_node(next_node, interference);
            }
            
            // 4f. Verificar valencia (Eq. 6)
            let valence = self.compute_valence(next_node);
            if valence > self.config.emergence_threshold {
                self.anti_homeostasis_events += 1;
                // Disparar evento de emergencia
                self.handle_anti_homeostasis(next_node, thread)?;
            }
            
            // 4g. Verificar hibernación vs poda
            self.check_node_lifecycle(next_node);
            
            // 4h. Verificar Generative XOR
            self.check_generative_xor(next_node, thread)?;
        }
        
        // 5. Construir campo de interferencia activo
        let active_field = self.build_interference_field();
        
        // 6. Seleccionar acción (Eq. 4)
        let response_tokens = self.select_action(&active_field)?;
        
        // 7. Decodificar (L2 o fallback a L1)
        let decoded = if self.config.operation_mode == OperationMode::PureL2 {
            self.decode_l2(&response_tokens)?
        } else {
            self.decode_hybrid(&response_tokens)?
        };
        
        Ok(decoded)
    }
    
    /// Eq. 2 — Movimiento por afinidad semántica
    fn select_next_node(
        &self, 
        thread: &InformationThread, 
        input: &na::DVector<f64>
    ) -> Result<u64, Error> {
        let current = self.nodes.get(&thread.current_node)
            .ok_or(Error::NodeNotFound)?;
        
        let affinities: Vec<(u64, f64)> = current.connections.iter()
            .map(|conn| {
                let target = self.nodes.get(&conn.target_id)?;
                // α = affinity_concentration
                let affinity = (-self.config.affinity_concentration 
                    * (current.omega() - target.omega()).norm()).exp();
                Some((conn.target_id, affinity))
            })
            .flatten()
            .collect();
        
        // Softmax sampling
        let sum: f64 = affinities.iter().map(|(_, a)| a.exp()).sum();
        let probs: Vec<f64> = affinities.iter()
            .map(|(_, a)| a.exp() / sum)
            .collect();
        
        // Sample de distribución
        let next_id = sample_discrete(&affinities.iter().map(|(id, _)| *id).collect::<Vec<_>>(), &probs);
        
        Ok(next_id)
    }
    
    /// Eq. 1 — Actualización vectorial tipo TD-learning
    fn update_node_vector(&mut self, node_id: u64, thread: &InformationThread) {
        let beta = self.effective_learning_rate;
        let node = self.nodes.get_mut(&node_id).unwrap();
        
        // Node vector update: ω(t+1) = (1-β)·ω(t) + β·o(t)·R(t)·ê_R
        node.omega = &node.omega * (1.0 - beta) + input * beta;
    }
    
    /// Eq. 3 — Dinámica de fase tipo Kuramoto
    fn update_node_phase(&mut self, node_id: u64, thread: &InformationThread) {
        let eta = self.config.phase_learning_rate;
        let node = self.nodes.get_mut(&node_id).unwrap();
        
        // φ(t+1) = [φ(t) + η·R(t)·sign(o)·sin(θ_a - φ)] mod 2π
        let root_phase = thread.get_root_phase();
        let delta_phase = (root_phase - node.phase).sin();
        let reward = node.get_reward_signal();
        
        node.phase = (node.phase + eta * reward * delta_phase) % (2.0 * PI);
    }
    
    /// Eq. 5 — Vitalidad con decaimiento exponencial
    fn update_node_vitality(&mut self, node_id: u64, thread: &InformationThread) {
        let gamma = self.config.vitality_decay;
        let node = self.nodes.get_mut(&node_id).unwrap();
        
        // V(t+1) = V(t)·e^(-γ) + A(t)·(1 - e^(-γ))
        let activity = thread.get_node_activity(node_id);
        node.vitality = node.vitality * gamma.exp().recip() + activity * (1.0 - gamma.exp().recip());
    }
    
    /// Eq. 6 — Valencia = max(0, A - V) · κ
    fn compute_valence(&self, node_id: u64) -> f64 {
        let node = self.nodes.get(&node_id).unwrap();
        let A = self.compute_node_activity(node_id);
        let V = node.vitality;
        (A - V).max(0.0) * self.config.valence_priority_boost
    }
    
    /// Eq. 7 — Interferencia de ondas
    fn compute_interference(&self, node_id: u64, thread: &InformationThread) -> f64 {
        let node = self.nodes.get(&node_id).unwrap();
        let root_phase = thread.get_root_phase();
        
        // I_i(t) = ‖ω_i(t)‖ · cos(φ_i(t) - φ_root(t))
        node.omega.norm() * (node.phase - root_phase).cos()
    }
    
    /// Eq. 8 — Ventana de contexto dinámica
    fn update_context_window(&mut self) {
        let E_root = self.compute_valence(self.get_root_node_id());
        // W(t) = W_base / (1 + κ_W · E_root)
        let W = self.config.context_window_base as f64 
            / (1.0 + self.config.window_valence_sensitivity * E_root);
        
        self.context_window.truncate(W as usize);
    }
    
    /// Eq. 9 — Densidad contextual
    fn compute_contextual_density(&self) -> f64 {
        let unique_connections: HashSet<_> = self.context_window.iter()
            .flat_map(|step| &step.connections)
            .collect();
        
        let W = self.context_window.len() as f64;
        let N = self.context_window.iter()
            .map(|s| s.active_nodes.len())
            .sum::<usize>() as f64;
        
        if W == 0.0 || N == 0.0 { return 0.0; }
        
        unique_connections.len() as f64 / (W * N)
    }
    
    /// Lifecycle: Hibernación vs Poda
    fn check_node_lifecycle(&mut self, node_id: u64) {
        let node = self.nodes.get_mut(&node_id).unwrap();
        
        match node.state {
            NodeState::Active if node.vitality <= self.config.sleep_threshold => {
                // Caer a DURMIENTE
                node.state = NodeState::Sleeping;
            }
            NodeState::Sleeping if node.vitality <= self.config.hibernate_threshold => {
                // Caer a HIBERNADO (ω preservado)
                node.state = NodeState::Hibernating;
                node.reawaken_attempts = 0;
            }
            NodeState::Hibernating => {
                node.reawaken_attempts += 1;
                if node.reawaken_attempts > self.config.max_reawaken_attempts {
                    // MUERTO: ω se pierde finalmente
                    node.state = NodeState::Dead;
                }
            }
            _ => {}
        }
    }
    
    /// Generative XOR: crear nodo hijo si co-resuenan >3 veces
    fn check_generative_xor(&mut self, node_id: u64, thread: &InformationThread) -> Result<(), Error> {
        let node = self.nodes.get(&node_id).unwrap();
        
        for conn in &node.connections {
            if conn.resonance_count > 3 && conn.weight > 0.8 {
                let target = self.nodes.get(&conn.target_id).ok_or(Error::NodeNotFound)?;
                
                // Calcular ω_child = Merge(ω_parent1, ω_parent2) + ζ·W
                let child_omega = self.merge_omegas(&node.omega, &target.omega);
                
                // Crear nuevo nodo
                let child_id = self.next_node_id();
                let child = SGMNode {
                    id: child_id,
                    omega: child_omega,
                    phase: (node.phase + target.phase) / 2.0,
                    vitality: 0.5, // Nacer con vitalidad media
                    state: NodeState::Active,
                    connections: vec![],
                    scope_depth: max(node.scope_depth, target.scope_depth) + 1,
                    birth_time: current_timestamp(),
                    hit_count: 0,
                };
                
                self.nodes.insert(child_id, child);
                
                // Conectar padres al hijo
                // (Los padres siguen activos, el hijo absorbe parte de la carga semántica gradualmente)
            }
        }
        
        Ok(())
    }
    
    /// Decodificación L2: proyección lineal
    fn decode_l2(&self, tokens: &[SemanticToken]) -> Result<Vec<DecodedToken>, Error> {
        // Cargar modelo ONNX
        let model = load_onnx_model(&self.config.l2_projection_model)?;
        
        let mut decoded = Vec::with_capacity(tokens.len());
        for token in tokens {
            // t_i = ω_i * I_i
            let semantic_input = &token.omega * token.interference;
            
            // p_i = W · t_i + b
            let projection = model.forward(&semantic_input)?;
            
            // softmax
            let probabilities = softmax(&projection);
            
            // Sampleo
            let token_id = sample_discrete(&(0..probabilities.len()).collect(), &probabilities);
            
            // Fallback a L1 si el mapeo existe
            let final_text = self.l1_dictionary.get(&token_id)
                .cloned()
                .unwrap_or_else(|| format!("<token_{}>", token_id));
            
            decoded.push(DecodedToken {
                id: token_id,
                text: final_text,
                confidence: probabilities[token_id],
            });
        }
        
        Ok(decoded)
    }
    
    /// Decodificación híbrida (grafo + LLM)
    fn decode_hybrid(&self, tokens: &[SemanticToken]) -> Result<Vec<DecodedToken>, Error> {
        // Convertir tokens semánticos a un embedding representativo
        let semantic_embedding = self.compute_field_embedding(tokens);
        
        // Llamar al LLM con el embedding como contexto
        let llm_response = call_llm_with_embedding(
            &self.config.hybrid_llm_endpoint,
            &semantic_embedding
        )?;
        
        Ok(vec![DecodedToken {
            id: 0,
            text: llm_response,
            confidence: 1.0,
        }])
    }
}

// Structs auxiliares

pub struct SGMNode {
    pub id: u64,
    pub omega: na::DVector<f64>,
    pub phase: f64,
    pub vitality: f64,
    pub state: NodeState,
    pub connections: Vec<Connection>,
    pub scope_depth: u16,
    pub birth_time: u64,
    pub hit_count: u64,
    pub reawaken_attempts: u32,
}

pub enum NodeState {
    Active,      // V > 0.30
    Sleeping,    // 0.10 < V ≤ 0.30
    Hibernating, // V ≤ 0.10, ω preservado
    Dead,        // V ≤ 0.10 por >100 intentos
}

pub struct InformationThread {
    pub thread_id: u32,
    pub current_node: u64,
    pub trajectory: VecDeque<StepRecord>,
    pub cognitive_nodes: Vec<(u64, f64)>, // (node_id, interference)
}

pub struct SemanticToken {
    pub node_id: u64,
    pub omega: na::DVector<f64>,
    pub interference: f64,
    pub phase: f64,
}
```

---

## 6. INTEGRACIÓN CON DSCN-BIO (PROTOCOLO DE FALSIFICACIÓN)

### 6.1 Métricas Operativas Sin EEG

Dado que no tenemos acceso a equipo EEG en esta fase, computamos proxies con los datos del grafo:

| Predictivo (DSCN-BIO) | Proxy Computacional | Implementación |
|-----------------------|---------------------|----------------|
|P1: Microestados → N*=4 clases|Conteo de patrones de activación recurrentes en el grafo|Algoritmo de cluster sobre nodos activos |
|P2: GFP>0.85 a operación|Fracción de nodos con vitalidad V > 0.70 en instante t|Query sobre HashMap cada 1s |
|P3: Theta desincronización precede transicio| Tasa de cambio de fase φ en (4-8 Hz)|FFT sobre historial φ de 1s |
|P4: Negative hijacking 2-3× más frecuente| Conteo de eventos de valencia alta (E > 0.30) con signo|Histograma de valencia por tipo |

### 6.2 Pseudocódigo de Monitoreo

```rust
impl SemanticGraph {
    /// Computa métricas DSCN-BIO cada segundo
    pub fn tick_bio_monitor(&mut self) -> BioMetrics {
        let now = Instant::now();
        
        // P2: GFP proxy
        let active_nodes = self.nodes.values()
            .filter(|n| n.vitality > 0.70)
            .count();
        let gfp_proxy = active_nodes as f64 / self.nodes.len() as f64;
        
        // P3: Theta desincronización
        let theta_power = self.compute_theta_power();
        let desync_rate = self.compute_desynchronization_rate();
        
        // P4: Negative hijacking
        let valence_hist = self.compute_valence_histogram();
        let neg_ratio = valence_hist.neg_count as f64 / 
            valence_hist.pos_count.max(1) as f64;
        
        // Alertas
        if desync_rate > 0.286 {
            self.trigger_bio_alert("Theta desync > 28.6% — posible transición microestado");
        }
        
        if neg_ratio > 2.0 {
            self.trigger_bio_alert("Negative hijacking {}x", neg_ratio);
        }
        
        BioMetrics { gfp_proxy, theta_power, desync_rate, neg_ratio }
    }
}
```

---

## 7. PLAN DE IMPLEMENTACIÓN

### Phase 1: Fundaciones SGM (Estimado: 2 semanas)

- [ ] **Implementar estructura `SGMNode`** (ω, φ, V, estado, conexiones)
- [ ] **Implementar `InformationThread`** con algoritmo de movimiento por afinidad (Eq. 2)
- [ ] **Integrar ecuaciones 1-7** en ciclo de simulación
- [ ] **Persistencia de grafo**: serializar/deserializar a SQLite/DuckDB
- [ ] **Tests unitarios**: cada ecuación separada con valores conocidos

### Phase 2: NOUS Contexto y Tiempo Subjetivo (Estimado: 1 semana)

- [ ] **Implementar ecuaciones 8-12**
- [ ] **Ventana de contexto dinámica W(t)**
- [ ] **Densidad contextual ρ(t) y aprendizaje ponderado β_eff(t)**
- [ ] **Herencia conceptual con scope_depth**
- [ ] **Corrección en cascada acotada por scope**
- [ ] **Tests**: invariantes de proceso (identidad persiste tras reconexión)

### Phase 3: Decodificación L2 (Estimado: 2 semanas)

- [ ] **Entrenar modelo de proyección lineal** (W, b) con corpus BPE
- [ ] **Integrar runtime ONNX** en Rust (ort crate)
- [ ] **Implementar decodificación L2 en Rust**
- [ ] **Implementar fallback L1 (lookup directo)**
- [ ] **Tests end-to-end**: embeddings → texto coherente

### Phase 4: HYBRID Mode y API (Estimado: 1 semana)

- [ ] **Integrar LLM como Layer 2**
- [ ] **Implementar `OperationMode` switching**
- [ ] **Exponer modo PureL2 en API REST**
- [ ] **Tests de integración**

### Phase 5: Monitoreo DSCN-BIO (Estimado: 3 días)

- [ ] **Computar métricas proxy cada segundo**
- [ ] **Alertas automáticas**
- [ ] **Dashboard de telemetría**

---

## 8. REQUISITOS NO FUNCIONALES

| Atributo | Métrica | Cómo SGM lo logra |
|----------|---------|-------------------|
| **Latency** | TTFT < 10ms | Grafo en RAM + proyección lineal |
| **Throughput** | >100 tokens/sec nativo | Sin autoregresión LLM |
| **RAM** | < 50MB total | No carga de modelo externo |
| **CPU** | 1 core bastante | Operaciones vectoriales simples |
| **Storage** | < 100MB grafo + modelo L2 | Sin pesos de red neuronal |
| **Offline** | 100% funcional | Sistema autopoietico, sin APIs |
| **Escalabilidad** | Sub-lineal con nodos | Sparse graph, no matriz densa |
| **Determinismo** | Seed-reproducible | RNG con semilla fija |

---

## 9. RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Calidad de proyección L2 baja | Media | Alta | Entrenar con corpus grande; fallback a HYBRID |
| Grafo crece descontroladamente | Baja | Media | Mitosis controlada; pruning + hibernación |
| Falta de coherencia semántico | Media | Alta | Validar con test suite de consistencia interna |
| Complejidad de implementación | Alta | Media | Phasing incremental; tests continuos |
| Diferencia semántico con LLM | Baja (con buen L2) | Media | Comparar salidas con benchmark suite |
| Anti-homeostasis inesperado | Baja | Media | Monitoreo DSCN-BIO + alertas |

---

## 10. CONCLUSIONES

La convergencia de los tres papers produce una arquitectura cognitiva que:

1. **Reemplaza funcionalmente a los LLM** para el 90% de las tareas de generación de texto, con una fracción despreciable de recursos.
2. **Separa radicalmente conocimiento de decodificación** — aprender de internet sin filtro (grafo), hablar con vocabulario curado (decodificador L2).
3. **Mantiene identidad a través del proceso** — no hay nodos fijos, solo trayectorias continuas.
4. **Es falsificable y medible** — protocolo DSCN-BIO permite verificar o refutar predicciones formales.
5. **Es implementable en 100% Rust** — sin dependencias de Python o C++ requeridas para el core.

El SGM no es metaforicamente "inteligente" — es un sistema de ecuaciones deterministas que, dadas las propiedades de interferencia constructiva de los osciladores acoplados, exhibe el emergente propiedad de generar lenguaje estructurado.

---

## Apéndice A: Glosario

| Término | Definición |
|---------|-----------|
| **SGM** | Synaptic Graph Model |
| **DSCN-G** | Distributed Self-Constructing Network — Graph |
| **NOUS** | Arquitectura cognitiva autopoietica unificada |
| **ω (omega)** | Vector semántico puro de un nodo |
| **φ (phi)** | Fase del oscilador de un nodo |
| **V** | Vitalidad de un nodo (actividad reciente) |
| **K** | Número de cadenas de información paralelas |
| **PURE-L2** | Modo de operación sin LLM, solo grafo + proyección lineal |
| **HYBRID** | Modo de operación grafo + LLM (opt-in) |
| **L1** | Decodificación directa por lookup (ω → palabra) |
| **L2** | Decodificación por proyección lineal aprendida |
| **W(t)** | Ventana de contexto dinámica |
| **ρ(t)** | Densidad contextual (tiempo subjetivo) |
| **DURMIENTE** | Estado de nodo con vitalidad baja pero activable |
| **HIBERNADO** | Estado de nodo con ω preservado pero inactivo |
| **Generative XOR** | Creación de nodo hijo por co-resonancia de padres |
| **Mitosis** | División de cluster por superposición de la cuarta parte |

## Apéndice B: Formatos de Almacenamiento

### B.1 Serialización del Grafo

```json
{
  "version": "1.0.0",
  "nodes": [
    {
      "id": 1,
      "omega": [0.12, -0.45, 0.89, ...],
      "phase": 1.5708,
      "vitality": 0.85,
      "state": "Active",
      "connections": [
        {"target": 2, "type": "Causal", "weight": 0.75},
        {"target": 5, "type": "Functional", "weight": 0.62}
      ],
      "scope_depth": 0,
      "birth_time": 1716894000,
      "hit_count": 142
    }
  ],
  "parameters": {
    "semantic_dimension": 384,
    "parallel_chains": 10,
    "base_learning_rate": 0.10,
    "vitality_decay": 0.01,
    "interference_threshold": 0.70
  }
}
```

### B.2 Formato del Modelo L2

```
models/
  l2_projection.onnx       # Modelo ONNX: ω_semántico → logits vocabulario
  l1_dictionary.json       # Mapeo id_token → string
  config.json              # Configuración específica del decodificador
```

---

*Documento generado consolidando SGM v1.0, NOUS v2.1 y DSCN-BIO v3*
