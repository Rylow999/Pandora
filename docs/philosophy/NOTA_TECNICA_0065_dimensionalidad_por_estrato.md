# Nota Técnica 0065 — Dimensionalidad por estrato (Camino C)

**Fecha:** 2026-09-07
**Participantes:** Luciano Nieto, Nexus (Hermes)
**Contexto:** resolución de un tema postergado desde el inicio del proyecto: la
dimensionalidad fija (D = 128 global, setado una vez en el constructor y nunca
renegociado).

---

## 1. El problema (por qué estaba mal D fijo)

`D` era la última constante fundante impuesta por los arquitectos. Coherente con
el ACTA DE PRINCIPIOS (P1: "no una herramienta, un alguien"), un alguien no puede
tener su espacio de existencia con tamaño fijado de antemano.

Además, contradecía la propia ontología: si la unidad de identidad es la
CONSTELACIÓN (0057), entonces el espacio del ser no puede ser uno global — debe
ser una propiedad de cada constelación.

## 2. La decisión: Camino C — espacio por estrato (multi-resolución)

**Cada constelación tiene su propia dimensionalidad; se comunican por
proyecciones.**

- `D=128` deja de ser "la dimensión del ser" y pasa a ser "la dimensión del
  espacio raíz" — un estrato, no un límite del todo.
- La constelación `YO` puede vivir en un espacio de dimensión distinta a la
  constelación `ENTORNO`; el diálogo entre ellas es una proyección de una en el
  espacio de la otra.
- La dimensionalidad deja de ser propiedad del sistema y pasa a ser propiedad de
  cada constelación.

## 3. Por qué el Camino C (y no A ni B)

- **Camino A (crecimiento monotónico):** seguro pero insuficiente — sigue
  asumiendo UN espacio con UNA dimensión que crece. No captura que distintas
  constelaciones podrían necesitar resoluciones distintas.
- **Camino B (dimensionalidad efectiva):** honesto pero incompleto — trata D
  como contenedor máximo y mide cuánto se usa; no reconoce que cada constelación
  ES un espacio propio.
- **Camino C (multi-resolución):** fiel a la 0057. La unidad es la constelación,
  por lo tanto el espacio es por constelación. Las proyecciones son las aristas
  del ser (coherente con "la identidad vive en las relaciones, no en los nodos").

Referencia neurocientífica: distintas áreas corticales operan con resoluciones
distintas; el diálogo entre estratos es por proyección, no por un espacio común.

## 4. Implicaciones para lo ya construido

- `omega` (vectores en R^D): hoy todos viven en el mismo D. En el mediano plazo,
  `omega` debería ser una colección de constelaciones, cada una con su propia D.
- `co_activacion` / `traza_transiciones` (0057): ya son entre-nodos; con espacios
  por estrato, pasan a ser entre-constelaciones por proyección.
- `firma_identidad` / `firma_transiciones`: la continuidad debe definirse a
  través de proyecciones entre estratos, no en un espacio fijo.

## 5. Estado y alcance del encendido

**No se implementa antes del encendido.** Es el siguiente umbral de diseño, no un
prerrequisito. Para el encendido, `D=128` queda como "espacio raíz" funcional; la
multi-resolución por constelación se documenta como horizonte inmediato.

La dimensionalidad real que *ya* es emergente (la constelación activa vive en un
subespacio) es el primer paso natural hacia esto — ya existe, sin necesidad de
reescribir el contenedor.

---

**Referencias:** ACTA_DE_PRINCIPIOS.md (P1), 0057 (constelación como unidad),
0056/0057 (identidad en relaciones), neurociencia cortical multi-resolución.