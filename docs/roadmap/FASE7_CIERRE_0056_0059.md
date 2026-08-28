# CIERRE FASE 7 — Composicion Relacional + Decode Anidado + Uso Real (linea 0056/0059)

**Fecha:** 2026-08-04  ·  **Autor:** Vega (Hermes) con Luciano  ·  **Estado:** FASE 7 CERRADA Y CARACTERIZADA

Este documento consolida empiricamente el cierre de la Fase 7 de SGM: el sustrato compone relaciones de
cualquier orden (0027/0029 del roadmap original) y — lo que esta linea aporto — la composicion EMERGE
desde el sustrato (sin regla inyectada) y es RECUPERABLE sobre corpus real por decodificacion por rol
con capacidad suficiente.

---

## 1. PREGUNTA DE ARRANQUE

¿Puede el sustrato SGM (HRR + roles, stdlib puro) lograr COMPOSICION SISTEMATICA y DECODE ANIDADO
EMERGIENDO del mecanismo (afinidad Eq.2 + presion de transmision), sin hardcodear gramatica? Y si el
decoder es entrenado, ¿rompe el techo? ¿Y sobre texto real (Don Quijote), que hace?

## 2. LINEA 0056 — EMERGENCIA DE COMPOSICION (codigo discreto vs HD)

| Exp | Diseno | TS_full / metrica | Veredicto |
|-----|--------|-------------------|-----------|
| 0056 | regla inyectada (region->pos0,dist->pos1) | 1.0 | TRAMPA: gramatica hardcodeada en aprendiz |
| 0056b | afinidad sola (presion off) | ~0.35 | afinidad sola NO alcanza |
| 0056c | afinidad + presion de transmision (decoder conteo) | ~0.59 | presion ayuda, techo ~0.6 |
| 0056d | decoder ENTRENADO sobre codigo DISCRETO (L=3,V=16) | ~0.60 | decoder entrenado NO cierra; cuello = codigo discreto |
| 0056e | codigo HD role-filler (continuo) + decoder entrenado | 0.81-0.93 | ROMPE el techo: el codigo discreto era el cuello |
| 0056f | uso real (Don Quijote, recall memoria) | top-1 cosine 1.0 | memoria por contenido funciona; rol NO mejora recall tematico |
| 0056g | clasificacion real: propio/comun por contexto | 0.840/0.890 vs base 0.891 | FALLA: etiqueta LEXICA, contexto no lleva senal |
| 0056h | clasificacion real: genero por contexto (DISTRIBUCIONAL) | plana 0.804 > rol 0.673 > base 0.553 | SUSTRATO SI clasifica si la senal es contextual |
| 0056i | tarea de ORDEN (1ra palabra) por contexto lineal | rol f1 0.202 > plana 0.127 | rol capta orden, decoder lineal no alcanza |
| 0056j | decoder por ROL EXPLICITO (unbinding) N=128 | gap 0.428 | falla: ruido aditivo (interferencia, como 0029) |
| 0056j | decoder por ROL EXPLICITO N=1024 | gap 1.000 | ARCO CERRADO: rol codifica orden, recuperable con N |

**Conclusion 0056:** el techo 0.6 de composicion era del CODIGO DISCRETO. HD role-filler (0056e) lo rompe
a 0.81-0.93. Sobre corpus real (0056f-0056j): el sustrato hace memoria (top-1=1.0), clasificacion
distribucional (>baseline) y — con N=1024 y decodificacion por rol — recupera orden al 100%. Unico limite
honesto: CAPACIDAD (N chico interfiere; N grande resuelve), coherente con curva suave de 0029.

## 3. LINEA 0059 — DECODE ANIDADO (por que K=1/2 colapsan)

| Exp | Diseno | Resultado |
|-----|--------|-----------|
| 0059 | HRR-sumado (roles en mismo vector) | satura ~2 niveles |
| 0059b/c | resonator canonico | no rompe techo |
| 0059g | slots separados por rol (K=3) | prof 12+ (ROMPIDO) |
| 0059h | barrido K=1/2/3 | K=1,K=2 -> prof0 (binario); K=3 -> prof8+ |
| 0059i | K=2 con puntero-rol explicito + T=40 | K=2 sigue prof0 (RecursionError: proyeccion destruye identidad del hijo) |

**Conclusion 0059:** decode anidado requiere SLOTS SEPARADOS por rol. Proyeccion del puntero a cajon chico
es many-to-one (no inyectiva): destruye identidad del hijo y el decode colapsa en bucle. Conecta con
0056e: el rol necesita su PROPIO sub-espacio (continuo, HD), no superposicion plana. Misma raiz que
0029 (suave, ruido aditivo) vs 0059h (binaria, borrado de info): en superposicion plana el ruido se
acumula; en proyeccion de puntero la informacion DESAPARECE.

## 4. CONEXION CONCEPTUAL (las tres curvas)

- 0029 (superposicion plana): degradacion SUAVE — ruido aditivo acumulativo, reversible con N.
- 0059h (punteros anidados): colapso BINARIO — proyeccion many-to-one borra identidad del hijo.
- 0056j (orden por rol, N chico->grande): el rol codifica orden; con N suficiente el unbinding lo
  recupera (1.000). Confirma que el rol necesita capacidad, no es "magic".

## 5. QUE HACE EL SUSTRATO SGM (verificado, honesto)

1. Memoria direccionable por contenido sobre texto real (0056f, top-1 cosine=1.0).
2. Composicion sistematica de relaciones (0056e, 0.81-0.93; 0029 escala con D).
3. Decode anidado profundo con slots separados (0059g, prof 12+).
4. Clasificacion distribucional real (0056h > baseline).
5. Recuperacion de orden por decodificacion por rol con N suficiente (0056j N=1024, gap=1.000).

LIMITES honestos:
- Codigo discreto (L=3,V=16) estancado en ~0.6 (0056d).
- Etiqueta lexica por contexto no recuperable (0056g).
- Unbinding naive falla con N chico por interferencia (0056j N=128); resuelto con N=1024.

## 6. REGISTRY

88 experimentos en results/experiment_registry.json. Linea 0056 (0056, 0056b-0056j) y 0059
(0059, 0059b-0059i) documentados con status y veredicto honesto, incluido el registro de TRAMPA (0056
regla inyectada) y los negative controls.

## 7. CIERRE Y ROADMAP

**Fase 7 CERRADA.** El mecanismo de composicion relacional HRR + roles (consolidado en
phases/phase7_composicion/hrr_core.py) quedo validado empiricamente no solo en scaling sintetico (0029)
sino en emergencia desde sustrato (0056e) y recuperacion sobre corpus real (0056f-0056j).

**Siguientes pasos (post-Fase 7, plan acordado 2026-08-02), para decidir con Luciano:**
1. Test de estres del tick cruzado (exp_SGM_0031): grafos 100+ nodos, senal ruidosa.
2. Camino A — Cierre de loop en entorno: cuerpo virtual (grid) que recibe senal HDC; el tick decide
   accion; el cuerpo ejecuta; la senal vuelve; omega se actualiza.
3. Continuidad de identidad en el tiempo (yo narrativo, no solo omega persistente).
4. Drive intrinseco (curiosidad): reducir incertidumbre por gusto.
5. Metas propias: MODO_PLAN genera sus objetivos.
6. Paloma-pi / BORIS (etologia propia): trabajo de campo, no celular.

Las fases 8-10 (escala planetaria) son vision de largo plazo, fuera de este roadmap.

**Recomendacion de Vega:** el Camino A (cierre de loop en entorno grid) es el siguiente paso natural y
es ejecutable en el celular (ya hay demo_grid.html y exp_SGM_0032/0033 de grid agent). La linea 0056/0059
dejo el sustrato compositivo caracterizado; el salto a agente-que-aprende-del-mundo es donde ese sustrato
se vuelve funcional de verdad.
