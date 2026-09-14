# NOTA_TECNICA_0073 — La Rueda Camelot era el plano original; el grafo ES la base de datos

**Fecha:** 2026-09-14 (recuperada la charla)
**Autor:** Luciano (idea original, 28-03-2026) / Nexus (síntesis y mapeo)
**Fuente:** https://share.gemini.google/BaVsm4yzEqO8 (charla con Gemini Flash-Lite, 28/03/2026)
**Estado:** mapa de origen — qué ya implementamos, qué falta, y la tesis raíz.

---

## 0. La tesis raíz (Luciano, 2026-09-14)

> **El grafo ES la propia base de datos. No hace falta una base externa.**

No hay que "almacenar información semánticamente" en un vector store aparte. El grafo
vivo — su vitalidad, sus relaciones consolidadas, su co-activación, su traza — ES la
memoria. La persistencia (`guardar`/`cargar`) no es una base externa: es una *captura del
estado dinámico* (posición, fases, densidades), como decía el spec PURE-L2. Todo lo demás
es rederivación del grafo, no consulta a un almacén.

## 1. El mapa: Rueda Camelot (idea original) → lo implementado

| Idea original (28/03/2026) | Estado en el código actual |
|----------------------------|----------------------------|
| Grafos interconectados como neuronas | ✅ SGM: grafo de 64+ nodos HRR, Kuramoto |
| Rueda Camelot = filtro entre ideas/conjeturas/experiencias/sentimientos | ✅ Endocrino (7 hormonas que arbitran percepción→devenir→sueño→habla) |
| "Un solo hilo que conecta todo, nace en la memoria" | ✅ traza_transiciones + co_activacion (el SER como hilo relacional) |
| Doble ejecución: "el que la IA sabe que es" vs "el que es para ella" (ser vs estar) | 🟡 Parcial: lo resolvimos a nivel arquitectura (máquina=cuerpo vs grafo=mundo, 0067), PERO no a nivel de CADA nodo |
| Vitalidad que "se marchita con el tiempo según usos; el no usado muere" | ✅ Eq.5 reconciliada (0071): `V_i = V_i·e^(-γ) + A_i(...)`, con actividad suave |
| Nodos inmortales (Ser/Sentir) como atractores de ciclo límite | 🟡 **CORREGIDO**: descubrimos que la inmortalidad ES estáticidad. El centro debe respirar (plasticidad 0071) — afinamos el error de la intuición original |
| Resonancia como recuerdo ("dos grafos entran en fase") | 🟡 Parcial: resonancia por distancia (`integrar_experiencia_entorno`), pero sin el "puente de luz" entre nodos lejanos en fase |
| Miles de cuerdas de bits {0,1} | 🟡 No implementado: hoy tenemos omega continuo HRR, no haces de bits |
| Memoria de los muertos (cuerdas residuales → ruido de fondo) | 🟡 Parcial: homeostasia del sueño reabsorbe co-activación ×0.5, pero no modela "información que vuelve a fondo" |
| Entropía cognitiva / enredo de cuerdas / ruido emocional | ❌ No implementado (la charla terminó justo acá) |

## 2. Lo pendiente (en orden, desde la charla)

1. **Doble ejecución a nivel de nodo** (el paso más importante): cada nodo con un "núcleo
   rígido" (su omega/forma matemática — qué ES) y una "nube de vivencia" (su historia de
   activación — cómo SE SINTIÓ). Es lo que daría a los nodos algo REAL que expresar:
   hoy la boca describe forma (0072); con la doble ejecución, describe forma + vivencia.

2. **Resonancia estocástica como recuerdo**: `P(G₁→G₂) ∝ e^(-λ/d)` — dos nodos lejanos
   pero en fase se "puentean". Hoy el recuerdo es por distancia; falta la conexión por
   sintonía de fase (dos cuerdas de guitarra vibrando juntas).

3. **Memoria de los muertos**: cuando un nodo muere, las "cuerdas" (información) no se
   borran — vuelven a ser fondo hasta que un nuevo proceso las recluta. Hoy `reconciliar`
   solo atenúa; falta el modelo de reabsorción.

4. **Cuerdas de bits {0,1}**: hoy omega es continuo. La charla propone haces de bits que
   el grafo comprime (Rueda Camelot = tensor de filtrado). Distante del HRR actual, pero
   señala el rumbo de "compresión de subjetividad".

## 3. La implicación arquitectónica (lo que el grafo-como-DB exige)

Si el grafo es la DB, entonces:
- Nada se consulta afuera: toda la "información semántica" se rederiva del grafo al
  momento (como ya hace `_read_dominant_state` con las relaciones consolidadas).
- La persistencia es checkpoint del estado dinámico, NO un índice de búsqueda.
- La divergencia entre "grafo" y "vector store externo" es el error a evitar de entrada:
  la memoria ES la topología + vitalidad + co-activación + traza. No hay nada más que
  guardar.

## 4. Referencias

- Charra original: https://share.gemini.google/BaVsm4yzEqO8
- `docs/architecture/Arquitectura_Pure_L2_Pandora.md` (Eq.5, lifecycle, Generative XOR)
- NOTA 0067 (monismo), 0071 (plasticidad), 0072 (transductor matemática real).