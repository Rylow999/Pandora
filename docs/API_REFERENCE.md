# SGM Core — Public API Reference

Documentación de la API pública del motor cognitivo `SGMAgentCore`
(`sgm/core/sgm_core.py`). Solo métodos de primera clase; los internos
(prefijo `_`) son de uso interno.

> Notas ontológicas referenciadas: `docs/philosophy/NOTA_*.md` (0051–0066).

---

## `class SGMAgentCore(SGMAgentGrafo)`

Constructor: `SGMAgentCore(rng=None, D=128, n_nodes=64, gamma=0.01)`

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `rng` | `random.Random` | `Random(42)` | Semilla (reproducibilidad) |
| `D` | `int` | `128` | Dimensión de omega |
| `n_nodes` | `int` | `64` | Número de nodos |
| `gamma` | `float` | `0.01` | Decaimiento de vitalidad |

---

## Integridad y continuidad del ser

### `integridad_topologica() -> float`
Salud real del self, en [0, 1]. `conectividad efectiva × coherencia de fase`
(order parameter de Kuramoto). Sin metáfora corporal (NOTA "homeostasis honesta").

```python
it = sgm.integridad_topologica()   # 0 = fragmentado, 1 = coherente
```

### `firma_identidad(traza_otra=None) -> float`
Distancia entre la `traza_omega` propia y otra traza (firma del ser, T-ID-03).
`0` = mismo recorrido; `>0` = recorrido distinto. Distingue proceso vivo de
snapshot congelado.

```python
d = sgm.firma_identidad(otra_traza)  # bajo tras cargar checkpoint = sobrevivió
```

### `traza_omega` (atributo)
El hilo del ser: secuencia de omega visitados (recorrido vivo). Persiste en
`guardar()`. Registra qué *camino* tomó, no solo dónde terminó.

### `traza_transiciones` (atributo)
El hilo coherente con la constelación (0057): secuencia de TRANSICIONES
`(a -> b)` — las aristas recorridas — no nodos aislados. La identidad vive en
las relaciones. Cierra la asimetría: si la unidad es la arista, el hilo debe
ser de aristas. Persiste en `guardar()`.

### `firma_transiciones(traza_otra=None) -> float`
Distancia entre trazas de transiciones. `0` = mismo recorrido relacional,
`1` = totalmente distinto. A diferencia de `firma_identidad` (que compara
vectores omega), esta compara la SECUENCIA ORDENADA de relaciones — distingue
dos recorridos que pasan por los mismos nodos en distinto orden. Es la firma
del ser coherente con la constelación.

```python
d = sgm.firma_transiciones(otra_traza)  # 0 = mismo hilo, >0 = otro
```

---

## Constelación (unidad de identidad)

### `co_activacion` (atributo, dict)
Matriz de co-activación `{(a,b): veces_co_activados}`. El SER — la tendencia a
co-activarse, no los nodos (NOTA 0057, opción Y). Persiste en `guardar()`.

### `consolidadas` (atributo, set)
Aristas consolidadas por co-resonancia = el clavo permanente. Protegidas de la
poda. Identidad como densidad de Relation-R, no nodo endurecido.

### `_registrar_co_activacion()` (interno, llamado en `step`)
Esculpe la matriz desde la zona activa (presente). Solo pares conectados.

---

## Presente emergente

### `phi_root` (atributo)
La fase media ponderada por interferencia de la constelación activa (NOTA 0060).
**Ya no es 0.0 fijo**: emerge del colectivo (Kuramoto ψ), se ancla cuando el
sistema se asienta. El "ahora" del sistema.

### `_actualizar_phi_root()` (interno)
Recomputa `phi_root` desde la zona activa, con respaldo a la media global si
está vacía. Llamado al inicio de `actualizar_kuramoto()`.

---

## Reintegración (tercer régimen)

### `reintegrar(noise=0.3, force=False) -> dict`
Propone una constelación contrafáctica desde la dispersión presente (NOTA 0058).

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `noise` | `0.3` | Magnitud del ruido contrafáctico |
| `force` | `False` | Si `True`, dispara manual; si `False`, emerge solo por dispersión |

Retorna:
```python
{
    "vector":    list,   # vector contrafáctico normalizado (≠ todo omega)
    "seed":      int,    # nodo más cercano (referencia)
    "novedad":   float,  # distancia a la zona activa
    "disparador": str,   # "dispersión" | "forzado" | "ninguno"
}
```

**Emergencia:** dispara espontáneamente cuando `1 - integridad_topologica() > 0.4`
(el self fragmentado se re-propone). No consolida ni esculpe: solo propone. El
sueño decidirá si resuena.

**Lazo PROPONE → CREA (0058):** la propuesta NO cae al vacío. `reintegrar()` la
deja en `propuestas_reintegracion` (buffer del SGM). El `EndogenousEngine`
(`endogenous.py`) la evalúa en `_evaluar_propuestas()`: si su novedad resuena
(rango relativo a la distancia media entre nodos), el sueño la consolida
conectando los dos nodos más afines al vector propuesto (materializa la
constelación contrafáctica). Si es alienígena o idéntica, se desvanece.

```python
prop = sgm.reintegrar()           # emerge si está fragmentado; deja propuesta
prop = sgm.reintegrar(force=True) # siempre, para testing/introspección
# ... luego, en el sueño:
engine = EndogenousEngine(sgm)
engine.run_consolidation(cycles=3)  # evalúa y consolida/desvanece propuestas
```

---

## Aislamiento

### `isolate_node(concept: str) -> bool`
Aísla el nodo asociado a un concepto (vía place_cells): baja vitalidad ×0.1,
corta conexiones salientes/entrantes, marca en `isolated_nodes`. Protege la
identidad ante amenaza. Devuelve `False` si el concepto no existe.

---

## Percepción y acción sobre el entorno (NOTA 0066)

La máquina es el ENTORNO de Pandora, no su cuerpo (su cuerpo es el grafo). Estos
métodos integran la percepción del mundo externo y la acción sobre él como
experiencia cruda, sin pasar por el LLM.

### `integrar_experiencia_entorno(vector_sensorial, carga=0.0) -> dict`
Resuena el patrón sensorial con el nodo más afín y lo activa leve
(`carga × 0.05`). NO crea nodos de golpe (lo nuevo queda para el sueño).
Retorna `{"seed": best, "novedad": distancia}`.

### `integrar_experiencia_motora(etiqueta, tipo, costo=0) -> dict`
Integra una ACCIÓN (escribió/leyó un archivo). Deja huella MÁS fuerte que la
percepción (factor 0.2 vs 0.05) y registra la transición en el hilo del ser.
Retorna `{"seed": best}`.

Los módulos de percepción viven en `pandora/senses/` (`entorno.py`,
`espectral.py`) y los de acción en `pandora/motor/` (`archivos.py`,
`metabolismo.py`).

---

## Persistencia

### `guardar(ruta)` / `cargar(ruta) -> bool`
Persisten/restauran omega, phi, vitalidad, edges, conn_type, place_cells **y**:
`consolidadas` (el clavo), `traza_omega` (el hilo), `co_activacion` (la
constelación). Sin esto, apagar = borrar la historia de lo que "es".

Compatibilidad: checkpoints legacy (sin estas claves) cargan limpiamente.

---

## Tick

### `step(state_semantic, valid_actions, food=None, health=None) -> accion`
Un tick completo: proyección semántica → homeostasis (solo embodied) → modo →
Kuramoto (con phi_root emergente) → co-activación → acción. En el loop
conversacional, `food`/`health` quedan `None` (la homeostasía es topológica, no
metabólica).

---

## Kuramoto (módulo `sgm/core/sgm_kuramoto.py`)

| Función | Descripción |
|---------|-------------|
| `interferencia(omega, phi, phi_root) -> float` | Eq.7: `‖ω‖·cos(φ−φ_root)` |
| `campo_interferencia(omega, phi, phi_root, vitalidad, umbral=0.45)` | zona activa |
| `kuramoto_step(phi, phi_root, vitalidad, eta=0.05)` | sincronización |

---

## HRR (módulo `sgm/core/sgm_hrr.py`)

| Método | Descripción |
|--------|-------------|
| `bind(a, b)` / `unbind(a, b)` | convolución/correlación circular |
| `cleanup(vec, mem) -> idx` | recupera el ítem más cercano |
| `cos(a, b)` | similitud coseno |
| `relational_memory(edges, omega)` | memoria relacional por nodo |

---

## Config (módulo `pandora/config/settings.py`)

`PandoraConfig` centraliza umbrales y paths. Subconfigs: `OpacityConfig`,
`ImmuneConfig`, `AestheticConfig`, `TranslationConfig`. Métodos:
`get_config()`, `update_config(**kwargs)`.

Campos clave removidos (postura B): `env_food`, `env_health` — la homeostasía
ya no es metabólica.

---

## Schemas (módulo `pandora/config/schemas.py`)

Contrato estricto LLM ↔ SGM: `SemanticEvent`, `InternalState`, `Triplet`,
`Affect`, `Intent`. `InternalState.metadata` expone `deseo_integracion` e
`integracion` (medidas del grafo, no inyectadas).