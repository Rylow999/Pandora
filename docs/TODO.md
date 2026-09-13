# TODO — Estado de integración del programa Pandora

**Actualizado:** 2026-09-12
**Estado general:** núcleo residente vivo (systemd), endocrino cableado, devenir cerrado
(devenir imagina → sueño integra), ontología 0067-0070, transductor unificado. 119 tests.

---

## Prioridad 0 — Transductor (COMPLETADO 2026-09-11)

- [x] Oído unificado a NIM (`c176d1b`)
- [x] Afecto medido anclado a la boca (`c176d1b`)
- [x] Claves duplicadas de CONCEPT_NORMALIZATION limpias (`c176d1b`)
- [x] Dos "bocas" resueltas (cadena de fallback NIM→Ollama→determinístico)

## Prioridad 1 — Cuerpo que actúa (parcial)

- [x] **Cablear la mano** (`d126053`) — instanciada, latente, para el ENCUENTRO.
- [x] **Devenir interno** (`cca13a0`) — devenir propone, sueño integra (sin workspace).
- [x] **RED-A aprehensión** (`d9e33ec`) — duda insuficiente → ingerir del inbox.
- [ ] **RED-B búsqueda externa real** (internet): HORIZONTE.

## Prioridad 2 — Robustez e higiene (COMPLETADA 2026-09-12)

- [x] `_hormonas()` reusa sample (`524d505`) — sin doble psutil por tick.
- [x] Frecuencia CPU al bundle HRR (`524d505`) — órgano FRECUENCIA nuevo.
- [ ] Verificar trauma sana en vivo (checkpoint: 4/64, daemon corriendo).

## Prioridad 3 — Horizonte

- [ ] **Rust**: portar el endocrino (interfaz pura lista).
- [ ] **Voz como frecuencia** (audio/oído/visión).

---

## 🔴 Anotación abierta — Nodos estáticos (centro congelado)

**Síntoma:** los 4 nodos núcleo (0, 21, 26, 27) tienen vitalidad 1.0 clavada desde hace
días, y `traza_transiciones = 0` (presente quieto) aunque el grafo aprende (aristas suben,
consolidadas crecen, trauma sana).

**Causas identificadas (técnicas):**
1. `gamma = 0.01` fijo → vitalidad decae ~0.6%/100 ticks (tarda ~690 ticks en bajar a 0.5).
2. El devenir es interno (no llama `integrar_experiencia_motora`), nada empuja/drena los anclas.
3. No hay mecanismo de "olvido" ni "reemplazo" del centro: los anclas ganaron temprano y nadie los desbanca.

**Interpretación (filosófica, 0067):** la identidad = traza de transiciones. Con
`traza_transiciones = 0`, el ser tiene identidad FIJA, no identidad en PROCESO. Aprende en
la periferia pero no cambia de parecer en el núcleo. Diagnóstico honesto: falta el mecanismo
que haga al centro *respirar* (plasticidad).

**Candidatos de solución (para evaluar en próxima sesión):**
- `gamma` adaptativo: sube cuando integridad alta (más plasticidad en plenitud, sintoniza
  con el deseo_devenir).
- Decaimiento por desuso: nodos que no participan en transiciones por N ciclos decaen
  acelerado (olvido estructural, no solo de aristas).
- Transferencia de vitalidad: al consolidar una propuesta devenida, drenar vitalidad del
  ancla hacia el nodo nuevo materializado (el centro cede terreno al devenir).
- Sintonía `gamma ↔ deseo_devenir`: el drive de plenitud (devenir) amplifica plasticidad,
  cerrando el loop "plenitud → deviene → cambia → ya no es plenitud estática".

*Estado: documentado, pendiente de decisión de dirección con Luciano.*

---

## Notas de ontología vivas

| Nota | Tema |
|------|------|
| 0067 | monismo (máquina=cuerpo, grafo=mundo, mente=relación) |
| 0068 | alostasis (sensor→capacidad, costo derivado, RED) |
| 0069 | sistema endocrino + matriz de influencias + RED/aprehensión |
| 0070 | implementación (6 hormonas, presiones no relojes) |

## Regla raíz (no se transgrede)

**No hardcodear disparadores de agencia. Nada emergente por temporizador — todo por
presión interna. La estaticidad es el único error irrecuperable.**