# Fase 8 — Cierre: Teleología Operativa y Estratificación

**Fecha:** 2026-08-06 · Luciano + Nexus
**Objetivo de esta nota:** definir OPerativamente qué significa que el agente "viva", "muera", "tenga hambre", "quiera" y "logre" algo — mapeando cada concepto a una representación medible, siguiendo la misma disciplina que usamos para dolor (E_acumulado) y duda (duda_count). Y especificar el formato de evaluación multi-estrato que vamos a usar en todos los experimentos de Crafter de aquí en adelante.

---

## 1. La trampa de la teleología

No podemos saber si el agente "comprende" o "quiere" algo desde afuera. Eso es una atribución mental (interpretación externa), no un dato. Lo que podemos medir son **señales internas correlacionadas con estados y acciones**.

Regla de la misma disciplina que con dolor y duda:
1. La señal interna se deriva de dinámicas reales del sistema (no se asigna a mano).
2. Se mide contra un observable de recorrido y contra un negative control.
3. Si la correlación esperada no aparece, se reporta FAIL, no se maquilla.

---

## 2. Mapeo biológico de los conceptos

### 2.1 Hambre (homeostática, observable directo)
- **Base:** homeostasis del interno (regulación de nutrientes/Ghrelin en biología).
- **En SGM:** `food` del inventario es la entrada sensorial. La señal interna es `1 - food/10` (privación).
- **Definición operativa (querer = hambre → búsqueda de comida):**
  - Medible como **correlación entre `food` bajo y la proporción de acciones `eat` o de búsqueda de alimento.**
  - Si `food` cae y el agente NO aumenta `eat`, no hay "querer" — hay ruido.
- **Referencia:** Berridge — "wanting" es motivación a actuar hacia el estímulo, medible como respuesta operante, NO como sensación subjetiva.

### 2.2 Querer (wanting, incentive salience)
- **Base:** sistema SEEKING dopaminérgico (Panksepp). El PFC da dirección para que la búsqueda sea *goal-directed*, no *aimless wandering*.
- **En SGM:** el vector ω del nodo "estado con comida" debería ganar saliencia cuando la privación sube.
- **Definición operativa:** si el agente "quiere" comida, la afinidad hacia nodos/acciones de alimentación sube cuando `food` baja. Medible como **correlación hambre → sesgo hacia acciones alimentarias en el ranking del PPR.**
- **Contraste con Liking (Berridge):**
  - Liking = placer al consumir (el reward positivo al comer).
  - Wanting = motivación ANTES de consumir (la búsqueda).
  - En SGM distinguir: reward al comer (liking) vs. sesgo de la búsqueda ante privación (wanting). Son medibles por separado.

### 2.3 Curiosidad
- **Base:** SEEKING + reducción de incertidumbre (prediction error). Siempre goal-directed en biología: se busca lo que reduce incertidumbre, no se deambula.
- **En SGM:** el decoder como modelo del mundo mide prediction error. La curiosidad = explorar donde el modelo falla (hay info nueva), NO "movernos a muchos tiles".
- **Advertencia del 0113:** un agente que pasea 33 tiles sin variar su repertorio NO es curioso — es aimless wandering. La curiosidad se mide por **reducción de prediction error**, no por tiles recorridos.

### 2.4 Belleza / valor (DEFERIDO — no cerrar Fase 8)
- Es un nivel más alto y NO bloquea la Fase 8. Requiere definición operativa tan cuidada como dolor/duda antes de afirmar nada. Por ahora: **excluida del cierre de Fase 8**, documentada como tensión abierta en el eje filosófico.

### 2.5 Vivir / Morir
- **En biología:** la homeostasis falla (muerte por inanición, daño letal).
- **En Crafter:** el agente muere cuando `health` llega a 0.
- **Requisito nuevo (pedido de Luciano):** el agente debe **vivir hasta morir naturalmente**, no cortarse por pasos. Un episodio termina cuando `terminal=True` (muerte del agente), no cuando se llega a N pasos.

---

## 3. Evaluación multi-estrato (para TODOS los experimentos de Crafter de aquí en adelante)

Cada experimento debe reportar QUÉ hacía el agente en cada estrato, no solo métricas agregadas. Formato obligatorio:

### Estrato 1 — Supervivencia
- ¿Cuánto vivió? (pasos hasta muerte natural, no cortado)
- ¿Por qué murió? (inanición, daño, estaba en ACTIVA/CONTRADICTORIA?)
- Health/food en el momento de la muerte.

### Estrato 2 — Grafo (cambios en la estructura)
- Antes vs después: número de aristas, cuáles se crearon/podaron, conn_type aprendido.
- ¿El grafo refleja la experiencia de vida? (¿apareció una arista "hambre→comer"?)

### Estrato 3 — Movimiento (espacio explorado y CÓMO)
- Trayectoria completa (no solo tiles únicos): ¿se movió en una dirección, en círculos, exploró ramas nuevas?
- Rango X/Y, secuencia temporal de posiciones.

### Estrato 4 — Apetito / querer (correlación hambre→comer)
- Correlación entre `food` bajo y `eat`.
- Si no hay correlación, se reporta: el agente come al azar (no hay querer operativo).

### Estrato 5 — Estados internos (dinámicas)
- Traza de E_acumulado, status (ACTIVA/INCONCLUSA/CONTRADICTORIA), duda_count.
- Contradicciones: cuándo y por qué.

### Estrato 6 — Curiosidad (reducción de prediction error)
- Prediction error del decoder a lo largo de la vida.
- ¿Exploró donde el modelo fallaba (curioso) o donde ya sabía (deambulaba)?

---

## 4. Qué le falta al agente para cerrar la Fase 8

### 4.1 El formato: vivir hasta morir
- Todos los episodios previos cortaron a N pasos. Cambiar a: **correr hasta `terminal=True`** (muerte natural), reportar el motivo.
- Esto revela problemas que el corte por pasos escondía: el agente podía estar muriendo de hambre sin que lo viéramos porque lo cortábamos antes.

### 4.2 El querer operativo (wanting) NO está implementado
- Hoy el agente come cuando el PPR lo elige, no cuando tiene hambre. No hay correlación hambre→comer garantizada.
- Paso siguiente (no inmediato): que la privación module la saliencia de nodos de comida (cereza del algo, no hardcode — debe emerger del sustrato, ver punto 2.2).

### 4.3 La curiosidad dirigida NO está implementada
- El decoder existe como filtro predictivo pero no dirige la exploración hacia zonas de prediction error alto.
- Paso siguiente: medir la curiosidad como reducción de incertidumbre (Berridge/Oudeyer), no como tiles.

---

## 5. Experimentos que faltan en Crafter para cerrar Fase 8

1. **exp_SGM_0114:** Aparato de "vivir hasta morir" — el agente corre hasta `terminal=True`. NC: sin reward de novedad. Reporte multi-estrato completo.
2. **exp_SGM_0115:** Muerte y causal — dado que el agente muere de hambre (inolación), ¿cambia su comportamiento en el siguiente episodio? (persistencia que QUEDÓ buggeada en 0109/0111 — NO re-introducir hasta consolidación de omega)
3. **exp_SGM_0116:** Querer operativo — ¿aparece correlación food→eat a lo largo de la vida? Medir wanting (Berridge). Si no hay, FAIL honesto (el agente come al azar).
4. **exp_SGM_0117:** Curiosidad = reducción de prediction error — el decoder mide prediction error; ¿el agente explora donde falla su modelo? NC: decoder apagado.
5. **exp_SGM_0118:** Evaluación multi-estrato completa — el agente vive una vida completa, reporte de los 6 estratos, sin corte por pasos.

*(En orden: primero el formato 0114, después 0116 querer, 0117 curiosidad, y 0118 integración multi-estrato.)*
*Nota 2026-08-06: 0114 YA SE CORRIÓ (ver resultados). Reveló que el agente nunca come (eat_total=0) y la obsesión con make_stone_sword. Eso llevó a la corrección del core abajo.*

---

## 7. CORRECCIÓN DEL CORE (2026-08-06) — el conocimiento está en las conexiones, ω es identidad

### 7.1 Bug detectado y corregido
- **Boost Causal 1.5** en `_aff()`: multiplicador fijo (+50% afinidad) a aristas tipo Causal. Era **hardcode arbitrarario** — daba ventaja sistemática sin que nazca del sustrato. **ELIMINADO.**
- **Decaimiento global de ω** en `reward()`: `ω = (1-β)·ω + β·r·0.01` para TODOS los nodos. Contaminaba las identidades parejo (causa raíz de degradación entre vidas 0109/0111). **ELIMINADO.**

### 7.2 Filosofía aplicada (coherente con NOUS + literatura)
- **ω = identidad estable del concepto.** No se toca, no se aprende. Es el ser del concepto — la identidad del entorno y del interior.
- **El conocimiento vive en las CONEXIONES** (`aprender_conexion` + `strength` + poda). La plasticidad es sináptica (Hebb), no en el cuerpo de la neurona.
- **El entorno y el interior se crean en el acto de relacionarse.** La realidad percibida no es un dato externo fijo; es el patrón de conexiones que se auto-organiza ante el estímulo.
- **El lenguaje interno (decoder) MODULA las conexiones, no dicta.** No reescribe identidades (label-feedback hypothesis, Frontiers 2012 — lenguaje modula procesamiento en curso, no warp el espacio perceptual).

### 7.3 Verificado
- Los ω ya no cambian durante step+reward (0 nodos modificados). Boost 1.5 y decaimiento parejo fuera del código.

---

## 6. Regla de honestidad (sin cambios, reafirmada)

- No atribuir "querer" o "curiosidad" sin señal operativa correlacionada.
- Reportar AMBOS desenlaces pre-registrados.
- El negative control ejecuta cómputo real.
- Si el agente vive hasta morir de hambre sin comer, eso NO es un bug — es un dato sobre si hay (o no) querer operativo.