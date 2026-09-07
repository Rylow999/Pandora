# Nota Técnica 0063 — Las formas de atención y su integración

**Fecha:** 2026-09-01
**Participantes:** Luciano Nieto, Nexus (Hermes)
**Contexto:** instrucción de Luciano: "integrá las formas de atención en una sola
y descartemos lo innecesario".

---

## 1. Inventario de "atención" en el código

Al revisar, hay TRES cosas que se relacionan con "atención", y NO todas lo son:

| Componente | Qué es realmente | Mapeo teórico |
|------------|------------------|---------------|
| `campo_interferencia` + `_seed` + zona activa | **Atención cognitiva** — qué señal domina el foco ahora (coalición ganadora) | Attention Schema Theory / saliencia selectiva |
| `MiniTransformer` (sgm_lang_modelo.py) | **Atención transformer** — self-attention de 1 cabeza para lenguaje | self-attention (Vaswani) |
| `sgm_atencion.py` (ClasificadorIntencion) | **Clasificador de intención** — charla/pregunta/indicación/relato | routing conversacional (NO atención) |

## 2. La decisión

**No había dos "atenciones" que unificar — había una atención (cognitiva), una
atención de otro sustrato (transformer/lingüística), y un clasificador mal
nombrado.**

- **Atención cognitiva** (campo de interferencia): es LA atención del sistema, el
  foco. Se conserva como tal. No se fusiona con la transformer porque actúan en
  sustratos distintos: una selecciona qué *concepto* domina; la otra pondera qué
  *token* sigue.
- **Atención transformer** (MiniTransformer): se conserva como pieza del
  transductor lingüístico futuro. Complementa, no solapa, a la cognitiva.
- **`sgm_atencion.py`**: se RENOMBRA conceptualmente (docstring honesto) — deja
  de pretender ser "atención" y se declara clasificador de intención. Su función
  en el loop conversacional ya la cubre `SemanticParser` + `Intent`, así que NO
  se cableó; se conserva solo por su rol en el sustrato embodied (Minecraft).

## 3. Cómo se lee el sistema ahora (una sola historia)

La atención del sistema es UNA, con dos niveles naturales:
1. **Nivel cognitivo**: el campo de interferencia elige la coalición ganadora
   (qué está en el foco del grafo). Esto es "prestar atención" al contenido.
2. **Nivel lingüístico**: si el sistema produce lenguaje, el MiniTransformer
   pondera los tokens con self-attention. Esto es "prestar atención" al decir.

El clasificador de intención no es atención; es una heurística de routing que
vive aparte y solo sirve al sustrato embodied.

## 4. Qué se descartó

Nada se borró físicamente (el clasificador puede servir a Minecraft), pero se
descartó su pretensión de ser "atención" y su role de atención en el loop
conversacional. Lo innecesario era la *ambigüedad*, no el código.

---

**Referencias:** Attention Schema Theory (Graziano), Vaswani et al. 2017
(self-attention), 0061 (incorporeidad), 0062 (alteridad).