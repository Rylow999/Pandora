# PLAN DE TEST REAL — CRAFTER (Nivel 2, todo el stack SGM en conjunto)

**Fecha:** 2026-08-04  ·  **Autor:** Vega (Hermes) con Luciano  ·  **Estado:** PLAN DECIDIDO, PENDIENTE DISPOSITIVO
**Decisión:** Crafter REAL (baselines documentados) · Objetivo NIVEL 2 (descubrimiento sin recetas dadas) ·
probar TODO el stack SGM integrado ("Camino A" del roadmap realizado en Crafter).

---

## 1. POR QUÉ CRAFTER REAL Y NO EL MINI-GRID

El mini-grid de 0032/0033 era un juguete (llegar a la meta, evitar dolor). Crafter (Hafner 2021,
"Benchmarking the Spectrum of Agent Capabilities") es un mundo 2D procedural abierto donde el agente
debe: sobrevivir (vida/hambre), juntar recursos (madera, piedra, hierro, agua, comida), craftear
herramientas en cadena (madera->mesa->pico->piedra->hierro), construir, comer, y esquivar/pelear
monstruos con ciclo dia/noche. Tiene 22 LOGROS, observacion SIMBOLICA (entidades+pos, inventario,
vida/hambre, dia) ademas de píxeles, y REWARD por paso +1 por nuevo logro.

Ventajas para nosotros:
- **Memoria a largo plazo real:** recordar donde viste madera y volver. Ejercita omega persistente.
- **Planificación composicional (HRR):** "juntar madera -> mesa -> pico -> minar piedra" es cadena de
  relaciones anidadas. Justo lo cerrado en 0056/0059.
- **Dolor/valencia real:** perder vida, hambre, golpe de monstruo -> alimenta E (dolor) y aprendizaje
  por afinidad Eq.2.
- **Comparativas YA DOCUMENTADAS:** el paper y el repo crafter reportan baselines (random, PPO/IMPALA,
  DreamerV3) con metricas estandar (conteo de logros, largo de episodio, return). Eso nos da un piso
  honesto contra el cual medir, no humo.

---

## 2. NIVEL 2 — LA RESTRICCIÓN DE HONESTIDAD (nuestra red line)

El test solo prueba el sustrato si el agente DESCUBRE las recetas por interaccion (ensayo-error con
dolor/exploracion), NO si le damos el arbol de crafting. Dar el arbol = memorizar receta = la trampa
de 0056 (regla inyectada = 1.0 = mentira).

Por eso el objetivo es NIVEL 2:
- Las combinaciones (entidad, accion, contexto) que desbloquean un logro NUNCA se hardcodean.
- El descubrimiento se driver por: +1 de reward al nuevo logro, dolor (E) al perder vida/hambre, y la
  memoria HRR del SGM (recordar que (madera cerca de mesa + "do") -> nuevo estado).
- El SGM debe recomponer la cadena el solo, usando afinidad Eq.2 + presion de transmision (0056c) +
  memoria relacional (0056e).

NIVEL 1 (recetas dadas, solo USO) queda como negative control, no como objetivo.

---

## 3. INTERFAZ SGM <-> CRAFTER (el puente)

- **Percepcion -> HDC:** usar `crafter.Env(observations="symbolic")`. La obs simbolica (entidades con
  posicion, inventario, vida/hambre/dia) se proyecta a senal HDC via SensorBridge (phase3, 0019). NO
  usamos píxeles (caros, no aportan; la obs estructurada ya es HDC-friendly).
- **Decisión:** el tick SGM (modo RAZON/PLAN) rutea por PPR + planifica por HRR, y el DECODER entrenado
  (phase5/0056d-e) mapea el estado SGM -> accion de Crafter (17 acciones discretas: move/turn/do/place).
- **Retro:** reward de Crafter -> actualiza omega (Eq.1) y E (dolor, Eq.6). Logro nuevo -> senal de
  "novedad" que refuerza la traza HRR del (contexto->accion) que lo causo.

---

## 4. "PROBAR TODO EN CONJUNTO" (que mecanismos se ejercitan)

Integracion explicita de fases ya validadas, todas en un solo agente vivo:
1. NodeCore sustrato (omega/phi/V/E) — fase 0.
2. Modos tipados Sensorial/Razon/Plan — fase 1.
3. SensorBridge simbolico->HDC — fase 3.
4. Ruteo PPR + abduccion XOR + duda/contradiccion — fase 2.
5. Planificacion relacional HRR (0056e, 0027-0030) — fase 7.
6. Decoder entrenado (0056d-e) — fase 5.
7. Dolor/valencia online (E cambia la eleccion, no castigo post-hoc — regla #6 del roadmap).
Opcionales segun dispongamos: curiosidad (drive intrinseco, item 4 roadmap), continuidad de identidad.

---

## 5. METRICAS Y BASELINES (documentados, no inventados)

Metricas estandar de Crafter (las mismas del paper para comparar en igualdad):
- Conteo medio de LOGROS por episodio (0-22).
- Largo de episodio (supervivencia).
- Return acumulado.
- (Si hay curiosidad) tiles explorados / entropia de visita.

Baselines DOCUMENTADOS a citar (cifras exactas se toman del repo crafter + paper al arrancar el env):
- Random policy.
- PPO / IMPALA (reportados en el paper).
- DreamerV3 (si aplica a la version usada).
NUNCA afirmar mejora sin (a) misma metrica, (b) negative control (Nivel 1 vs Nivel 2), (c) varias
semillas.

---

## 6. CONTROLES NEGATIVOS (obligatorios, regla #7 del roadmap)

- **NC-A:** SGM con recetas DADAS (Nivel 1) vs SGM SIN recetas (Nivel 2) -> aislar aporte del descubrimiento.
- **NC-B:** politica RANDOM -> piso absoluto.
- **NC-C:** SGM sin dolor online (E fijo) -> aislar aporte de valencia.
- **NC-D:** SGM sin HRR (solo BoW plana) vs SGM con HRR -> aislar aporte de composicion (como 0056h/i).

---

## 7. DECISION PENDIENTE — DISPOSITIVO (lo decide Luciano)

El celular NO corre Crafter (requiere numpy + gymnasium + display; aca es stdlib puro sin pip). El
harness SGM es stdlib puro y SÍ es portable; lo que falta es el ENV Crafter + los deps. Opciones:
- (a) Máquina local de Luciano (Linux/Windows + Python + pip).
- (b) Google Colab (free/Pro) — numpy+gymnasium+pygame ya vienen o se instalan en 1 click.
- (c) Server propio.
Al definirse, el plan de ejecucion es:
  1. Crear env: `pip install crafter` (repo danijar/crafter).
  2. Portar el harness SGM (hrr_core, tick_relational_core, decoder, SensorBridge) tal cual (stdlib).
  3. Escribir el bridge simbolico->HDC y decoder->accion.
  4. Correr NC-A..D + baselines, registrar en experiment_registry.json con status honesto.
  5. Documentar resultados en este mismo doc.

---

## 8. REGISTRY

Se agrega entrada `exp_SGM_0052_crafter_nivel2` como PLANNED (no run) con objetivo, restriccion de
honestidad (Nivel 2, sin recetas) y la lista de mecanismos integrados. Al correrse en el dispositivo
elegido, se actualiza a RUNNING/PASS con metricas reales.

## 9. CONCLUSION

Crafter real + Nivel 2 + stack completo es el "Camino A" del roadmap hecho carne: el salto de mecanismo
aislado a agente que aprende del mundo, con comparativas documentadas y negative controls. El unico
pendiente es el dispositivo; el diseno y la restriccion de honestidad ya estan fijados.
