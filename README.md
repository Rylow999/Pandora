# SGM — Synthetic Graph Mind

**Motor cognitivo de grafo sináptico para agentes autónomos.**

SGM es un sistema de inteligencia artificial basado en grafos cognitivos donde cada nodo tiene identidad (vector omega), fase (Kuramoto), vitalidad y valencia. El sistema opera como sustrato cognitivo autopoyético: memoria persistente, dolor/valencia interna operacional, duda/contradicción, y decodificación semántica a lenguaje natural.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    SGM Cognitive Core                        │
├─────────────────────────────────────────────────────────────┤
│  sgm_core.py (~200 líneas)                                   │
│    SGMAgentCore: step() + hook arbitro                      │
│    Componentes: HDC, HRR, PPR, Kuramoto, grafo, homeo      │
├─────────────────────────────────────────────────────────────┤
│  experiments/                                                │
│    sgm_grafo.py      → Nodos, aristas, place cells         │
│    sgm_hdc.py        → HDC + SensorBridge                  │
│    sgm_hrr.py        → HRR bind/unbind, memoria relacional │
│    sgm_ppr.py        → PPR + PPR inverso                   │
│    sgm_kuramoto.py   → Kuramoto + interferencia            │
│    sgm_homeostasis.py→ Homeostasis grafo-cuerpo             │
│    sgm_memoria.py    → Episódica + NOUS + lugar            │
│    sgm_instintos.py  → Instintos biológicos                │
│    sgm_l2_system.py  → Rosetta + L2 + DecodeL2             │
│    sgm_pulsiones.py  → 10 plugins + Arbitro modos          │
│    sgm_bridge.py     → Adaptador HTTP                      │
├─────────────────────────────────────────────────────────────┤
│  sgm_lang.py (487 tokens)   → Diccionario MC 1.20.4        │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. Nodos del Grafo (`sgm_grafo.py`)

Cada nodo tiene:
- **omega** (`Vec<D>`): Vector semántico de identidad
- **phi** (`f32`): Fase del oscilador (Kuramoto)
- **vitalidad** (`f32`): Actividad reciente (decae con γ)
- **es_place_cell** (`bool`): Si es mutable (place cell) o inmutable (concepto)

**Inmutabilidad de omega:**
- Los **conceptos** (nodos base, recursos, herencias) tienen `omega` **inmutable** después de la creación
- Los **place cells** (nodos-lugar emergentes) tienen `omega` **mutable** (plasticidad local)

### 2. Arbitro de Pulsiones (`sgm_pulsiones.py`)

Cada pulsión es un plugin independiente que devuelve `{accion: peso_crudo}`:

| Pulsión | Descripción |
|---------|-------------|
| `PulsionPPR` | Base: PPR × vitalidad |
| `PulsionInteraccion` | Interactuar (do) cuando hay necesidad |
| `PulsionExploracion` | Curiosidad dirigida al mundo |
| `PulsionGradiente` | Quimiotaxis hacia recurso visible |
| `PulsionDriveNoop` | Empuje contra inacción (SEEKING) |
| `PulsionReEncare` | Moverse hacia objetivo para interactuar |
| `PulsionNavegacionMeta` | Ir a lugar recordado |
| `PulsionAlimentacion` | Comer cuando hay carencia |
| `PulsionDesplazamiento` | Moverse cuando necesidad local no se resuelve |
| `PulsionSeeking` | Búsqueda de alimento bajo hambre real |

**Modos del Arbitro:**
- **BASE**: Todas las pulsiones compiten por igual
- **SUPERVIVENCIA**: Pulsiones de supervivencia dominan, otras atenuadas

### 3. Decodificador L2 (`sgm_l2_system.py`)

**Piedra Rosetta (L1):** Diccionario directo token ↔ omega determinístico.

**Proyección L2:** `W·ω + b → softmax → token`
- Entrenada offline con corpus desde Piedra Rosetta
- Guardada en `l2_projection.npz`

**Pipeline de decodificación:**
1. Campo de interferencia (Eq.7) → nodos relevantes
2. Promedio ponderado de omega
3. Fallback L1 → L2 → softmax → sample

### 4. Homeostasis (`sgm_homeostasis.py`)

- `V_grafo = media(vitalidad) × factor_cuerpo(food, health)`
- `_hambre_real = 1 - food/20`
- `V_grafo` sube/baja con salud del player

### 5. Memoria y Navegación (`sgm_memoria.py`)

- **Memoria episódica**: Buffer de eventos salientes
- **Place cells**: Nodos-lugar emergentes con posición espacial
- **Modelo de objetos**: Predicción de posición futura (object permanence)
- **Navegación a meta**: Ir a lugar recordado donde se resolvió antes

---

## Ejecución

### Test rápido
```bash
cd ~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM
source ~/crafter-env/bin/activate
python3 -c "
from sgm_core import SGMAgentCore
ag = SGMAgentCore(random.Random(42), 128, n_nodes=64, gamma=0.01)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
ag.instinto_alimentacion = 5
ag._hambre_real = 0.7; ag._amenaza = 0.1; ag._algo_enfrente = 1
ag._posicion_actual = (10, 10); ag._hay_gradiente = True
ag._gradiente_dir = (1, 0); ag._config_grad = {'activo': True, 'fuerza': 0.8}
sv = [0.2, 0.2, 0.7, 0.1, 0.8, 1.0, 1.0] + [0.0] * 11
print(f'Acción: {ag.step(sv, list(range(17)))}, Modo: {ag.modo}')
"
```

### Verificación completa
```bash
python3 /tmp/hermes-verify-omega-l2.py
```

---

## Estado Actual

| Componente | Estado |
|-----------|--------|
| `sgm_core.py` | ✅ Estable, modular, flujo completo |
| `sgm_pulsiones.py` (10 plugins) | ✅ Integrado |
| `sgm_l2_system.py` | ✅ Entrenado, 6/6 correctos |
| `sgm_lang.py` (487 tokens) | ✅ Diccionario MC 1.20.4 |
| Experimentos verificados | 170+ |

---

## Licencia

Proyecto de investigación — NOUS: The Pandora Research.

---

*Última actualización: 2026-08-24 — Core flujo completo + modular.*