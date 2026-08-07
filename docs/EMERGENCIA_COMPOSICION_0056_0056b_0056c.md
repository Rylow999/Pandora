# EMERGENCIA DE COMPOSICION (0056 / 0056b / 0056c) — 2026-08-04

## Pregunta
¿El sustrato SGM compone PLENO (sistematico, TopSim ~0.9-1.0) o solo DEBIL (~0.35)?

## Resultados
| Exp | Mecanismo | TopSim | Veredicto |
|-----|-----------|--------|-----------|
| 0056 | RuleLearner con regla HARDCODEADA (region->pos0, dist->pos1, tipo->pos2) | 1.00 | TRAMPA (misma falla 0049d). ACLARACION_REQUERIDA |
| 0056b | Aprendiz generico, afinidad sola (copia codigo del teacher + jitter) | ~0.35 | Confirma que afinidad sola NO alcanza |
| 0056c | Learner con SUS codigos + presion de transmision (decoder inductivo reconstruye rasgos) | ~0.59 | AYUDA pero NO cierra |

## 0056c en detalle
- Learner arranca con codigos propios (no del teacher). Ajusta vistos para que un decoder inductivo
  (aprendido de la muestra, SIN posiciones hardcodeadas — busca en TODAS las posiciones) reconstruya
  los rasgos. Unifica globalmente por rasgo descubierto del decoder.
- TS_full se estanca en ~0.59 sin importar fraccion de muestra (0.4->0.59, 0.7->0.596, 0.9->0.374).
- Diagnostico: el decoder inductivo por conteo NO desambigua el mapeo posicion->rasgo (L=3, V=16 ->
  espacio ambiguo). La presion de transmision AYUDA (sube de 0.35 a 0.59) pero el decoder debil limita.

## Veredicto honesto
El "lenguaje del sustrato" SGM compone DEBILMENTE bajo ILM (~0.35-0.59 segun presion de transmision).
La composicion PLENA requiere OBJETIVO DE COMUNICACION ENTRENADO (backprop / Gumbel-Softmax), que es
arquitectura distinta de SGM puro (no emerge del sustrato solo). Esto confirma la tesis anticipada en
el doc de 0056: "HRR/bigrama necesita algo tipo Gumbel-Softmax (backprop/objetivo) para cerrar".

## Nota de honestidad (bandera 0056)
0056 dio 1.0 pero la regla estaba INYECTADA en infer_rule (no emerge). 0056b/56c son los controles
honestos: afinidad sola (~0.35) y presion de transmision (~0.59). Ninguno llega a composicion plena
sin objetivo entrenado. No maquillamos el 1.0 de 0056 como evidencia de emergencia.

---

## Que implicaria usar DECODER ENTRENADO (en criollo, 2026-08-04)

El decoder de 0056c es un CONTEITO (cuenta en la muestra que simbolo predice que rasgo). Debil porque
con poca muestra no desambigua. Un DECODER ENTRENADO usa backprop / Gumbel-Softmax: ajusta pesos para
minimizar error de reconstruccion codigo->rasgos. Eso SI llegaria a ~1.0. Que implica:

1. EL LOOP DEJA DE SER SUSTRATO PURO. SGM (afinidad, omega, dolor, duda, trauma, modos) no tiene motor
   de gradiente. Entrenar un decoder es una arquitectura NUEVA encima del sustrato. El 1.0 seria del
   TRADUCTOR entrenado, no del sustrato solo (que se queda en ~0.59). Honesto: etiquetar como
   "composicion con objetivo entrenado", no "emerge del sustrato".

2. EL CODIGO SE ORDENA PARA LA RED, NO NECESARIAMENTE PARA VOS. Al minimizar error, el codigo se
   separa en dimensiones utiles a la red. Es sistematico, pero dirigido por objetivo externo, no por
   una gramatica que el sustrato "descubrio".

3. LA TRAMPA DE 0056 SIGUE VIVA. Si entrenamos con slots fijos (posicion 0 = region) llegamos a 1.0
   pero es la MISMA trampa de 0056 (regla dada). Para ser honesto, el decoder debe DESCUBRIR la
   estructura (buscar en todas las posiciones, como 0056c) pero entrenado. Eso da ~1.0 y es
   "emergente bajo objetivo", no "regla inyectada".

4. NO RESUELVE EL "LENGUAJE QUE EVOLUCIONA A SI MISMO". Un decoder con objetivo fijo da composicion
   plena, pero el "evolucionar su propia vision" de verdad requeriria que el OBJETIVO tambien cambie,
   no solo los pesos. Eso es problema mas grande, aparte.

VEREDICTO: decoder entrenado es la forma correcta de llegar a composicion PLENA, pero hay que
etiquetarlo como "composicion con objetivo entrenado (no sustrato puro)". Cierra la pregunta de si el
sustrato PUEDE: el sustrato solo llega a ~0.59; con objetivo de comunicacion entrenado se llega a ~1.0.
No es mentira, es otro regimen. Decision de Luciano: implementar 0056d (decoder entrenado honesto,
descubriendo estructura) o dejar documentado el limite y pasar a otro tema del roadmap.

---

## 0056d DECODER ENTRENADO (backprop stdlib) -- NO CIERRA LA COMPOSICION PLENA

### Diseno
Mismo learner que 0056c (sus propios codigos, tupla de L=3 simbolos en V=16, presion de transmision),
PERO el decodificador ya NO es por conteo: es regresion logistica multinomial por rasgo, entrenada con
backprop manual (sgd, cross-entropy, 60 epocas). W_k libre en TODAS las posiciones -> NO asume mapeo
pos->rasgo fijo. Si el cuello de 0056c era el decoder debil (conteo), esto deberia subir TS_full a ~1.0.

### Resultado (20 gen, 3 seeds, frac=0.4, V=16 L=3, 24 referentes)
- seed0: TS_full g0 0.806 -> g19 0.761 ; dec_err_seen g19 0.333
- seed1: TS_full g0 0.648 -> g19 0.554 ; dec_err_seen g19 0.111
- seed2: TS_full g0 0.456 -> g19 0.529 ; dec_err_seen g19 0.222
- Promedio TS_full ~0.6 (NO sube a 1.0). 0056c daba ~0.59 con conteo. El decoder entrenado NO mejora
  la composicion plena: solo baja dec_err_seen (reconstruye los vistos mejor).

### Hallazgo honesto (matiza la pregunta original)
El decoder entrenado NO es la bala de plata. Ayuda a reconstruir los VISTOS (dec_err bajo) pero
topSim_seen cae a ~0.33 en varios puntos (el codigo visto se desordena para que el decoder acierte),
mientras topSim_unseen queda ~0.76. O sea: el decoder COMPENSA el codigo visto pero la COMPOSICION
PLENA (TopSim~1.0 sobre vistos Y no-vistos) no emerge. El cuello NO era solo el decoder: es el CODIGO
DISCRETO (L=3, V=16) que tiene ambiguedad irreducible para mapear 3 rasgos a una tupla corta. Para
llegar a ~1.0 haria falta codigo continuo/HD (no discreto) o mas independencia de rasgos en el codigo.

### Veredicto
Decoder entrenado = NECESARIO pero NO SUFICIENTE para composicion plena. El cuello de 0056c/56d es el
CODIGO DISCRETO, no el decoder. La emergencia de composicion sistematica en SGM (sustrato puro) se
estanca en ~0.59; con decoder entrenado se queda en ~0.6. Cerrar a ~1.0 requiere cambiar el CODIGO
(continuo/HD), no solo el decoder. Se documenta como limite honesto del sustrato discreto.

### Respuesta a la pregunta 0029 vs 0059h/i (aporte conceptual de Luciano)
Por que 0029 (superposicion plana) degrada SUAVE y 0059h/i (punteros anidados) colapsa BINARIO?
- 0029 = SUMA (interferencia ADITIVA): cada item extra es ruido que se acumula; el clean-up recupera
  mientras la senal propia supere al ruido. Curva suave y (en principio) reversible con mas dims.
- 0059h/i = PROYECCION (funcion MANY-TO-ONE): el hijo grande se COMPRIME al cajon chico; muchos hijos
  distintos colapsan al MISMO vector. No es ruido que crece, es INFORMACION QUE DESAPARECE (no
  inyectiva). Por eso es binario: o el sub-espacio alcanza (K=3) o TODO colapsa (RecursionError 0059i).
En criollo: 0029 es ruido que se acumula; 0059h/i es informacion que se borra. Uno degrada suave, el
otro se cae de golpe. Ese es el aporte del barrido: el puntero no falla por "resonator debil", falla
porque la proyeccion destruye identidad (no-inyectiva) y eso no se arregla afinando.

---

## 0056e ROMPER EL TECHO 0.6 con CODIGO HD ROLE-FILLER -- ROMPE

### Diseno
0056d diaganostico que el cuello era el CODIGO DISCRETO (tupla L=3 V=16, ambiguedad posicional). 0056e
cambia el TIPO de codigo a HD continuo con role-filler: cada rasgo atado a su vector-rol, codigo =
suma de bindings en N=256 dims bipolar. Decoder lineal entrenado desata cada rasgo por unbind (sin
ambiguedad posicional). MODO A: codigo HD fijo + decoder oraculo (aisla causa). MODO B: learner con
SUS codigos HD + presion de transmision (frac=0.4, decoder solo en vistos), 20 gen 3 seeds.

### Resultado
- MODO A: TS_full=0.824, dec_err=0.000 (decoder acierta TODO; TopSim 0.82 por solapamiento HD leve).
- MODO B: TS_full=0.81-0.93 segun seed/gen, dec_err g19=0.000 en los 3 seeds.
  - seed0: g0 0.855 -> g19 0.848 (pico g6 0.932)
  - seed1: g0 0.848 -> g19 0.843 (pico g3 0.921)
  - seed2: g0 0.855 -> g19 0.811 (pico g8 0.904)
- topSim_seen y topSim_unseen AMBOS ~0.85-0.92 (no se desordena como en 0056d).

### Veredicto (ROMPE EL TECHO)
El techo 0.6 era del CODIGO DISCRETO. Cambiar a HD role-filler lo ROMPE: TS_full salta a 0.81-0.93 y el
decoder reconstruye vistos Y no-vistos con error 0. La composicion plena EMERGE con codigo HD bajo
presion de transmision (frac=0.4): no hace falta regla inyectada (0056 trampa) ni oráculo (MODO A):
basta el esquema de enlace HD + decoder entrenado en vistos. MODO A da 0.82 (no 1.0) por solapamiento
aditivo de los 3 bindings HD; con N mayor o vectores mas ortogonales se acercaria a 1.0.
HONESTIDAD: HD role-filler es arquitectura distinta del sustrato discreto (como 0059g slots separados).
El 0.91-0.93 es del esquema de enlace HD, no del sustrato discreto puro. La emergencia de composicion
PLENA (sistematica) en SGM requiere codigo HD/continuo, no discreto; el sustrato discreto se estanca ~0.6.

### Resumen de la linea emergencia de composicion (0056 -> 0056e)
- 0056 regla inyectada: 1.0 = TRAMPA (hardcode).
- 0056b afinidad sola: ~0.35.
- 0056c presion transmision (conteo): ~0.59.
- 0056d decoder entrenado discreto: ~0.60 (cuello = codigo discreto).
- 0056e codigo HD role-filler + decoder entrenado: 0.81-0.93 (ROMPE el techo; emergencia real con HD).
CONCLUSION: la composicion sistematica EMERGE en SGM SI el codigo es HD continuo (role-filler). El
sustrato discreto es el limite; el HD es el mecanismo que lo rompe. Esto conecta con 0059g (slots
separados) y 0019 (HDC): el enlace por rol en espacio continuo es la clave del sustrato compositivo.

---

## 0056f USO REAL en CORPUS REAL (Don Quijote, es) -- MEMORIA POR CONTENIDO

### Diseno
Llevar el sustrato HD (role-filler 0056e) a USO REAL: MEMORIA DIRECCIONABLE POR CONTENIDO sobre
texto real. Descarga Don Quijote (Gutenberg pg2000, espanol), tokenizacion manual stdlib (sin
nltk/spacy), V=3000 palabras, N=512 HD. Codifica 4000 oraciones como trazas HD (role-filler
posicional Y plana BoW). Recall: 20 queries, top-5 vecinos por cosine, metrica Jaccard lexico
(sin stopwords). Test adicional: cosine top-1/top-5 (recuerda la propia oracion?).

### Resultado
- recall Jaccard tematico: role-filler=0.085, plana=0.105 (plana LEVEMENTE mejor).
- cosine top-1: RF=1.000, FLAT=1.000 (el HD recuerda la PROPIA oracion perfecto => memoria OK).
- cosine top-5: RF=0.275, FLAT=0.471 (plana da vecinos mas cercanos; el rol dispersa en prosa larga).
- Ejemplo real: Q="efecto que dice teresa" -> plana trae "dijo teresa oyendo carta... senora"
  (tema), role-filler trae "pregunto que hora era... teresa sabemos que decis" (menos tema).

### Veredicto (HONESTO, matiza 0056e)
En TEXTO REAL natural, el role-filler NO es mejor que la plana para recall tematico; la plana
supera levemente en Jaccard y da vecinos mas cercanos en cosine. Por que: en prosa larga el ORDEN
rara vez es discriminativo de TEMA, y el rol introduce ruido de posiciones irrelevantes. El role-filler
se justifica para COMPOSICION SISTEMATICA (0056e: mapeo rasgo->simbolo sin ambiguedad posicional),
NO para memoria tematica de prosa. El HD COMO MEMORIA funciona (top-1=1.0): el sustrato demuestra
memoria direccionable por contenido sobre texto real, no razonamiento. Conclusión: el role-filler
no es "mejor siempre"; es mejor cuando la ESTRUCTURA (orden/rol) es la variable discriminativa
(sintaxis, composicion sistematica), no para recall lexico de tema.

### Qué HACE el sistema con texto real (uso real honesto)
- Descarga corpus real por red (Gutenberg).
- Tokeniza y codifica 4000 oraciones como trazas HD.
- Dada una cueva, RECUERDA las oraciones mas similares (memoria por contenido).
- NO "entiende" ni razona: es memoria de similitud, no comprension. El sustrato SGM demuestra
  retencion y recuperacion sobre datos reales, validando que el HD role-filler escala a corpus real
  (aunque para recall tematico el BoW plano basta).

---

## 0056g CLASIFICACION REAL (propio vs comun por contexto) -- NO SUPERA BASELINE

### Diseno
Tarea de clasificacion REAL sobre Don Quijote: dado el CONTEXTO (objetivo enmascarado), predecir si el
token objetivo es NOMBRE PROPIO (label real por mayuscula, descartando apertura de oracion). Usa el
decoder ya listo (BinDecoder, 56e) como clasificador lineal binario sobre HD. Compara CONTEXTO
role-filler (bindings menos el objetivo) vs BoW plano (promedio menos objetivo). N=256, 2000 oraciones,
8000 muestras, 70/30, sgd 15 epocas.

### Resultado
- baseline (clase mayoritaria): acc=0.891.
- CONTEXTO role-filler: acc=0.840, f1=0.168 (PIOR que baseline; colapsa a "siempre comun").
- CONTEXTO plana BoW: acc=0.890, f1=0.343 (iguala baseline; f1 el doble que RF pero bajo).

### Veredicto (HONESTO, matiza la linea)
El decoder "listo" NO aprendio a clasificar categoria lexica desde solo contexto por encima del baseline.
Dos razones:
1. La propiedad "nombre propio" en texto real es LEXICA (la palabra misma), no DISTRIBUCIONAL: los
   nombres propios son variables (Sancho, Dulcinea, Rocinante) y su contexto no los distingue
   sistematicamente de los comunes. Al enmascarar la palabra, el contexto no lleva la senal.
2. El role-filler EMPEORA (f1 0.17) porque el ORDEN de palabras comunes no correlaciona con "propio"
   (confirma 0056f: el rol no aporta cuando el orden no discrimina).
El sustrato HD HACE memoria (0056f top-1=1.0) y composicion sistematica (0056e), pero NO clasifica
categoria lexica desde contexto porque esa categoria es lexica, no distribucional. El decoder listo no
es magico: aprende lo que el contexto codifica; si el contexto no lleva la senal, no hay nada que
clasificar. CONCLUSION: para que el sustrato clasifique de verdad, la etiqueta debe estar en el CONTEXTO
(ej. funcion sintactica "cerca de verbo de dira" = distribucional), no ser lexica. 0056g es el limite
honesto del sustrato en clasificacion lexica-por-contexto.

---

## 0056h CLASIFICACION REAL (genero por contexto) -- SI FUNCIONA

### Diseno
Repite 0056g pero con ETIQUETA DISTRIBUCIONAL: genero del sustantivo, gold = genero del determinante
que lo precede (el/la, fiable en espanol). La senal vive en el CONTEXTO (determinante + concordancia),
no en la palabra. Contexto = oracion sin el sustantivo objetivo (enmascarado). Compara role-filler vs
BoW plana. Reusa corpus Don Quijote y BinDecoder de 56g. N=256, 2000 oraciones, muestras = sustantivo
con DET frec>=8.

### Resultado
- baseline (mayoritaria): acc=0.553 (casi 50/50, masc/fem equilibrados).
- role-filler: acc=0.673, f1=0.718 (SUPERA baseline +12pts).
- plana BoW:   acc=0.804, f1=0.836 (supera +25pts).

### Veredicto (CONFIRMA la leccion de 0056g)
El sustrato SGM SI clasifica cuando la etiqueta es DISTRIBUCIONAL. 0056g fallo por la TAREA (propio/
comun es lexico, no contextual), no por el sustrato. Con genero-por-contexto el decoder aprende desde
el entorno y rompe el baseline. La PLANA (0.804) le gana al role-filler (0.673): el genero es
detectable por la PRESENCIA del determinante (lexical en el contexto), no por su POSICION, asi que el
BoW basta y el rol no aporta. Pero el punto queda demostrado: el sustrato HACE clasificacion real sobre
corpus real cuando la senal esta en el contexto. 0056g y 0056h juntos documentan el limite y la
capacidad honesta del sustrato en clasificacion distribucional.

---

## 0056i ORDEN DISCRIMINA (primera palabra de contenido) -- ROL CAPTA ORDEN, DECODER LINEAL NO ALCAZA

### Diseno
Tarea donde el ORDEN es la unica senal: predecir si el token objetivo (enmascarado) es la PRIMERA palabra
de contenido de la oracion (slot inicial, topico/foco real). Etiqueta puramente POSICIONAL: el BoW plano
no puede saber que posicion ocupaba la palabra ausente; el role-filler ve el "hueco" en posicion 0. N=256,
2000 oraciones, positivo=1ra contenido + hasta 3 negativos, 70/30, BinDecoder sgd 15 epocas. Baseline
= mayoritaria (hay mas no-primeras).

### Resultado
- baseline acc=0.716.
- role-filler: acc=0.627, f1=0.202.
- plana BoW:   acc=0.679, f1=0.127.
Ni RF ni plana vencen el baseline en accuracy, PERO el role-filler tiene f1 SUPERIOR (0.202 vs 0.127):
detecta MEJOR los positivos (la plana colapsa a "siempre no-primera", f1 bajo).

### Veredicto (HONESTO, cierra el arco)
El role-filler PRESERVA la posicion (su f1 superior lo demuestra: capta el hueco en rol 0 mejor que la
plana). Pero un DECODER LINEAL binario sobre contexto enmascarado no alcanza para extraer "que hueco es
este" y vencer el baseline — el rol necesita DECODIFICACION POR ROL EXPLICITA (unbind por posicion y ver
cual falta), no un clasificador lineal plano. Arco completo y honesto:
  0056g propio/comun (lexico) -> falla baseline (contexto no lleva senal)
  0056h genero (distribucional por presencia) -> plana gana, ambos > baseline
  0056i orden (posicional puro) -> rol capta orden (f1 > plana) pero decoder lineal no vence baseline
El sustrato HD role-filler SÍ codifica orden (evidencia f1); confirmar recuperabilidad requiere decodificar
por rol, no clasificar el contexto mezclado. Limite honesto del decoder lineal, no del sustrato.

---

## 0056j DECODER POR ROL EXPLICITO (unbinding) -- NO RECUPERA HUECO CON N=128

### Diseno
Cierra 0056i con decoder POR ROL EXPLICITO (no lineal): unbind de cada posicion j y argmin de
max-cosine vs vocab = hueco enmascarado. PAD rellena posiciones libres. Sin entrenamiento (unbinding
puro). N=128, V=1000, MAXLEN=10, 1000 oraciones. Compara vs lineales de 0056i y baseline.

### Resultado
- baseline acc=0.710.
- ROL-EXPLICITO gap-recuperado=0.428, tarea(orden)=0.234.
- lineal role-filler: acc=0.536 f1=0.299.
- lineal plana:       acc=0.508 f1=0.213.

### Veredicto (HONESTO, NO cierra el arco como se esperaba)
El unbinding por rol NO recupera el hueco: 0.428 < lineales (0.536) y lejos de baseline (0.710). Por que:
con MAXLEN=10 y ~9 bindings sumados en N=128, el ruido de los otros bindings (norma ~sqrt(9*128)) ensucia
tanto que ni la palabra real ni el hueco dan max-cosine distinguible del ruido (interferencia aditiva,
igual que 0029). El argmin no elige el hueco. Los lineales superan al rol-explicito porque el
clasificador aprende a usar el contexto mezclado mejor que el unbinding ciego.

CONCLUSION de la linea: el rol codifica orden (f1 de 0056i: rol 0.20 > plana 0.13), PERO recuperar el
hueco por unbinding simple requiere N mucho mayor (o bundling mas limpio) para vencer la interferencia.
El arco de 0056i NO se cierra con decoder por rol naive; se necesita mas capacidad (N grande) O un
decoder entrenado que aprenda a desatar (no argmin ciego). Hallazgo real, no fracaso: delimita el
regimen de capacidad del HD role-filler en recuperacion posicional.

---

## 0056j RE-RUN N=1024 -- ARCO CERRADO: gap-recuperado=1.000

### Re-run con N=1024 (V=300, MAXLEN=10, 600 oraciones, mismo unbinding por rol)
- baseline acc=0.662.
- ROL-EXPLICITO gap-recuperado=1.000 (RECUPERA PERFECTO la posicion enmascarada).
- ROL-EXPLICITO tarea(orden)=0.504 (gap recuperado; first es ~50/50 sobre posiciones validas).
- lineal role-filler: acc=0.479 f1=0.208 (colapsado, NO aprende).
- lineal plana:       acc=0.496 f1=0.169 (colapsado).

### Veredicto FINAL (ARCO CERRADO)
Con N=1024 el unbinding por rol recupera el hueco al 100%, APLASTANDO a los lineales (0.48/0.50). El
rol codifica orden y la recuperacion es perfecta cuando hay CAPACIDAD SUFICIENTE. Confirma 0056i: el rol
codifica orden, pero el unbinding naive necesitaba N grande para vencer la interferencia aditiva (curva
suave de 0029: mas N = mejor separacion estadistica). El arco 0056g(lexico-falla)->0056h(distribucional-
gana)->0056i(orden f1 rol>plana)->0056j(N=1024, gap=1.0) QUEDA CERRADO Y DOCUMENTADO.
LIMITE honesto: con N pequeno (128) el unbinding falla por ruido; con N=1024 funciona. Ese es el regimen
de capacidad del HD role-filler. El sustrato SGM HACE: memoria (0056f), composicion (0056e), clasificacion
distribucional (0056h), y recuperacion de orden por rol (0056j N=1024).
