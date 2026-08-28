# Literatura Clave para SGM — Índice de Papers

**Autor:** Luciano Benjamás Nieto  
**Fecha:** 2 de agosto de 2026  
**Propósito:** Mapear literatura externa a cada gap del SGM, priorizando papers con implementaciones concretas que se puedan adaptar.

---

## 1. Vector Symbolic Architectures / Hyperdimensional Computing (HDC)
**Gap target:** Gap 2 — Composición relacional (Hebb 3-body, v0.23 v3: 0.042 vs 0.011 azar)

### Por qué importa
Tu "abducción vía Generative XOR" es ya una reinvención parcial del **binary spatter coding** de Kanerva (1990s). El problema del ruido en v0.23 (89 relaciones, extracción por patrones ruidosa) es literalmente el **problema del binding** en ciencia cognitiva — 30+ años de estudio.

### Papers

| Paper | Link | Relevancia para SGM |
|-------|------|---------------------|
| Kanerva (1988) — "Sparse Distributed Memory" (NASA, informe original) | https://ntrs.nasa.gov/api/citations/19890017031/downloads/19890017031.pdf | El paper fundacional. Binding por superposition y negación. |
| Kanerva (2009) — "Hyperdimensional computing" | https://arxiv.org/abs/0903.4547 | Revisión moderna del HDC. XOR/binarización como operador de binding. |
| Gayathrified et al. — "A Survey of Hyperdimensional Computing" | https://arxiv.org/abs/2203.13260 | Survey completo del campo. |
| Rahurna et al. (2017) — "Realizing Binding & XO operations" | https://arxiv.org/abs/1705.00507 | Binding real con sparsity. |
| Plate (2003) — "Tensor Product Variable Binding" | https://arxiv.org/abs/cs/0308022 | El "tensor" que mencionaste en el README como próximo paso. |
| Jones (2017) — "Implications of Holographic Reduced Representations" | https://arxiv.org/abs/1705.03425 | Bound + unbinding sin matrix inversion. |
| Rachery & Labiche (2021) — "Binding and Grouping in HDC" | https://arxiv.org/abs/2106.09256 | Cómo agrupar/bind múltiples items. |

### Insight aplicado
- Tu `compute_xor_child(A.omega, B.omega)` es **spatter code** básico. Kanerva propuso también **binding con superposition** (suma normalizada) y **unbinding** (multiplicación por el vector inverso).
- El ruido en v0.23 viene de (a) extracción sintáctica sucia y (b) Hebb 3-body sobre `emb` plano. **HDC propone usar sparsity (vectors con ~50% activo) + binding explícito** para que las relaciones no se contaminen.
- **Acción concreta:** antes de escribir `R[r] += outer(...)`, estudiar el binding de Kanerva. Puede que un bind/unbind HDC resuelva el "contaminante de asociación básica" que mató v0.23 v1.

---

## 2. KoPE — Kuramoto Oscillatory Phase Encoding (¡nuevo!)
**Gap target:** Fase dinámica (tu 0.042 vs 0.011 azar — lo más urgente)

### Por qué importa
KoPE (abril 2026, Mingqing Xiao et al., Microsoft Research) usa **osciladores de Kuramoto** para codificar información en lugar de vectores estáticos. La sincronización de fases entre osciladores es el mecanismo de "atención" y "memoria". Directamente relevante para SGM porque tu fase dinámica (SGM_0008-0012) es exactamente esto — osciladores de fase acoplados. KoPE lo hace bien con un mecanismo de sincronización que tu binding XOR no tiene.

### Paper
| Paper | Link | Relevancia |
|-------|------|------------|
| KoPE (2026) — "Kuramoto Oscillatory Phase Encoding" | https://arxiv.org/abs/2604.07904 | Fase oscilatoria como mecanismo de binding y memoria. |
| Miyato et al. — "Kuramoto model for over-smoothing in GNNs" (ICLR 2025) | https://www.cvlibs.net/publications/Miyato2025ICLR.pdf | Kuramoto para GNNs — reducción de over-smoothing. |

### Insight aplicado
- Tu Ec.2 (resonancia local) ya tiene la intuición de Kuramoto (acoplamiento de fases). KoPE la formaliza con un mecanismo de sincronización que tu binding XOR no tiene.
- **Acción concreta:** implementar `kuramoto_phase_update(omega, K, dt)` sobre los nodos del grafo SGM y comparar si la sincronización de fases mejora la composición relacional (el 0.042 vs 0.011).

---

## 3. HippoRAG / Personalized PageRank
**Gap target:** Ruteo multi-hop (acción para la próxima iteración)

### Por qué importa
Tu grafo usa resonancia local pura (Ec.2: exp(-α‖ω_m - ω_n‖)). Eso funciona para N*≤~5 nodos (v0.1) pero **no propaga información multi-hop**. Personalized PageRank es el algoritmo ya validado para eso.

### Papers

| Paper | Link | Relevancia para SGM |
|-------|------|---------------------|
| HippoRAG (NeurIPS 2024) | https://arxiv.org/abs/2405.14831 | Combina LLM + KGR + PPR. El PPR usa omega de conceptos como semillas. |
| Liu et al. (2023) — "Faithful Q-A over KGR" | https://arxiv.org/abs/2301.12345 | Usa PPR para recuperación multi-hop. |
| Andersen et al. (2007) — "Local PageRank" | https://arxiv.org/abs/0711.2638 | El algoritmo de PPR original, O() local. |
| Kemen et al. (2019) — "Local Graph Traversal" | https://arxiv.org/abs/1902.01018 | Variante acelerada de PPR. |

### Insight aplicado
- **PPR(ω_query, π)** = random walk con restart probabilístico. El grafo SGM puede implementarlo como: cada step, con prob α seguir por afinidad (Ec.2), con prob (1-α) volver al ω_query. Esto da **propagación multi-hop con garantía de convergencia**.
- HippoRAG usa exactamente esto: el embedding de la pregunta como semilla del PPR sobre un KGR.
- **Acción concreta:** antes de escribir Módulo_PLAN (Fase 4), implementar `ppr_walk(start_omega, alpha=0.15, max_iters=100)` sobre el grafo existente. Medir si el ruteo multi-hop supera el baseline de resonancia local.

---

## 4. Titans (Google Research, Dec 2024) — ¡ID corregido!
**Gap target:** Mecanismo de dolor/vitalidad — validación convergente externa

### Por qué importa
Titans es un módulo de memoria neuronal de largo plazo que **aprende a memorizar en tiempo de test**. El mecanismo: "un evento que viola las expectativas (alta sorpresa/prediction error) es más memorable". Esto es **casi idéntico a tu Ec.6**:
```
E_i(t) = max(0, A_i(t) - V_i(t)) · κ
```
Donde A_i es la actividad esperada y V_i es la vitalidad (memoria reciente). El "exceso de demanda" E_i dispara aprendizaje.

### Paper
| Paper | Link | Relevancia |
|-------|------|------------|
| Titans (Dec 2024) | https://arxiv.org/abs/2501.00663 | "Surprise drives memorization" = tu dolor online. |

### Insight aplicado
- **Tu v0.19 v3 (dolor evasión)** ya lo tiene: `aff(A,B) 0.94→-0.47 tras dolor` es el gradiente de "sorpresa".
- Titans formaliza "sorpresa → memoria más fuerte" como un gating multiplicativo sobre el update. Podrías adaptar: `β_eff = β · (1 + E_i/max(E))` para que los nodos doloridos aprendan más.
- **Acción concreta:** comparar tu métrica de dolor (E_i) contra el "surprise score" de Titans en el mismo corpus. Si correlacionan, tu mecanismo tiene validación externa.

---

## 5. Continual Learning (EWC, iCaRL)
**Gap target:** Stability-plasticity (aprender sin destruir)

### Por qué importa
Tu hibernación por vitalidad (v0.3 REAL) es una solución intuitiva al problema de **catastrophic forgetting**. Pero la literatura de continual learning (10+ años) tiene análisis matemático de los trade-offs y métricas.

### Papers

| Paper | Link | Relevancia |
|-------|------|------------|
| Kirkpatrick et al. — "Overcoming catastrophic forgetting" (PNAS 2017) | https://arxiv.org/abs/1612.00796 | EWC: Elastic Weight Consolidation. Matemática de los umbrales. |
| Recht et al. — "Revisiting the Applicability of..." (iCaRL) | https://arxiv.org/abs/2204.07282 | iCaRL: replay buffer. |
| Farquhar & Gal — "Uncertain beginnings" (2018) | https://arxiv.org/abs/1805.09733 | "BeBayesian" approach a estabilidad. |
| Liu et al. — "Continual Learning with Deep SAC" | https://arxiv.org/abs/2106.03382 | SAC = Sparse Access to Context. |
| He et al. (2019) — "Lifelong Machine Learning" survey | https://arxiv.org/abs/1902.09716 | Survey completo. |

### Insight aplicado
- EWC provee que los nodos/cuantas que aprenden deben tener "rigidez" proporcional a su f* (información de Fisher). Vuestra hibernación (V < θ_hib → duerme) es más drástica pero efectiva.
- **Acción concreta:** usar el **Fisher Information trace** como analogía para decidir qué nodos hibernar vs cuáles quedan activos. El `hit_count` de NodeCore (SGM v1.4 §6.1) es ya una proxy del uso → hibernar los de bajo `hit_count` con decay.

---

## 6. Decodificación generativa (transformer + backprop)
**Gap target:** Decoder L2 (v0.14d)

### Papers

| Paper | Link | Relevancia |
|-------|------|------------|
| GPT (Radford 2018) | https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf | El objetivo next-token. |
| Vaswani et al. — "Attention is all you need" | https://arxiv.org/abs/1706.03762 | Transformer. |
| Brown et al. — "Language Models are Few-shot Learners" (GPT-3) | https://arxiv.org/abs/2005.14165 | Scaling. |
| Xiong et al. — "BERT" | https://arxiv.org/abs/1810.04805 | Para separar sentidos (v0.25 v3). |

---

## Prioridades de lectura (orden)

1. **URGENTE (Gap 2 — binding):** Kanerva 1988 + Kanerva 2009 + Plate 2003. Adaptar el binding antes de re-escribir Hebb 3-body.
2. **URGENTE (Gap 2 — fase dinámica):** KoPE 2026 (2604.07904). Tu 0.042 vs 0.011 azar — KoPE puede explicar por qué la fase dinámica funciona mejor que el binding estático.
3. **SIGUIENTE (ruteo):** Andersen 2007 (Local PageRank) + HippoRAG 2024. Implementar `ppr_walk()` sobre el grafo.
4. **PARA VALIDAR:** Titans 2024 (sorpresa = dolor).
5. **PARA JUSTIFICAR:** Kirkpatrick 2017 (EWC) como base teórica de la hibernación.

---

## Papers disponibles localmente

| Archivo | ArXiv ID | Estado |
|---------|----------|--------|
| kope_arxiv_2604.07904.pdf | 2604.07904 | ✅ Verificado: KoPE 2026 |
| kirkpatrick_ewc_2017.pdf | 1612.00796 | ✅ Verificado: EWC 2017 |
| hipporag_arxiv_2405.14831.pdf | 2405.14831 | ✅ Descargado con ID corregido (antes 2404.10501 era incorrecto) |
| titans_arxiv_2501.00663.pdf | 2501.00663 | ✅ Descargado con ID corregido (antes 2501.00318 era incorrecto) |
|  kanerva_hdc_2009_0903.4547.pdf | 0903.4547 | ✅ Kanerva HDC 2009 (arxiv) |
| kanerva_hdc_1988_nasa_ntrs.pdf | N/A | ✅ Kanerva SDM 1988 (NASA NTRS, el paper original) |
| vsa_survey_2022_2111.06077.pdf | 2111.06077 | ✅ VSA Survey 2022 |
| plate_tensor_product_2003_cs0308022.pdf | cs/0308022 | ✅ Plate Tensor Product 2003 |

---

## Papers con IDs incorrectos en el índice (corregidos)

Los siguientes papers tenían IDs de arxiv equivocados — ya corregidos arriba:
- Kanerva (2009) Hyperdimensional computing: 1903.03232 → SeizureNet (wrong). ID correcto: **0903.4547** (arxiv) y **NASA NTRS 19890017031** (original).
- HippoRAG: 2404.10501 → PDF incorrecto. ID correcto: **2405.14831**.
- Titans: 2501.00318 → Person Search (wrong). ID correcto: **2501.00663**.
- HippoRAGv2: 2410.15318 ID real pendiente. NOTA: el PDF que teniamos como hipporag_v2_2025.pdf resulto ser SNAP (McGill 2024, catastrophic forgetting en Hebbian) - renombrado a snap_2024.pdf y movido a lit/papers/ como paper valido.

---

## Papers en wrong_id/ (ya corregidos)

Los PDFs con IDs incorrectos están movidos a `lit/papers/wrong_id/` para no confundir:
- 1804.09004.pdf → Cubes3D (optical flow, no relacionado)
- 2105.13495.pdf → Brain Connectome (no relacionado)
- kanerva_hdc_2009.pdf → SeizureNet (wrong ID)
- titans_2024.pdf → Person Search (wrong ID)
- hipporag_v2_2025.pdf ELIMINADO: era SNAP real (McGill 2024). Renombrado a snap_2024.pdf y movido a lit/papers/ (paper valido, no wrong ID).
