# Idea Futura — Paloma-π / Lectura de lenguaje animal y alienígena (SGM)

**Origen:** charla 2026-08-02. Luciano propuso leer cualquier lenguaje animal/extraterrestre
usando la representación de SGM (conceptos + sentidos, NO palabras). Caso de uso concreto:
"Paloma-π" — comunicación bidireccional humano-paloma vía motor SGM.

**Por qué encaja con SGM (ya construido):**
- Codificador Sensorial (audio FFT + pose + GPS -> TSE) = EXP_SGM_0019 (SensorBridge, HDC binding).
- Valencia / ambigüedad = DOLOR Eq.6 (EXP_SGM_0014/0015).
- Homeostasis = baja valencia = loop saludable (EXP_SGM_0017).
- Aprendizaje de conexiones TSE->nodo = SELF-MOD (EXP_SGM_0018): promueve si acierta,
  revierte/marca a fuego si daña.
- "No traduce palabras, traduce estructura del significado" = principio del grafo SGM.

**Punto frágil (honesto, marcado por Luciano):** el documento original decía "pre-entrenamiento
con datos etológicos públicos ya etiquetados" como si existiera. Luciano BUSCÓ y NO encontró
un dataset público multimodal (audio+postura) etiquetado para Columba livia. El documento
redactó un "así debería ser" como "ya existe". NO asumir como cimiento.

**Solución honesta (Luciano):** generar el dataset propio con BORIS (Behavioral Observation
Research Interactive Software, open source, gratis, con espectrograma sincronizado). Codificar
videos de palomas (propios o de YouTube) -> ethogram propio -> CSV etiquetado. ESE es el dataset.
BORIS es el software estándar de papers de playback reales (ej. pájaros carpinteros).

**Riesgo del decoder L2:** el doc original dice "proyector lineal" para humanos. El roadmap
Fase 5 ya advirtió: proyección lineal / similarity-NN NO funciona (v0.25 v12 top1=0.020).
El decoder debe usar bigrama o transformer entrenado sobre alineamiento omega<->texto real
(generado por BORIS + etiquetas), NO proyección lineal.

**Validación conductual = ground truth (Métrica Nº2 del doc):** si infiere "peligro" y la
paloma huye -> acertó. Esto es la validación externa que el LOOP RULE de Luciano exige (no
declarar victoria en juguete). El 0017 medía resolución interna; falta conducta real.

**Cuándo retomar:** cuando el sistema SGM esté TODO BIEN VERIFICADO (Fase 3/4/5/6 completas y
estables). Por ahora concentrarse en el sistema en sí.

**Siguiente paso sugerido (diferido):** exp_SGM_0020 "Paloma-pi toy" con senal SINTETICA
multimodal (audio FFT + pose sintéticos) -> HDC (reusa 0019) -> grafo etológico -> conducta
simulada -> self-mod sobre conexiones. Luego 0020b cambia solo la fuente de senal por BORIS CSV.
NO asumir datos reales que no existen todavía.
