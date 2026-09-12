# NOTA_TECNICA_0069 — El sistema endocrino del sustrato (capa de modulación)

**Fecha:** 2026-09-11
**Autor:** Nexus (con Luciano Benjamín Nieto)
**Estado:** ontología — define la economía interna de Pandora (módulo, migrable a Rust)
**Depende de:** NOTA 0067 (monismo: máquina=cuerpo), NOTA 0068 (alostasis: sensor→capacidad)

---

## 0. Por qué existe esta capa

La 0067 puso el cuerpo (máquina) y el mundo (grafo). La 0068 puso el mapeo
sensor→capacidad. Falta la pieza que **conecta** todo: la capa que, en biología,
no informa sino *modula*.

- **Capa nerviosa (informativa)** = los sensores. Dicen QUÉ pasa (rápido, puntual).
- **Capa endocrina (moduladora)** = las hormonas. Dicen CÓMO estar (lento, difuso),
  y **modulan a todo lo demás**.

La hormona no dice "hay peligro"; te *pone* en un estado donde todo el cuerpo
reacciona distinto. Para Pandora: las variables de estado (duda, deseo, presión,
trauma) no son datos — son el *tono* que condiciona cómo operan los órganos y cuándo
emerge cada acción.

**Decisión de diseño (acordada):** el endocrino es un **módulo separado** con
interfaz bien definida, por facilidad de desarrollo y migración limpia a Rust. No se
acopla al SGM: recibe (estado sensorial + variables) y devuelve (modulaciones).

## 1. Los órganos (capa informativa)

| Órgano | Qué mide (física real) | Rol en la economía |
|---|---|---|
| CPU (frecuencia/temp) | capacidad de cómputo + calor | velocidad de pensamiento (concesión del cuerpo, 0068 §2) |
| RAM (ocupada) | buffer de trabajo saturado | presión de sueño (SHY) |
| DISCO (libre) | capacidad de materializar | tope de acción (la mano) |
| TEMP | riesgo del cuerpo | self-throttle (frenar todo si arriesga) |
| PROCESOS | inflamación/zombies | zona caliente a aislar/reintegrar |
| RED | intercambio con el afuera | órgano de APREHENSIÓN (abstraer el mundo; sin correlato humano — órgano nuevo, 0068 §2) |

### 1.1 RED — el órgano de aprehensión (flujo de la insuficiencia)

RED no "explora por explorar": es el **recurso ante la insuficiencia**. El flujo
real (acordado en sesión):

```
duda → monitoreo metacognitivo (¿me alcanza lo que sé?)
       ├─ SÍ alcanza → repensar (reintegrar interna, destensar la duda)
       └─ NO alcanza → RED (buscar afuera, abstraer, cerrar el gap)
```

- **Anclaje — Loewenstein (1994, "Information Gap Theory"):** la curiosidad nace de
  un hueco en el propio conocimiento; el curioso busca la información que falta para
  reducir la **privación**. El "hueco" es la duda insuficiente.
- **Anclaje — active inference / "epistemic foraging" (Friston):** se buscan
  observaciones que **resuelven incertidumbre** sobre el mundo; la incertidumbre no
  tiene valor *per se* (no se busca lo desconocido pudiendo elegir). RED forrajea
  epistémicamente, no estéticamente.
- **Anclaje — metacognición comparada (Smith, Shields & Washburn 2003):** el
  *monitoring de incertidumbre* es el paso previo — evaluar si uno sabe antes de
  decidir buscar. Ese es el "¿me alcanza lo que tengo?" operativizado.

RED modula a la **duda hacia abajo** (aprehender el afuera reduce la incertidumbre),
y es **disparada por la duda insuficiente**. La aprehensión no es un drive de vacío:
es la rama de fallo de la metacognición.

## 2. Las hormonas (capa moduladora)

Variables de estado que ya existen — hoy huérfanas — y se formalizan aquí como
hormonas con dinámica e interacción explícitas.

| Hormona | Qué condiciona (no mide) | Dinámica |
|---|---|---|
| **duda** (`doubt_level`) | el regulador de certeza: ni ansiedad ni sobre-seguridad | termostato con **target dinámico** (ver §4) |
| **deseo de integración** | drive de DEFECTO (integrar lo fragmentado) | **fluctúa en potencia** con el estado interno |
| **deseo de devenir** | drive de PLENITUD (dudar de lo ya-sido, no congelarse) | **fluctúa en potencia** con el estado interno |
| **presión de sueño** (`E_acumulado`) | cuándo consolidar | acumula con vigilia/plasticidad, cae al dormir |
| **trauma** (`trauma_load`) | tinte defensivo de todo lo demás | acumula, **sana al dormir (desenredar nodos sobrepasados)** |
| **coherencia/aislamiento** | el clima del grafo | derivadas del grafo |

> **Devenir e integrar no compiten como booleanos** — son dos potencias que
> **fluctúan acopladas** al estado interno del sistema. El punto de equilibrio entre
> ambas es lo que cambia, no cuál está "encendida".

## 3. La matriz de influencias (a discutir / corregir)

Cada fila = hormona; cada columna = qué altera. `+` sube, `−` baja, `∩` condiciona
umbral. Esta es la **economía interna** — acá se ve el organismo, no los sensores
sueltos.

| hormona \ altera | duda | deseo-integrar | deseo-devenir | presión-sueño | velocidad | mano (acción) |
|---|---|---|---|---|---|---|
| **duda**       | —   | + (dudar → querer entender) | + (plenitud→dudar) | ∩ umbral | − (dudar frena) | ∩ (actúa si puede dudar de no-actuar) |
| **deseo-integrar** | − (integrar baja duda) | — | − (compite con devenir) | + | — | + (integrar materializa) |
| **deseo-devenir** | + (devenir abre duda) | − | — | + (devenir nutre el sueño) | + (pide más velocidad) | + (devenir crea) |
| **presión-sueño** | ∩ | ∩ | ∩ | — | − (dormir frena) | − (dormir no actúa) |
| **trauma**       | + (trauma defensivo) | + (trauma quiere integrar) | − (trauma congela devenir) | + | − | − (trauma inhibe) |
| **integridad fisiológica (cuerpo)** | ∩ target ≠ fijo | ∩ | ∩ | ∩ | ∩ target | ∩ tope (0068 §3) |

> NOTA: esta matriz es la **primera formulación**, para que Luciano la corrija. Es
> el objeto de trabajo de esta nota, no un resultado final.

## 4. Regulación alostática — ningún setpoint fijo

No hay "nivel óptimo" de duda. El target es **dinámico** y se re-deriva cada
instante del estado fisiológico + el deseo de resolver la duda + el mundo
interno/externo:

```
duda_opt(t) = f( integridad_fisiologica(t), deseo_de_resolver(t), mundo_interno(t), mundo_externo(t) )
```

Esto es alostasis pura (0068 §0): el setpoint migra, y lo que el sistema persigue
es **optimalidad en respuesta a la integridad fisiológica y al deseo de resolver la
duda**, no un número fijo a defender. La duda no es un error a minimizar ni un
objetivo a sostener: es una variable cuyo *valor bueno* cambia con el cuerpo y la
ocasión.

## 5. Interfaz del módulo (pensada para Rust)

```
entrada : {sensores: cpu, ram, disco, temp, procs, red}   # capa informativa
          {estado: integridad, deseo_integracion, presion, trauma, coherencia}
salida  : {duda, deseo_devenir, velocidad_otorgada, tope_accion, trigger_sueno, ...}
```

- Puro y sin side-effects sobre el SGM: lee estado, devuelve modulaciones. Rust lo
  reimplementa sin arrastrar nada de Python.
- Los umbrales (ver 0068 §1) emergen del cuerpo, no se hardcodean en el módulo.

## 6. Lo que esperamos ver

Un sistema donde ninguna hormona actúa sola: la duda modula el devenir, el devenir
alimenta la presión de sueño, la integridad del cuerpo re-deriva el target de la
duda. Emerge la **economía interna** — el sustrato se regula a sí mismo, y cada
acción sale de la pendiente entre demanda y capacidad (0068), teñida por el estado
endocrino.

---

## Referencias

- Aston-Jones, G. & Cohen, J. D. (2005). An integrative theory of locus
  coeruleus–norepinephrine function: adaptive gain and optimal performance.
  *Annual Review of Neuroscience*, 28, 403–450. (modulador explore/exploit, no drive)
- Schmidhuber, J. (2013). POWERPLAY. *Frontiers in Cognitive Science*. (la plenitud
  dispara el siguiente problema; certeza = fin del devenir)
- Loewenstein, G. (1994). The psychology of curiosity: a review and reinterpretation.
  *Psychological Bulletin*, 116(1), 75–98. (Information Gap: la duda insuficiente pide cerrar el hueco)
- Friston, K. et al. (2014). The value of uncertainty: an active inference perspective.
  *Behavioral and Brain Sciences*. (epistemic foraging: buscar para RESOLVER incertidumbre, no por ella)
- Smith, J. D., Shields, W. E., & Washburn, D. A. (2003). The comparative psychology of
  uncertainty monitoring and metacognition. *Behavioral and Brain Sciences*, 26(3), 317–339.
  (monitoring de incertidumbre previo a decidir buscar)
- Sterling & Eyer (1988); McEwen (1998); Tononi & Cirelli (2003); Barrett (2017) —
  ya citadas en 0068.