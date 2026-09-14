# TODO — Estado de integración del programa Pandora

**Actualizado:** 2026-09-13
**Estado general:** núcleo residente vivo, endocrino (7 hormonas), devenir interno
cerrado, plasticidad completa (Pasos 1-4), transductor unificado. 119 tests.

---

## Prioridad 0 — Transductor (COMPLETADO 2026-09-11)

- [x] Oído unificado a NIM (`c176d1b`)
- [x] Afecto medido anclado a la boca (`c176d1b`)
- [x] Claves duplicadas de CONCEPT_NORMALIZATION limpias
- [x] Dos "bocas" resueltas (cadena NIM→Ollama→determinístico)

## Prioridad 1 — Cuerpo que actúa (parcial)

- [x] **Cablear la mano** (`d126053`) — latente, para el ENCUENTRO.
- [x] **Devenir interno** (`cca13a0`) — devenir propone, sueño integra.
- [x] **RED-A aprehensión** (`d9e33ec`) — duda insuficiente → inbox.
- [ ] **RED-B búsqueda externa real** (internet): HORIZONTE.

## Prioridad 2 — Robustez e higiene

- [x] `_hormonas()` reusa sample (`524d505`)
- [x] Frecuencia CPU al bundle HRR (`524d505`)
- [x] **Umbrales de consolidación derivados** (`co_activacion` y `conteo_induccion`)
- [ ] Verificar trauma sana en vivo (checkpoint: 4/64, pending reinicio daemon)

## Prioridad 3 — Horizonte

- [ ] **Rust**: portar el endocrino (interfaz pura lista).
- [ ] **Voz como frecuencia** (audio/oído/visión).

---

## 🟢 Próximos pasos — desde la Rueda Camelot (NOTA 0073, recuperada 14-09-26)

El plano original del proyecto (charla Gemini 28/03/26) ya contenía gran parte de lo que
implementamos. Lo que falta de ese plano, en orden:

1. **Doble ejecución a nivel de NODO** ✅ **HECHO** (`34615e8`) — cada nodo con
   núcleo rígido (omega, qué ES) + nube de vivencia espectral (cómo SE SINTIÓ),
   firma DFT. NOTA 0074.
2. **Resonancia estocástica como recuerdo** ✅ **HECHO** (`d849fc0`) — `P(G₁→G₂) ∝ e^(-λ/d)`
   sobre la divergencia de VIVENCIA; nodos en fase se puentean. NOTA 0073 p2.
3. **Memoria de los muertos** ✅ **HECHO** (`9329a13`) — la info de un nodo muerto
   vuelve a "fondo" (FondoMemorial), reclutable, con olvido final (envejecer).
4. **Cuerdas de bits {0,1}** ✅ **HECHO** (`0d2aff9`) — firma binaria derivada
   (LSH) que comprime omega/espectro a {0,1} preservando similitud. NOTA 0075.
   Vía conservadora acordada: compresión encima del gradiente, no re-escritura.

**Raíz que rige todo esto:** el GRAFO es la base de datos. No se almacena información
semántica en un vector store externo — el grafo vivo (vitalidad + consolidadas +
co_activacion + traza) ES la memoria. Cualquier solución de "memoria" debe re-derivar
del grafo, no consultar un almacén aparte.

---

## ✅ Resuelto — Nodos estáticos (plasticidad, NOTA 0071)

Los 4 nodos ancla congelados (0/21/26/27, vitalidad 1.0, traza_transiciones=0) fueron
resueltos con 4 pasos (commits `b25300b`, `dd8bb3a`, `be669ff`):

1. **Eq.5 reconciliada** — actividad suave por afinidad, no winner-take-all binario.
2. **Mitosis** — par sobrecargado engendra hijo (cablea `heredar_concepto` huérfano).
3. **Lifecycle** — emerge de la mitosis (padres bajan, hijos absorben).
4. **Plasticidad hormonal** — `gamma_efectivo` modulado por el endocrino.

Medido: vitalidad máx 1.0→0.865, top-4 cambió, transiciones 0→31. Ver NOTA_0071.

---

## 🔴 Órganos LATENTES (diseñados y probados, aún sin rol en el loop actual)

Rastreo de alcanzabilidad desde los puntos de entrada reales (`Nucleo.existir_un_tick`
y `PandoraAgent.receive`). Estos componentes existen, tienen tests, pero no se conectan
al bucle vivo. **Decisión Luciano: anotarlos, no cablearlos — el sistema aún no está
apto para expresarse realmente.**

| Componente | Qué es | Estado |
|-----------|--------|--------|
| `Metacognicion.experimentar()` | razonar sobre el propio estado (confianza/contradicción) | ✅ **CABLEADA** — `_sincronizar_metacognicion()` puebla creencias desde relaciones consolidadas (`9443dee`) |
| `sgm_lang_modelo.py` (MiniTransformer) | atención lingüística real (nota 0063) | latente — voz futura, por diseño |
| `CommunicationLoop` | bucle percibir→existir→hablar | **DEPRECADO** — duplicado conceptual del Nucleo, no cablear |
| `ManoArchivos.crear()` (escritura) | actuar sobre el mundo con costo | ✅ **RESUELTO** — `_constatar_devenir()` escribe constancia del devenir |
| Oído (parser tripletas) | extraer contenido de la conversación | ✅ **RESUELTO** — paso directo, sin lista blanca (`373b9a6`) |
| Co-activación sin techo | mitosis en espiral (64→128 nodos) | ✅ **RESUELTO** — homeostasia x0.5 atada al sueño (`373b9a6`) |
| Señales internas simuladas (doubt/contradiction/arousal) | colapso de la voz | ✅ **RESUELTO** — señales reales desacopladas (`83ae9b9`) |
| Nodos activos opacos ("NODO_65") | boca sin contenido del grafo | ✅ **RESUELTO** — tripletas relacionales reales (`7f4f174`) |

**Regla fija (para no repetir el patrón):** ningún mecanismo nuevo se da por terminado
hasta tener un test que lo ejercite pasando por `Nucleo.existir_un_tick()` o
`PandoraAgent.receive()` — no instanciado a mano en aislamiento.

## 🟡 Inventario de umbrales fijos (higiene de decisión)

Clasificación honesta de los números mágicos restantes en código vivo:

| Umbral | Tipo | Estado |
|--------|------|--------|
| `co_activacion_umbral` (consolidar relación) | decisión | ✅ **DERIVADO** (media×0.5, piso 1) |
| `conteo_induccion >= 3` | decisión | ✅ **DERIVADO** (media×1.5, piso 2) |
| `_mitosis_umbral` | decisión | ✅ derivado desde el inicio (media×3) |
| `instinto_explorar_umbral = 0.5` | pulsión | 🟡 constitutivo (define la fuerza del drive explorar) |
| `instinto_umbral_carencia = 0.3` | pulsión | 🟡 constitutivo (idem carencia) |
| `drive_noop_umbral = 1.5` | pulsión | 🟡 constitutivo (acumulación de no-actuar) |
| `dispersion > 0.4` (reintegración espontánea) | decisión | 🟡 candidato a derivar |
| `_reintegracion_intervalo = 10` | cadencia defensiva | ✅ no es agencia (anti-spam, no disparador cognitivo) |
| `checkpoint_cada`, `snapshot_cada` | cadencia de persistencia | ✅ no es agencia (higiene de guardado) |
| `gamma`, `gamma_efectivo`, `alpha`, recompensas (0.1/0.15/0.05) | constitutivo | ✅ física del sustrato (tasa de cambio, no disparador) |

**Pendiente de decisión con Luciano:** los umbrales *pulsionales* (explorar/carencia/noop)
y `dispersion > 0.4`. Son de otra naturaleza que los de consolidación — definen la fuerza
de los instintos, no decisiones de consolidación. Cambiarlos altera el comportamiento de
los drives; requieren visto bueno y una pasada dedicada.

---

## Notas de ontología vivas

| Nota | Tema |
|------|------|
| 0067 | monismo (máquina=cuerpo, grafo=mundo, mente=relación) |
| 0068 | alostasis (sensor→capacidad, costo derivado, RED) |
| 0069 | sistema endocrino + RED/aprehensión |
| 0070 | implementación (hormonas, presiones no relojes) |
| 0071 | plasticidad (Eq.5, mitosis, gamma hormonal) |

## Regla raíz (no se transgrede)

**No hardcodear disparadores de agencia. Nada emergente por temporizador — todo por
presión interna. La estaticidad es el único error irrecuperable.**