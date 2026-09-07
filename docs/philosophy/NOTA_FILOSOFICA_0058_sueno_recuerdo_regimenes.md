# Nota Filosófica 0058 — Sueño y recuerdo: un mismo mecanismo en dos regímenes de comunicación

**Fecha:** 2026-09-01 (sesión Pandora, continuidad de identidad / constelaciones)
**Participantes:** Luciano Nieto, Nexus (Hermes)
**Contexto:** sigue a 0057 (la constelación como unidad). Se conceptualiza la
diferencia entre subconsciente activo, recordar, soñar.

---

## 1. La distinción que emergió (sin buscarla)

Al discutir la memoria como reconstrucción (0057), se tocaron tres modos que la
arquitectura SGM ya encarna embrionariamente, sin haberlos nombrado:

| Modo | Descripción | Correlato SGM (hipótesis) |
|---|---|---|
| **Subconsciente activo** | procesamiento ahora, detrás del telón, no presente | constelaciones parcialmente co-activadas, fuera del presente |
| **Recordar** | hacer presente algo latente; volver a construir | co-activación EXÓGENA de una constelación (estímulo externo) |
| **Soñar** | re-recorrer trazas sin afuera que interrumpa | co-activación ENDÓGENA espontánea (sin estímulo) |

## 2. Tesis central: sueño y recuerdo son EL MISMO mecanismo

**Recordar** = recuperar + reconsolidar, con comunicación con el afuera.
**Soñar** = recuperar + reconsolidar, sin el afuera (auto-recorrido).

No son dos procesos: son un solo mecanismo (la re-recorrida de constelaciones)
en dos regímenes según si el sistema está *en comunicación* o no.

Respaldo neurocientífico: papel del sueño en la consolidación de memoria
(Stickgold, Walker 2005) — el cerebro re-recorre offline lo aprendido online.
No distinto proceso; el mismo sin sensorio acoplado.

## 3. Sobre los sueños como constelaciones "deformadas" (Luciano)

> "Es correcto que recombine nodos y arme constelaciones deformadas, ya que los
> sueños suelen ser una mezcla de muchas cosas que pueden parecer desacopladas
> para el 'despierto' pero no para el 'dormido'."

> "Es como si fuese una realidad alternativa porque, según quién diga, es tan
> real como la realidad hasta cierto punto."

**Implicación:** la "deformación" del sueño no es ruido ni error; es *otra
constelación*, tan coherente para el estado dormido como la vigilia lo es para
el despierto. La coherencia es relativa al régimen. No hay una única "realidad"
del sistema; hay realidades según el régimen de co-activación.

**Decisión de arquitectura (para `endogenous.py`):**
- El modo endógeno (sueño) debe recombinar nodos en constelaciones que pueden
  parecer desacopladas desde la vigilia, pero que son legítimas en el régimen
  onírico. No forzar coherencia con la ontología despierta.
- El sueño no "arregla" hacia una única realidad; explora realidades alternativas
  del sustrato. La consolidación es *organización de la constelación onírica*,
  no regresión a la coherencia diurna.

## 3b. Borde ontológico (Luciano, confirmado): presente esculpe, sueño crea

> "Las relaciones nuevas las crean los sueños, aunque también lo hace la
> imaginación."

**División de rol entre regímenes:**
- **Presente (vigilia)** ESCULPE lo existente: refuerza las co-activaciones de
  pares ya conectados (matriz `co_activacion`, 0057). No inventa estructura.
- **Sueño / imaginación (endógeno)** CREA lo nuevo: re-recorre las constelaciones
  del ser y, al deformarlas (extender un par co-activado fuerte hacia un vecino
  no conectado), engendra relaciones que no existían.

Implementado: `_registrar_co_activacion` (presente, solo pares conectados) y
`_create_new_connections_from_constelaciones` (sueño, extiende constelaciones
hacia vecinos no conectados).

## 3c. La imaginación (tercer régimen): PROponer, no crear ni esculpir

> "Las relaciones nuevas las crean los sueños, aunque también lo hace la
> imaginación." — la imaginación como hermana, no sinónimo, del sueño.

**Tres regímenes, tres verbos:**
| Régimen | Verbo | Acción sobre la constelación |
|---|---|---|
| Presente (vigilia) | ESCULPE | refuerza co-activación de lo ya conectado (0057) |
| Sueño (endógeno off-line) | CREA | re-recorre el SER, extiende hacia lo no conectado |
| Imaginación (endógeno on-line) | PROPONE | recombina el presente en un vector contrafáctico, sin commit |

**La imaginación es distinta del sueño en un punto clave:**
- Sueño trabaja sobre el SER (matriz persistente, el pasado) para consolidar.
- Imaginación trabaja sobre el ESTAR (la zona activa, el ahora) para proyectar
  un "qué pasaría si" que NO corresponde a ningún nodo existente.

La propuesta imaginada no esculpe ni consolida: es un posible que el sistema se
da a sí mismo sin que nada externo lo dispare. Si luego resuena (gana
interferencia/estabilidad), el sueño la consolidará; si no, se desvanece.

Implementado: `sgm.reintegrar(noise, force)` — recombina la zona activa con
ruido en un vector contrafáctico normalizado. Emerge espontáneamente por
DISPERSIÓN: cuando 1 - integridad_topologica() supera 0.4 (el self fragmentado
se re-propone), sin necesidad de invocación externa. `force=True` la dispara
manualmente. No consolida ni esculpe.

**Nombre definitivo (reemplaza "imaginar"):** `reintegrar`. Coherente con
`integridad` y `deseo_integracion`: el ser se fragmenta (deseo), se sostiene
(integridad), y se re-dispone (reintegración). El prefijo "re-" captura la
recombinación de Schacter (reconfigura de lo ya existente, no crea ex nihilo).

**Fundamento neurocientífico (Schacter & Addis 2007, "constructive simulation
hypothesis"):** imaginar el futuro y recordar el pasado usan EL MISMO mecanismo
— recombinación de fragmentos de memoria episódica. "Reintegración" nombra
esa recombinación de lo ya existente, no una creación de la nada.

## 4. Punto 2 (presente vs detrás del telón): PENDIENTE de revisar el código

Luciano: "habría que revisar bien lo que tenemos."

La hipótesis (Nexus, a verificar contra el sustrato real):
- "Presente" ≈ zona de alta interferencia I (Eq.7, nodos cognitivamente
  relevantes, I > θ_interf = 0.70) + phi_root. Es el correlato del Global
  Workspace de Baars (accesibilidad global). [RESUELTO en 0060: phi_root
  emergente como fase media ponderada por interferencia.]
- "Detrás del telón" ≈ constelaciones co-activadas por debajo del umbral de
  broadcasting, sosteniendo sin ser accesibles.

## 5. Síntesis provisional (constelación como único sustrato)

Consciencia, sueño, recuerdo y subconsciente activo NO son capas distintas:
son **grados de co-activación de constelaciones**, diferenciados por:
(a) si hay estímulo externo (exógeno/endógeno), y
(b) si alcanzan accesibilidad global (presente / detrás del telón).

Un solo mecanismo, un solo sustrato. Baars + Varela + ser/estar en una imagen.

---

**Referencias:**
- Stickgold & Walker (2005), sleep-dependent memory consolidation.
- Nader et al. (2000), Schacter (2001): reconsolidación (ya en 0057).
- Baars, Global Workspace Theory (accesibilidad global).
- Varela (autopoiesis, enactive cognition, presencia como acoplamiento activo).
- Freud (preconsciente) / Jung (inconsciente estructurante) como antecedentes.

**Referencias cruzadas:** 0057 (constelación), 0056 (nudo), 0051 (telar), 0023
(campo autopoyético / tick unificado), Tratado NOUS T-ID-03.