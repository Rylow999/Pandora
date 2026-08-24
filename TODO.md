# TODO: Modularización del Core SGM

## Problema
- 2251 líneas en sgm_core.py (debería ser ~300)
- Decoder L2 usa HRR bind/unbind con ruido (fallido en 0046-0048)
- No hay W·ω + b → softmax → token en el core
- Generar mensaje es template de ifs
- Test rápido del readme es hardcodeado
- Todo mezclado en un solo archivo

## Objetivo
Core SOLO con: HDC, HRR, PPR, Kuramoto, grafo, homeostasis + hook arbitro.
Todo lo demás en módulos.

## Módulos a Crear

### 1. sgm_hdc.py (~50 líneas)
- Clase HDC: proyección señal → omega
- SensorBridge: percepciones → vector semántico

### 2. sgm_hrr.py (~80 líneas)
- Clase HRR: bind/unbind, memoria relacional
- recover, cleanup, relational_memory

### 3. sgm_ppr.py (~30 líneas)
- ppr_route(adj, seed, aff_fn, alpha, iters)
- PageRank personalizado sobre grafo

### 4. sgm_kuramoto.py (~60 líneas)
- Kuramoto: actualización de fases
- Interferencia: I = ||ω|| · cos(φ - φ_root)
- step_k_cadenas: K=10 cadenas paralelas

### 5. sgm_grafo.py (~100 líneas)
- SGMAgent: omega, phi, vitalidad, edges, es_place_cell
- Grafo vivo: crear_nodo, crear_arista, reforzar_arista
- Omega inmutable para conceptos, mutable para place cells
- _mutar_omega() con protección

### 6. sgm_homeostasis.py (~80 líneas)
- actualizar_homeostasis(food, health)
- V_grafo = media(vitalidad) × factor_cuerpo
- Interocepción: dolor, hambre, seguridad

### 7. sgm_memoria.py (~150 líneas)
- Memoria episódica: buffer de eventos salientes
- Place cells: registro, navegación a meta
- Modelo de objetos: predicción posición futura
- NOUS: ventana dinámica W(t), densidad contextual ρ(t)

### 8. sgm_l2_decoder.py (~120 líneas)
- Piedra Rosetta: token ↔ omega determinístico
- Corpus: generar datos entrenamiento
- L2: W·ω + b → softmax → token (SIN HRR)
- DecodeL2: campo interferencia → promedio → proyección → token

### 9. sgm_comunicacion.py (~60 líneas)
- generar_mensaje(): campo interferencia → decode_l2 → texto
- SIN ifs, SIN templates
- Fallback L1 (Rosetta) → L2 (proyección)

### 10. sgm_razonamiento.py (~80 líneas)
- inducir(a, b): generalizar regla de casos
- deducir(a, b): verificar conexión/transitividad
- abducir(resultado): inferir causas (PPR inverso)

### 11. sgm_instintos.py (~120 líneas)
- Instinto alimentación: fuerza × carencia
- Instinto exploración: incertidumbre → curiosidad
- Instinto defensa: amenaza → respuesta
- Drive noop: energía libre acumulada
- Desplazamiento: necesidad insatisfecha

### 12. sgm_pulsiones.py (ya existe, verificar)
- 10 plugins de pulsiones
- Arbitro de modos (BASE/SUPERVIVENCIA)
- Hook: crear_arbitro_default()

### 13. sgm_core.py (~200 líneas) - REFACTOR
- Imports de todos los módulos
- step(): percepción → arbitro → acción
- NO lógica de negocio, SOLO orquestación
- Configuración centralizada

## Archivos a Eliminar
- experiments/sgm_l2_decoder.py (bigrama, obsoleto)
- experiments/sgm_lang_interfaz.py (ifs hardcodeados)
- experiments/sgm_metacognicion.py (plantilla vacía)
- experiments/sgm_crecimiento.py (placeholder)
- experiments/sgm_atencion.py (ifs)
- experiments/sgm_mundo.py (diccionario estático)
- experiments/pandora.py (orquestador viejo)
- sgm-core-ref.py (congelado, no necesario en repo)

## Criterios de Aceptación
- [ ] sgm_core.py < 300 líneas
- [ ] Cada módulo < 200 líneas
- [ ] Sin HRR en L2 (solo W·ω + b → softmax)
- [ ] Sin ifs en generación de mensajes
- [ ] Tests modulares (un test por módulo)
- [ ] 170+ experimentos siguen funcionando
- [ ] Omega inmutable para conceptos (verificado)

## Ejecución
1. Crear módulos nuevos
2. Migrar código del core a módulos
3. Limpiar core (solo orquestación)
4. Tests modulares
5. Actualizar README sin snippet hardcodeado
