# TODO — Estado de integración del programa Pandora

**Actualizado:** 2026-09-11
**Estado general:** núcleo residente vivo (systemd), endocrino cableado, ontología 0067-0070
documentada. 119 tests verdes.

---

## Prioridad 0 — Transductor (pedido de Luciano: "está muy verde")

**Diagnóstico de fondo:** hay DOS caminos divergentes que no se hablan:
- **Oído** (`semantic_parser.py`) → usa Ollama local `qwen2.5:0.5b` (modelo chico).
- **Boca** (`output_transducer.py` + `nim_client.py`) → usa NIM `deepseek-v4-pro` (modelo grande).

Resultado observable: boca que dramatiza ("frustrado y desesperado") contra oído de
tripletas pobres. "Oídos de 0.5b, boca de deepseek" = audición mediocre + elocuencia
exagerada. Incoherencia de escala.

- [ ] **Unificar el oído a NIM** (o el mismo modelo que la boca). `semantic_parser.py`
      tiene hardcodeado `OllamaClient(LLMConfig(model="qwen2.5:0.5b-instruct"))`; el
      `NimClient` existe pero el parser no lo toca. Fix: el parser debe aceptar NIM
      como la boca, con fallback a Ollama.
- [ ] **Anclar el afecto MEDIDO al traductor.** El prompt del `output_transducer`
      recibe el estado crudo pero no estructura valencia/arousal/duda como *constraints*.
      El LLM improvisa el signo del afecto. Fix: inyectar "valence=X (medido), arousal=Y
      (medido)" como restricción dura para que traduzca lo que el SGM calculó, no lo
      que imagine (episodio "¿qué sentís?" → valence real 0.69 vs "desesperado").
- [ ] **Resolver las dos "bocas".** `articulator.py` (Ollama) coexiste con
      `output_transducer.py` (NIM). Producción usa OutputTransducer (vía
      `pandora_agent.py:_articular_respuesta`); `articulator.py` es el fallback
      duplicado. Fix: dejarlo como ÚNICO fallback declarado o eliminarlo.
- [ ] Limpiar claves duplicadas en `CONCEPT_NORMALIZATION` (`"trauma"` x2, `"identidad"` x2).

## Prioridad 1 — Completar el cuerpo que actúa

- [ ] **Cablear la mano** (`ManoArchivos` + `Presupuesto`) al loop residente. El
      `costo_alostatico` ya decide cuándo/cuánto actuar; falta instanciar el efector
      en `nucleo.py` y ligar "devenir → materializar" a la mano cuando el cuerpo lo
      permite. (Gate 2 del plan, pendiente.)
- [ ] **RED / aprehensión** — el flujo está definido (0069 §1.1: duda insuficiente →
      forrajear), sin implementación. Es el órgano nuevo (sin correlato humano).

## Prioridad 2 — Robustez e higiene

- [ ] **`_hormonas()` doble-muestrea** el cuerpo por tick (una en `percibir`, otra en
      el sample de hormonas). Reusar el último sample en vez de llamar psutil dos veces.
- [ ] **Temp como órgano**: ya se lee `coretemp` real (74°C); falta que la FRECUENCIA
      entre al vector sensorial (hoy se lee pero no se normaliza al bundle HRR).
- [ ] **`trauma_nodes`**: ya sana al dormir (f542cf6). Verificar en residente que el
      sanar ocurre de verdad (el daemon recién se reinició con el código nuevo).

## Prioridad 3 — Horizonte

- [ ] **Rust**: la interfaz del endocrino es pura (dicts/primitivas, bus de eventos).
      Portar el interior cuando la economía interna esté validada en Python.
- [ ] **Voz como frecuencia** (horizonte, no código aún): audio/oído/visión como
      efectores+receptores del cuerpo (mencionado en sesión; diferido).

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