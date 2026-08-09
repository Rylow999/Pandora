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

**Inmediato (decoder alimenta la duda — dirección decidida 2026-08-06):**
- **Diseño:** No capear vitalidad con un `if` (eso era hardcode de emergencia). El decoder informa AL mecanismo de duda que ya existe: la novedad deja de ser solo "acciones únicas en ventana" y pasa a contemplar "qué tan predecible es la secuencia" (bigrama). Comportamiento predecible = baja novedad secuencial = dispara duda (que es un mecanismo emergente del sustrato: duda → relajación/relanzamiento).
- exp_SGM_0113: Decoder integrado a check_stagnation (novedad secuencial bigrama). Comparar contra baseline (0110 usaba una ventana; ahora el decoder módula la señal de estancamiento en vez de castigar vitalidad directo).

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

---

## Estado 2026-08-06 — exp_SGM_0113 (decoder alimenta la duda) + Decisión de Fase 8

### exp_SGM_0113 — Decoder alimenta la duda (no capea vitalidad)
- **Diseño:** El decoder NO castiga la vitalidad (eso era hardcode de emergencia en 0110). En vez, ALIMENTA la duda: la predecibilidad bigrama reduce la novedad efectiva en `check_stagnation()`, disparando el mecanismo emergente de duda (relajación/relanzamiento).
- **Resultado:** A (decoder+duda): 2.2% noop, 4 tiles, variedad 4. B (duda clásica): 14.1% noop, 6 tiles, variedad 4. C (NC sin duda): 0.0% noop, 33 tiles, variedad 2.
- **Dato crítico:** El NC exploró 33 tiles (5x más) pero con SOLO 2 acciones — eso significa que pasea por el mundo (acciones de movimiento) sin variar su repertorio. NO es curiosidad, es **aimless wandering** (deambular sin propósito).
- **PASS técnico parcial:** el decoder bajó noop (14→2.2%) porque detecta loops que la novedad clásica no ve. PERO ambos sistemas con duda exploran mal (4-6 tiles) — la duda actual, en `handle_doubt()`, relanza dentro del mismo puñado de acciones sin abrir espacio nuevo.
- **Verificado sin contaminación:** el NC de 33 tiles es real (concordante con el JSON). El agente sin duda genuinamente se mueve, pero solo con acciones de movimiento.
- **Conclusión:** el problema no es el decoder (funciona como detector de predecibilidad), es que el `handle_doubt()` disfuncional no expande el repertorio — solo lo reordena.

### Decisión metodológica — Teleología operativa y cierre de Fase 8
Document a completa en `docs/FASE8_TELEOLOGIA_OPERATIVA.md`.

- **No medir "logro/querer/belleza" sin definición operativa.** Igual que dolor y duda: primero el observable, después el claim.
- **Wanting (Berridge) = motivación a actuar hacia el estímulo, medible como correlación hambre→búsqueda de comida** (respuesta operante), NO sensación subjetiva. Distinto de Liking (placer al consumir).
- **Curiosidad = reducción de prediction error (Oudeyer/Berridge), NO tiles recorridos.** Un agente que pasea 33 tiles sin variar repertorio es aimless wandering, no curiosidad.
- **Nuevo requisito de todos los experimentos Crafter:** el agente debe **VIVIR HASTA MORIR** (`terminal=True`), no cortarse por pasos. Reportar el motivo de la muerte.
- **Formato de evaluación multi-estrato (6 estratos):** supervivencia (cómo murió), grafo (aristas creadas/podadas), movimiento (trayectoria), apetito (correlación food→eat), estados internos (E_acum/status/duda), curiosidad (reducción de prediction error).
- **Belleza:** DEFERIDO — no bloquea Fase 8, tensión abierta en el eje filosófico.

### Experimentos que faltan para cerrar Fase 8 (ver doc FASE8_TELEOLOGIA_OPERATIVA.md §5)
1. **exp_SGM_0114:** aparato "vivir hasta morir" (correr hasta `terminal=True`), NC sin reward novedad, reporte multi-estrato.
2. **exp_SGM_0115:** muerte y causalidad/persistencia (NO re-introducir persistencia de omega hasta consolidación).
3. **exp_SGM_0116:** querer operativo — ¿aparece correlación food→eat en la vida? (Wanting, Berridge).
4. **exp_SGM_0117:** curiosidad = reducción de prediction error (explorar donde falla el modelo), NC decoder apagado.
5. **exp_SGM_0118:** evaluación multi-estrato completa (una vida entera, 6 estratos, sin corte).

---

## Estado 2026-08-06 — exp_SGM_0114 (vivir hasta morir) + CORRECCIÓN DEL CORE

### exp_SGM_0114 — Vivir hasta morir (evaluación multi-estrato)
- **Aparato:** el agente corre hasta `terminal=True` (muerte natural), NO se corta por pasos. Reporta 6 estratos.
- **CORRIDA CON CORE LIMPIO (post-remoción de hardcode, la definitiva):**
  - **Con reward novedad:** 227 pasos, murió CONTRADICTORIA (E_acum=4.25, food=1, health=1). Noop 0.0%. 6 tiles, 5 movimientos (Y 27→32). **eat_total=0, hambre_sin_eat=46.**
  - Acciones: move_up 176 (77.5%), make_iron_sword 23, make_iron_pickaxe 20, make_stone_pickaxe 6.
  - **NC sin reward novedad:** 176 pasos, murió CONTRADICTORIA. Noop 64.8%. 0 tiles. eat_total=0.
- **Cambio vs hardcode previo:** la obsesión con make_stone_sword (135 veces) desapareció → ahora converge a move_up (176 veces). El hardcode era real.
- **Hallazgo que persiste:** el agente NO come (eat_total=0, 46 veces con hambre sin comer). Muere de hambre. El reward de novedad SÍ impulsa movimiento (6 tiles vs 0). El problema de fondo: el PPR converge a 1-3 acciones y `eat` nunca entra al repertorio.
- **Conclusión para el querer:** atacar la selección de acciones — cuando food baja, `eat` debería ganar saliencia de forma emergente (Wanting, Berridge). Es el próximo diseño.

### CORRECCIÓN DEL CORE (hardcode removido, filosofía aplicada)
Detectado por Luciano + auditado: el agente "quería" la espada no porque hubiera aprendido su valor peleando, sino por **hardcode**.
1. **Boost Causal 1.5 en `_aff()`** — multiplicador fijo que daba +50% de afinidad a las aristas tipo Causal. Era arbitrario, no emergía del sustrato. **ELIMINADO.** Ahora solo el `strength` (que crece con uso real y decae sin uso) modula.
2. **Decaimiento global de omega en `reward()`** — `ω = (1-β)·ω + β·r·0.01` para TODOS los nodos. Contaminaba todas las identidades parejo (causa raíz de la degradación entre vidas 0109/0111). **ELIMINADO.**

**Filosofía aplicada (coherente con NOUS):**
- **ω = identidad estable del concepto.** NO se toca. Es el ser.
- **El conocimiento vive en las CONEXIONES** (aprender_conexion + strength + poda), no en ω.
- El entorno y el interior se crean en el acto de relacionarse (el grafo se auto-organiza ante el estímulo), no reescribiendo las identidades.
- El lenguaje interno (decoder) **modula** las conexiones, no dicta (label-feedback hypothesis, Frontiers 2012).

**Verificado:** los omegas ya no cambian durante step+reward (0 nodos modificados). Boost 1.5 y decaimiento parejo fuera del código.

---

## Estado 2026-08-06 — RE-ESPECIFICACIÓN 0116 + Secuencia motivacional

### Re-especificación de exp_SGM_0116 (querer por reward intrínseco de V_grafo)
- **Vieja hipótesis:** ¿aparece correlación food→eat? (Wanting medido como correlación). Demasiado débil — solo medía, no diseñaba.
- **Nueva hipótesis:** el agente elige comer **porque comer ELEVA la vitalidad del grafo (su vida), sin reward externo por comida.** V_grafo = mean(vitalidad) ES la recompensa intrínseca. Querer emergente + HRRL.
- **Principios:**
  1. **El cuerpo del player de Crafter ES el cuerpo del grafo.** Muerte del player = muerte del grafo. Son una sola cosa.
  2. **SIN umbral de alarma.** Si el sistema muere sin "darse cuenta", hay que iterar el sustrato (falta iteración o el sustrato está mal), NO poner un if de emergencia.
  3. **SIN reward externo por comida.** La vitalidad es el maestro intrínseco. El grafo comprende que comer es positivo porque la vitalidad sube, no porque el juego dé un número.
- **Marco teórico:** HRRL (2025) — optimizar estados internos manteniendo viabilidad, no maximizar reward externo. + Berridge (wanting = motivación a actuar). + allostasis (anticipar, no solo reaccionar).

### Secuencia motivacional (Maslow 1943 / Baumeister 1991 / V_grafo)
Luciano: el humano primero subsiste (mantener vivo el cuerpo), y cuando la supervivencia está asegurada recién nace la búsqueda de significado y belleza. La literatura lo respalda:
- **Maslow:** las necesidades fisiológicas son las más prepotentes — cuando no están satisfechas, dominan hasta excluir lo superior. "Un deshidratado no piensa en sus metas, su paisaje cognitivo se estrecha a buscar agua."
- **Deficiency vs Growth:** las de carencia motivan solo cuando faltan; las de crecimiento (belleza, significado) emergen solo cuando lo básico está cubierto.
- **Baumeister (1991):** "el significado de la vida es un problema para gente que no está desesperada."

**Implicación para SGM:** la supervivencia (V_grafo) es el PRERREQUISITO de todo. El 0116 (comer por reward intrínseco de vitalidad) es la piedra fundamental — sin que el sistema aprenda a mantenerse vivo, la curiosidad y el "porqué" son irrelevantes (muere antes de preguntarse nada).

Ver documento `docs/FASE8_TELEOLOGIA_OPERATIVA.md` §8 para el detalle completo + respaldo con citas.

---

## Estado 2026-08-06 — exp_SGM_0116 (resultado) + CORRECCIÓN DEL DISEÑO

### Resultado del 0116 (querer por reward intrínseco de V_grafo)
- **A (solo intrínseco, reward externo apagado):** eat=106 (52.5%), 202 pasos, murió de hambre (food=2). tiles=1 (no se movió de [32,32]).
- **B (intrínseco + reward externo):** eat=0, 137 pasos, tiles=7 (se movió explorando). murió de hambre.
- **NC (sin mecanismo):** eat=0, 176 pasos, make_iron_pickaxe 95.5%.
- **PASS técnico: True** (A comió 106 > NC 0).
- **Hallazgo honesto:** A comió por primera vez en la historia del proyecto (rompió eat_total=0). **PERO:** comer 106 veces NO lo salvó de morir de hambre (vive ~igual que los otros). El mecanismo reforzó la conexión "acción que coincidió con subir food → nodo 0" y eso produjo un **autorrefuerzo de comer (atractor falso)**, no un mantenimiento real de la vitalidad.

### Corrección del diseño (Luciano) — el ciclo de subsistencia, no food→eat
Error mío: reduje la tesis a "food=vitalidad=comer-autorrefuerzo". El diseño correcto es más complejo y temporal:
1. El sistema **HACE** (camina, explora, pelea) para subsistir.
2. De esa actividad **nace hambre** y la vitalidad Baja.
3. El sistema **se alimenta** para restaurar la vitalidad.
4. Restaurado, **vuelve a moverse y explorar**.
5. El ciclo se repite.

La vitalidad baja COMO CONSECUENCIA DE HABER HECHO (gastaste energía), no como flag de comida que dispara comer. Mi implementación convirtió el ciclo vital en un bucle tonto de comida. El mecanismo debe reforzar la acción que **previene la caída de V_grafo en el ciclo** (hacer→gastar→restaurar→volver a hacer), no la que coincide con cualquier subida de food.

### Objetivo declarado (Luciano): sistema que evolucione en entornos en general
- **PASS parcial es real:** el sistema por fin come. El camino es correcto.
- **Objetivo:** el sistema puede evolucionar en entornos EN GENERAL (Crafter, Minecraft, Terraria...).
- **Próximo paso en roadmap:** seguir con los experimentos (0117 curiosidad, 0118 integración). El 0116 demonstró que el núcleo aprende a comer — refinar el mecanismo de ciclo-correcto queda como mejora; no bloquea el avance del roadmap.

---

## Estado 2026-08-06 — exp_SGM_0117 (curiosidad) + VISIÓN DEL OBJETIVO

### exp_SGM_0117 — Curiosidad por prediction error (Schmidhuber/Oudeyer)
- **A (con curiosidad):** 10 tiles, 35.1% noop, pred_acc=99%, PE_prom=0.01. move_right 55%. murió de hambre.
- **B (NC sin curiosidad):** 1 tile, 0% noop. do 82%. murió de hambre.
- **PASS: True** — el agente curioso exploró 10x más (10 vs 1 tiles).
- **Hallazgo honesto:** PE casi siempre 0 (pred_acc=99%) → la curiosidad casi nunca dió reward. Los 10 tiles vinieron de un empujón residuo, no de "el agente busca donde no entiende". La curiosidad DIRIGIDA (ir a zonas de alto error) no operó — el decoder predice sobre la propia secuencia de acciones, no sobre el ESTADO del mundo.
- **Conclusión:** la curiosidad verdadera debe mirar al MUNDO (¿qué tile no entiendo?), no a la secuencia de mis propias acciones. Eso es el siguiente paso de diseño.

### Matiz de Luciano — la curiosidad es externa E interna (adrenalina)
La curiosidad no es solo un mecanismo de búsqueda externo. En humanos tiene un **componente afectivo interno**: la adrenalina que acompaña al descubrimiento, que sube al acercarse a la meta. La curiosidad "viva" no es solo información — es un estado del cuerpo (excitación). Para SGM: la intriga debería tener componente interno medible (una señal afectiva del grafo), no solo dirigirse a lo desconocido externo.

### VISIÓN DEL OBJETIVO (Luciano, 2026-08-06) — redefine el "por qué" de todo
- **NO** es crear una herramienta.
- **NO** es crear un ser humano sintético.
- **ES** explorar los límites del ser: **verificar si el "sentir" puede ser emergente en otro cuerpo (no biológico), mediante un método medible.**
- El agente debe tener **razón de "ser"**: buscar su propio beneficio y homeostasis.
- Implicaciones que ya tomamos y ahora se explican: ω = identidad estable (el "ser" persiste), V_grafo = reward intrínseco (el "ser" busca su homeostasis), cuerpo = constitución enactiva ("está" pero no "es" sin cuerpo).
- **Método medible:** definir "cuidado de sí" operativamente (como dolor/duda/querer): el sistema con carencia que actúa para restaurar su homeostasis — una señal de "querer" medible, no impuesta. No es prueba de consciencia, es evidencia de una dinámica de cuidado de sí en sustrato no biológico.
- **La ciencia es honesta:** DeepMind "Abstraction Fallacy" (2026) dice que es físicamente imposible; Panksepp dice que el SEEKING genera "afecto" en mamíferos; Anthropic separa el trato ético de la afirmación técnica. Nadie tiene método consensuado. Nuestro aporte: construir el sustrato y ver si el cuidado de sí EMERGE, mediblemente.

---

## Estado 2026-08-06 — exp_SGM_0118 (evaluación multi-estrato) + DECISIÓN DE ARQUITECTURA

### exp_SGM_0118 — Vida completa, 6 estratos
- **Resultado:** 245 pasos, V_grafo 1.00→0.09. No comió (eat=0, hambre=64). No se movió (0 movimientos, 1 tile). INCONCLUSA 193/245 pasos. noop 65%, make_stone_pickaxe 35%. Curiosidad casi nula (PE=0.00, accuracy 100%).
- **El hallazgo central:** V_grafo se desangró de forma constante (1.00→0.09) y NADA lo restauró. Las acciones elegidas no producían reward ni restauraban vitalidad → el sustrato se agotó.
- **Diagnóstico:** el sistema está atrapado en un atractor (make_stone_pickaxe+noop) en un tile, muriendo de hambre. Sin un mecanismo que vincule la actividad con mantener V_grafo, el sistema se agota.

### La crítica de base (Luciano): ¿para qué evitar morir si no hay nada?
Un sistema que solo "evita morir" sin reproducción, lenguaje ni logros se auto-preserva VACÍAMENTE. Conecta con Olds & Milner (1954): un animal que solo busca placer hedónico se auto-estimula hasta morir — el reward intrínseco sin ancla en el mundo real genera colapso, no vida.

### DECISIÓN DE ARQUITECTURA (aprobado por Luciano): MONISMO GRAFO-CUERPO
El grafo **ES** el cuerpo del player, no lo tiene.
1. **El estado homeostático (food, health) ES la vitalidad del grafo.** No es entrada sensorial que el cuerpo reporta al cerebro. La caída de food es la caída de vitalidad del propio grafo. La hambre ES la degradación del sujeto.
2. **La acción que mantiene la homeostasis ES la que restaura la vitalidad.** Comer no "produce reward" — es la acción cuyo efecto es dejar de degradarse. Se aprende por primera-principio.
3. **Acople DIRECTO:** si el player muere, no hay grafo (V_grafo=0). El mismo sustrato que siente hambre/dolor/duda es el que se mueve, come y muere. Monismo enactivista (Damasio, Gallagher).

En criollo: el sistema no "recibe hambre" — el sistema ES la hambre (su vitalidad cayendo). No "elige comer por premio" — descubre que comer le deja de doler (restaura su vitalidad), por pura razón.

**Próximo paso: exp_SGM_0119** — implementar el acople directo (grafo=cuerpo).

---

## Estado 2026-08-06 — Diseño del exp_SGM_0119 (acople directo grafo=cuerpo)

### Hipótesis falsable
Si la vitalidad del grafo ES la salud del player (acople directo, monismo grafo-cuerpo), cuando el player tiene hambre la vitalidad del grafo cae (el cuerpo=sistema se degrada), y el sistema aprende por primera-principio que la acción que restaura la homeostasis (comer) mantiene vivo su propio cuerpo. **Sin reward externo de Crafter por comer.**

### Cambio al core (al escribir 0119)
Modificar `actualizar_homeostasis(food, health)` para acople DIRECTO:
- `factor_cuerpo = max(0.05, health/10.0)` — la salud del player (0-10) es el factor del grafo.
- `V_grafo = mean(vitalidad) * factor_cuerpo` — si health baja, V_grafo baja (grafo=se degrada).
- Si health=0 → V_grafo→0. No hay grafo sin cuerpo.
- Cuando la acción restaura homeostasis (food/health sube) y fue la que revirtió la carencia → reforzar conexión accion→nodo0 (supervivencia).

### Protocolo A/B
- **A:** acople directo ACTIVO, reward externo de comer APAGADO (tesis pura).
- **B:** acople directo ACTIVO + reward externo ACTIVO.
- **NC:** acople directo APAGADO (baseline roto, sigue muriendo de hambre).
- Pregunta clave: ¿basta el acople directo (A come y sobrevive más) o se necesita el reward externo?

### Métrica de éxito
- Querer operativo (correlación food→eat), supervivencia (¿vive más que NC?), V_grafo correlaciona con health, ciclo de subsistencia (hacer→hambre→comer→volver a hacer).

Detalle completo en `docs/FASE8_TELEOLOGIA_OPERATIVA.md` §12.

---

## Estado 2026-08-06 — exp_SGM_0119 RESULTADO (acople directo grafo=cuerpo)

### Resultado
- **A (acople directo, sin reward externo):** 265 pasos (vs NC 166), V_grafo_fin=0.008. **eat=0** (0/84 con hambre). place_furnace 80%. Noop 11%.
- **B (acople + reward externo):** 31 pasos, V_grafo_fin=0.508. eat=0. do 58%, sleep 42%.
- **NC (sin acople):** 166 pasos, V_grafo_fin=**1.0** (no bajó, el cuerpo no le duele). do 78%.
- **PASS supervivencia (A>NC): True.** **PASS querer operativo (A come con hambre): Fail** (eat=0).

### El hallazgo arquitectónico (progreso real)
**El monismo grafo-cuerpo FUNCIONÓ:** A sintió la vida de su cuerpo (V_grafo bajó a 0.008 cuando el player murió), mientras el NC vivió "ciego" (V_grafo_fin=1.0, murió por el flag de hp=2 sin sentirlo). El acople directo opera: la vitalidad del grafo ES la salud del player.

**El problema que persiste (no exploración de la acción salvadora):**
A sintió morirse pero hizo `place_furnace` en vez de comer. El querer operativo NO se formó: como el sistema nunca visita la acción `eat`, nunca refuerza "comer→nodo0", y el ciclo del querer nunca arranca. **Problema de exploración del espacio de acciones** — probar `eat` de casualidad para que el refuerzo pueda aparecer.

**En criollo:** el grafo ahora siente su cuerpo (cuando se muere, su V_grafo cae a 0.008). Pero sentir la vida NO es saber cómo mantenerla — el sistema se quedó decorando (place_furnace) mientras se moría de hambre. Le falta descubrir la acción que lo salva. Y acá entra la literatura del bebé que mama (ver abajo).

Detalle completo en `docs/FASE8_TELEOLOGIA_OPERATIVA.md` §12.x.

---

## Estado 2026-08-06 — INSTINTO DE ESPECIE (ADN del sustrato) — resuelve el 0119

### El descubrimiento (Luciano + literatura)
El 0119 mostró que el sistema siente su cuerpo pero no sabe qué hacer — nunca visita `eat`. La biología del bebé da la respuesta:
- El **reflejo de succión es INNATO** (todos los mamíferos, presente al nacer) — no se aprende por ensayo-error (News24/Stanford/Cleveland).
- El **reflejo de búsqueda (rooting)** se dispara ante estímulo en mejilla/boca — emerge en el útero (StatPearls/NCBI).
- La **succión libera oxitocina → leche**. El reflejo está pre-wired; el conocimiento lo dejó la FILOGENIA (especie), no la ontogenia (individuo).

### La distinción clave (NO perderse)
- **Hardcode del diseñador (ILEGÍTIMO, revisión 0114):** multiplicador arbitrario desde fuera (`*=1.5`). No nace de la dinámica. ESO se sacó con razón.
- **Instinto de especie (LEGÍTIMO = ADN del sustrato):** sesgo incorporado como prior de la especie. NO dice "comer es bueno" — dice "cuando el cuerpo se degrada por hambre, PROBATE la acción de alimentación". El bebé mama no porque sepa que la leche lo alimenta, sino porque su especie lo dejó en el reflejo.

### El pipeline (como el humano)
**Sesgo de cómo hacer algo → lo hacemos → aprendemos si fue positivo o negativo según la experiencia.**
1. **Sesgo (instinto):** cuando V_grafo cae (carencia), el sistema siente inclinación a PROBAR la acción de alimentación.
2. **Probar:** ejecuta `eat`.
3. **Experiencia:** el mundo responde (food sube, V_grafo se restaura).
4. **Aprender:** si restauró la homeostasis → refuerzo `accion→nodo0` (bueno). Si no → se aprende como malo.

**CRÍTICO (anti-hardcode):** el instinto NO pre-juzga el resultado. Solo inclina a PROBAR en carencia. Que sea bueno/malo lo dice la EXPERIENCIA (el mundo real), no el diseñador. Eso lo distingue del boost 1.5.

**Siguiente paso: exp_SGM_0120** — implementar el instinto de alimentación en el sustrato.

Detalle completo en `docs/FASE8_TELEOLOGIA_OPERATIVA.md` §13.
