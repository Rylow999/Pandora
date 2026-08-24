# SGM — Synthetic Graph Mind

**Motor cognitivo de grafo sináptico para agentes autónomos.**

SGM es un sistema de inteligencia artificial basado en grafos cognitivos donde cada nodo tiene identidad (vector omega), fase (Kuramoto), vitalidad y valencia. El sistema opera como sustrato cognitivo autopoyético: memoria persistente, dolor/valencia interna operacional, duda/contradicción, y decodificación semántica a lenguaje natural.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    SGM Cognitive Core                        │
├─────────────────────────────────────────────────────────────┤
│  sgm_core.py          │  Motor principal (HDC, HRR, PPR,    │
│                       │  Kuramoto, instintos, memoria,      │
│                       │  place cells, arbitro de pulsiones) │
├─────────────────────────────────────────────────────────────┤
│  sgm_pulsiones.py     │  Plugins de pulsiones independientes │
│                       │  + Arbitro de modos (BASE/SUPERV.)  │
├─────────────────────────────────────────────────────────────┤
│  sgm_l2_system.py     │  Decodificador L2: Piedra Rosetta   │
│                       │  (L1) + Proyección Lineal (L2)     │
├─────────────────────────────────────────────────────────────┤
│  sgm_lang.py          │  Diccionario base (487 tokens)      │
├─────────────────────────────────────────────────────────────┤
│  sgm_bridge.py        │  Adaptador HTTP para entornos      │
│                       │  externos (Minecraft, Crafter)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. Nodos del Grafo (`sgm_core.py`)

Cada nodo tiene:
- **omega** (`Vec<D>`): Vector semántico de identidad
- **phi** (`f32`): Fase del oscilador (Kuramoto)
- **vitalidad** (`f32`): Actividad reciente (decae con γ)
- **es_place_cell** (`bool`): Si es mutable (place cell) o inmutable (concepto)

**Inmutabilidad de omega:**
- Los **conceptos** (nodos base, recursos, herencias) tienen `omega` **inmutable** después de la creación
- Los **place cells** (nodos-lugar emergentes) tienen `omega` **mutable** (plasticidad local)
- El helper `_mutar_omega()` protege esta invariante

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

**Piedra Rosetta (L1):** Diccionario directo token ↔ omega determinístico (hash-based).
Si un omega está cerca de un token conocido, se usa directamente sin proyección.

**Proyección L2:** `W·ω + b → softmax → token`
- Entrenada offline con corpus generado desde la Piedra Rosetta
- Loss: cross-entropy con SGD
- Guardada en `l2_projection.npz`

**Pipeline de decodificación:**
1. Campo de interferencia (Eq.7) → nodos relevantes
2. Promedio ponderado de omega
3. Fallback L1 (Piedra Rosetta)
4. Proyección L2 → softmax → sample

### 4. Instintos y Drives

| Mecanismo | Descripción |
|-----------|-------------|
| Instinto de alimentación | Fuerza modulada por hambre real |
| Instinto de exploración | Curiosidad dirigida por incertidumbre |
| Instinto de defensa | Respuesta a amenaza/dolor |
| Drive noop (SEEKING) | Energía libre que empuja a actuar |
| Desplazamiento | Reacción a necesidad insatisfecha local |

### 5. Memoria y Aprendizaje

- **Memoria episódica**: Buffer de eventos salientes (logros, crafteo, comida)
- **Place cells**: Nodos-lugar emergentes con posición espacial
- **Modelo de objetos**: Predicción de posición futura (object permanence)
- **Herencia conceptual**: Nuevos conceptos como hijos del más cercano (Eq.11)
- **Consolidación**: Conexiones se fortalecen por sincronización Kuramoto

---

## Estado Actual

| Componente | Estado |
|-----------|--------|
| `sgm_core.py` (2250 líneas) | ✅ Estable, verificado |
| `sgm_pulsiones.py` (10 plugins) | ✅ Integrado, tests pasando |
| `sgm_l2_system.py` | ✅ Entrenado, 6/6 correctos |
| `sgm_lang.py` (487 tokens) | ✅ Diccionario MC 1.20.4 |
| `sgm_bridge.py` | ✅ Adaptador HTTP |
| Experimentos verificados | 170+ en registry |

---

## Ejecución

### Test rápido del core
```bash
cd ~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM
python3 -c "
from sgm_core import SGMAgent
import random
ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
ag.instinto_alimentacion = 5
ag._hambre_real = 0.7; ag._amenaza = 0.1; ag._algo_enfrente = 1
ag._posicion_actual = (10, 10); ag._hay_gradiente = True
ag._gradiente_dir = (1, 0); ag._config_grad = {'activo': True, 'fuerza': 0.8}
ag._config_curio = {'activo': True, 'fuerza': 0.4}
ag._inc_dirs = {1: 1.0, 2: 0.5, 3: 0.5, 4: 0.5}
sv = [0.2, 0.2, 0.7, 0.1, 0.8, 1.0, 1.0] + [0.0] * 11
a = ag.step(sv, list(range(17)))
print(f'Acción: {a}, Modo: {ag.modo}')
"
```

### Entrenar L2
```bash
python3 /tmp/entrenar_l2.py
```

### Verificación completa
```bash
python3 /tmp/hermes-verify-omega-l2.py
```

---

## Experimentos Clave

| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0159 | Gate exploración | PASS | Memoria episódica + imaginación mejoran subsistencia |
| 0125 | Kuramoto habituación | PASS | Sincronización consolida conexiones |
| 0126 | Hebbian consolidación | PASS | Co-ocurrencia actividad-resultado refuerza |
| 0127 | Instinto hambre real | PASS | food<3 → pulsión a comer |
| 0128 | Drive noop | PASS | Energía libre empuja a actuar |
| 0140 | Arbitro modos | PASS | SUPERVIVENCIA amplifica supervivencia |
| 0143 | Place cells | PASS | Mapa emergente autónomo |
| 0144 | Modelo objetos | PASS | Predicción posición futura |
| 0153 | Memoria episodios | PASS | Recuerdos salientes recuperables |
| 0156 | Experiencia interna | PASS | Buffer episodico de trayectoria |
| 0158 | Memoria recuperable | PASS | Episodios significativos reconstruibles |
| 0160 | Valor hedónico | PASS | Preferencias individualizadas por objeto |
| 0164 | Modelo del otro | PASS | Teoría de la mente emergente |
| 0168 | Drive búsqueda | PASS | SEEKING homeostático bajo hambre |

---

## Próximos Pasos

1. **Minecraft**: Adaptación del bridge para entorno real (bot JS + core Python)
2. **L2 online**: Entrenamiento continuo con feedback del entorno
3. **Composición relacional**: HRR para planes multi-paso
4. **Identidad persistente**: Hilbert Thread entre sesiones
5. **Metacognición**: Reflexión sobre el propio conocimiento

---

## Referencias

- **Documento técnico**: `docs/Arquitectura_Pure_L2_Pandora.md`
- **NOUS (teoría)**: `NOUS/`
- **Documentos DSCN-G**: `docs/DSCN-G/`
- **Literatura**: `docs/SGM_literature_index.md`

---

## Licencia

Proyecto de investigación — NOUS: The Pandora Research.

---

*Última actualización: 2026-08-24 — Core v0.8-sgm-stable, Arbitro de Pulsiones, Sistema L2 completo.*