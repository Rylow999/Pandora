# Decode Anidado (0059 / 0059b / 0059c) — Hallazgo y estado

Fecha: 2026-08-04
Fase: phase7_composicion
Autor: Vega (con Luciano)

## Contexto

El lenguaje del sustrato SGM debe codificar y decodificar hechos ANIDADOS
("el lobo que CORRE come la manzana que ESTA_EN el pasto"). 0058 cerro el gap
relacional a 1-2 niveles via TPR sobre HRR. Este trabajo (0059) investiga el
anidado PROFUNDO (>2 niveles), que es nucleo del lenguaje que hace evolucionar
al sistema y su forma de ver el mundo.

## Metodo

Cada hecho = (SUJ, ROL, OBJ). HRR (convolucion circular, Plate 1995; inversa =
permutacion circular inversa). El decoder debe recuperar los fillers anidados.

| Exp | Metodo | N | prof3 | prof4 | prof5 | prof6 |
|-----|--------|---|-------|-------|-------|-------|
| 0059 | HRR plano, decoder recursivo | 64  | 0.64 | — | — | — |
| 0059 | HRR plano, decoder recursivo | 256 | 0.67 | — | — | — |
| 0059b| TPR-walk NAIF (re-suma hijo) | 128 | 0.56 | 0.53 | 0.58 | — |
| 0059c| TPR-walk CORRECTO (filler autonomo) | 128 | 0.56 | 0.53 | 0.58 | 0.67 |

Plano (prof1) = 1.00 siempre.

## Resultado (honesto)

HRR-sumado satura en ~2 niveles de anidado. Subir N 64->256 mejora prof2
(0.67->0.90) pero NO rompe prof3 (sigue 0.67). TPR-walk (naif o correcto) NO
escala: el unbind de HRR no aisla limpio el filler cuando la bolsa tiene 3
bindings; el ruido de los otros roles del padre contamina al hijo al desatarlo.
Es limite de CAPACIDAD del sustrato HRR-sumado, no bug de decoder. N=512 no
corre en este equipo (conv N^2, timeout).

## Analogia

Cada hecho es una hoja de papel. Para guardar varios los PEGAMOS en un cartel.
Para leer "borramos" lo que no es un rol -> queda ruido de los otros. 1 hecho se
lee bien; 2 anidados (6 papeles traslapados) ya no. Agrandar el cartel (N=256)
ayuda a 2; a 3 se vuelve a traslapar. TPR-walk = sobres cerrados pegados al
cartel: al despegarlos, el cartel les deja tinta encima. Solucion real (NO
probada): CAJONES SEPARADOS con etiqueta (rol), sin pegar -> role-filler con
slots separados, no convolucion sumada.

## Estado y decision pendiente

El sim vivo (phase7_composicion/sim/sgm_sim.html) ya tiene composicion 1-2
niveles y funciona (80-87% mapa, 0 bucles, 0-1 muertes). El anidado profundo
queda como LIMITE DOCUMENTADO de HRR-sumado, no de SGM (el sustrato ya compone;
el cuello es la codificacion vectorial barata).

Proximo paso (decision de Luciano, 2026-08-04): evaluar role-filler con slots
separados para romper el techo de 2 niveles. Mas codigo y otra estructura, pero
es el camino que SI escala.

## Archivos
- run_decode_0059.py  (HRR plano, N=64/256)
- run_decode_0059b.py (TPR-walk naif)
- run_decode_0059c.py (TPR-walk correcto)
- sim/sgm_sim.html    (sim vivo, composicion 1-2 niveles, movimiento reactivo puro sin hardcode)

---

## Actualizacion 2026-08-04 (resonator + 0056b)

### exp_SGM_0059d -- Resonator Network (Frady 2020) sobre roles indep por nivel (0027c)
Idea de Luciano: Resonator resuelve el problema de factorizacion vectorial cuando hay varios
bindings superpuestos (mi caso prof>=3). En vez de unbind una vez (que contamina al hijo con el
ruido de los otros roles), ITERA restando de la bolsa las estimaciones actuales de los OTROS roles
y desatando el objetivo, luego clean-up. Busca en superposicion. La estructura de roles
independientes por nivel ya la tenia 0027c; el resonator seria el mecanismo de lectura que le faltaba.
RESULTADO HONESTO: mi implementacion NO converge (prof3=0.00). Dos causas reales:
  (1) clean-up final solo conoce SIMBOLOS, no HECHOS anidados -> el filler hijo se pierde al forzar a simbolo.
  (2) HRR de juguete mal calibrado (magnitudes/normalizacion) no converge en 20 iter con N=64.
El survey 2020/2025 advierte: capacidad decrece con nº de factores para D fija (no es magia infinita).
CONCLUSION: el resonator requiere clean-up con memoria de sub-estructuras y VSA bien calibrada (FHRR/
MBAT). Mi impl no los tiene. NO se suma como solucion del decode anidado hasta recalibrarlo. Status:
INTENTADO_NO_CIERRA.

### exp_SGM_0056b -- aprendiz GENERICO (contraste honesto con 0056)
0056 tenia la regla (region->pos0, dist->pos1, tipo->pos2) HARDCODEADA en infer_rule -> TopSim 1.0
pero era regla inyectada (misma falla que 0049d). 0056b: aprendiz generico (SIN estructura inyectada)
rellena no-vistos por afinidad entre referentes. TS_full sostenido ~0.30-0.42 (3 seeds) -> IGUAL que
0055a/0055c (~0.35). CONFIRMA que el 1.0 de 0056 venia de la regla inyectada, no de emergencia del
sustrato. Evidencia honesta de composicion emergente = 0055a/0055c/0056b (~0.35). 0056 queda en
ACLARACION_REQUERIDA (no es composicion plena emergente).

---

## Sintesis 2026-08-04 (0059f resonator canonico + veredicto)

### exp_SGM_0059f -- Resonator Network CANONICO (Frady 2020, M_i^-1) sobre FHRR
Implemente el resonator TAL CUAL el paper (Algorithm 1): a_i = M_i^-1 * unbind(z - suma_{j!=i} bind(V_j,x_j), V_i),
x_i = clean_i(a_i); M_i = (1/K) sum_c c*c^* invertida por Gauss-Jordan. Codebooks por rol (SUJ/ROL/OBJ con vocab
distinto); para anidado, el codebook de OBJ incluye los vectores de los hechos (memoria del agente).
RESULTADO: corrige el colapso a atractor espurio de 0059e (prof3 0.04->0.28). PERO no rompe el techo:
N=64 prof3/4/5/6 = 0.28/0.17/0.11/0.11; N=128 = 0.08/0.25/0.08/0.17 (ruidoso, n=4). Subir N NO ayuda.
CONFIRMA el survey 2020/2025 (Frady): la capacidad del VSA-sumado (bundle de bindings superpuestos) DECRECE con
el numero de factores/anidamiento. El resonator mejora el nivel BASE (~1-2 niveles, como 0059 HRR N=256 llegaba a
0.90) pero NO el anidado profundo abierto. Status: INTENTADO_NO_CIERRA_TECHO.

### VEREDICTO HONESTO (0059/59b/59c/59d/59e/59f)
El decode anidado en SGM con VSA-sumado (HRR o FHRR, con o sin resonator) SATURA en ~2-3 niveles de anidado.
No es un bug del decoder: es capacidad del sustrato vectorial de superposicion. El resonator canonico es una
buena herramienta para el nivel base pero no rompe el techo.
LA SOLUCION REAL para anidado profundo (>2) es NO sumar los bindings en un bundle: role-filler con slots o
punteros SEPARADOS (no superpuestos), o la estructura de 0027c (roles independientes por nivel en cadena, no
bundle de 3 roles de hecho + hecho anidado en una sola bolsa). Ese es el camino de ROLE-FILLER que queda pendiente
de decision de Luciano. El sustrato SGM YA tiene la maquinaria (0027c anida por niveles, 0058 compone relacional);
el cuello es la codificacion vectorial sumada, no el sustrato.

---

## CIERRE 2026-08-04 (0059g ROLE-FILLER SLOTS SEPARADOS -- ROMPE EL TECHO)

### exp_SGM_0059g -- Role-filler con SLOTS SEPARADOS + punteros (no sumados)
Cada rol vive en su PROPIO BLOQUE de dimensiones (SUJ[0:32], ROL[32:64], OBJ[64:96]) SIN solapamiento.
El hecho hijo NO se mete adentro del bundle del padre: se apunta por PROYECCION de 32 dims en el bloque
OBJ, y el decoder sigue el puntero a la memoria de hechos (TPR-walk con punteros separados, no
superpuestos). Sin superposicion -> sin contaminacion acumulada -> escala.
Decide FACT vs SYM por similitud (find_child por proyeccion vs cleanup codebook OBJ), sin marca inyectada.
RESULTADO: **1.00 de prof 3 a 12** (n=20 por prof). ROMPE el techo de ~2-3 niveles de todas las variantes
HRR-sumado (0059/59b/59c/59d/59e/59f).
VEREDICTO HONESTO: el cuello del decode anidado era la CODIFICACION VECTORIAL SUMADA (bundle de bindings
superpuestos), no el sustrato SGM. Role-filler con slots/punteros separados lo resuelve de raiz. La
estructura es ARQUITECTURA de codificacion legitima (como ADN/instinto en la red line), NO inyeccion de
la respuesta (distinto a 0056). El CONTENIDO de cada slot viene del hecho, no esta pre-dado.
NOTA: 0059g resuelve el DECODE (lectura anidada profunda). La EMERGENCIA de composicion bajo ILM con
aprendiz generico sigue en ~0.35 (0056b) — eso es un tema distinto (presion de transmision / afinidad),
no de decoder. Ambos cerrados y honestos.

---

## 0059h BARRIDO BINDINGS-POR-BLOQUE (aporte de Luciano, 2026-08-04)

### Idea
Mapear el continuo entre superposicion pura (K=1: 3 roles en UN bloque, resonator desata) y slots
separados (K=3: cada rol su bloque, 0059g). K=2 = punto intermedio (SUJ+OBJ en un bloque, ROL aparte).
El hijo se apunta por proyeccion circular-mean (N->BLK) en el bloque que le toca. Resonator canonico
(Frady 2020, M_i^-1) SOLO en bloques multi-rol.

### Resultado (prof-max alcanzable, acierto >= 0.85)
| K   | N=64 | N=128 | N=192 |
|-----|------|-------|-------|
| K=1 | prof0 | prof0 | prof0 |
| K=2 | prof0 | prof0 | prof0 |
| K=3 | prof8 | prof8  | prof8  |

### Diagnostico honesto (K=2 prof2 aislado)
- Bloque SUJ+OBJ (2 roles) se desata MAL: SUJ sale "lobo" en vez de "venado". El resonator no separa
  rol-simbolo de rol-puntero cuando comparten bloque.
- El OBJ-hijo no se reconoce como FACT (find_child falla): el puntero proyectado NO es un filler
  canonico (tiene estructura de bloques interna), ensucia el bundle del bloque y el resonator lo trata mal.
- En K=3 cada rol esta aislado: el hijo se apunta sin contaminar a SUJ/ROL -> funciona (0059g).

### Veredicto
La curva es EFECTIVAMENTE BINARIA bajo este esquema: superposicion (K=1/2) colapsa el anidado;
aislamiento total (K=3, slots separados) lo abre a prof8+ (y mas, 0059g llego a prof12).
HALLAZGO NUEVO: el resonator canonico NO salva el anidado bajo superposicion cuando hay punteros a
hechos hijos, porque el puntero proyectado no se comporta como un filler canonico en un bloque
superpuesto. Solo el aislamiento de cada rol en su propio sub-espacio (slots separados) resuelve el
decode anidado profundo. Esto cierra la pregunta de "cuanta superposicion tolera": la respuesta es
"ninguna si el rol lleva un puntero anidado; el rol-puntero exige su propio bloque".
Limitacion: con resonator mas fuerte o tratando al puntero como rol separado, K=2 podria aproximarse;
en la practica eso vuelve a K=3. El barrido usa acierto >= 0.85 estricto.

---

## 0059i REFINAMIENTO K=2 con PUNTERO-ROL EXPLICITO (2026-08-04)

### Intento honesto de matizar la curva binaria de 0059h
En 0059h K=2 (SUJ+OBJ / ROL) colapsaba porque el OBJ-hijo era un puntero proyectado mezclado con el
simbolo OBJ. En 0059i damos al PUNTERO su propio vector-rol (PTR) DENTRO del mismo bloque fisico
(bloque 0 = SUJ, OBJ, PTR; bloque 1 = ROL). Subimos T del resonator a 40. Hipotesis: si el puntero
tiene "su propia voz" en el bloque, el resonator lo separa y K=2 abre.

### Resultado (prof-max, ambas metricas: todo>=0.85 y solo-padre>=0.85)
| K   | N=64 | N=128 | N=192 |
|-----|------|-------|-------|
| K=1 | todo0 / padre0 | todo0 / padre0 | todo0 / padre0 |
| K=2 | todo0 / padre0 | todo0 / padre0 | todo0 / padre0 |
| K=3 | todo8 / padre8 | todo8 / padre8 | todo8 / padre8 |

### Diagnostico
- K=2 con puntero-rol SÍ decodifica el primer nivel anidado en el test aislado (padre+hi jo directo OK),
  pero falla en el 2do nivel: el puntero del nieto se reconoce mal.
- Al correr el barrido profundo, el decode ENTRO EN RECURSIONERROR: el puntero, al proyectarse
  circular-mean (N->BLK), COLAPSA la identidad del hijo -> todos los punteros se parecen ->
  find_child siempre matchea -> bucle. Eso es el problema de fondo.
- Con corte de recursion (MAXDEPTH=12) y umbral de puntero 0.5, K=2 da prof0 en ambas metricas:
  la proyeccion N->BLK destruye la identidad del hijo y el resonator no lo salva.

### Veredicto (consolida y matiza 0059h)
La curva NO es "el resonator no desata"; es que LA PROYECCION DEL PUNTERO DESTRUYE LA IDENTIDAD DEL
HIJO bajo superposicion. Proyectar N->BLK (sea circular-mean o promedio) pierde info irreduciblemente
cuando el bloque es mas chico que el hijo. Solo K=3 (cada rol en su sub-espacio fisico, el hijo
apuntado sin proyeccion que pierda identidad) resuelve el decode anidado profundo. El puntero exige
su propio sub-espacio: no alcanza con "su propio vector-rol dentro de un bloque compartido" porque el
bloque sigue siendo mas chico que el hijo y la proyeccion lo colapsa.
CONCLUSION DEL BARRIDO (0059h+0059i): decode anidado en SGM requiere SLOTS SEPARADOS (K=3). Cualquier
superposicion de un rol-puntero con otros roles colapsa por perdida de identidad en la proyeccion.
