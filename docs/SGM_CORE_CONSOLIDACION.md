# CONSOLIDACION SGM_CORE (2026-08-04) — un modulo, no 63 scripts sueltos

**Motivo:** preparar el test real en Crafter (exp_SGM_0052) sin repetir el desorden de 63 experimentos
sueltos. Se consolidan SOLO los mecanismos GANADORES en `sgm_core.py` (stdlib puro, portable a donde
corra Crafter: Colab/maquina local/server).

## ADENTRO (ganadores validados)
- **HRR + rol-por-nivel (0027c / hrr_core):** composicion relacional. Rol = role_vecs[indice_nodo] (NO
  posicion ni cyclic shift — ese era el bug de 0029). Bind=conv circular (signo i-k, 0027), unbind=
  correlacion, cleanup OBLIGATORIA (VSA survey).
- **PPR (0004):** ruteo multi-hop con restart (alpha=0.15). Supera resonancia local 1-paso.
- **Decoder bigrama validado en corpus real (0026):** top1 >> azar y > lineal; shuffled cae a azar.
- **Slots separados K=3 (0059g):** anidado profundo (prof 12+). K=1/2 colapsan binariamente.

## AFUERA EXPLICITAMENTE (no ganaron / fallaron / trampa)
- **NodeCore en Python (0002):** no aporto rendimiento medible; usamos omega como lista de floats.
- **Fase dinamica para XOR:** fallo documentado; no se reimplementa.
- **0056 con regla inyectada:** TRAMPA (gramatica hardcodeada en aprendiz); excluida por honestidad.
- **Resonator puro (0059f):** techo confirmado, NO rompe; usamos slots K=3 (0059g).

## SensorBridge (0019) — alimentacion
El HDC proyecta ESTADO SEMANTICO (inventario/logros/salud de Crafter) -> omega. **NO píxeles crudos**
(instruccion de Luciano): meter vision encima del problema ya resuelto = debuggear dos cosas a la vez.

## Bucle (instruccion 3 de Luciano)
`SGMAgent.step(state, valid_actions)` y `SGMAgent.reward(r, pain)`: percepcion->tick->accion SOLIDO.
**NO se incluye multi-agente ni capa de lenguaje (0055/0056)** en esta primera pasada: cerrar el loop
solo primero (logros simples: cortar madera, hacer mesa), y recien despues sumar 2do agente + lenguaje.
Si se meten las dos capas juntas y algo falla, no se sabe cual rompio.

## Arquitectura del modulo
- `HDC(rng,D)`: project(signal)  (SensorBridge 0019)
- `HRR(D,rng,n_roles)`: bind/unbind/cos/cleanup/role/relational_memory/recover  (0027c)
- `ppr_route(adj,seed,aff_fn)`: ruteo (0004)
- `BigramDecoder(counts)`: top1/top5 (0026)
- `SGMAgent(...)`: step/reward (integra todo en un agente vivo)
- `build_nested_K3(...)`: anidado profundo slots separados (0059g)

Smoke test (`python sgm_core.py`): OK, stdlib puro, recover HRR = 1.0.
