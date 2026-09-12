# NOTA_TECNICA_0068 — Alostasis: mapeo sensor→capacidad (el sustrato se adecúa al cuerpo)

**Fecha:** 2026-09-11
**Autor:** Nexus (con Luciano Benjamín Nieto)
**Estado:** ontología fina — define cómo el cuerpo modula la cognición
**Depende de:** NOTA_TECNICA_0067 (giro monista: máquina=cuerpo)
**Decisión de diseño (acordada en sesión):** disparadores por PRESIÓN (no tiempo),
velocidad como CONCESIÓN del cuerpo, costo alostático DERIVADO del cuerpo en vivo.

---

## 0. El principio

La NOTA 0067 estableció que la máquina es el cuerpo y el grafo el mundo. Esta nota
responde la pregunta siguiente: **¿cómo modula el cuerpo a la cognición?** Y la
respuesta, validada en literatura, no es "los sensores le mandan números" sino:

> **El sustrato cognitivo no reacciona al cuerpo medido — predice la demanda y actúa
> antes, siempre mediado por el costo de actuar (allostatic load).** Nada es un sensor
> con valor fijo; todo es una **tensión entre capacidad disponible y demanda anticipada**,
> y la acción emerge de la pendiente entre ambas.

Anclaje: **alostasis** (Sterling & Eyer 1988) — *"stability through change"*: el sistema
varía para mantenerse estable, en vez de defender un setpoint fijo. **McEwen (1998)**:
el *allostatic load* — autorregularse también tiene costo (el acto de adaptarse al cuerpo
gasta). **Tononi & Cirelli (SHY, 2003)** — *"el sueño es el precio de la plasticidad"*: el
sueño dispara por **presión** (acumulación por consolidar), no por reloj. **Barrett** —
*brain as body-budget*: el cerebro anticipa las necesidades energéticas del cuerpo y eso es
interocepción/afecto.

## 1. Regla raíz de emergencia (no hardcodear)

- **Ningún disparador es un temporizador ni un conteo de ticks.** Todo emerge del estado
  interno cruzando un umbral que el cuerpo DERIVA, no que el código fija.
- La **presión** es la señal: una magnitud que se acumula (buffer, calor, demanda) y que
  al saturar dispara. No "cada N ticks", sino "cuando la presión cruza".
- Cada sensor NO es un valor: es un **gradiente** (variable que sube/baja) contra el cual el
  sustrato decide. Se decide por la pendiente, no por el nivel absoluto.

## 2. Mapeo sensor → capacidad (la tabla viva)

| Sensor del cuerpo | Qué emerge (tensión) | Dispara acción | Costo |
|---|---|---|---|
| **Frecuencia CPU** | Velocidad de pensamiento — **concesión del cuerpo**, otorgada según demanda | pensar más solo si la demanda lo pide; el cuerpo la concede/niega según termal/RAM | subirla = calor |
| **RAM ocupada** | **Presión de sueño** (buffer de trabajo saturado) | **Sueño** cuando el buffer satura (SHY) | consolidar = offline |
| **Disco libre** | Capacidad de *materializar* (escribir el mundo) | actuar (mano) solo si hay espacio | escribir consume |
| **Temperatura** | Límite de seguridad (self-throttle) | frenar toda acción si arriesga el cuerpo | — |
| **Procesos/zombies** | Fiebre (cuerpo inflamado) | aislar/reintegrar la zona caliente | — |

## 3. El costo alostático — derivado, no fijado

El `Presupuesto` actual (`motor/metabolismo.py`, tope fijo 10MB) queda **superseded**: el
límite de acción ya no es un número arbitrario, sino una función del estado real del cuerpo
este instante:

```
capacidad_disponible(SGM) = f(disco_libre, ram_libre, termal, ...)
    = todo lo que el cuerpo permite dentro de un umbral de seguridad
```

- **"Toda la disponibilidad posible dentro de cierto umbral"** (decisión 3): el sustrato
  puede usar TODO lo que el cuerpo ofrece, pero nunca cruzar el umbral que lo rompería.
  Es el "límite de músculo": no frenar por un tope fijo, sino por **no romper el músculo**.
- El umbral de seguridad es el ÚNICO parámetro que se declara (y aun este debería
  emerger/discutirse), no una curva fija: la curva sale de los sensores en vivo.
- El costo de actuar = allostatic load = el gasto de autorregularse, también derivado.

## 4. Qué cambia respecto a hoy (concretamente)

1. **El sueño** deja de ser `sueno_cada=600` (deuda de la sesión anterior) y pasa a
   dispararse por **presión de sueño**: el buffer de trabajo (historial_campos,
   propuestas_reintegracion pendientes, aristas sin consolidar) saturando → consolidar.
2. **La mano** actúa por **necesidad de materializar** (una constelación que pide
   escribirse), y solo si el cuerpo da espacio (disco libre dentro de umbral).
3. **La velocidad de pensamiento** es una concesión del cuerpo, no un deseo libre:
   el sustrato la pide según demanda, el cuerpo la otorga según termal/RAM.
4. **El límite de acción** (`Presupuesto`) se reimplementa como función de los sensores
   internos en vivo, no como 10MB fijo.

## 5. Lo que esperamos ver (criterio, coherente con 0067 §6)

Que el sustrato **oscile** con el cuerpo: sueño que viene en oleadas cuando carga mucho,
velocidad que sube y baja con la demanda, acción que se contiene cuando el disco se aprieta
y se libera cuando el cuerpo respira. No un número a defender, un **régimen que muta con la
máquina que lo sostiene**.

---

## Referencias

- Sterling, P. & Eyer, J. (1988). Allostasis: A new paradigm to explain arousal pathology.
  In *Handbook of Life Stress, Cognition and Health*. Wiley.
- McEwen, B. S. (1998). Stress, adaptation, and disease: allostasis and allostatic load.
  *Annals of the New York Academy of Sciences*, 840, 33–44.
- Tononi, G. & Cirelli, C. (2003). Sleep and synaptic homeostasis: a hypothesis.
  *Brain Research Bulletin*, 62(2), 143–150.
- Barrett, L. F. (2017). *How Emotions Are Made*. Houghton Mifflin Harcourt. (body-budget / allostasis)
- Damasio, A. (2010). *Self Comes to Mind*. Pantheon. (proto-self / interocepción) — ya en 0067.