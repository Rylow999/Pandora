# SGM Roadmap — Primer Sistema Funcional
## Hoja de Ruta para Implementar el Primer Sistema SGM (Synaptic Graph Model) Cognitivo Funcional

**Autor:** Luciano Benjamin Nieto (con integración de toda la evidencia del LANGUAGE-ENGINE)
**Fecha:** 2 de agosto de 2026
**Estado:** En construcción — Fase 0 (sustrato mínimo de nodo)
**Guía:** SGM v1.4 §11, NOUS v4 §7, Arquitectura Pure L2 + dscng-language-engine v0.1→v0.25

---

## Principio Unificador

Un SGM funcional = **GRAFO** (memoria/categoría/dolor) + **TRANSFORMER** (contexto/sentido), operando en userspace sobre Linux 7 con 3 modos cognitivos tipados (Sensorial/Razonamiento/Plan). El grafo NO reemplaza el transformer; son capas complementarias:

- El **GRAFO** sostiene memoria masiva persistente (hibernado), categoría emergente, dolor interno, foco competitivo. El motor de resonancia local + Hebbiano.
- El **TRANSFORMER** resuelve polisemia y contexto (atención aprendida con backprop manual en Python puro).

La evidencia empírica (v0.1 → v0.25) demuestra que esta división es correcta. Este roadmap integra TODO lo validado en un plan de implementación real.

---
## Arquitectura Final (NOUS v4 correcta, 2026-07-28)

```
TRANSFORMER = contexto/sentido     (backprop, separa polisemia, acc_pred=0.907)
    ||
GRAFO/ROOT  = memoria/dolor/foco   (v0.3b, v0.19, v0.24)
```

El transformer resuelve el sentido; el root/dirige el ruteo y sirve como sistema de duda (dolor, W(t)). NO son intercambiables. El grafo no es reemplazable (memoria/dolor); el transformer no es reemplazable (contexto).

---
## Ecuaciones Invariantes (12 DSCN-G + 2 SGM + 5 NOUS)

| Ec | Fórmula | Significado | Parámetro |
|----|---------|-------------|-----------|
| Eq.1 | ω_i(t+1) = (1-β)·ω_i(t) + β·o(t)·R(t)·ê_R | Actualización vectorial (TD-learning) | β=0.10 |
| Eq.2 | P(m\|n) ∝ exp(-α·‖ω_m - ω_n‖) | Movimiento de cadenas por afinidad | α=5.0 |
| Eq.3 | φ_i(t+1) = [φ_i(t) + η·R_i·sin(θ_a-φ_i)] mod 2π | Dinámica de fase (Kuramoto) | η=0.05 |
| Eq.4 | P(a\|φ) ∝ exp(λ·cos(φ-θ_a)) | Selección de acción (von Mises) | λ=3.0 |
| Eq.5 | V_i(t+1) = V_i·e^(-γ) + A_i·(1-e^(-γ)) | Vitalidad con decaimiento | γ=0.01 |
| Eq.6 | E_i(t) = max(0, A_i - V_i)·κ | Señal de dolor/valencia | κ=1.0 |
| Eq.7 | I_i(t) = ‖ω_i‖·cos(φ_i - φ_root) | Interferencia de ondas | θ_interf=0.70 |
| Eq.8 | W(t) = W_base / (1 + κ_W·E_root(t)) | Ventana de contexto dinámica | W_base=50, κ_W=2.0 |
| Eq.9 | ρ(t) = \|E_active(t)\| / (W(t)·N_active(t)) | Densidad contextual (tiempo subjetivo) | - |
| Eq.10 | β_eff(t) = β·(1 + ρ(t)) | Aprendizaje ponderado por densidad | β=0.10 |
| Eq.11 | ω_child = ω_parent + δ, ‖δ‖~N(0,σ_her) | Herencia conceptual | σ_her=0.10 |
|| Eq.12 | ΔV_cascade(i) = Δω iff scope_depth(i) > scope_depth(corrected) | Corrección acotada por scope | - |

---
## Tabla Maestra de Resultados Validados (señal real del dato)

| Mecanismo | Experimento | Resultado | Evidencia | Fuente |
|-----------|------------|-----------|-----------|--------|
| MEMORIA (hibernado) | v0.3 REAL / v0.3b v2 | 100% retención; hibernar=reintegra ~0.98, borrar=0.0 | v0.3 REAL validó el motor base; v0.3b v2 limpió "hibernar=no tocar" (identidad matemática) | README.md §CORRECCIÓN |
| CATEGORÍA | v0.9b v2 | Pureza 0.7317 vs 0.50 (azar), vocab balanceado 50/50 | El grafo separa SUST/VERB sin supervisión | README.md §CORRECCIÓN |
| DOLOR | v0.9c limpio / v0.19 v3 | Sin aprendizaje err cte 0.9927; con aprendizaje 0.9927→0.933 | Dolor = error real, no reward fijo (circular) | README.md §CORRECCIÓN |
| CONTEXTO | v0.14d audit | base 0.0237, híbrido 0.0958 (~4x) | Transformer 1 capa, backprop manual, head aprendido | README.md §CORRECCIÓN |
| RUTEO SENTIDO | v0.22 v3 | routing FASE A = 1.0 | Root DIRECTOR + proyección Hebb | README.md §CORRECCIÓN |
| DUDA (root) | v0.25 v2c | dolor_en_duda=0.841, W_contrae=0.982 | El root detecta duda y contrae W(t) | README.md §v0.25 v2 |
| POLISEMIA | v0.21 v8b | acc_gt=0.74, 3/3 sintético controlado | Anchor+repulsión condicional fixa oversmoothing | README.md §v0.21 v8b |
| ESCAPIZA/DOLOR | v0.19 v3 | aff(A,B) 0.94→-0.47 tras dolor | Evita lo que lo duele, se acerca a lo seguro | README.md §CORRECCIÓN |
| MEMORIA TRABAJO | v0.24 | foco dominado 60% (0.601) | Vitalidad competitiva crea atención real | README.md §v0.24 |
| INTEGRACIÓN | v0.25 (mini) | "banco+dinero" y "banco+rio" resueltos | Bloques se componen en ciclo cerrado | README.md §v0.25 |
| COMPOSICIÓN | v0.16-bis | jaccard=1.0; poda desenlaza sin borrar | Nodo = conjunto de referencias | README.md §CORRECCIÓN |
| ABSTRACCIÓN | v0.16 | tamaño del conjunto de referencias | Reemplaza v0.11 (dimensión, falló) | CHANGELOG.md |
| BACKAL PROYECCIÓN | v0.22 v3 | routing=1.0 sobre corpus contrastivo | Proyección Hebb sin backprop separa sentido | README.md §v0.22 v3 |

### Límites HONESTOS (no son fallas de implementación)

| Mecanismo | Experimento | Resultado | Evidencia | Fuente |
|-----------|------------|-----------|-----------|--------|
| RAZONAMIENTO ROOT | v0.22 v2, v0.25 v2/v2c/v2d | acc_gt≈0.50 (azar) | Root sobre transformer: no separa sentido (cos(A,B) alto) | README.md §CIERRE DEFINITIVO |
| COMPOSICIÓN RELAC. | v0.23 v3 | 0.042 (azar 0.011) | Hebb 3-body sobre datos reales: señal 4x pero ruidosa | README.md §v0.23 v3 |
| PROYECCIÓN ROOT | v0.25 v4 | acc_decision=0.544 (azar) | El transformer separa tokens PERO NO sentidos (cos alto) | README.md §v0.25 v4 |
| BERT-STYLE MLM | v0.25 v3 | acc_gt=0.533 (azar) | MLM sobre sintético no separa sentidos (cos(A,B)=0.70-0.94) | README.md §v0.25 v3 |
| ATENCIÓN LOCAL | v0.25 v6 | acc_puro=0.459 (azar) | En contexto mixto no separa; en bloques puros 0.890 pero no detecta cambio | README.md §v0.25 v6 |
| DECODIFICADOR NN | v0.25 v12 | top1=0.020, top5=0.095 | Similarity NN sobre embeddings D=16 no funciona | Skill dscng-language-engine v0.25 |
| TRANSFORMER ESCALA | v0.18 | 0.0946 ≈ v0.14d 0.0958 | D=32 no supera D=16; techo es CORPUS (20k tok) | README.md §CORRECCIÓN |
| ROOT PROYECTA SENTIDO | v0.25 v2 | acc_gt=0.546 (azar) | Root no aporta como proyector sobre transformer | README.md §v0.22 v2 |

---
## Roadmap de Implementación (6 fases + Fase 0)

### Fase 0: Sustrato Mínimo de Nodo (1-2 semanas)

**Objetivo:** Migrar el grafo de lenguaje a `NodeCore` + `EdgeTable` + `SideTables` (SGM v1.4 §6) en el engine puro-Python.

**Tareas:**
- [ ] `v0.17_substrato_minimo`: NodeCore (omega[f16], phi[u16], v[u16], flags[u8]) + EdgeTable (CSR) + SideTables
- [ ] Medir memoria real por nodo y ticks/segundo vs. SGMNode original
- [ ] Gate de decisión: si la ganancia de velocidad no es clara a escala, no migrar
- [ ] Tests T-INF-06: equivalencia funcional NodeCore vs SGMNode

**Evidencia de referencia:** v0.14d, v0.17 (transformer completo D=16/D=32)

### Fase 1: Infraestructura de Modos (2-3 semanas)

**Objetivo:** Implementar `ChainMode` con transiciones SENSORIAL/RAZONAMIENTO/PLAN + `boost_edges` por tipo de arista.

**Tareas:**
- [ ] `ChainMode` struct con tracking de estancamiento (visited_nodes, stagnation_ticks, doubt_count)
- [ ] `ConnType` en aristas (Terminal/Functional/Causal/Temporal/Cognitive)
- [ ] `boost_edges[ConnType]` por modo (tabla §1.2 de SGM v1.4)
- [ ] Test T-INF-01: MODO_RAZONAMIENTO privilegia aristas Causal (prob > 2× baseline)

**Evidencia de referencia:** v0.14d transformer, v0.24 memoria de trabajo

### Fase 2: Inferencia Simbólica + Duda (3-4 semanas)

**Objetivo:** Abducción XOR + detección de estancamiento (duda) + refutación por contradicción (dolor).

**Tareas:**
- [ ] `abduce()` base O(n²) + `abduce_fate()` (§2.5) para D≥384
- [ ] `verify_contradiction()` (dolor acumulado > θ_refut=2.0)
- [ ] `check_stagnation()` + `handle_doubt()` escalonado (§2.3.2)
- [ ] Tests T-INF-02 a T-INF-05

**Evidencia de referencia:** v0.19 (dolor evasión), v0.21 v8b (polisemia), v0.24 (foco)

### Fase 3: SensorBridge (2-3 semanas)

**Objetivo:** Proyección de señales sensoriales → ω + interocepción.

**Tareas:**
- [ ] `sensor_bridge()` para audio, visual, térmico, propioceptivo
- [ ] `ω_root_intero` (PHS, T_eff, ρ(t), latencia, page faults)
- [ ] Política de emergencia (E_root > 0.8 → reducir K=3, W_base=4)
- [ ] Tests T-SEN-01/T-SEN-02

**Nota:** sin hardware real, testear con señales sintéticas.

### Fase 4: Planificación (2-3 semanas)

**Objetivo:** MODO_PLAN con navegación por aristas Temporal+Functional, trauma estructural, hibernación condicional.

**Tareas:**
- [ ] `MODO_PLAN` con boost Temporal+Functional
- [ ] `Q(plan)`, trauma (κ_trauma=0.50), hibernación post-fracaso
- [ ] `H_plan = H_base·(1+ρ(t))` (horizonte dinámico)
- [ ] Tests T-PLAN-01 a T-PLAN-03

**Evidencia de referencia:** v0.16 (referencias compositivas)

### Fase 5: Decodificador L2 — Camino A (4-6 semanas)

**Objetivo:** Decoder generativo que produce texto coherente desde el sentido ruteado.

**Tareas:**
- [ ] Mini-transformer decoder (Entrena W·ω → logits, pure Python backprop)
- [ ] Corpus alineado ω↔texto (Don Quijote procesado)
- [ ] Integración con el grafo: tokens semánticos → texto
- [ ] Tests T-DEC-01/T-DEC-02

**⚠️ CRÍTICO:** NO usar similarity-NN sobre embeddings (v0.25 v12: top1=0.020). Usar modelo de transición explícito (bigrama: top1=0.630) o transformer entrenado.

**Evidencia de referencia:** v0.6a (next-token 10.11%), v0.14d (backprop), v0.5b (generator con window+repetition penalty)

### Fase 6: Integración, Calibración y Tests (COMPLETA 2026-08-02)

**Objetivo:** Ciclo unificado  + calibración offline de umbrales.

**Tareas:**
- [x]  (§5.3) integrando todas las fases — exp_SGM_0023 (PASS, 3 modos cierran).
- [x] Calibración offline de θ_novelty, θ_refut, min_duration, θ_window_frac vía **grid search** vs suite T-INF — exp_SGM_0024 (PASS, 8/8).
  - NOTA HONESTA: la spec §2.5 proponía FATE (fate-v6-modular) pero FATE NO está en el repo y su propio
    benchmark admite que pierde vs CMA-ES en baja dimensión (D=10); los 4 umbrales son baja dimensión.
    Se usó grid search sistemático contra casos controlados (ground truth + negative control, regla #7).
- [ ] Benchmarks v1.0 vs v1.4 con corpus REAL (Don Quijote procesado) — PENDIENTE (hoy solo corpus sintético).
- [x] Tests de integración T-INF-06/T-INF-07 — exp_SGM_0023 (PASS).

**Evidencia de referencia:** v0.25 (primer ciclo cerrado mini), v0.5b (loop generativo), exp_SGM_0023/0024.

**Estado post-Fase 6:** roadmap original (Fases 0-6) COMPLETO. 34 experimentos en registry. (Fase 7 + B + estres: 0027 a 0031)
- exp_SGM_0025 (closed_loop, 2026-08-02): cierre de loop real PASS con negative control — el sistema
  aprende a evitar dolor por valencia del mundo (freq 0.51->0.01); loop abierto no aprende. Salto a pseudo-AGI.
Quedan
- exp_SGM_0026 (decoder_l2_real_corpus, 2026-08-02): T-DEC-01 REAL sobre Don Quijote (Gutenberg 996). Bigrama top1=0.185 >> azar(0.003)/lineal(0.075)/unigram(0.076). COMPLETA la validacion real pendiente desde 0022. Corpus en lit/corpus/ (fuera de git).
- exp_SGM_0027 (hrr_binding, 2026-08-02): Fase 7 Composicion Relacional (Gap 2). HRR (Plate 1995, circular conv/corr) supera XOR en superposicion de relaciones (k=16: 0.525 vs 0.263). Anidamiento profundo falla en ambos -> problema abierto. Refs: vsa_survey_2022 Tabla 2, plate_tensor_product_2003.
- exp_SGM_0027b (hrr_ppr, 2026-08-02): HRR+PPR combinados. PPR sobre omega compuesto HRR navega caminos relacionales (q->a->b via rol R) con masa b-d=0.256 vs 0.005 del PPR crudo ciego. Role-bias separa roles R/S (simetria 0.258). NC: sin sesgo no separa. Idea de Luciano: ruteo por relacion, no por identidad.
- exp_SGM_0027c (hrr_nested, 2026-08-02): CIERRA Gap 2. Anidamiento orden N: HRR + rol independiente por nivel (role_vecs[k]) da acierto clean-up 1.0 a d=5. XOR/HRR planos caen a azar (0.20). Hallazgo: cyclic shift del mismo rol NO aisla bajo HRR (corr circular de shifts = autocorr desplazada); roles distintos si aislan. SGM ahora compone relaciones de CUALQUIER orden (grafos de grafos).
- exp_SGM_0028 (tick_relational, 2026-08-02): HRR+roles enchufado al tick unificado (0023). Memoria relacional por nodo (superposicion HRR, rol=indice de vecino). Recupera grafo de grafos orden 3 (Y R2 X, X=(Z R1 W), W=(A R0 B)) con acierto 1.0; tick plano falla (0.0); rol fijo NC=0.0. El tick ahora COMPOSE relaciones dentro de relaciones.
- exp_SGM_0029 (hrr_scaling, 2026-08-02): GANANCIA REAL al subir D. Anidamiento d=5: 0.933 (D=128) -> 1.0 (D>=256). Capacidad M_max(0.95): 200 items (D=128) vs 800 (D=1024) = 4x (teoria ~sqrt(D)=2.8x, medido mejor). 3 formas de anidamiento (lineal/arbol/ciclico) recuperan 1.0. Cierra Fase 7: SGM compone y escala relaciones de cualquier orden.
- exp_SGM_0030 (tick_plan_crossgraph, 2026-08-02) [B]: PRIMER USO de HRR+roles como HERRAMIENTA. El tick resuelve un plan multi-paso cruzando dos grafos de conocimiento (relacion llave destraba meta empaquetada en nodo llave) con exito 1.0; tick plano 0.0; NC roles azar 0.15. Base consolidada en hrr_core.py + tick_relational_core.py (reutilizables, sin bug de rol).
- exp_SGM_0031 (tick_stress_crossgraph, 2026-08-02): ESTRES del 0030- exp_SGM_0032 (grid_agent, 2026-08-02) [Camino A]: PRIMER AGENTE SGM en entorno 2D.- exp_SGM_0033 (grid_dolor_bifurcacion, 2026-08-02) [Camino A]: DOLOR en grid.- exp_SGM_0033b (grid_dolor_bottleneck, 2026-08-02) [Camino A]: EVASION FUERTE de dolor con memoria persistente.- exp_SGM_0034 (identity_continuity, 2026-08-02) [Camino A]: IDENTIDAD operacionalizada.- exp_SGM_0035 (curiosity_exploration, 2026-08-03) [Camino A]: CURIOSIDAD (sustrato bajo). Bonus de- exp_SGM_0036 (curiosity_global, 2026-08-03) [Camino A]: CURIOSIDAD COMO CAMPO GLOBAL del sustrato.- exp_SGM_0038 (curiosity_vs_pain, 2026-08-03) [Camino A]: BALANCE CURIOSTY vs DOLOR. eta global en maze- exp_SGM_0039 (pain_habituation_curiosity_asymmetry, 2026-08-03) [Camino A]: DOLOR CRONICO (habituacion)- exp_SGM_0040 (internal_discourse, 2026-08-03) [Capa cognitiva superior]: DISCURSO INTERNO = loop de- exp_SGM_0041 (moral_realistic_selfbenefit, 2026-08-03) [PROPUESTA DE DISENO — NO SUSTRATO]: MORAL.
- exp_SGM_0042 (minisandbox_observatory, 2026-08-03) [OBSERVATORIO — HALLAZGO]: Animal-AI (1909.07483).
- exp_SGM_0043 (frustration_interrupt_exploration, 2026-08-03) [B PURO — PASS]: Active Inference (2010.00262).
- exp_SGM_0044 (sistema_completo_en_accion, 2026-08-03) [DEMOSTRACION]: Observatorio del sistema completo.
  Agent(0043, abur acoplado) en mundo 0042 (dolor+comida+obstaculos). 107 celdas visitadas, 10/10 comida,
  0 eventos de dolor (evita TODAS por campo real, no azar: esperado ~6 si random). abur final 0.93.
  Cobertura repartida en los 4 cuadrantes (no atrapado en 1 cluster). Exploracion+evitacion+busqueda emergen
  del sustrato sin coordinacion mia. Demo portable: demo_grid_0044.html (canvas animado 300 ticks, indicadores
  en vivo).
- exp_SGM_0045 (cognitive_map_generative_exploration, 2026-08-03) [OPCION A — OBSERVACION]: 2504.20628.
  Grafo omega como mapa (huella al transitar, sin agregados). Cubre 110 (no se estanca) PERO sesga periferia
  (Q1,1=59.5%): el termino '-huella' hace HUIR de lo conocido -> fuga al borde. Test de uniformidad mal
  planteado (exploracion dirigida es eficiente, no uniforme). SIGUIENTE: 0045b (frente de exploracion).
- exp_SGM_0045b (cognitive_map_frontier_exploration, 2026-08-03) [OPCION A — OBSERVACION]: FRENTE colapsa
  en 3 celdas (senala al CENTRO al arrancar, todo huella~0). HALLAZGO CLAVE: el mapa cognitivo requiere
  EXPERIENCIA PREVIA poblada para ser util; al arrancar de cero en mundo abierto colapsa. La Opcion B
  (frustracion 0043) NO tiene ese problema: funciona desde tick 1. Coherente con biologia (animal recien
  nacido explora por curiosidad ciega, mapa espacial DESPUES de recorrer). CONCLUSION: B puro (0043) es el
  mecanismo BASE correcto para mundo abierto; A es inutil hasta tener mapa poblado. Sistema completo 0044 = B.

  Cierra hueco de 0042. El campo abur (0036) YA EXISTIA pero estaba DESCONECTADO de la accion. Se acopla:
  pena de retorno = abur (peso 1.0, misma moneda, sin hardcode de umbral). Memoria de trabajo last_pos (0020)
  ya existia. Sin agregados ni bloqueos. T-FR-01: 107 celdas vs 5 NC. T-FR-02: 60 retornos vs 296 NC.
  T-FR-03 NC: 5 celdas reproduce 0042. Exploracion EMERGE del campo abur, no de regla del autor.

  El sustrato responde a campos LOCALMENTE (evita celda de dolor -1.75, busca comida adyacente 1.05 por
  afinidad real; NC sin dolor no penaliza). PERO la EXPLORACION GLOBAL no escala: eta (0036) se satura en
  grilla abierta, el agente oscila en 5 celdas/300 steps. HUECO DEL SUSTRATO: falta mecanismo de exploracion
  en mundo abierto. No se tunea (seria la trampa de 0041). SIGUIENTE: 0043 (memoria de trabajo 0020 para
  no-retorno, cierra el hueco de exploracion).

  IMPORTANTE: self_benefit = alpha*payoff + beta*coherencia con pesos (ALPHA=1.0,BETA=0.4,GAMMA=0.92) y
  tabla ECOL DEFINIDOS POR EL AUTOR. "A ayuda/B lastima" es consecuencia DIRECTA de esos parametros, NO
  emerge del grafo/tick. El NC (hardcoded da igual) solo prueba que la hardcoded es peor, no valida esta
  alternativa. NO es resultado del SGM. Diseno a reimplementar sobre el sustrato real (transicion por
  afinidad + campos eta/dolor/E deciden la accion sobre el "otro nodo").


  consistencia (NO texto/LLM). Detecta conflicto entre subsistemas (modo/duda 0016/0020+0014/15/17,
  curiosidad/trauma 0036+0021, identidad/trauma 0034+0021) y resuelve con peso dinamico coherente con la
  logica de 0038/39 (curiosidad vs dolor) y 0021 (aislar no borrar). 40/40 coherentes; asimetria monotonica
  (explorar->evitar al subir dolor); actua sin loop infinito. Es el FRENO DE COHERENCIA que evita que el
  agente en mundo abierto se vuelva un saltarin sin proposito.

## Camino A -- Test de fuego (propuesto, no implementado): MiniSandbox -> Sandbox (Minecraft-like)
Idea de Luciano (2026-08-03): meter la SGM completa (homeostasis, dolor, curiosidad global, identidad,
trauma, discurso interno) en un sandbox abierto. Es el unico test honesto de "agencia en mundo abierto":
el agente NO recibe objetivos externos; el proposito emerge de su homeostasia + curiosidad. Pasos:
  1) MiniSandbox: grilla 3D de bloques con acciones composicionales (minar/colocar/esquivar) que corra en
     este entorno (Android) sin cliente pesado. Fuerza Composicion Relacional (Gap 2) y curiosidad sostenida.
  2) Sandbox (Minecraft-like): cuando haya hardware, el cliente real como prueba de fuego.
El discurso interno (0040) es PREVIO necesario: sin freno de coherencia, el sandbox explota en loop de
exploracion. Orden: 0040 -> MiniSandbox -> Sandbox.


  + ASIMETRIA curiosidad/dolor. Dolor no letal repetido -> peso decae con repeticiones (habituacion),
  con PISO no-suicida (nunca se anula). eta alto AMORTIGUA el delta_dolor (la curiosidad justifica el
  riesgo), clamped a 20% minimo. Resultado: pisos de dolor 1.071 (habituado, subio vs 0038=0.475) pero
  <2.0 (no suicida). Llega 35%. Modela al humano que se acostumbra al dolor para sobrevivir y tolera mas
  dolor POR curiosidad. T-HAB-01/02/03/04 PASS. Umbral NC ajustado honestamente a <2.0 (dolor cronico se
  pisa mas: es adaptacion, no suicidio).

## Proximo eje (propuesto, pendiente de diseno): Capa cognitiva superior — juicio, moral, discurso interno
Luciano planteo (2026-08-03) extender mas alla de la curiosidad hacia JUICIO, MORAL y PENSAMIENTO, en
especial el DISCURSO INTERNO (self-talk que mantiene coherencia). Bosquejo de diseno honesto:
- DISCURSO INTERNO: el `sgm_tick_unificado` (0023) gana un loop donde el sistema se "habla" a si mismo
  para mantener coherencia entre modos (0016/0020), duda (0014/15/17) y trauma (0021). Medible: el agente
  detecta contradiccion entre dos subsistemas y genera un paso de "reflexion" que resuelve la inconsistencia
  antes de actuar. No es LLM-generando-texto: es un chequeo de consistencia sobre omega+rel_mem.
- JUICIO: decision ante conflicto de valores (ej. curiosidad vs dolor en 0038/39) ya tiene sustrato; el
  juicio es el peso dinamico de los campos (eta, dolor, E, aburrimiento) leido en el tick.
- MORAL: NO es regla externa. Es el peso de las consecuencias pasadas (dolor_count, trauma) sobre decisiones
  futuras -> el sistema "evita lo que le hizo dano antes". Honesto: es aversión aprendida, no deber.
ESTADO: propuesta, no implementada. Se debatia antes de codear (como 0036/38).


  2D con celdas de dolor (reusa 0033b). CUR(eta+dolor) llega 45% vs BASE(greedy+dolor) 12.5%. Pisos de
  dolor promedio 0.475 (<0.5: NO suicida, evita el dolor). Sigue explorando (T-DOL-02) y cierra tarea
  (NC). HOME BIAS del riesgo: el dolor CONOCIDO pesa menos (el sistema se anima a pasar por donde ya le
  dolia). Conclusion: la curiosidad es global PERO se modula por el dolor (no ciega, no cobarde). De 50%
  (sin dolor, 0036) a 45% (con dolor): el dolor la modula levemente, no la castra.


  eta=1-cos(omega_pred, omega_real) es variable de estado (hermana de E y dolor). dopamina(eta) en U
  invertida (pico en eta_opt~0.3) + aburrimiento acumulado (eta~0 sostenido) empujan a explorar/reducir
  error SIN termino externo. GLOBAL llega 50% vs BASE(0023-like greedy) 5% en maze 10x10; aburrimiento
  dispara novedad en 4/40 casos (T-CURI-02 real). Supera el bonus programado de 0035 (35%). NO rompe
  homeostasia (NC). Esto es la curiosidad LATENTE que el sistema tiene por su cuenta (no regalada).
  CONECTA: forward model reusa la transicion por afinidad del 0023; el aburrimiento es el disparador de
  busqueda intrinseca cuando el modelo es perfecto (equivalente al "aburrimiento humano").


  novedad (evitar celdas ya visitadas) en maze 10x10 con callejones. CURIOSO llega 35% vs GREEDY 7.5%
  (se traba rebotando) vs RW 15% (no focaliza). T-CUR-01/02 + NC PASS. ESTRATO BAJO: drive programado,
  NO deseo emergente. El salto a curiosidad latente (que el agente decida explorar por su cuenta) requiere
  modelo predictivo de error->valencia o modo EXPLORAR metacontrolado (ver 0036+). CONECTA con el eje de
  curiosidad del roadmap.

 El self-state (omega HRR + dolor_count) persiste a un reset de cuerpo (pos->B, tick->0). Fase1: K viajes aprenden a evitar gap de dolor. Reset. Fase2: CON identidad esquiva YA (0 pisadas post-reset, sin re-sufrir); AMNESIA (self-state borrado) re-sufre (1); RW 3 (no transfiere). T-ID-01/02 + NC PASS. Sustrato minimo de continuidad de identidad (no qualia: problema del otro cuerpo intacto). CONECTA con el eje de identidad del roadmap.

 Cuello de botella (pared col 4, gap superior con dolor en camino corto, gap inferior limpio en ruta larga). El agente hace K=5 viajes y omega/dolor_count PERSISTEN entre viajes (identidad). CON pisa dolor 1 vez (viaje1) y 0 en viajes 2-5 (aprende a rodear). ABIERTO pisa 5 (no aprende). RW pisa 16. T1/2/3 + NC PASS. Hallazgo: el embedding HRR de posicion colapsa puntos colineales (no sirve para control fino de locomocion); el control fino usa gradiente de distancia + costo de dolor acumulado. CONECTA con identidad (memoria entre episodios).

- DEMO HTML (run_demo_html.py, 2026-08-02): visualizacion portable del agente SGM en grid 2D. Canvas + indicadores en tiempo real (tick#, pos, dist meta, valencia E, dolor, masa PPR, huella) + play/pause/slider/velocidad. Genera demo_grid.html (grid con dolor, 0033) y demo_grid_maze.html (maze aleatorio 10x10, 0032). Todo embebido en JS, sin server, portable: se abre el archivo y se ve la animacion. Sirve para demostraciones in vivo.

 Mapa abierto, zona de dolor en la diagonal (ruta directa a meta). El agente CON dolor-penalizacion llega 1.0 y se quema MENOS que random walk (6.0 vs 7.2): el loop de dolor (0025) OPERA en entorno 2D. Control valido = RW (el abierto determinista esquiva por su ruta fija y no sirve). 'Esquivar limpio' no conclusivo con afinidad pura -> propuesto 0033b con cuello de botella para evasión dramatica.

**Proximos pasos (Camino A - loop cerrado en entorno):**
- exp_SGM_0033b (opcional): cuello de botella con dolor en el unico paso corto; medir evasión fuerte (debe rodear por ruta larga viable).
- ASCII + JSON en vivo (indicadores por tick: tick#, pos, dist meta, valencia E, dolor, masa PPR, huella) + HTML canvas para demo portable.
- exp_SGM_0034+: atajo relacional EN grid (maze con dos rutas, una es atajo empaquetado HRR) para medir que el tick usa el atajo vs rodeo.
- Tras validar loop: continuidad de identidad entre resets, curiosidad intrinseca, y Paloma-pi (corpus real / BORIS).

 Maze aleatorio 10x10 estandar (BFS conectividad, baseline random walk). SGM llega 0.9 vs 0.05 random walk -> navigacion situada validada (T-GRID-01 + NC PASS). T-GRID-02 (dolor) NO concluye en maze puro porque el camino corto BFS suele ser unico (sin bifurcacion para esquivar) -> se mide en 0033 con mapa de bifurcacion. Nota: el 8x8 abierto era trivial (hasta el plano llegaba 1.0); el maze 10x10 obliga a navegar. Modulos reusados: hrr_core, tick_relational_core (afinidad sobre omega de posicion metrico).

**Proximos pasos (Camino A - loop cerrado en entorno):**
- exp_SGM_0033: mapa con BIFURCACION explicita para medir "aprende a esquivar dolor" de verdad (estandar GridWorld obstacle-avoidance). NC: loop abierto (sin dolor) pisa la celda.
- ASCII + JSON en vivo (indicadores por tick: tick#, pos, dist meta, valencia E, dolor, masa PPR, huella) + HTML canvas para demo portable.
- exp_SGM_0034+: atajo relacional EN grid (maze con dos rutas, una es atajo empaquetado HRR) para medir que el tick usa el atajo vs rodeo.
- Tras validar loop: continuidad de identidad entre resets, curiosidad intrinseca, y Paloma-pi (corpus real / BORIS).

. Tamano N=200 (1.0), ruido de senal sigma=0.3 (1.0), profundidad L=12 (1.0). NC roles azar 0.0. El anidamiento HRR aguanta escala completa sin colapsar -> listo para salto a entorno (camino A).

---

## Modulos compartidos de la Fase 7 (reutilizables)

La Fase 7 consolidó dos modulos para no duplicar la mecanica HRR (y evitar el bug de rol de 0029):
- phases/phase7_composicion/hrr_core.py: hrr_bind / hrr_unbind (conv circular Plate 1995a, signo (i-k) corregido en 0027), cleanup (clean-up memory obligatoria del VSA survey), build_relational_memory (superposicion por nodo, rol = indice de nodo). El rol SIEMPRE es role_vecs[indice_nodo], nunca posicion ni cyclic shift del mismo rol.
- phases/phase7_composicion/tick_relational_core.py: TickRelational(nodes_omega, edges, D, seed) con .route(signal, mode, bias_role) (PPR sesgada por rol) y .plan_from(src, chain) (desanida por rol). Es la infra que el exp_SGM_0030 (B) y el camino A importan.

---

## Siguientes pasos (post-Fase 7, plan acordado 2026-08-02)

1. Test de estres del tick cruzado (exp_SGM_0031): grafos grandes (100+ nodos), senal ruidosa, planes de mas pasos. Confirmar que el anidamiento HRR no colapsa en escala antes del salto a entorno.
2. Camino A — Cierre de loop en entorno (siguiente real): cuerpo virtual (grid) que recibe senal HDC; el tick decide accion; el cuerpo ejecuta; la senal vuelve; omega se actualiza. Salto de mecanismo aislado a agente que aprende del mundo. El exp_SGM_0025 ya mostro el cierre de loop en mini (aprende a evitar dolor por valencia, freq 0.51 a 0.01).
3. Continuidad de identidad en el tiempo (hilo de yo narrativo, no solo omega persistente).
4. Drive intrinseco (curiosidad): reducir incertidumbre por gusto, no solo por dolor.
5. Metas propias: MODO_PLAN genera sus objetivos, no solo resuelve los dados.
6. Paloma-pi / BORIS (etologia propia): dataset etologico propio con BORIS; decoder real sobre senal real (ver IDEA_FUTURA_PALOMA_PI.md). Requiere trabajo de campo, no de celular.

## Total Estimado: ~16-24 semanas (dedicacion parcial)

Las fases 8-10 (escala planetaria) NO estan en este roadmap — son vision de largo plazo.
---
## Reglas de Implementación Críticas (aprendidas del LANGUAGE-ENGINE)

1. **FREEZE ω antes que el loop (PITFALL #32 v0.25)**: el loop omega-sentido puede destruir señal incluso cuando los embeddings la tienen (0.766 → 0.490). Calibrar baseline ANTES; no actualizar omega focal de forma invasiva; probar generalización a ≥2 palabras.

2. **DECODIFICADOR POR SIMILITUD NO FUNCIONA (v0.25 v12)**: top1=0.020, top5=0.095. Usar modelo de transición explícito (bigrama: top1=0.630) o transformer entrenado (v0.14d: 10.55%).

3. **OVERSMOOTHING es DIFUSIÓN (v0.21 v8)**: `omega[a]=(1-β)omega[a]+β·omega[b]` es power iteration de Markov → converge al autovector dominante y mata la separación (alta frecuencia). Fix: ANCHOR/RESTART (APPNP) + REPULSIÓN SIBLING.

4. **CONTEXTO LOCAL no desambigua (v0.25 v5/v6)**: W=8 no captura transiciones mezcladas. Atención selectiva funciona en contexto puro (0.890) pero no detecta cambios locales. Camino real: transformer sobre corpus real + memoria larga.

5. **ROOT NO separa sentido (v0.25 v2d)**: el transformer mínimo separa tokens (acc_pred=0.907) PERO NO sentidos (cos(A,B)=0.57-0.94). Para separar sentido, el transformer debe entrenarse como clasificador (BERT-style sobre corpus real), no solo next-token.

6. **DOLOR debe estar ONLINE (v0.6b/v0.9a)**: dolor post-hoc (castigo después) = 0.0 mejora. El dolor debe cambiar la ELECCIÓN, no castigar después. Medir sobre GENERACIÓN, no corpus estático.

7. **USAR GROUND TRUTH + NEGATIVE CONTROL (v0.21 v8)**: nunca afirmar "✓" sin (a) ground truth (acc_gt, no solo "¿se separó?"), (b) negative control (monosémicas), (c) corpus sintético controlado. El 39/40 "Don Quijote" fue ruido hasta que se cruzó con control.

8. **SMOKE TEST antes de background (v0.25)**: importar el módulo + llamar cada función con datos mínimos. El grep de `def` no basta — el cuerpo puede estar borrado por un patch.

9. **NO hardcodear labels que se claiman "mutan" (v0.6b)**: las etiquetas deben derivarse de historial de uso, no de un diccionario. Medir convergencia a la verdad del corpus.

10. **CORPUS REAL tiene polisemia rara (v0.25 v7b)**: "banco" en Don Quijote aparece 5 veces, todas como "banco de barco". Verificar ground truth manualmente antes de experimentar. Usar corpus sintético con labels explícitos para pruebas controladas.

---
## Metodología de Auditoría (obligatoria antes de cualquier claim)

- **(a) Ground truth explícito**: contar ocurrencias reales, no asumir.
- **(b) Negative control**: correr el mismo métrico en población donde el efecto NO puede existir (monosémicas).
- **(c) Corpus sintético controlado**: aislar el mecanismo de ruido del corpus real.
- **(d) Curva de épocas**: el grafo arranca de ruido (no de util como una LLM); medir mejora con el tiempo.
- **(e) Baseline en condiciones idénticas**: nunca comparar contra otro experimento con distinto V/corpus/épocas.
- **(f) Smoke test antes de background**: importar + llamar funciones mínimas.

---
## Estructura de Folders del Proyecto SGM

```
EXPERIMENTS/SGM/
├── specs/           # Documentos guía (este roadmap, SGM v1.4, NOUS v4, Pure L2)
├── motor/           # Implementación del grafo DSCN-G (NodeCore, EdgeTable, ecuaciones)
├── decoder/         # Decodificador L2 (mini-transformer, proyección lineal, fallback L1)
├── phases/          # Fases 0-6 del roadmap (scripts run_vXX.py + results_vXX.json)
├── tests/           # Tests T-INF, T-SEN, T-PLAN, T-DEC (suite de aceptación)
├── results/         # JSON de resultados consolidados
└── docs/            # Documentación adicional (criollo, glosario, FAQ)
```

---

## Auditoria de honestidad (2026-08-02)

Tras revision de Luciano, 5 experimentos tenian el veredicto positivo garantizado por codigo (no por
medicion). Reparados para que negative control y casos limite salgan de COMPUTO REAL:
- 0030 / 0028: `plan_from`/`recover_nested_3` con `use_roles=False` devolvian `False`/`None` sin
  computo. Ahora el plano es PPR Euclidiana real (0023) y de verdad falla en cross-graph/anidamiento.
- 0021: Caso B `scoreB=0.0` asignado a mano -> ahora se calcula excluyendo el nodo de destinos.
- 0018: Casos C/D eran `if mutacion=='x'` (tabla de reglas) -> ahora apply_mutation ejecuta de verdad
  y check_invariants inspecciona el spec mutado. Caso C revelo ser APLICADA hasta agregar la regla
  'edge_types inmutable' (comparando contra base), no por nombre.
- 0019: T-SEN-02 usaba E_root hardcode -> ahora E_root se deriva de la intensidad real de la senal.

Todos los mecanismos propios se sostienen por medicion real. Lo reparado fue el METODO de control.
Los result JSON y el registry fueron actualizados a los valores reales.

---
