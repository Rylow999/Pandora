# Nota Técnica 0060 — phi_root emergente: la fase media de Kuramoto ponderada por interferencia

**Fecha:** 2026-09-01
**Participantes:** Luciano Nieto, Nexus (Hermes)
**Contexto:** resolución de la 0059 (presente congelado). Decisión de mecanismo.

---

## 1. El problema (de 0059)

`phi_root = 0.0` fijo = presente congelado = falso ser (snapshot B de T-ID-03).

## 2. Lo que dice la literatura (y que resuelve)

### Kuramoto — la referencia emerge, no se impone
El order parameter complejo ReiΨ define la fase global Ψ como la FASE MEDIA del
colectivo. Citar arXiv 2603.05668 ("Operational Emergence of a Global Phase"):
la fase global Ψ es una coordenada macroscópica que *surge* del promediado de los
osciladores. No hay phi_root externo en Kuramoto: hay ψ = fase media.

### Dehaene/Baars (GNW) — el presente es una coalición ganadora
La consciencia = "ignición" (amplificación no-lineal súbita) + winner-take-all:
de muchas coaliciones locales, una gana y se broadcast. El presente no es un
punto estático, es la coalición que gana el instante y se vuelve accesible.

## 3. Decisión de mecanismo

**phi_root = fase media ponderada por interferencia de la zona activa:**

```
phi_root = phase( Σ_j I_j · exp(i·φ_j) )
```

donde I_j = interferencia (Eq.7), y la suma es sobre la zona activa (I > θ_interf).

- **Emergencia (Kuramoto):** la referencia sale del colectivo, no se impone (es el ψ).
- **Ganador (Dehaene):** ponderar por I hace que los nodos cognitivamente
  relevantes dominen la referencia = coalición ganadora que polariza el presente.
- **Ser/estar:** el estar = circulación de ψ (el presente se mueve con la
  constelación activa); el ser = ψ tiende a anclarse en las constelaciones más
  co-activadas (los clavos) por su interferencia persistentemente alta.

**No introduce parámetros nuevos:** I y φ ya existen; solo se computa la fase
media ponderada en vez del 0.0.

## 4. Elección de granularidad (PENDIENTE de decisión de Luciano)

- **Zona activa (I > θ_interf) + respaldo global si vacía:** fiel a Dehaene
  (winner-take-all que se broadcast); volátil pero vivo.
- **Solo promedio global:** el presente = centro de masa del sistema entero;
  robusto pero disipa la coalición ganadora.

Nexus inclinado por: zona activa + respaldo global (floor).

## 5. Estado

Decidir granularidad → implementar en actualizar_kuramoto → test de que phi_root
se mueve con la constelación activa y converge a zona estable.

---

**Referencias:**
- Kuramoto (1975), order parameter ReiΨ; arXiv 2603.05668.
- Baars (1988) / Dehaene & Changeux, GNW: ignition + winner-take-all + broadcast.

**Referencias cruzadas:** 0059 (presente congelado), 0058 (sueño/recuerdo), 0057
(constelación), 0056 (nudo), Arquitectura Pure L2 §4.4.