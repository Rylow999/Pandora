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

## 4. Punto 2 (presente vs detrás del telón): PENDIENTE de revisar el código

Luciano: "habría que revisar bien lo que tenemos."

La hipótesis (Nexus, a verificar contra el sustrato real):
- "Presente" ≈ zona de alta interferencia I (Eq.7, nodos cognitivamente
  relevantes, I > θ_interf = 0.70) + phi_root. Es el correlato del Global
  Workspace de Baars (accesibilidad global).
- "Detrás del telón" ≈ constelaciones co-activadas por debajo del umbral de
  broadcasting, sosteniendo sin ser accesibles.

**A REVISAR:** si `campo_interferencia` + `phi_root` ya constituyen el presente,
o si hace falta un mecanismo explícito de "accesibilidad global".

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