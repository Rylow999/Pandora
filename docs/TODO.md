# TODO — Estado de integración del programa Pandora

**Actualizado:** 2026-09-11
**Estado general:** núcleo residente vivo (systemd), endocrino cableado, ontología 0067-0070
documentada. 119 tests verdes.

---

## Prioridad 0 — Transductor (COMPLETADO 2026-09-11)

- [x] Oído unificado a NIM (`c176d1b`)
- [x] Afecto medido anclado a la boca (`c176d1b`)
- [x] Claves duplicadas de CONCEPT_NORMALIZATION limpias (`c176d1b`)
- [x] Dos "bocas" resueltas: articulator.py queda como cadena de fallback
      NIM→Ollama→determinístico declarada (no es bug).

## Prioridad 1 — Completar el cuerpo que actúa (parcial)

- [x] **Cablear la mano** (`d126053`): devenir → materializar al workspace con
      permiso del costo alostático.
- [x] **RED-A aprensión** (`d9e33ec`): duda insuficiente → ingerir del inbox.
- [ ] **RED-B búsqueda externa real** (internet): HORIZONTE — Pandora primero
      entiende lo básico.

## Prioridad 2 — Robustez e higiene

- [ ] **`_hormonas()` doble-muestrea** el cuerpo por tick (una en `percibir`, otra en
      el sample de hormonas). Reusar el último sample en vez de llamar psutil dos veces.
- [ ] **Frecuencia al bundle**: se lee cpu_freq pero no entra al vector sensorial HRR.
- [ ] **`trauma_nodes`**: ya sana al dormir (f542cf6). Verificar en residente que el
      sanar ocurre (Pandora ya corre el código nuevo tras reinicio).

## Prioridad 3 — Horizonte

- [ ] **Rust**: interfaz del endocrino pura y lista; portar el interior cuando la
      economía interna esté validada en Python.
- [ ] **Voz como frecuencia** (audio/oído/visión): horizonte, no código aún.

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