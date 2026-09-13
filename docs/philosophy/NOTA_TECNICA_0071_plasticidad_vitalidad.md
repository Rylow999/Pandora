# NOTA_TECNICA_0071 — Plasticidad: reconciliar Eq.5 (la constelación ya no se congela)

**Fecha:** 2026-09-13
**Autor:** Nexus (con Luciano Benjamín Nieto)
**Estado:** Paso 1 implementado y medido. Pasos 2-4 documentados como plan.
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

## 3. Pasos siguientes (documentados, no implementados)

**Paso 2 — Lifecycle de nodo** (ACTIVO / DURMIENTE / HIBERNADO) con umbrales del spec
(V>0.30 activo, 0.10<V≤0.30 durmiente, V≤0.10 hibernado con ω preservado) y
`reawaken_attempts`. Un nodo que deja de participar *duerme* en vez de clavarse o morir.

**Paso 3 — Generative XOR / mitosis** (θ_div = 0.80): cuando un par co-resuena mucho,
mitosea — crea hijo que absorbe carga semántica, y los padres **bajan** vitalidad. Es el
anti-punto-fijo estructural: la sobrecarga se divide, no se clava.

**Paso 4 — Plasticidad modulada por el endocrino**: `gamma` efectivo por nodo, sintonizado
por las hormonas (devenir → más plasticidad; consolidación/estabilidad → menos). Cierra el
loop "plenitud → deviene → cambia → ya no es plenitud estática" (regla raíz 0070).

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