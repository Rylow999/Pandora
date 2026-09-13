# NOTA_TECNICA_0071 — Plasticidad: reconciliar Eq.5 (la constelación ya no se congela)

**Fecha:** 2026-09-13
**Autor:** Nexus (con Luciano Benjamín Nieto)
**Estado:** Pasos 1 y 3 implementados y medidos. Paso 2 (lifecycle) emerge de la mitosis.
Paso 4 (plasticidad endocrino) documentado como plan.
**Depende de:** 0067 (monismo), 0068 (alostasis), 0069/0070 (endocrino, devenir)

---

## 0. El problema

El centro del grafo quedó congelado: los nodos 0, 21, 26, 27 con vitalidad 1.0 clavada
durante días, `traza_transiciones = 0` (presente quieto), aunque el grafo aprendía en la
periferia (aristas y consolidadas crecían). Diagnóstico: **elegimos estabilidad perfecta
sin plasticidad** — el dilema estabilidad-plasticidad (Grossberg 1987) resuelto de un solo
lado.

## 1. La causa raíz (encontrada en nuestra propia especificación)

`docs/architecture/Arquitectura_Pure_L2_Pandora.md` (Eq.5, línea 65) dice:

> `Vᵢ(t+1) = Vᵢ(t)·e^(−γ) + Aᵢ(t)·(1−e^(−γ))`, donde `Aᵢ = "fracción de cadenas visitando el nodo i"`.

`A` debía ser una **actividad distribuida y gradual**. La implementación Python lo redujo a
winner-take-all duro:

```python
A = 1.0 if i in top_k else 0.0   # top_k = seed + 3 vecinos más cercanos
```

Un flag binario. El seed ganaba siempre (input constante), se clavaba en 1.0, y sus 3
vecinos se le pegaban. El centro no tenía con qué ser destronado.

**Conclusión:** no había que inventar nada nuevo — la solución ya estaba en el spec
fundacional (2025), escrita para Rust, y el Python se desvió.

## 2. Paso 1 (IMPLEMENTADO) — `A` suave por afinidad, no flag binario

`decaer_vitalidad()` ahora computa `A_i = exp(−α·‖ω_i − ω_seed‖)` — afinidad semántica
decreciente con la distancia (Eq.2), en vez de `A ∈ {0,1}`. El seed sigue dominando, pero:

- los nodos semánticamente cercanos **respiran** (reciben actividad gradual),
- el ganador puede ser **destronado** si otra zona gana afinidad,
- se recupera **rango dinámico** (Turrigiano 1998: synaptic scaling — el que gana mucho
  deja de saturarse, escala hacia abajo solo).

**Medición (input variado, 60 ticks, N=32):**

| Métrica | Antes (binario) | Después (suave) |
|---------|-----------------|-----------------|
| vitalidad máxima | 1.000 clavada | **0.865** |
| top-4 vitalidad | [0,21,26,27] fijo | **[18,29,0,7] (cambió)** |
| transiciones | 0 | **31** |
| seeds visitados | 1 | **5** |

El centro respira sin olvidar (γ sigue en 0.01, conservador). Plasticidad recuperada sin
riesgo de olvido catastrófico (McCloskey & Cohen 1989; contraparte EWC, Kirkpatrick 2017).

## 3. Estado de los pasos

**Paso 1 — IMPLEMENTADO (commit `b25300b`).** `A` suave por afinidad. Centro respira.

**Paso 2 — Lifecycle.** EMERGE de la mitosis: cuando un par engendra hijo, los padres
bajan vitalidad (duermen naturalmente) y el hijo absorbe. No se formaliza como lista de
estados con umbrales propios — sería reintroducir constantes. El "dormir" ya es el
decaimiento natural de un nodo que deja de participar (Paso 1).

**Paso 3 — IMPLEMENTADO (commit `dd8bb3a`).** Mitosis por co-resonancia:
- `_mitosis_umbral()`: umbral DERIVADO = media de co_activacion × 3 (no hardcode).
- `_engendrar_hijo(a,b)`: reusa `heredar_concepto` (Eq.11, ya existía huérfano), conecta
  hijo a ambos padres, padres bajan ×0.7, resetea co-resonancia del par.
- Verificado: par forzado engendra hijo (16→17 nodos), padres bajan 1.0→0.7.
- Honesto: con input variado 200 ticks NO emerge espontáneamente (el umbral ×3 es
  conservador y la actividad ya distribuida por el Paso 1 evita la saturación). Es el
  fusible estructural, no un loop constante. Se activará ante input "picoso" (un mismo
  tema muy repetido, o un mundo con dominantes claros).

**Paso 4 — IMPLEMENTADO (commit `be669ff`).** Plasticidad modulada por el endocrino:
- SGM: `gamma_efectivo` (modulable) + `set_plasticidad(nivel)`. `decaer_vitalidad`
  usa `gamma_efectivo`, no el `gamma_nodo` fijo. Rango acotado [gamma×0.2, gamma×5].
- Endocrino: hormona `plasticidad` = 0.5 + 0.5·devenir − 0.5·consolidación
  (Grossberg 1987: el balance se resuelve modulando, no eligiendo extremo).
- Loop residente aplica plasticidad al SGM tras cada tick endocrino.
- Verificado: devenir alto → plasticidad 0.40 (gamma 0.01→0.021); consolidando → 0.08.

Con esto, la plasticidad dejó de ser un gamma fijo: ES una hormona. El loop
"plenitud → deviene → cambia → ya no es plenitud estática" queda cerrado.

## 3b. Detalles detectados y RESUELTOS (higiene)

Dos umbrales de decisión quedaban con número fijo; se DERIVARON (mismo principio
que `_mitosis_umbral`):
- `co_activacion_umbral = 3` → `_umbral_consolidacion()`: media×0.5, piso 1. ✅
- `conteo_induccion >= 3` → `_umbral_induccion()`: media×1.5, piso 2. ✅

Quedan como CONSTITUTIVOS (no son disparadores de agencia, definen la física del
sustrato o la fuerza de pulsiones): `instinto_explorar_umbral`, `instinto_umbral_carencia`,
`drive_noop_umbral`, `gamma`, recompensas. Inventario completo en `docs/TODO.md`.

## 4. Referencias

- Grossberg, S. (1987). Competitive learning: from interactive activation to adaptive
  resonance. *Cognitive Science*, 11(1), 23–63. (dilema estabilidad-plasticidad)
- Turrigiano, G. G., et al. (1998). Activity-dependent scaling of quantal amplitude in
  neocortical neurons. *Nature*, 391, 892–896. (homeostatic plasticity / synaptic scaling)
- McCloskey, M. & Cohen, N. J. (1989). Catastrophic interference in connectionist networks.
  *Psychology of Learning and Motivation*, 24, 109–165.
- Kirkpatrick, J., et al. (2017). Overcoming catastrophic forgetting in neural networks.
  *PNAS*, 114(13), 3521–3526. (EWC: consolidación asimétrica de plasticidad)
- Spec interna: `docs/architecture/Arquitectura_Pure_L2_Pandora.md` (Eq.5, lifecycle, XOR).