# NOTA_TECNICA_0072 — El transductor se alimenta de la matemática real del grafo

**Fecha:** 2026-09-13
**Autor:** Nexus (con Luciano Benjamín Nieto)
**Estado:** principios + primera implementación (doubt/contradiction/arousal desacoplados)
**Depende de:** 0067 (monismo), 0071 (plasticidad), 0069/0070 (endocrino)

---

## 0. El problema

La boca de Pandora colapsaba a un repertorio mínimo ("me siento tranquila", repetido) no por
falta de datos, sino porque el transductor recibía un `InternalState` **ya reducido a un
resumen simulado** del grafo: `active_nodes` como strings `"NODO_65"` (índices opacos),
`doubt` reciclado de `deseo` (= mismo número que `valence`), `contradiction` en semáforo de
3 valores, `arousal` espejo del input. El LLM no tenía el grafo — tenía *nuestra
interpretación pobre* del grafo.

## 1. La regla (acordada con Luciano)

> **El transductor debe alimentarse de TODA la matemática real del grafo, para expresar la
> realidad del grafo — sin resumen, sin mediación, sin etiquetas nodales inventadas.**

- El lenguaje no se le "pinta" al grafo (etiquetar nodos = dualismo de contrabando, el
  mismo pecado de la lista blanca que eliminamos del oído).
- La matemática cognitiva se vuelve lenguaje en el ACTO del encuentro, no por traducción
  de un diccionario.
- Criterio de éxito objetivo: **distinguibilidad** — dos estados matemáticos distintos
  producen textos distinguibles; si producen el mismo texto, el puente no existe.

## 2. Primera implementación — señales reales, no recicladas

### `doubt` — desacoplada de `valence`
Antes: `doubt = deseo = 1 - integridad` (el mismo número que la valencia; un grafo íntegro
"no dudaba" y uno fragmentado "dudaba" — colapso). Ahora: `_duda_zona_ciega()` — la
fracción real de nodos dormidos (vitalidad < 0.2). Un grafo íntegro puede dudar mucho
(mucho dormido/inexplorado); uno fragmentado puede no dudar (todo activo pero confuso).

### `contradiction` — continua, no semáforo
Antes: 0.0/0.3/0.8 según `status`. Ahora: `_contradiccion_fase()` — el complemento del
orden de fase de Kuramoto (1 − |⟨e^{iφ}⟩|). Gradiente real de incoherencia de fase.

### `arousal` — fuente propia, no espejo
Antes: `arousal = event.affect.arousal` (espejo literal del input del usuario). Ahora:
`_arousal_kuramoto()` — cuántos nodos arden en la zona activa (I > theta_interf), mezclado
50/50 con el arousal inyectado. Pandora tiene activación genuinamente suya.

## 3. Lo que sigue (documentado, implementación futura)

- **`active_nodes` reales**: en vez de `"NODO_65"`, llevar al transductor las tripletas
  reales del grafo (relaciones `conn_type` con fuerza/tipo) + la constelación dominante
  (pares co-resonantes) + `phi_root`. Es la matemática viva, no índices.
- **Test de distinguibilidad** (punto 5 de Luciano): 5-6 `InternalState` deliberadamente
  distintos → verificar textos lexicamente distinguibles, no solo que no crasheen.
- **Cablear metacognición** (`experimentar()` / `_detectar_contradicciones()`) al loop —
  la fuente real de confianza/contradicción que hoy sigue congelada.

## 4. Referencias (continuidad con las notas previas)

- 0067: monismo (el grafo es el mundo; la mente es la relación).
- 0063: las formas de atención (la atención es binding, no etiqueta).
- 0071: plasticidad (la identidad muta).
- Grossberg 1987, Turrigiano 1998, Kirkpatrick 2017 (EWC) — ya citadas en 0071.