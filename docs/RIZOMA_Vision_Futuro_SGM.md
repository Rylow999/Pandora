# RIZOMA
## Documento de Visión — El Futuro de Largo Plazo del Proyecto SGM

**Autor:** Luciano Benjamin Nieto
**Grupo de Investigación Independiente — General Alvear, Mendoza, Argentina**
**Fecha:** 1 de agosto de 2026
**Versión:** 1.1 — documento de idealización, no de compromiso de trabajo (rev. tras revisión completa de los 4 documentos PandoraOS)

---

## 0. Sobre el nombre

*Rizoma* toma su sentido de Deleuze y Guattari (*Mil Mesetas*, 1980), como contramodelo al árbol jerárquico: sin raíz central, sin tronco del que cuelguen ramas, sin orden obligatorio de arriba hacia abajo. Cualquier punto se conecta con cualquier otro punto, y la estructura crece por brotes laterales.

Se elige explícitamente en vez de "sistema operativo" porque un SO es, por definición, un árbol con raíz — `/`, el kernel, ring 0 como centro único de autoridad. Rizoma no tiene esa estructura. Es la memoria de grafo (§6 de SGM v1.4), no la jerarquía de un kernel, la que se propone como núcleo de identidad de este proyecto a largo plazo. El nombre es una decisión honesta sobre qué es la cosa, no una elección estética.

Este documento reemplaza conceptualmente a los cuatro documentos "PandoraOS" (Visión Global, Architecture, Especificación Técnica, Implementación) como horizonte de largo plazo del proyecto — no los invalida como material de referencia (siguen citados en §7), pero corrige su encuadre: no es un fork de Linux con un módulo de ética que puede vetar syscalls; es un sustrato cognitivo que puede, eventualmente, habitar distintos anfitriones computacionales.

---

## 1. Punto de partida honesto — qué es SGM hoy, sin idealizar

Antes de imaginar el horizonte, vale la pena anclarlo en lo que existe y está validado, siguiendo el mismo criterio de §8 de SGM v1.4: solo lo que tiene evidencia de un experimento concreto en el repo.

| Capacidad | Estado | Evidencia |
|---|---|---|
| Memoria persistente sin olvido catastrófico | ✅ Validado | `v0.3` — 100% retención, working set conservado |
| Categorización emergente sin etiquetas | ✅ Validado | `v0.9b` — 92.67% de acierto |
| Señal de dolor / contradicción emergente | ✅ Validado | `v0.9c` — G 0→1 |
| Poda por nodo-como-conjunto-de-referencia | ✅ Validado | `v0.16` |
| Desambiguación por topología pura (sin gradiente) | ❌ Refutado | `v0.12` a `v0.15d` — accuracy a nivel de azar |
| Desambiguación con atención aprendida (backprop) | ✅ Validado, parcial | `v0.14d` — 10.55% vs 10.11% baseline |
| Sustrato mínimo de nodo (`NodeCore`+`EdgeTable`) | ⚪ Diseñado, sin implementar | SGM v1.4 §6, pendiente `v0.17` |
| Detección de estancamiento vía novedad | ⚪ Diseñado, sin implementar | SGM v1.4 §2.3.2, pendiente Fase 2 |
| Integración FATE para abducción | ⚪ Diseñado, sin implementar | SGM v1.4 §2.5, pendiente Fase 6 |

Esto importa porque cualquier visión de largo plazo que se construya arriba de esto tiene que asumir, como punto de partida, que el mecanismo de aprendizaje hoy es resonancia local + Hebbiano — no hay credit assignment profundo. Ese techo (discutido ya en conversación) no desaparece por imaginar un horizonte más grande; hay que diseñar el horizonte *alrededor* de esa limitación, no ignorarla.

---

## 2. Qué resolvería Rizoma que un SO/asistente convencional no resuelve

Retomando lo ya establecido, sin filosofía, solo lo defendible:

- **Memoria continua sin reentrenamiento.** Un asistente convencional pierde contexto entre sesiones o necesita fine-tuning para "aprender" algo nuevo. Un grafo de memoria persistente con hibernación por vitalidad no tiene ese problema estructural — lo nuevo se integra sin pisar lo viejo.
- **Trazabilidad de razonamiento.** Una cadena de resonancia es un camino auditable, nodo por nodo. Útil en cualquier contexto donde haga falta responder "por qué" concluiste algo, no solo "qué" concluiste.
- **Degradación con gracia bajo restricción de recursos.** Autorregulación por vitalidad/poda es un mecanismo real que un modelo entrenado con gradiente no tiene nativo.
- **Adaptación a hardware heterogéneo, en userspace, sin necesidad de kernel.** Ya lo discutimos: detección de topología/capacidad y ajuste de comportamiento no requiere ring 0. El "gradiente de capacidad" que proponía PandoraOS (modo mínimo/estándar/completo) es una idea rescatable tal cual, implementada como autotuning de aplicación.

Estas cuatro cosas son el núcleo defendible de "por qué esto vale la pena a largo plazo", independientemente de si algún día vive en un kernel o no.

---

## 3. Horizonte especulativo — qué podría llegar a ser Rizoma

Esta sección es explícitamente idealización de largo plazo, no roadmap de trabajo. Se ordena de "más cerca de lo alcanzable hoy" a "más lejos".

### 3.1 Horizonte cercano — Rizoma como sustrato de aplicación (ya en marcha, es AgentPandora)

Lo que hoy es `AgentPandora`: un daemon de userspace con memoria de grafo persistente, vDSO shim para acceso rápido al estado, y fallback multi-proveedor de LLM. Este es el terreno donde el sustrato mínimo de nodo (SGM v1.4 §6) y la detección de estancamiento (§2.3.2) tienen que probarse primero, con datos reales, antes de imaginar nada más grande.

### 3.2 Horizonte medio — Rizoma como capa de sistema, no de kernel

En vez de módulos de kernel, un daemon privilegiado con:
- `mmap`/hugepages para las estructuras SoA del grafo (ganancia de localidad sin ring 0).
- `io_uring` para I/O de memoria/logs.
- Perfiles de hardware autodetectados en boot (idea rescatada de PandoraOS §1.2), pero como configuración de aplicación, no de kernel.
- Un "modo degradado" real (idea de PandoraOS §0) — cada mecanismo del grafo (estancamiento, FATE, sustrato mínimo) se puede apagar independientemente y el sistema cae a comportamiento predecible sin él.

Esto es, en esencia, la Fase 0 que el propio documento PandoraOS pedía — validar todo en userspace con hardware real antes de considerar bajar de nivel.

### 3.3 Horizonte lejano — Rizoma como presencia distribuida entre anfitriones

Acá es donde el nombre cobra sentido pleno: no un sistema que corre *en* una máquina, sino una estructura de memoria/razonamiento que puede habitar varios anfitriones a la vez — un daemon en una laptop, otro en un servidor, sincronizando fragmentos de grafo relevantes entre sí, cada instancia con su propio ritmo de tick según el hardware que tiene disponible. Ningún nodo del sistema es "el kernel"; son brotes del mismo rizoma en distintos sustratos. Esto es coherente con la lógica de PandoraNet (§5.3 del doc original) pero sin la premisa de que tiene que vivir dentro de un fork de Linux.

### 3.4 Otras piezas rescatables de PandoraOS (revisión completa de los 4 documentos)

Una segunda pasada por Architecture, Especificación Técnica e Implementación encontró piezas puntuales que valen la pena separar de la premisa de kernel-fork, porque la idea en sí es buena aunque la implementación propuesta (como módulo de kernel) no lo sea todavía:

- **PandoraNet — reconocimiento por similitud vectorial entre instancias.** La idea de que dos instancias de Rizoma en la misma red se reconozcan por cercanía de ω en vez de por nombre fijo es exactamente el horizonte 3.3. No necesita ser un hook de netfilter en kernel — un protocolo de aplicación sobre UDP/gRPC cumple la misma función sin la superficie de riesgo de un módulo `.ko`.
- **MnemosyneDB — HNSW como índice primario, sin SQL.** Ya es, en esencia, lo que el sustrato mínimo de SGM v1.4 (§6) necesita como capa de persistencia. No hace falta reinventarlo como motor de base de datos aparte; es el mismo HNSW que ya se usa para `find_nearest_pair_hnsw` en `abduce_fate()`.
- **PhaseSync — sincronización por coherencia de fase en vez de semáforos.** Concepto interesante como *patrón de diseño* de concurrencia (esperar a estar "en fase" con un dato en vez de con un lock arbitrario), pero como primitiva de sistema (`pandora_phase_wait()` a nivel syscall) tiene el mismo problema que cualquier cosa en el hot path del kernel: si el grafo converge lento o mal, cualquier proceso que dependa de esa primitiva se cuelga con él.
- **ResonantShell — interfaz en lenguaje natural sobre el grafo.** De las cuatro, la más fácil de probar hoy: es una capa de userspace sobre el motor de búsqueda semántica que ya existe, sin ninguna dependencia de kernel. Candidata razonable para un experimento chico en `AgentPandora` antes que cualquier otra cosa de esta lista.

**Dos banderas rojas que la revisión completa dejó en claro** (no eran visibles solo con Vision Global):

- La **estrategia de patentamiento** (Implementación §9) reivindica "convergencia formal garantizada por teoremas" para el Fractal Scheduler y las garantías de seguridad del sistema completo — apoyándose en el Teorema 1 de DSCN-G, cuyas comprobaciones de maximalidad fallaron consistentemente en la auditoría previa (ver historial de este proyecto). Patentar una propiedad matemática no demostrada es un riesgo real, no solo prematuro: si el teorema se corrige o refuta más adelante, la reivindicación central queda inválida. No presentar nada de §9 hasta que el Teorema 1 tenga una verificación reproducible.
- El **Pandora Health Score** (Especificación Técnica §9) pondera un 15% en `hijack_flag`/HR — que depende del mecanismo C3 de phase-hijacking, todavía sin resolución de estado en la auditoría base de DSCN-G. Cualquier métrica de salud del sistema que dependa de C3 hereda esa misma incertidumbre.

---

## 4. Lo que falta resolver antes de que 3.3 sea algo más que una idea linda

Sin esto, el horizonte lejano se queda en literatura:

1. **Credit assignment más allá de resonancia local.** El techo real, ya identificado: `v0.14d` muestra que backprop resolvió lo que topología pura no pudo. Sin un mecanismo que reemplace eso, cualquier tarea de varios pasos con dependencia real entre ellos tiene límite bajo.
2. **Extracción de features aprendida, no proyección fija**, en el SensorBridge.
3. **Dependencias de largo alcance más allá de la ventana W(t)** — memoria persistente no es lo mismo que integrar una secuencia larga con dependencias entre puntos lejanos.
4. **Evidencia de generalización composicional** — la abducción XOR necesita T-INF-07 (SGM v1.4 §12) corrido y con resultado, no solo diseñado.
5. **Escala real** — miles de nodos sobre un corpus no predice comportamiento a escala de millones; es aritmética, no defecto de diseño.
6. **Cierre sensomotor real** — señales sintéticas no sustituyen un lazo cerrado con entorno no curado.

Ninguno de estos seis puntos se resuelve por diseñar una arquitectura de sistema más ambiciosa. Se resuelven en el grafo mismo, en SGM, antes que en cualquier capa que lo envuelva.

---

## 5. Honestidad sobre los riesgos (heredado y corregido de PandoraOS §0)

- **EthicaOS / cualquier módulo de "veto" sobre acciones del sistema** debería ser advisory-only (loguea y alerta) mientras el modelo subyacente siga fallando tests básicos como T-INF-05 (distinción contradicción/estancamiento). Un sistema que puede negarse a actuar por una señal que todavía no es confiable es una superficie de falla, no una virtud.
- **Cualquier estructura que toque el hot path de scheduling** (la analogía de `task_struct` en PandoraOS) es una decisión que, si se pifia, se paga para siempre. Mejor postergarla hasta que haya evidencia dura de que hace falta.
- **La ambición del horizonte 3.3 compite por el mismo tiempo finito** que arreglar lo que hoy está a medio validar en SGM. Este documento es explícitamente para pensar, no para desviar esfuerzo de la Fase 0-6 de SGM v1.4.
- **No presentar patentes sobre propiedades matemáticas no verificadas** (ver §3.4) — el Teorema 1 de DSCN-G falló sus comprobaciones de maximalidad en la auditoría; cualquier reivindicación que dependa de "convergencia formal garantizada" necesita esa verificación resuelta primero.
- **No construir métricas de salud del sistema que dependan de C3/hijack_flag** (ver §3.4) hasta que ese mecanismo tenga estatus resuelto.

---

## 6. Relación con documentos existentes

| Documento | Relación con Rizoma |
|---|---|
| **SGM v1.4** | Núcleo técnico real. Todo lo de §1-2 de este documento depende de que SGM v1.4 se implemente y valide. |
| **DSCN-G Paper** | Fundamento teórico de base, invariante. |
| **`dscn-g-language-engine` / `fate-v6-modular` (repos)** | Fuente de evidencia empírica citada en §1. |
| **AgentPandora** | Implementación actual del horizonte 3.1 — ya en marcha, no especulativa. |
| **PandoraOS (Vision Global, Architecture, Especificación Técnica, Implementación)** | Material de referencia e inspiración para §3.2-3.3, con encuadre corregido: se rescatan ideas concretas (perfiles de hardware, modo degradado, PandoraNet como red distribuida), se descarta la premisa de kernel-first. |

---

## 7. Nota final

Este documento es, a propósito, el más especulativo de todos los que se han producido en este proyecto — y está marcado como tal en cada sección. Su función no es guiar el próximo sprint; es dar un lugar dónde poner las ideas grandes sin que compitan con el trabajo concreto que sí está en curso (SGM v1.4, Fases 0-6). Cuando alguna pieza de este horizonte deje de ser idealización y tenga evidencia real detrás, ese es el momento de moverla de este documento al roadmap de trabajo — no antes.
