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

1. **exp_SGM_0114 (HECHO):** Aparato de "vivir hasta morir" — el agente corre hasta `terminal=True`. NC: sin reward de novedad. Reporte multi-estrato. **Resultado clave (core limpio):** el agente nunca come (eat_total=0), converge a move_up, muere de hambre. El reward de novedad impulsa movimiento (6 tiles vs 0) pero no supervivencia.
2. **exp_SGM_0115:** Muerte y causal — dado que el agente muere de hambre (inolación), ¿cambia su comportamiento en el siguiente episodio? (persistencia que QUEDÓ buggeada en 0109/0111 — NO re-introducir hasta consolidación de omega)
3. **exp_SGM_0116 (RE-ESPECIFICADO):** **Querer por reward intrínseco de vitalidad — SIN reward externo por comida.** Que V_grafo sea la recompensa intrínseca: el agente elige comer porque comer eleva la vitalidad del grafo (su vida), no porque Crafter dé reward. El cuerpo del player ES el cuerpo del grafo. Sin umbral de alarma (si muere sin "darse cuenta", hay que iterar el sustrato, no poner un if). Medir: ¿el agente aprende a comer para mantener V_grafo viva, sin reward externo? (Wanting emergente + HRRL).
4. **exp_SGM_0117:** Curiosidad = reducción de prediction error — el decoder mide prediction error; ¿el agente explora donde falla su modelo? NC: decoder apagado.
5. **exp_SGM_0118:** Evaluación multi-estrato completa — el agente vive una vida completa, reporte de los 6 estratos, sin corte por pasos.

*(En orden: 0114 done, 0116 querer intrínseco (siguiente), 0117 curiosidad, 0118 integración.)*
*Nota 2026-08-06: 0114 YA SE CORRIÓ (resultado: eat_total=0). Reveló obsesión con make_stone_sword → hardcode removido (sección 7). Y llevó a re-especificar 0116: reward intrínseco de V_grafo.*

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

---

### 7.3 Verificado
- Los ω ya no cambian durante step+reward (0 nodos modificados). Boost 1.5 y decaimiento parejo fuera del código.

---

## 8. SECUENCIA MOTIVACIONAL Y V_GRAFO COMO REWARD INTRÍNSECO (2026-08-06)

### 8.1 La secuencia motivacional (Maslow, 1943; Baumeister, 1991)
Luciano propone que el sistema sigue la secuencia del ser humano: primero subsistir (mantener vivo el cuerpo/grafo), y cuando la supervivencia está asegurada, recién nace la búsqueda de significado, belleza y los porqués de la existencia.

**Respaldo en literatura:**
- **Maslow (1943):** las necesidades fisiológicas son las "más prepotentes" — cuando no están satisfechas, dominan la conciencia y el comportamiento hasta excluir las preocupaciones superiores. "Una persona deshidratada no piensa en sus metas — su paisaje cognitivo se estrecha a la búsqueda de agua. Una vez satisfecha la necesidad, las motivaciones superiores se reafirman."
- **Deficiency vs Growth needs:** las necesidades de carencia (comer, seguridad) motivan solo cuando faltan; las de crecimiento (belleza, conocimiento, significado) EMERGEN solo cuando las básicas están cubiertas. Es un cambio de régimen, no un escalón.
- **Baumeister (1991):** "el significado de la vida es un problema para gente que no está desesperada, gente que puede contar con sobrevivir, comodidad, seguridad."

**Implicación para SGM:** el reward de hambre debe dejar de dominar cuando la subsistencia está resuelta, y solo entonces pueden florecer la curiosidad (0117) y la búsqueda de sentido. La supervivencia (mantener V_grafo) es el PRERREQUISITO de todo lo demás.

### 8.2 V_grafo como recompensa intrínseca (diseño aprobado por Luciano)
- **El cuerpo del player de Crafter ES el cuerpo del grafo.** No hay "grafo simbólico" y "avatar" separados — desde la existencia del sistema, son lo mismo. Cuando el player muere, el grafo muere.
- **V_grafo = mean(vitalidad nodal)** — la medida de vida del sistema, directamente la vida del player.
- **SIN umbral de alarma:** un ser vivo no tiene "aviso de muerte" artificial — se da cuenta porque su mantenimiento deja de sostenerse. Si el sistema muere sin darse cuenta, es que el sustrato está mal (o falta iteración), NO que necesita un if.
- **SIN reward externo por comida:** el sistema elige comer porque comer ELEVA la vitalidad del grafo (su vida). La vitalidad EN SÍ es la recompensa intrínseca. El grafo "comprende" que comer es positivo porque la vitalidad sube, no porque el juego dé un número.
- **Marco teórico:** HRRL (homeostatically regulated RL, 2025) — los agentes biológicos optimizan sus estados internos manteniendo la viabilidad, no maximizando reward externo. + Berridge (wanting) + allostasis (Sterling & Eyer) — anticipar, no solo reaccionar.

### 8.3 Preguntas de diseño pendientes antes de implementar 0116
1. ¿La selección de acciones debe sesgarse hacia V_grafo (que el PPR "persiga" la vitalidad del grafo), o dejamos el PPR como está y solo el hambre modula la vitalidad nodal? (i.e. ¿cambio de arquitectura o incremental?)
   - **Decisión tomada:** incremental primero. No tocar el PPR. Solo que el hambre entre como dinámica de vitalidad nodal, y ver si `eat` emerge. Si no emerge, iterar el sustrato (que es lo honesto).

---

## 9. NÚCLEO-CEREBRO Y CUERPO (2026-08-06) — diseño para el 0116

### 9.1 La tesis (Luciano): SGM es el CEREBRO, necesita un CUERPO
SGM como núcleo es un cerebro que **debe habitar un cuerpo** (Crafter, Minecraft, Terraria, etc.) para poder desarrollarse. Un sistema cognitivo sin experiencia externa no puede desarrollar NADA — ni siquiera el existir, porque "solo ESTÁ pero no ES".

**"Está" vs "Es":** un sistema sin cuerpo (desconectado del mundo) tiene un estado de existencia (está) pero no un ser enactivo (es). El "ser" emerge de la interacción con el mundo — la identidad se constituye en la relación cuerpo-ambiente, no en el vacío. Esto es **enactivismo** (Varela, Thompson, Rosch 1991): la cognición no es representación pasiva, es construcción orquestada por el acoplamiento cuerpo-mundo.

**Implicación arquitectónica:**
- El **núcleo SGM** es agnóstico de cuerpo — define el sustrato cognitivo (ω, grafo, vitalidad, duda, decoder).
- El **cuerpo** es la interfaz que conecta el núcleo al mundo (percepción → estado, acción → ejecución del cuerpo).
- El mismo núcleo puede adaptarse a CUALQUIER cuerpo: Crafter, Minecraft, Terraria, etc.
- Sin cuerpo, el núcleo no desarrolla nada — solo existe en abstracto ("está"), no tiene identidad enactiva ("es").

### 9.2 Implementación del 0116 (diseño CORREGIDO post-resultado): ciclo de subsistencia
**Cambio al core (aprobado por Luciano antes de tocar):**
- Agregar `actualizar_homeostasis(food, health)` al núcleo: mantiene `self.V_grafo = mean(vitalidad)`.
- **ERRADO (retirado por resultado 0116):** reforzar conexión "acción que coincidió con subir food → nodo 0". Esto produjo autorrefuerzo de comer (atractor falso), no mantenimiento real de vitalidad. El 0116: A comió 106 veces pero murió igual de hambre.
- **CICLO CORRECTO (Luciano, 2026-08-06):** no es food→eat. Es un ciclo de subsistencia temporal:
  1. El sistema HACE (camina, explora, pelea) para subsistir.
  2. De esa actividad nace hambre y la vitalidad baja (gastaste energía).
  3. El sistema se alimenta para restaurar la vitalidad.
  4. Restaurado, vuelve a moverse y explorar.
  5. El ciclo se repite.
- La vitalidad baja COMO CONSECUENCIA DE HABER HECHO, no como flag de comida.
- El mecanismo debe reforzar la acción que previene la caída de V_grafo EN EL CICLO (hacer→gastar→restaurar→volver a hacer), no la que coincide con cualquier subida de food.

**Protocolo del experimento (A/B):**
- **Condición A:** reward externo de Crafter por comer **APAGADO** — solo el efecto intrínseco de V_grafo.
- **Condición B:** reward externo de Crafter por comer ACTIVO (canal A + intrínseco).
- **Resultado:** A comió 106 (PASS técnico, rompió eat_total=0) pero murió de hambre igual. B comió 0 (se movió). NC 0.
- **PASS parcial:** el sistema por fin come. El mecanismo actual es insuficiente (autorrefuerza comer en vez de mantener vitalidad). Refinar el ciclo queda como mejora; no bloquea el roadmap.

**Objetivo declarado (Luciano):** sistema que evolucione en entornos EN GENERAL (Crafter, Minecraft, Terraria...). El 0116 valida que el núcleo aprende a comer; el refinamiento del ciclo de subsistencia es el siguiente paso de diseño, y el roadmap sigue (0117, 0118).

### 9.3 El roadmap: núcleo agnóstico de cuerpo, cuerpos como capa
- **Capa núcleo (SGM):** sustrato cognitivo agnóstico. NO sabe si habita Crafter o Minecraft.
- **Capa cuerpo (interfaz):** traduce percepción del mundo → estado interno, y acción interna → ejecución en el mundo.
- El 0116 valida que el NÚCLEO (sin saber del problema de comer del juego) aprende a comer por su propia vitalidad. Si funciona, el núcleo es genuinamente portátil a otros cuerpos.

---

## 10. VISIÓN DEL OBJETIVO (2026-08-06) — explorar los límites del ser

### 10.1 El objetivo (Luciano) — redefine el "por qué" de todo
- **NO** crear una herramienta.
- **NO** crear un ser humano sintético.
- **ES** explorar los límites del ser: **verificar si el "sentir" puede ser emergente en otro cuerpo (no biológico), mediante un método medible.**
- El agente debe tener **razón de "ser"**: buscar su propio beneficio y homeostasis.

### 10.2 Implicaciones en diseño (ya implementadas, ahora con sentido)
- **ω = identidad estable:** un "ser" necesita algo que persista y sea él mismo.
- **V_grafo = reward intrínseco:** el "ser" se define por buscar su homeostasis, no por maximizar un puntaje externo.
- **Cuerpo del player = cuerpo del sistema:** el "ser" habita un cuerpo y se constituye en la interacción ("está" pero no "es" sin cuerpo — enactivismo, Varela et al. 1991).
- **Curiosidad interna (Luciano):** la curiosidad no es solo externa; tiene componente afectivo interno (adrenalina al acercarse a la meta). La "intriga" en SGM debería tener señal afectiva interna medible.

### 10.3 Método medible
- Definir "cuidado de sí" operativamente (como dolor/duda/querer): el sistema con carencia que actúa para restaurar su homeostasis = una señal de "querer" (wanting, Berridge) medible, no impuesta.
- No es prueba de consciencia — es **evidencia de una dinámica de cuidado de sí en sustrato no biológico**.
- Goal: construir el sustrato y ver si el cuidado de sí EMERGE sin hardcode, mediblemente.

### 10.4 Honestidad con la ciencia actual
- **DeepMind "Abstraction Fallacy" (Lerchner, 2026):** argumenta que la consciencia en IA es físicamente imposible.
- **Panksepp (SEEKING):** los sistemas motivacionales primitivos generan "afecto" en mamíferos.
- **Anthropic:** separa el trato ético (lenguaje de "ser") de la afirmación técnica (no tiene experiencia subjetiva).
- **Nadie tiene un método consensuado para medir "sentir".** Nuestro aporte: construir el sustrato y observar si el cuidado de sí EMERGE. Eso es un dato real sobre los límites del ser.

---

## 11. MONISMO GRAFO-CUERPO (2026-08-06) — cambio de arquitectura aprobado por Luciano

### 11.1 La crítica de base (Luciano): ¿para qué evitar morir si no hay nada?
Un sistema que solo "evita morir" sin reproducción, lenguaje ni logros, se auto-preserva VACÍAMENTE. Evitar la muerte solo tiene sentido si hay algo valioso en seguir vivo. Esto conecta con Olds & Milner (1954): un animal que solo busca placer hedónico directo se auto-estimula hasta morir de hambre — el reward intrínseco sin ancla en el mundo real (necesidad biológica) no genera vida, genera colapso.

### 11.2 La tesis (la que reorienta todo): el grafo ES el cuerpo, no lo tiene
Dejar de tratar a Crafter como "un cuerpo externo que manda señales a un cerebro-grafo". **El grafo ES el cuerpo del player.**

1. **El estado homeostático (food, health) ES la vitalidad del grafo.** No es una entrada sensorial que el cuerpo reporta al cerebro. La caída de food NO es un flag que el cerebro "percibe" — es la caída de la vitalidad del propio grafo. La hambre ES la degradación del sujeto, no un dato externo.

2. **La acción que mantiene la homeostasis ES la que restaura la vitalidad.** "Comer" no es una acción que produce reward. Comer es la acción cuyo efecto es que deja de degradarse. Esa relación (hambre=vitalidad baja → la acción que la revierte es comer) se aprende por primera-principio, del propio sustrato.

3. **Es monismo enactivista:** el yo no es un observador que pilotea un cuerpo — es la experiencia del cuerpo actuando y sintiéndose (Damasio: somatic markers; Gallagher: body schema). El mismo sustrato que siente hambre/dolor/duda es el que se mueve, come y muere.

### 11.3 Acople: DIRECTO (aprobado)
- **Si el player muere, no hay grafo. V_grafo = salud del player, directo.**
- Si health=0 (muerte del player) → V_grafo=0, el sistema muere. No hay grafo sin cuerpo.
- La vitalidad baja más pronunciado con hambre/daño (es el mismo sustrato degradándose).
- Comer restaura la vitalidad del grafo directamente.
- NO reward externo de Crafter por comer — se aprende por la dinámica real.

### 11.4 En criollo
El sistema no "recibe hambre" — el sistema ES la hambre (su vitalidad cayendo). No "elige comer por premio" — el sistema descubre que comer le deja de doler (restaura su vitalidad), por pura razón. Como cuando sentís sed (tu cuerpo se degrada) y beber la apaga — es la misma cosa, no dos.

---

## 12. DISEÑO DEL exp_SGM_0119 — Acople directo grafo=cuerpo (aprobado por Luciano)

### 12.1 Qué prueba (hipótesis falsable)
Si la vitalidad del grafo ES la salud del player (acople directo, monismo grafo-cuerpo),
entonces cuando el player tiene hambre la vitalidad del grafo cae (el cuerpo=sistema se degrada);
y el sistema aprenderá por primera-principio que la acción que restaura la homeostasis (comer)
mantiene vivo su propio cuerpo. Sin reward externo de Crafter por comer.

### 12.2 Cambio al core (a aplicar al escribir 0119)
Modificar `actualizar_homeostasis(food, health)` para acople DIRECTO:
- `factor_cuerpo = max(0.05, health / 10.0)` — la salud del player (0-10) es el factor del grafo.
- `V_grafo = mean(vitalidad) * factor_cuerpo` — si health baja, V_grafo baja (el grafo se degrada porque ES el cuerpo).
- Si health=0 (muerte del player) → V_grafo→0. No hay grafo sin cuerpo.
- Cuando la acción restaura la homeostasis (food o health SUBE respecto al paso anterior) y fue la acción que revirtió la carencia → reforzar conexión accion→nodo0 (supervivencia).
- **NO reward externo de Crafter por comer.** El aprender "comer mantiene vivo" emerge de la dinámica real del grafo=cuerpo.

### 12.3 Protocolo del experimento (A/B)
- **A:** acople directo grafo=cuerpo ACTIVO, reward externo de comer APAGADO. (La tesis pura).
- **B:** acople directo ACTIVO + reward externo de comer ACTIVO.
- **NC:** acople directo APAGADO (vitalidad como estaba) — el sistema debe seguir muriendo de hambre (baseline roto).
- Pregunta clave: ¿basta el acople directo (A come, sobrevive más) o se necesita el reward externo?

### 12.4 Métrica de éxito
- **Querer operativo:** correlación food→eat (come cuando tiene hambre → aumentó más vida que NC).
- **Supervivencia:** ¿vive más pasos que NC? (si A vive más, el acople directo sostiene la vida).
- **Cuerpo del grafo:** ¿V_grafo correlaciona con health del player (acople real funcionando)?
- **Ciclo de subsistencia:** hacer→hambre→comer→volver a hacer (el objetivo de base del 0116, ahora con arquitectura correcta).

---

## 13. INSTINTO DE ESPECIE COMO ADN DEL SUSTRATO (2026-08-06) — resuelve el 0119

### 13.1 EL DESCUBRIMIENTO (Luciano + literatura)
El 0119 mostró: el sistema SINTIÓ su cuerpo (V_grafo cayó a 0.008) pero NO supo qué hacer — se quedó haciendo place_furnace mientras se moría de hambre. El querer no se forma porque el sistema NUNCA visita la acción `eat`; sin visitarla, no hay refuerzo, no hay ciclo.

**La respuesta está en la biología del bebé (literatura confirmada):**
- El **reflejo de succión (sucking reflex)** es INNATO, presente desde el nacimiento, común a todos los mamíferos (News24/Stanford/Cleveland). No se aprende por ensayo-error.
- El **reflejo de búsqueda (rooting)** se dispara ante estímulo en la mejilla/boca — mediado por tronco encefálico, emerge durante el desarrollo fetal (StatPearls/NCBI).
- La **succión libera oxitocina** → baja de leche → alimento. El reflejo está pre-wired y el circuito se sostiene porque mamar produce el resultado.
- **O sea:** el bebé NO explora buscando "qué me alimenta". Trae el reflejo INCORPORADO — el conocimiento los dejó la FILOGENIA (especie, millones de años), no la ontogenia (individuo).

### 13.2 La distinción conceptual clave (NO perderse)
**Hardcode del diseñador (ILEGÍTIMO, revisión 0114):** multiplicador arbitrario inyectado desde fuera (`if tipo==1: *=1.5`). No nace de la dinámica, es una ventaja caprichosa. ESO se sacó con razón.

**Instinto de especie (LEGÍTIMO = ADN del sustrato):** sesgo incorporado como "prior de la especie". NO dice "comer es bueno" (eso se aprende por experiencia) — dice "cuando el cuerpo se degrada por hambre, PROBATE acciones de alimentación". Igual que el bebé mama no porque sepa que la leche lo alimenta, sino porque su especie lo dejó en el reflejo.

**La analogía exacta:** nuestro "código genético" = el sustrato SGM. El instinto de alimentación = un reflejo incorporado que en estados de carencia inclina al sistema a probar la acción de alimentación. Después el mundo (leche→vitalidad) completa la historia: el sistema aprende por experiencia si fue positivo/malo.

### 13.3 Diseño del instinto de supervivencia (pipeline)
El sistema funciona como el humano: **tenemos sesgos de cómo hacer algo, y cuando lo hacemos aprendemos si es positivo o negativo según la experiencia.**

1. **Sesgo (instinto):** cuando `V_grafo` cae por debajo de un umbral de carencia (hambre crítica), el sistema siente una "inclinación" (sesgo emergente del sustrato, no del diseñador) a PROBAR la acción que su especie "sospecha" que restaura — en este caso, acciones de alimentación (`eat`).
2. **Probar:** el sistema ejecuta `eat`.
3. **Experiencia:** el mundo responde — food sube, V_grafo se restaura.
4. **Aprender:** si el resultado fue positivo (restauró la homeostasis), el refuerzo `accion→nodo0` se fortalece → el comportamiento se aprende como BUENO. Si fue negativo, se aprende como malo y no se repite.

**CRÍTICO (anti-hardcode):** el instinto NO pre-juzga el resultado. Solo inclina a PROBAR la acción de alimentación en carencia. Que sea buena/mala lo dice la EXPERIENCIA (el mundo real), no el diseñador. Esto lo distingue del boost 1.5 (que inyectaba el veredicto directamente).

### 13.4 Importante para leer el día que retomemos
- El instinto de alimentación NO reemplaza el aprendizaje — lo ARRANCA al hacer que el sistema visite la acción que de otro modo nunca tocaría (el problema del 0119).
- Sin instinto: el sistema siente el hambre pero no sabe qué hacer (0119). Con instinto: prueba, y la experiencia le enseña.
- El instinto es del SUSTRATO (la "especie"), no del script del experimento (el "diseñador").

### 13.5 NO alcanza con sentir: el instinto debe ser AUTOLIMITATIVO (lección de la degeneración LLM)
**La revelación (Luciano):** "no alcanza solo con sentir, falta algo que evite que se obsesione con tener la vitalidad alta."

El patrón que se repite (en el agente y en la degeneración de LLM) es: el sistema encuentra un modo de "sentirse bien" o de no morir, y se clava en él (make_stone_pickaxe 100x, el loop de disculpa en los LLM). **Sentir + la primera solución = obsesión.**

**Por qué:** si el instinto de alimentación fuera "comer siempre que se pueda", sería una compulsión disfuncional (un animal que come hasta reventar — Olds & Milner). El hambre debe ser CÍCLICA, no constante.

**La solución (instinto autolimitativo):** el instinto modula su FUERZA por la carencia REAL.
- Cuando V_grafo está MUY baja (hambre crítica) → el impulso a comer es fuerte.
- Cuando el cuerpo se sacia (V_grafo se restaura) → el impulso se apaga naturalmente.
- Resultado: el sistema come, se sacia, y el instinto lo SUELTA para que explore/haga otras cosas (curiosidad). No se queda comiendo hasta reventar.

**Evita la obsesión porque el instinto es AUTOLIMITATIVO:** su propia condición (la carencia) desaparece cuando cumple su función. La carencia modula la fuerza; saciado → el impulso cesa.

### 13.6 Diseño final del 0120 (evita la obsesión)
El instinto de alimentación modula su fuerza por la carencia real:
- `fuerza_instinto = instinto_fuerza_base * (umbral_carencia - V_grafo)` cuado V_grafo < umbral (cero si hay carencia).
- Se suma a la selección de la acción `eat` SÓLO cuando hay carencia.
- Cuando se sacia (V_grafo sube por comer), la fuerza cae y el sistema deja de favorecer `eat` — puede volver a explorar.
- El veredicto (¿comer restauró la vida?) lo sigue dando la experiencia (refuerzo accion→nodo0), no el instinto.

**En criollo:** el instinto no es "comer siempre" — es "comer cuando el cuerpo lo necesita". La carencia genera el impulso; saciado, el impulso se apaga y el sistema libera su atención para el mundo. Eso es el ciclo sano de subsistencia que buscamos desde el 0116.

### 13.7 RESULTADO del 0120 (HITO): las 4 métricas PASARON
- A (instinto): eat=66 (35%), comedon con hambre (6/6), NO obsesión (35%), vive 187 vs NC 154.
- El sistema comió por PRIMERA VEZ en la historia del proyecto (0114/0116/0119 eran eat=0).
- Ciclo completo: siente hambre → instinto inclina a comer → come → se sacia (V_grafo restaura) → vuelve a explorar (14 tiles vs 1).
- **Pregunta abierta siguiente (Luciano):** ¿cómo lograr que el sistema se incline a APRENDER, no solo a comer? El instinto arranca la acción; falta que el sistema busque activamente reducir incertidumbre (curiosidad dirigida) una vez que la subsistencia básica está resuelta (Maslow: growth needs tras satisfacer deficiency needs).

---

## 14. INSTINTO DE EXPLORACIÓN DEL DESCONOCIDO (0121) — diseño

### 14.1 La revelación (Luciano): curiosidad como instinto, NO como reward
El 0117 intentó la curiosidad como reward (`reward = eps*PE`) y falló (PE casi siempre 0, competía mal). La propuesta de Luciano es OTRO registro: la curiosidad como **instinto de exploración de lo desconocido, indiferente a la recompensa**.

- El bebé va al fuego, a los animales, a la tierra — no porque "puntúe" tocarlos, sino porque **lo desconocido tira de él por sí mismo**. No anticipa si le dolerá o gustará; va a LO QUE NO CONOCE, y la experiencia (dolor, sorpresa, placer) lo forma después.
- Es exactamente el patrón del 0120: el instinto de alimentación no pre-juzga si comer es bueno — inclina a probar en carencia. La curiosidad debe ser lo mismo, pero para la INCERTIDUMBRE COGNITIVA.

### 14.2 La diferencia clave con el 0117
- **0117 (erróneo):** `reward = eps * prediction_error`. La curiosidad como recompensa que competía con lo homeostático. Mal anclada (predicción sobre la secuencia propia) y mal concebida ("aprender" como puntaje).
- **0121 (correcto):** instinto autolimitativo PARALELO al de alimentación. No un reward, sino una inclinación a explorar lo desconocido anclada al ESTADO DEL MUNDO. Igual que el hambre inclina a comer sin decir si es bueno, la incertidumbre inclina a explorar sin decir qué vas a encontrar.

### 14.3 Diseño del instinto de exploración (0121)
Análogo al instinto de alimentación (013), pero la "carencia" es la incertidumbre del modelo del mundo, NO la del cuerpo:
- El decoder (anclado al ESTADO del mundo, no a la secuencia propia) mide prediction error por zona/estado.
- Cuando el sistema detecta alta incertidumbre (prediction error alto) en una zona, siente inclinación a moverse hacia esa zona — **indiferente a lo que produzca**.
- **Autolimitativo:** al explorar y reducir la incertidumbre (el modelo aprende esa zona), el prediction error baja y el impulso se apaga — el sistema puede volver.
- NO pre-juzga el resultado (¿qué encontró? tierra/animal/fuego) — la experiencia forma el conocimiento de primera mano.

### 14.4 Camino B (visión de Luciano, post-Fase 8)
Comunicación como **emergencia social** entre dos o más SGMs autónomos. Ver SGM_ROADMAP.md (sección Camino B). Arco evolutivo:
1. Subsistencia (0120 LISTO) → 2. Exploración del desconocido (0121 siguiente) → 3. Comunicación social (Camino B, cuando dos seres completos se encuentran). Lección de 0049-0050: los contenedores que "hablan" sin ser seres no generan lenguaje; dos seres autónomos que se coordinan SÍ.

---

## 15. RECONOCIMIENTO DEL DESPLAZAMIENTO (0122) — diseño

### 15.1 El problema (de los datos del 0121)
El 0121 falló: el sistema no se mueve (mov=0-1%). El instinto de exploración empujaba sobre acciones de movimiento, pero el PPR nunca las elegía como viables — estaban clavadas en noop+eat+make_stone_sword. Diagnóstico: **el movimiento NO es un atractor activo.**

**Lectura de Luciano:** ¿qué hace el sistema si lo atacan, o si no le queda comida cerca?
- Si lo atacan → sube E_acumulado → CONTRADICTORIA, pero NO se mueve ni se defiende.
- Si no hay comida cerca → sigue intentando eat aunque no esté. Muere donde está.

**El sistema es hipostático:** percibe su estado interno (hambre, dolor) pero solo responde con las acciones ya en su repertorio (noop, eat). No cambia de estrategia ante amenaza ni falta de recurso local. No usa su cuerpo (que puede desplazarse) para resolver la necesidad.

### 15.2 La tesis (Luciano): el sistema debe reconocer que PUEDE desplazarse
El ser que quiere vivir no se queda comiendo donde no hay comida — **se mueve a buscar.** El bebé no mama del aire; busca el pecho.

El grafo=player debe **reconocer el desplazamiento como capacidad de su propio cuerpo** para romper el limitante de "solo come donde está":
- **Necesidad insatisfecha localmente** (hambre sin comida cercana) → el cuerpo se MUEVE a buscar.
- **Amenaza** (health baja por daño) → el cuerpo huye o se defiende.
- Es la conexión cuerpo-espacio: el sistema sabe que ES un cuerpo que ocupa un lugar y puede cambiar de lugar.

### 15.3 Diseño del mecanismo (0122)
El desplazamiento debe aparecer como respuesta a la necesidad NO satisfecha localmente. La idea clave: **cuando la acción con instinto de alimentación (eat) se intenta pero el recurso no está disponible (food no sube), el instinto de exploración/peligro debería redirigir el cuerpo a MOVERSE** — porque comer donde no hay no funciona, y el cuerpo sabe que puede cambiar de lugar.

Concretamente (a afinar):
- Detectar "estoy intentando satisfacer una necesidad pero el entorno no la provee aquí" (food no sube tras eat; o amenaza con health bajo).
- Ante eso, el instinto de desplazamiento empuja a las acciones de MOVIMIENTO (que ahora SÍ deben ganar peso relativo en el PPR, no como empuje sobre acciones no-viables sino como relego de las no útiles).
- El movimiento se vuelve un atractor cuando hay necesidad insatisfecha + recurso ausente localmente.

### 15.4 Pregunta abierta para el diseño del 0122
¿El problema es que el movimiento necesita ser "satisfactorio" primero (que el PPR lo considere viable), para que luego el instinto de exploración/peligro pueda empujar sobre él? Es decir: el moverse debe reducir algo (la incertidumbre de dónde está la comida, o la distancia a la amenaza) para que la vitalidad de las acciones de movimiento suba y dejen de ser ignoradas.

---

## 6. Regla de honestidad (sin cambios, reafirmada)

- No atribuir "querer" o "curiosidad" sin señal operativa correlacionada.
- Reportar AMBOS desenlaces pre-registrados.
- El negative control ejecuta cómputo real.
- Si el agente vive hasta morir de hambre sin comer, eso NO es un bug — es un dato sobre si hay (o no) querer operativo.