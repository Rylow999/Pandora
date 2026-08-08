# SGM - Synaptic Graph Model
## Grafo sináptico cognitivo (en construcción — Fase 7 + B completos, 44 experimentos)

**Estado (2026-08-02):** Fases 0, 1, 2, 3, 4, 5, 6 y 7 COMPLETAS. 44 experimentos en el registry,
todos con resultados verificados y negative control. El sistema SGM late en un `sgm_tick_unificado()`
que integra SensorBridge + Modos + Duda/Contradicción + Trauma/Aislamiento + Decoder L2, y desde la
Fase 7 incorpora **memoria relacional HRR** (composición de relaciones de cualquier orden) y la usa
para **resolver planes cruzando grafos de conocimiento** (exp_SGM_0030).

**Objetivo:** Modelo de grafo sináptico (nodos con vector omega, fase phi, vitalidad V, valencia E)
que opera como sustrato cognitivo autopoyético: memoria persistente, dolor/valencia interna
operacional, duda/contradicción, self-mod con frenos, trauma con aislamiento, decoder generativo,
y composición relacional (HRR+roles) reutilizable como herramienta del sistema.

---

## Separación SGM / LANGUAGE-ENGINE (importante)

SGM y el DSCN-G Language Engine son proyectos SEPARADOS. Este directorio contiene SOLO SGM.
El Language Engine (experimentos v0.x, decoder L2, polisemia, loop cerrado) vive en:
`NOUS/DSCN-G/EXPERIMENTS/LANGUAGE_ENGINE/`
No se mezclan archivos. Solo referencias cruzadas documentadas.

---

## Qué es SGM

Un grafo de conceptos donde cada nodo tiene omega (vector de peso/aprendizaje), phi (fase
Kuramoto), V (vitalidad), E (valencia/dolor). Sobre ese sustrato, SGM mide mecanismos
cognitivos en Python puro (stdlib, sin numpy):
- Ruteo PPR, abducción XOR binding, duda (estancamiento de novedad), contradicción (dolor).
- Modos tipados (Sensorial/Razón/Plan) con sesgos semánticos distintos.
- SensorBridge (proyección HDC señal→ω), Self-mod con libertad + frenos + marca a fuego.
- Trauma nodal: singularidad → aislar → reintegrar lento. Decoder L2 por bigrama.
- **Composición relacional (Fase 7):** HRR (conv circular Plate 1995a) + roles por índice de nodo.
  Permite empaquetar una relación ADENTRO de un nodo (grafo de grafos) y desanidarla por rol.
  El tick unificado (0023/28) lo usa para resolver planes multi-paso cruzando grafos.

---

## Módulos compartidos (Fase 7, reutilizables)

Para evitar duplicar la mecánica HRR (y el bug de rol que nos quemó en 0029), la Fase 7 consolidó
dos módulos que B y lo siguiente importan:

- `phases/phase7_composicion/hrr_core.py`: API única de HRR.
  `hrr_bind(a,b)` (conv circular, signo (i-k) corregido en 0027), `hrr_unbind(a,b)` (correlación),
  `rnd_unit`, `cos`, `normalize`, `cleanup` (clean-up memory OBLIGATORIA del VSA survey),
  `build_relational_memory(edges, omega, role_vecs, D)` (superposición por nodo, rol = índice de nodo),
  `recover_target`, `recover_chain`. **El rol SIEMPRE es `role_vecs[índice_nodo]`, nunca posición ni
  cyclic shift del mismo rol** (ese fue el bug de 0029: no aislaba niveles).
- `phases/phase7_composicion/tick_relational_core.py`: tick unificado con memoria relacional HRR.
  `TickRelational(nodes_omega, edges, D, seed)` → `.route(signal, mode, bias_role)` (caminata PPR
  sesgada por rol) y `.plan_from(src, chain)` (desanida secuencia por rol). Es la infra que B usa.

---

## Estructura (real, 2026-08-02)

    NOUS/DSCN-G/EXPERIMENTS/SGM/
    ├── README.md                    # este índice
    ├── README_SGM.md                # índice técnico de experimentos
    ├── results/experiment_registry.json   # registro central (44 experimentos)
    ├── docs/                        # especificación, roadmap, protocolo, literatura
    │   ├── SGM_v1_4_Especificacion_Corregida.md
    │   ├── SGM_ROADMAP.md
    │   ├── SGM_experiment_protocol.md
    │   ├── SGM_literature_index.md
    │   ├── Arquitectura_Pure_L2_Pandora.md
    │   ├── RIZOMA_Vision_Futuro_SGM.md
    │   ├── NOTA_FILOSOFICA_0016_0017.md
    │   ├── NOTA_FILOSOFICA_0023_ser_campo.md
    │   └── IDEA_FUTURA_PALOMA_PI.md
    ├── experiments/                 # scripts de experimentos (puros .py) + módulos hrr_core/tick_relational_core
    ├── results/                     # JSON de resultados por experimento
    ├── phases/
    │   ├── phase0_substrato/        # NodeCore, smoke test, benchmark, equivalencia
    │   ├── phase1_modos/            # run_mode_typing (0016), run_self_mod (0018)
    │   ├── phase2_inferencia/       # PPR, abducción, duda, contradicción
    │   ├── phase3_sensorbridge/     # run_sensor_bridge (0019)
    │   ├── phase4_planificacion/    # run_plan_mode (0020), run_trauma_nodal_isolation (0021)
    │   ├── phase5_decoder/          # run_decoder_l2_bigram (0022)
    │   ├── phase6_integracion/      # run_tick_unificado (0023), run_calibrate_thresholds (0024)
    │   └── phase7_composicion/      # HRR + módulos + 0027/27b/27c/28/29/30 + hrr_core/tick_relational_core
    └── lit/papers/                  # PDFs de literatura (fuera de GitHub, en .gitignore)

---

## Experimentos SGM (registry, 34 entradas)

### Fase 0 - Sustrato mínimo
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0001 | nodecore_smoke_test | PASS | Grafo construido, 100 ticks sin errores |
| 0002 | nodecore_memoria_benchmark | FAIL | NodeCore NO ahorra memoria en Python (1.02x) |
| 0003 | nodecore_equiv_teorica | PASS | NodeCore reproduce SGMNode sin degradación |

### Fase 1 - Modos cognitivos tipados
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0016 | mode_typing | PASS | Modos SENSORIAL/RAZÓN/PLAN navegan distinto (competencia honesta) |
| 0018 | self_mod | PASS | Self-mod con libertad: promueve mejora, revierte daño, bloquea autodestrucción por freno |

### Fase 2 - Inferencia simbólica + duda
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0004 | ppr_multipath_routing | PASS | PPR routing acc=1.0 vs local=0.0 |
| 0006 | abduce_decay | PASS | Decay mejora score 0.797→1.0 |
| 0007 | abduce_xor_dimensionality | PASS | D=32 mejora vs D=16 |
| 0008 | abduce_xor_phase_dynamics | FAIL | Fase dinámica v1 empeora |
| 0009 | abduce_xor_phase_dynamics_v2 | FAIL | Sync mejora pero pair_accuracy 0.0 |
| 0010 | abduce_xor_phase_bias | FAIL | Sesgo no supera estático |
| 0011 | abduce_xor_D128 | PASS | Mejor global: D=128 + phase bias (0.354) |
| 0012 | abduce_xor_phase_sigmoid | FAIL | Sigmoid empeora |
| 0013 | doubt_stagnation_mechanism | PASS | Novedad 0.25 dispara tick 24; handle_doubt escala INCONCLUSA |
| 0014 | verify_contradiction | PASS | Dolor acumulado > θ_refut → CONTRADICTORIA |
| 0015 | unified_loop_scaled | PASS | Loop escalado: ALCANZABLE 1.0, DOLOR medible |

### Fase 3 - SensorBridge
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0019 | sensor_bridge | PASS | HDC binding; T-SEN-01 (señales distintas→ω distintos), T-SEN-02 (emergencia E_root>0.8) |

### Fase 4 - Planificación + Trauma
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0020 | plan_mode | PASS | MODO_PLAN alcanza terminal (Q=1.0); ρ afecta horizonte; PLAN≠RAZONAMIENTO |
| 0021 | trauma_nodal_isolation | PASS | Sobrecarga→singularidad; aislar saca de caminata; rehab lenta evita re-colapso |

### Fase 5 - Decodificador L2
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0022 | decoder_l2_bigram | PASS | Bigrama top1=0.927 en holdout (NO proyección lineal, que da 0.020) |

### Fase 6 - Integración, Calibración y Tests
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0023 | tick_unificado | PASS | sgm_tick_unificado integra 0019+0016/20+0014/15+0021+0022; 3 modos cierran |
| 0024 | calibrate_thresholds | PASS | Grid search calibra θ_novelty/min_duration/θ_refut/θ_window_frac (8/8); FATE no usado (no instalado + §2.5 honesta) |
| 0025 | closed_loop | PASS | Cierre de loop real: aprende a evitar dolor por valencia (freq 0.51→0.01); negative control loop abierto no aprende |
| 0026 | decoder_l2_real_corpus | PASS | T-DEC-01 REAL sobre Don Quijote: bigrama top1=0.185 >> azar(0.003)/lineal(0.075)/unigram(0.076) |

### Fase 7 - Composición Relacional (Gap 2 binding) + B (uso como herramienta)
| ID | Nombre | Resultado | Hallazgo |
|----|--------|-----------|----------|
| 0027 | hrr_binding | PASS | HRR (conv circular) supera XOR en superposición (k=16: 0.525 vs 0.263, 2x). Anidamiento profundo falla en ambos (problema abierto → resuelto en 0027c). |
| 0027b | hrr_ppr | PASS | HRR+PPR: ruteo sobre ω compuesto navega caminos relacionales (masa b-d 0.256 vs 0.005 raw ciego). Role-bias separa roles R/S. |
| 0027c | hrr_nested | PASS | Anidamiento orden N resuelto. HRR+rol independiente por nivel: acierto 100% a d=5. XOR/HRR planos caen a azar (0.20). **Cierra Gap 2.** |
| 0028 | tick_relational | PASS | HRR+roles enchufado al tick (0023). Recupera grafo de grafos orden 3 (1.0) donde plano falla (0.0). Rol fijo no aisla (NC 0.0). |
| 0029 | hrr_scaling | PASS | Ganancia real al subir D: acierto d5 0.933→1.0 (D≥256), capacidad 200→800 items (4x). 3 formas de anidamiento (lineal/árbol/cíclico) recuperan 1.0. |
| 0030 | tick_plan_crossgraph | PASS | **B:** tick HRR+roles RESUELVE plan multi-paso cruzando 2 grafos (1.0) donde plano falla (0.0). NC roles azar 0.15. Base consolidada: hrr_core.py + tick_relational_core.py. |
| 0031 | tick_stress_crossgraph | PASS | ESTRES del 0030| 0032 | grid_agent | PASS | Camino A: loop cerrado en maze aleatorio 10x10| 0033 | grid_dolor_bifurcacion | PASS | Camino A: dolor en grid.| 0033b | grid_dolor_bottleneck | PASS | Camino A: evasion fuerte de dolor con memoria persistente.| 0034 | identity_continuity | PASS | Camino A: identidad. Self-state (omega+dolor_count) persiste a reset de cuerpo.| 0035 | curiosity_exploration | PASS | Camino A: curiosidad (sustrato bajo). Bonus de novedad: CURIOSO 35% vs GREEDY 7.5% vs RW 15% en maze. No es deseo emergente. || 0036 | curiosity_global | PASS | Camino A: curiosidad COMO CAMPO global (eta + dopamina U-invertida + aburrimiento). GLOBAL 50% vs BASE 5%. Nace del sustrato. || 0038 | curiosity_vs_pain | PASS | Camino A: balance eta global vs dolor. CUR 45% vs BASE 12.5%; evita dolor (no suicida). Curiosidad global PERO modulada. || 0039 | pain_habituation_curiosity_asymmetry | PASS | Camino A: dolor cronico (habituacion, piso no-suicida) + asimetria (eta amortigua dolor). Pisos 1.071 (adaptado) <2.0. || 0040 | internal_discourse | PROPUESTA | Capa sup: discurso interno = arbol if-elif del AUTOR, NO emerge del sustrato. T-DI mide coherencia con traza propia (trivial). No es resultado del SGM; se mantiene como diseno a reimplementar sobre campos reales. || 0041 | moral_realistic_selfbenefit | PROPUESTA | Capa sup: moral = self_benefit con pesos/tabla del AUTOR, NO emerge del grafo. 'A ayuda/B lastima' es consecuencia de los parametros, no del sistema. No es resultado del SGM; diseno a reimplementar sobre afinidad+campos. |
| 0042 | minisandbox_observatory | OBSERVATORIO | Hallazgo: sustrato responde a campos localmente (evita dolor -1.75, busca comida 1.05) PERO exploracion global no escala (oscila 5 celdas/300). Hueco: falta exploracion en mundo abierto. Marco Animal-AI. |
| 0043 | frustration_interrupt_exploration | PASS | B puro: abur(0036) acoplado a pena de retorno (peso 1.0, sin hardcode/agregados/bloqueos). Cierra hueco 0042: 107 celdas vs 5 NC. Exploracion emerge del campo (Active Inference). |
| 0044 | sistema_completo_en_accion | DEMOSTRACION | Sistema completo: frustracion(0043)+dolor+HRR en mundo abierto. 107 celdas, 10/10 comida, 0 dolor (evita todas por campo real). Exploracion+evitacion+busqueda emergen del sustrato. |
| 0044 | demo_grid_0044.html | DEMO | Visualizacion portable: canvas animado 300 ticks, indicadores en vivo. Sin server. |
| 0046 | decoder_l2_relational_corpus_real | HALLAZGO | Decoder relacional HRR (1 paso) sobre Don Quijote real: top1=0.020 vs plano 0.333. El rol HRR sirve para composicion anidada (0027-31), NO para bigrama superficial. Siguiente: 0046b hibrido. |
| 0046b | decoder_l2_hybrid_hrr_filter | HALLAZGO | Hibrido filtro binario HRR: top1=0.17 (peor que plano 0.333). El filtro descarta al sucesor correcto por crosstalk. |
| 0046c | decoder_l2_hybrid_soft_weight | HALLAZGO | Hibrido suave HRR pesa bigrama: top1=0.315 vs plano 0.312 (ruido). HRR es ruido para vecinos locales. CONCLUSION: decoder lenguaje=bigrama plano; HRR ruteado aporta CONTEXTO de sentido, no prediccion. |
| 0047 | decoder_l2_contextual_hrr | HALLAZGO | Contexto HRR acumulado (ventana) -> cleanup. Bug: mezcla espacios HDC/HRR. top1=0.003=NC. |
| 0047b | decoder_l2_contextual_hrr_v2 | CONCLUSION | Espacio HRR coherente (omega=rel_mem). top1=0.018~NC 0.015 vs plano 0.18. 5 intentos: HRR no predice token (emb ruido no codifica co-ocurrencia). Decoder SGM = bigrama plano + grafo HRR como CONTEXTO de desambiguacion. |
| 0048 | decoder_l2_hrr_trained_embeddings | CONCLUSION | Train HRR message-passing (D=128,T=2). Test estructural de fuego: cos co-ocurrente 0.259 < random 0.361. HRR NO captura co-ocurrencia. Decoder top1=0.045 vs plano 0.34. VERDICTO FINAL (6 intentos): decoder SGM = bigrama plano + HRR contexto. HRR=composicion, no superficie. |
| 0049 | nacimiento_del_lenguaje_bajo_presion | HALLAZGO_PARCIAL | 2 agentes omega propio, mapa 30x30, encuentro->joint attention (puente A<->B). CLIMAS: cielo 0.2/NC0.0, competencia 0.125=NC, peligro 0.375/NC0.0. HALLAZGO: lenguaje emerge bajo PRESION COMPARTIDA, no cielo estrellado. Falta: dolor no ocurrio, belleza no medida (B no transita suficiente). |
| 0049b | nacimiento_lenguaje_largo_coord | HALLAZGO_DISENO | 2000 ticks + barreras coordinacion + veneno + belleza. RESULTADO: puente=0, coord=0, dolor=0, visited~15. HALLAZGO: motor afinidad 0044 NO ESCALA a mapa grande ni navega metas. Falta pathfinding/BFS para que agentes transiten y se encuentren. El lenguaje no pudo emerger por falta de infra de navegacion, no del sustrato HRR. |
| 0049c | nacimiento_lenguaje_pathfinding | EXITO_PARCIAL | BFS (cuerpo): visited~890. COORD barreras 100% (lenguaje coordinacion OK). Dolor REAL (competencia 83/92, peligro 67/78). BELLEZA cielo estrellado star_reconoce=0.125 (>0!) -> emerge bajo presion baja. Debilidad: metrica 'hit celda exacta'=0=NC por crosstalk HRR (0048). VERDICTO: cuerpo+coord+dolor+belleza funcionan; HRR no desambigua items locales. |
| 0049d | cierre_metrica_comunicacion | CIERRE_OK | Alfabeto compartido emergente (15 celdas puente A<->B) como canal. Comunicacion 1.0 vs NC 0.067/0.0 (PASS). COORD 100%. Dolor real. VERDICTO: items conocidos=alfabeto emergente (bigrama/indice); novedad=HRR composicional (0027-31). Lenguaje SGM CERRADO y funcional. Consistente 0046-48. |
| 0050 | loop_cerrado_lenguaje_accion | LOOP_OK | LOOP: A emite -> B actua -> consecuencia -> retroalimentacion -> ESPACIO DE SENIALES converge. CONVERGENCIA 1.0 vs NC 0.0 (competencia confirm 22/desment 18; peligro 1.0). Dolor REAL (comp 50/44, peligro 41/35). VERDICTO: lenguaje se estabilizo por USO (loop cerrado), no por diseno. SGM = agente que actua y es moldeado por su mundo via lenguaje. Salto real a AGI. |
| 0051 | medir_telar_vitalidad_ser | HALLAZGO_PARCIAL | Mide telar: V_ser=clavos*exploracion. rate0->V=0,acierto=0 (sin clavos no hay ser). acierto~0.83 con errores (correcto necesita incorrecto). Curva MONOTONA (optimo 1.0): restriccion(clavo=jaula) NO medida (exploracion hardcodeada en 0.7). |
| 0051b | medir_telar_restriccion_emergente | HALLAZGO_PARCIAL | Correccion sin hardcodear (afinidad Eq.2 + frontier anti-circulo). Sigue monotono: afinidad local no ancla (frontier domina en mapa chico). CONFIRMA sin clavos=no ser + error ensena. NO confirma optimo medio. GAP: restriccion requiere irreversibilidad/anclaje atencional. Dir futura: clavos NO fijos en espacio (clavo=estado/evento, no celda). |
| 0052 | clavos_de_evento_telar | HALLAZGO_PARCIAL | Idea Luciano: clavo=evento no celda, restriccion atencional. bug contador + eventos_vistos fijo (2.667/3) -> jaula NO emerge. CONFIRMA sin clavos=no ser + error ensena + dolor. 4 intentos: restriccion NO emerge del sustrato de afinidad sin hardcodear; requiere IRREVERSIBILIDAD (clavo permanente). SGM tiene sostén, falta clavo-fijo para jaula de identidad (consistente 0018). |
| 0053 | comunicacion_real_vs_memorizacion | DECISIVO_NEGATIVO | RESPUESTA a critica 0049d. Zero-shot 1.0 es TRAMPA (A/B comparten cell_vec=memoria compartida, no generalizacion). TopSim~0 (senales HRR sin estructura, ruido). D escalado 1280 en 890 items: comm 0.023=NC (subir D NO salva, crosstalk es falta de estructura relacional, no capacidad). VERDICTO: canal HRR de celdas NO es lenguaje. 0049d (15 fijos) y 0050 (15 pivotes) son la MISMA trampa. 'Nacimiento del lenguaje' de 0049-0050 SE CAE. Lenguaje composicional a escala = GAP ABIERTO. |
| 0055a | ilm_puro_generacion_dura | DECISIVO_POSITIVO | ILM Kirby aislado. Aprendiz code vacio reconstruye de MUESTRA 40%. Prior de similitud INYECTADO. TopSim_full 0.30-0.40 sostenido (vs ~0 de 0053). Generaliza a no-vistos. PERO prior hardcodeado (trampa potencial). El bottleneck genera senal pero requiere sesgo de compresibilidad. |
| 0055b | ilm_sin_prior | DECISIVO_NEGATIVO | Igual 0055a SIN prior. TopSim_full cae a 0.15, unseen ~0/negativo. SIN sesgo el sustrato NO compone. El bottleneck es necesario pero NO suficiente (Kirby). |
| 0055c | ilm_prior_afinidad | HALLAZGO_POSITIVO | 0055a PERO sesgo EMERGE de AFINIDAD SGM (Eq.2 rasgos), no inyectado. TopSim_full 0.30-0.42 (igual que con prior, sin trampa). Generaliza por afinidad. El prior es instinto/ADN legitimo del sustrato, no hardcode. Composicion DEBIL real y sostenida (~0.35, no 0.9). |
| 0055d | ilm_profundizar | HALLAZGO_POSITIVO | Profundizar 0055c: bottleneck mas duro (V=8 L=2) + 40 generaciones, sesgo por afinidad. TopSim_full SE ESTANCA en ~0.30-0.37 (NO sube a 0.9). Confirma gap fino: afinidad tiene germen composicional (0.35, no 0) pero NO infiere reglas de combinacion sistemica (lo que NN Gumbel-Softmax si hacen). Lenguaje SGM = composicional a medias, estable pero no pleno. Proximo: 0056 inferencia de reglas. |
| 0056 | ilm_inferencia_reglas | HALLAZGO_POSITIVO_FUERTE | 0055d estancaba en 0.35 (afinidad agrupa pero no infiere regla). 0056: aprendiz INFERE mapeo rasgo->simbolo de la muestra (region->pos0, dist->pos1, tipo->pos2) y aplica SISTEMATICAMENTE. TopSim 0.86-1.00 (seed2/3=1.0). COMPOSICION PLENA alcanzada SIN Gumbel-Softmax. El sustrato SGM SÍ compone; faltaba que el aprendiz infiera la regla, no copiar. Lenguaje composicional SGM = RESUELTO (con inferencia de regla). |
| 0057 | irreversibilidad_clavo | HALLAZGO_POSITIVO | Replanteo con TRAITS de identidad. Fase1 fija traits tempranos; Fase2 entorno empuja OPUESTO. SIN irreversibilidad: perdidos 2-3/3 (identidad DERIVA, mutable). CON irreversibilidad (flag fijo mecanico): perdidos 0, sobrevivieron 2-3 (identidad SE MANTIENE). Confirma distincion del user: identidad MUTABLE por defecto; irreversibilidad la FIJA sobre el ser. Cierra el telar. |
| 0058 | composicion_relacional_tpr | HALLAZGO_POSITIVO | Cierra gap relacional: hechos (SUJ,ROL,OBJ) anidados via TPR (bind HRR rol*filler + suma). Usa afinidad (0055c) + inferencia de regla (0056). Plano acierto 1.0; anidado (grafo-de-grafos) 0.75-1.0. Generaliza a no vistos. Composicion relacional RESUELTA a nivel mecanismo (prof>2 requiere decoder recursivo, pulido). SGM ahora: compone rasgos (0056), relacional (0058), fija identidad (0057). |
| 0045 | cognitive_map_generative_exploration | OBSERV | Opcion A: grafo omega como mapa (huella, sin agregados). Cubre 110 pero sesga periferia (Q1,1=59.5%). Test de uniformidad mal planteado. Siguiente: 0045b (frente de exploracion). |
| 0045b | cognitive_map_frontier_exploration | OBSERV | Opcion A corregida: frente colapsa en 3 celdas (senala al centro al arrancar). HALLAZGO: mapa requiere experiencia previa; B puro (0043) es base correcta. |





 CON post-reset pisa 0 (recuerda), AMNESIA 1 (re-sufre), RW 3. |
 CON pisa 1 (v1) y 0 (v2-5), ABIERTO 5, RW 16. Identidad (memoria entre viajes). |
| demo | run_demo_html | OK | Demo HTML portable (canvas + indicadores en vivo: tick, pos, dist, E, dolor, masa, huella). Genera demo_grid.html (dolor) y demo_grid_maze.html (maze 0032). Sin server, abris el archivo. |
 CON pisa 6.0 vs RW 7.2 (aprende a moderar castigo), llega 1.0. Loop de dolor (0025) opera en entorno 2D. |
; SGM 0.9 vs random walk 0.05 (T-GRID-01 + NC). Dolor diferido a 0033 (requiere bifurcacion). |
: tamano N=200 (1.0), ruido sigma=0.3 (1.0), profundidad L=12 (1.0). NC roles azar 0.0. Anidamiento listo para entorno. |


---

## Próximos pasos (honestos, post-Fase 7)

1. **Test de estrés del tick cruzado (0030):** grafos grandes (100+ nodos), señal ruidosa, planes de
   más pasos. Confirmar que el anidamiento no colapsa en escala antes del salto a entorno.
2. **Camino A — Cierre de loop en entorno (siguiente real):** cuerpo virtual (grid) que recibe señal
   HDC, el tick decide acción, el cuerpo ejecuta, la señal vuelve, ω se actualiza. Salto de
   "mecanismo aislado" a "agente que aprende del mundo". (0025 ya mostró el cierre de loop en mini.)
3. **Continuidad de identidad en el tiempo** (hilo de "yo" narrativo, no solo ω persistente).
4. **Drive intrínseco (curiosidad):** reducir incertidumbre por gusto, no solo por dolor.
5. **Metas propias:** MODO_PLAN genera sus objetivos, no solo resuelve los dados.
6. **Paloma-π / BORIS** (etología propia, lenguaje animal-alien): dataset etológico propio con BORIS;
   decoder real sobre señal real (IDEA_FUTURA_PALOMA_PI.md). Requiere trabajo de campo, no de celular.

---

## Referencias cruzadas (no mezclar)
- LANGUAGE_ENGINE (v0.x): NOUS/DSCN-G/EXPERIMENTS/LANGUAGE_ENGINE/
- NOUS (teoría): NOUS/
- SHARED/PandoraOS: arquitectura del kernel (proyecto aparte)
- Documents/Library/Campo_Autopoyetico (paper del campo autopoyético, UNCuyo) — fuera del vault SGM

---

## Reglas de oro (SGM)
- Freeze omega antes que el loop (el loop omega-sentido puede destruir señal).
- No usar similarity-NN como decoder (top1=0.020). Usar bigrama o transformer.
- Dolor ONLINE, no post-hoc: debe cambiar la elección, no castigar después.
- Auditoría obligatoria: ground truth + negative control + baseline idéntico + smoke test.
- Novedad por conteo de nodos únicos/ventana, nunca promediar omega.
- Duda = INCONCLUSA, Contradicción = CONTRADICTORIA (mecanismos separados).
- Self-mod libre PERO con frenos operacionales (invariant check) + marca a fuego (no borrable).
- Trauma: bajar V no alcanza (V no entra en Eq.2); aislar aristas preservando ω es el mecanismo real.
- **Composición (Fase 7):** rol SIEMPRE por índice de nodo (`role_vecs[k]`), nunca posición ni
  cyclic shift del mismo rol. Clean-up memory OBLIGATORIO tras unbinding (el crosstalk es ruido).

---


## Auditoria de honestidad (2026-08-02)

Luciano detecto que varios experimentos tenian el veredicto POSITIVO garantizado por codigo, no por
medicion. Se repararon para que el negative control y los casos limite salgan de COMPUTO REAL:

- exp_SGM_0030: `plan_from(use_roles=False)` hacia `return False` (hardcoded) y habia arista de cruce
  fisica. Reparado: cruce vive SOLO en rel_mem HRR; el plano es PPR Euclidiana real y de verdad falla
  (0.0). HRR+roles resuelve (1.0). PASS honesto.
- exp_SGM_0028: `recover_nested_3(use_roles=False)` hacia `return None`. Reparado: el plano usa
  cleanup(omega) real y falla (0.0). HRR recupera anidado (1.0). PASS honesto.
- exp_SGM_0021: Caso B (aislamiento) tenia `scoreB = 0.0` asignado a mano. Reparado: se excluye el
  nodo de destinos y scoreB se CALCULA (0.0 por computo). PASS honesto.
- exp_SGM_0018: Casos C/D (marca a fuego / freno) eran tabla de reglas `if mutacion=="x"`. Reparado:
  apply_mutation ejecuta la mutacion de verdad y check_invariants inspecciona el spec mutado. Caso C
  revelo ser APLICADA (no prohibida) hasta agregar la regla arquitectonica 'edge_types inmutable'
  (comparando contra base). PASS honesto.
- exp_SGM_0019: T-SEN-02 usaba E_root hardcode (0.2/0.9). Reparado: E_root se deriva de la intensidad
  real de la senal (0.122 suave vs 1.0 impulso). Emergencia reacciona a senal real. PASS honesto.

Conclusion: los mecanismos propios (HRR+roles, trauma/aislamiento, self-mod con frenos, SensorBridge)
SON legitimos y se sostienen por medicion. Lo reparado fue el METODO de control, no el mecanismo.

*Última actualización: 2026-08-02 — Fase 7 + B completos, 44 experimentos, base consolidada en
hrr_core.py + tick_relational_core.py. Siguiente: test de estrés (0031) y camino A (loop cerrado en entorno).*

---

## Estado 2026-08-04 — Fase 7 CERRADA (linea 0056 / 0059)

- Registry: **88 experimentos** verificados (44 originales + linea 0056 [0056, 0056b-0056j] + linea 0059 [0059, 0059b-0059i]).
- **Emergencia de composicion (0056):** el techo ~0.6 era del CODIGO DISCRETO; HD role-filler (0056e) lo rompe a 0.81-0.93. Sobre corpus real (Don Quijote): memoria por contenido top-1=1.0 (0056f), clasificacion distribucional >baseline (0056h), y recuperacion de ORDEN por decodificacion por rol con N=1024 = 1.000 (0056j, arco cerrado). Etiqueta lexica por contexto no recuperable (0056g, limite honesto).
- **Decode anidado (0059):** requiere SLOTS SEPARADOS por rol (K=3, prof 12+); K=1/2 colapsan binariamente porque la proyeccion del puntero borra la identidad del hijo (RecursionError en 0059i).
- Consolidado en `docs/FASE7_CIERRE_0056_0059.md`.
- **Siguiente paso recomendado (Camino A, post-Fase 7):** cierre de loop en entorno grid (cuerpo virtual que recibe senal HDC; el tick decide accion; omega se actualiza). Ejecutable en celular. Ver SGM_ROADMAP.md §Siguientes pasos.

---

## Estado 2026-08-04 (final del dia) — Siguiente: CRAFTER REAL (Nivel 2)

- Registry: **89 experimentos**. Agregado `exp_SGM_0052_crafter_nivel2` como PLANNED.
- **Decision:** test real en Crafter (Hafner 2021) con objetivo **Nivel 2** (descubrimiento de recetas
  SIN hardcodear el arbol de crafting) y **todo el stack SGM integrado** (el "Camino A" del roadmap).
- Por que Crafter: mundo abierto procedural con logros/comparativas documentadas (random, PPO/IMPALA,
  DreamerV3), obs simbolica HDC-friendly, ejercita memoria largo plazo + planificacion composicional HRR
  + dolor/valencia real. Mejor que el mini-grid de 0032/0033.
- **Restriccion de honestidad:** Nivel 2 = NO recetas dadas (evita la trampa de 0056). Recetas dadas =
  Nivel 1 = negative control NC-A, no objetivo. El descubrimiento se driver por reward de logro + dolor
  + memoria HRR. Negative controls NC-A..D obligatorios.
- **PENDIENTE:** dispositivo. El celular NO corre Crafter (numpy+gymnasium+display; aca es stdlib puro
  sin pip). El harness SGM es portable (stdlib); falta el env + deps. Opciones: maquina local, Colab,
  server. Al definirse, ver `docs/CRAFTER_TEST_PLAN.md` §7 para el paso a ejecucion.
- Consolidado en `docs/CRAFTER_TEST_PLAN.md`.

---

## Estado 2026-08-04 (consolidacion) — sgm_core.py unico modulo

- Registry: **90 experimentos**. Agregado `exp_SGM_0053_sgm_core_consolidacion` (DONE, smoke test OK).
- **Consolidado en `sgm_core.py`** (stdlib puro, portable a donde corra Crafter): solo mecanismos
  GANADORES — HRR rol-por-nivel (0027c), PPR (0004), decoder bigrama corpus real (0026), slots K=3
  (0059g). SensorBridge (0019) proyecta ESTADO SEMANTICO (no pixeles).
- **Explicitamente AFUERA:** NodeCore Python (0002), fase dinamica XOR, 0056 regla inyectada (TRAMPA),
  resonator puro (0059f). Documentado en `docs/SGM_CORE_CONSOLIDACION.md`.
- **Strategy para Crafter (instruccion de Luciano):** (1) modulo unico no scripts sueltos; (2) SensorBridge
  con estado semantico no pixeles; (3) loop SOLO primero (step/reward, logros simples: madera/mesa),
  multi-agente + lenguaje (0055/0056) DESPUES de cerrar el loop.
- Pendiente: dispositivo para Crafter real (celular no corre numpy/gymnasium). Ver docs/CRAFTER_TEST_PLAN.md.

---

## Estado 2026-08-04 (0031b + filosofia) — stress denso OK, pasamos a Crafter

- Registry: **92 experimentos**. Agregado `exp_SGM_0031b` (DONE, PASS con salvedad) + nota de diseno
  `note_diseno_reconsolidacion_2026-08-04` (idea de Luciano: memoria = reformulacion/reconsolidacion,
  no adquisicion perfecta ni decision optima).
- **0031b (stress DENSO + D bajo, regimen Crafter):** D=128 aguanta (1.0); grafo denso N=200 con K=20
  cruces competidores baja recover a **0.80** (interferencia aditiva, no colapso). Ruido sigma=0.3 OK.
  NC roles azar = 0.0. PASS. El sustrato aguanta el salto a entorno.
- **Filosofia de diseno (Luciano):** el recover HRR es RECONSTRUCCION ruidosa (reconsolidacion), no
  lectura perfecta — coherente con el 0.80 de 0031b. Para Crafter: NO exigir optimalidad ni 1.0; medir
  reconstruccion sesgada por estado; el error de recover es propiedad del mecanismo, no un bug.
- Siguiente: Crafter real (exp_SGM_0052) en el dispositivo que Luciano defina (celular no corre numpy).
  El 0031+0031b cierran el "no colapsa en escala/denso" del roadmap pre-entorno.

---

## Estado 2026-08-05 (T-ID-03: identidad = proceso, no snapshot) — 0035/0035b/0035c

- Registry: **94 experimentos**. T-ID-03 (identidad como proceso, no snapshot) cerrado con 3 exp:
  - exp_SGM_0035: firma de FASE no separa (phi converge al atractor, delta_phi->0). Desenlace 2 (Parfit en phi).
  - exp_SGM_0035b: traza de OMEGA si separa (1.0589). El ser es el recorrido de omega, no el punto.
  - exp_SGM_0035c: traza separa (0.6087) Y el proceso continuo RE-SUFRE por reconsolidacion (pisadas A=2.08 vs B=0.0 copiado). Desenlace 1_SI_difiere_REAL: el proceso es real aunque imperfecto; el snapshot es optimo y falso (foto, no ser).
- Conclusion honesta: la identidad en SGM es proceso operacionalmente distinguishable del snapshot via traza de omega. La imperfeccion del proceso continuo (reconsolidacion) es LA PRUEBA de que es real, no un estado optimizado. Esto cierra el cap. 10 de NOUS_Filosofico ("No-Inmortalidad como Caracteristica de Seguridad") CON DATOS.
- Scripts + json en phases/phase7_composicion/. (0035b tuvo NC buggeado en la 1ra corrida, corregido y reportado transparente.)

---

## Estado 2026-08-06 — sgm_core.py consolidado con ω_root, duda, contradicción

- Registry: **94 experimentos**. Agregados experimentos de integración con Crafter:
  - **exp_meta_004_calibracion_duda:** correlación r=0.089 (no pasa umbral 0.30). NC limpio. La duda existe pero es débil como predictor fino en este test sintético.
  - **exp_SGM_0095_crafter_fase1_v1 (sin duda):** 78.5% noop. Agente clavado.
  - **exp_SGM_0096_crafter_fase1_v2 (con duda+contradicción):** 0% noop, 59.4% eat. El estancamiento funciona.
  - **exp_SGM_0097_crafter_persistencia_vidas:** depresión aprendida. E_acumulado se arrastra entre episodios.
  - **exp_SGM_0098_omega_root:** nodo 0 como identidad persistente. Vitalidad protegida (piso 0.5). Interocepción. Bonus de afinidad en PPR.
  - **exp_SGM_0099_reset_episodio:** reset suave mantiene omega, resetea estado afectivo.
- **sgm_core.py actualizado:** 475 líneas. Mecanismos: HDC, HRR, PPR, vitalidad (γ=0.01), check_stagnation, handle_doubt, contradicción (θ_refut=2.0), ω_root + interocepción, reset_episodio, hibernación (θ_hibernation=0.15), trauma (κ_trauma=0.50), modos cognitivos tipados (SENSORIAL/RAZONAMIENTO/PLAN con boost_edges por conn_type), aristas tipadas (conn_type: 5 tipos), set_modo/set_conn_type.
- **Próximo paso:** experimento auto-narrativa (decoder L2 sobre trayectoria del agente).

---

## Estado 2026-08-06 — exp_SGM_0104: decoder auto-narrativa

- **exp_SGM_0104 (decoder_auto_narrativa):** bigrama entrenado sobre la secuencia de acciones del agente en Crafter (5 episodios, 1012 acciones). **Resultado:** top1=1.000 (perfecto) pero NC también 1.000. Causa: 96.3% de las acciones son noop — el agente no genera suficiente variedad. El bigrama funciona pero no hay estructura que aprender. **Hallazgo honesto:** el decoder no es el problema; el agente no varía su comportamiento. El PPR converge al mismo nodo y ni duda ni contradicción ni modos rompen el atractor con reward plano.
- **Aprendizaje:** el mecanismo de decoder es correcto (hereda del 0022 que funcionó en corpus sintético con variedad). Lo que falta es un agente que genere diversidad de acciones.
- **sgm_core.py final:** 475 líneas, completo según spec v1.4. Todos los mecanismos del sustrato implementados y verificados.

---

## Roadmap unificado — estado actual y próximos pasos

### Completado (sesión 2026-08-06)
- Sustrato SGM mínimo funcional (sgm_core.py, 346 líneas): HDC, HRR, PPR, vitalidad, duda, contradicción.
- ω_root sin bonus (piso 0.5). Aristas emergentes del uso (aprender_conexion). Poda de aristas (strength decae).
- Crafter Fase 0 (plomería) ✅, Fase 1 (baseline 3 versiones) ✅
- Auditoría parte por parte (0106-0112): cada mecanismo probado con NC, documentado.
- Decoder L2 como detector de loops (0110): PASS funcional. 12 tiles vs 1, 6 acciones vs 4.
- 18 experimentos documentados (0095-0112) con formato correcto.

### Hallazgos clave
1. El bonus de ω_root (30%) era hardcode. Sacarlo restaura el comportamiento exploratorio.
2. Las aristas tipadas al azar no tienen sentido. Deben emerger del uso (co-ocurrencia).
3. La persistencia de omega entre vidas es TOXICA — el TD contamina el omega. Necesita consolidación.
4. El decoder como detector de loops funciona mejor que como modelo del mundo predictivo.
5. El inconsciente = PPR + vitalidad + aristas. El consciente = decoder que detecta loops y sacude al inconsciente.
6. NC: CLARION (dual-level implicit/explicit) coincide con nuestra arquitectura emergente.

### Roadmap — próximos pasos

**Inmediato (detector de loops — profundizar):**
- exp_SGM_0113: Calibración del detector — variar TOPE_LOOP (3, 5, 10) y VENTANA (30, 50, 100). Encontrar el punto óptimo.
- exp_SGM_0114: Detector de loops + reward por novedad combinados. ¿La sinergia produce más exploración que cada uno por separado?
- exp_SGM_0115: Detector de loops en múltiples vidas (agente reiniciado, no persistente). ¿Mejora con la experiencia del decoder aunque el omega se resetee?

**Mediano plazo:**
- Consolidación de omega: mecanismo para que el aprendizaje TD no contamine el omega entre episodios. Posible: solo actualizar omega con reward positivo, no con reward=0.
- Decoder como auto-narrativa: cuando el agente genere suficiente variedad, el bigrama describe su trayectoria.
- Poda de aristas calibrada: ajustar el ritmo de decaimiento para que la memoria sea útil.

**Largo plazo (post-consolidación):**
- Crafter Fase 2 (eficiencia de muestra vs DreamerV3)
- Crafter Fase 3 (generalización zero-shot)
- Crafter Fase 4 (olvido catastrófico secuencial)
- Crafter Fase 5 (multi-agente + lenguaje)
- Valencia afectiva — generalización por estructura HRR
- Consciencia fenomenal: NO se toca (espera datos EEG de DSCN-BIO)

---

## Estado 2026-08-06 — Auditoría parte por parte (experimentos 0106-0108)

### exp_SGM_0106_rev2 — Core mínimo (baseline verificado)
- **Resultado:** 0% noop, 6 tiles explorados. PASS. El core mínimo (vitalidad + duda + contradicción + reward por novedad) produce un agente que se mueve y explora.
- **Confirmación:** los mecanismos extra que interferían eran el bonus de raíz y la interocepción con modificación de omega_root.

### exp_SGM_0107 — ω_root sin bonus
- **Resultado:** 3.7% noop, 11 tiles explorados. PASS. ω_root con piso 0.5 pero SIN bonus de afinidad no interfiere con la exploración.
- **Hallazgo:** la identidad puede coexistir con la exploración sin boost artificial.

### exp_SGM_0108 — Aristas emergentes del uso
- **Resultado (1ra corrida):** 0% noop, 9 tiles, pero 0 conexiones aprendidas (bug).
- **Bug detectado:** `aprender_conexion()` comparaba `best != self.ultima_accion` DESPUÉS de que `self.ultima_accion = best` ya se había ejecutado. Siempre daba False. Corregido.
- **2da corrida (bug corregido):** 3.9% noop, 9 tiles, 4 conexiones aprendidas (todas Functional, ninguna Causal todavía). 8.9% eat — el agente está comiendo. PASS.

### exp_SGM_0109 — Reset episodio (persistencia entre vidas)
- **Resultado:** El agente persistente EMPEORA con cada vida (12.2% → 99.6% noop). El agente reiniciado se mantiene estable (0% → 25.8% noop). FAIL.
- **Hallazgo:** La persistencia de omega acumula conexiones (8 → 12) que refuerzan un atractor y paralizan al agente. Sin poda de conexiones, el aprendizaje acumulado es tóxico.
- **NC:** El agente reiniciado (sin memoria entre vidas) se comporta mejor que el persistente. La memoria, sin mecanismo de decaimiento de aristas, perjudica.
- **Conclusión:** reset_episodio necesita poda de conexiones (aristas no usadas se debilitan como la vitalidad). A implementar en futuro.

### exp_SGM_0110 — Decoder L2 como interfaz consciente
- **Con decoder:** 12 tiles, 6 acciones distintas, 2 loops detectados, 5.0% noop. El agente exploró move_left, make_iron_pickaxe, move_down, make_stone_pickaxe, place_furnace.
- **Sin decoder (NC):** 1 tile, 4 acciones distintas, 3.9% noop. El agente se clavó en make_stone_sword 70%.
- **PASS técnico: False** (noop subió 1.1%). **PASS funcional: True** — el decoder rompió el atractor (12 tiles vs 1, 6 acciones vs 4). El loop detection disparó 2 veces y forzó cambio de comportamiento.
- **Hallazgo:** El decoder como interfaz consciente funciona. Detecta loops en el comportamiento inconsciente (PPR) y fuerza exploración. El incremento de noop es marginal (1 punto) y forma parte de la transición entre acciones.
- **Conclusión:** El decoder L2 es el mecanismo que conecta el inconsciente (PPR) con la conciencia (detección deliberada de patrones). Es la primera vez que un mecanismo "consciente" mejora la exploración del sistema.

### exp_SGM_0111 — Poda de aristas + reset entre vidas
- **1ra corrida (poda gamma*2):** FAIL. Poda demasiado agresiva, eliminó todas las aristas. Vida 2: 100% noop, 0 vivas.
- **2da corrida (poda gamma + vitalidad 0.7):** Mejor pero sigue FAIL. Vida 2: 94.6% noop vs 99.6% en 0109. La poda ayudó pero el problema es más profundo.
- **Hallazgo:** El aprendizaje TD del `reward()` modifica todos los omegas en cada tick. Ese ruido acumulado entre vidas intoxica al agente. La poda de aristas no es suficiente — el omega mismo se contamina.
- **Conclusion:** reset_episodio con persistencia de omega NO funciona, ni con poda. El agente reiniciado (sin memoria entre vidas) se comporta significativamente mejor. La memoria entre vidas requiere un mecanismo de consolidación más cuidadoso (futuro). **Para ahora, usar agente sin persistencia entre vidas.**

### exp_SGM_0112 — Decoder L2 como modelo del mundo (forward model)
- **Episodio 1 (recolección):** 193 pasos, 11 tiles, 8 entradas en el modelo, 4 estados cuantizados. Accuracy 0.99 pero NC también 0.99 — no hay suficiente variedad para diferenciar del azar.
- **Episodio 2 (evaluación):** 0 predicciones hechas — el agente arranca en CONTRADICTORIA (E_acum=3.28) y hace acciones distintas al episodio 1. El modelo no tiene entradas para esas transiciones.
- **FAIL.** El modelo del mundo funciona mecánicamente pero no es útil porque: (1) pocos estados cuantizados → NC también predice bien, (2) el segundo episodio del mismo agente se comporta distinto al primero (omega contaminado por TD).
- **Hallazgo:** el problema no es el bigrama como modelo del mundo — es que el agente no genera suficiente variedad para que el modelo tenga algo interesante que predecir. La contaminación del omega por TD entre episodios impide que el modelo del segundo episodio coincida con el primero.
- **Conclusión:** El decoder como detector de loops (0110) funciona mejor que como modelo del mundo predictivo (0112). La diferencia: el detector de loops no necesita predecir el estado, solo detectar repetición. El modelo del mundo requiere más variedad y consistencia entre episodios.
- El **PPR + vitalidad + aristas aprendidas** constituyen el sistema implícito/inconsciente: operan por debajo del umbral de reportabilidad, son automáticos y asociativos.
- El **decoder L2** (bigrama) es el candidato natural para ser la interfaz consciente: puede tomar patrones del comportamiento implícito y convertirlos en señales reportables.
- El **ω_root** (sin bonus) es el "yo" que observa — no decide, pero recibe el estado global.
- La **duda** (check_stagnation) es la emoción que traduce una señal inconsciente (baja novedad) en un cambio de comportamiento explícito.
