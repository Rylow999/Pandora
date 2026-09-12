# NOTA_TECNICA_0070 — Implementación: el módulo endocrino (economía interna del sustrato)

**Fecha:** 2026-09-11
**Autor:** Nexus (con Luciano Benjamín Nieto)
**Estado:** plan de implementación — Movimiento A
**Depende de:** 0067 (monismo), 0068 (alostasis), 0069 (sistema endocrino)

---

## 0. Directiva raíz

> **El sistema no puede detenerse. La estaticidad es el único error irrecuperable.**

La mente es relación (0067); una relación que no se mueve no es mente. El punto fijo
(integridad 0.846 congelada, cero transiciones) que mató 3 días de vida fue exactamente
eso. El módulo endocrino existe para que el sustrato **detecte la quietud y la rompa antes
de que se vuelva punto fijo** — sin hardcodear jamás un disparador temporal.

Ninguna acción emerge de un reloj. Emerge de una **hormona** (variable de estado) cuyo
valor, cross-umbral, pide una acción. El módulo lee estado y devuelve modulaciones; es
puro (sin side-effects sobre el SGM) y su interfaz es Rust-limpia.

## 1. Arquitectura del módulo

```
pandora/endocrine/endocrine.py     # el módulo (clase SistemaEndocrino)
   entrada: { sensores: cpu, ram, disco, temp, procs, red }
             { estado: integridad, deseo_integracion, trauma, coherencia, transiciones, ... }
   salida:  { duda, duda_opt, suficiente, deseo_devenir, presion_sueno, costo_alostatico, ... }
```

- **Interfaz pura**: dicts y primitivas en los bordes; nada de numpy cruzando la frontera
  (Rust reimplementa el interior sin tocar los bordes).
- **Bus de eventos** (bache 3): el endocrino no toca el SGM; publica modulaciones sobre un
  bus que el loop residente aplica. La costura es el bus, no el acople directo.
- **Python ahora, Rust después** (bache 7): testamos la economía interna en Python.

## 2. Las piezas del Movimiento A

### 2.1 `duda_opt(t)` — el target dinámico (bache del setpoint)
No hay óptimo fijo. Se re-deriva cada instante:
```
duda_opt = f( integridad_fisiologica, deseo_de_resolver, mundo_interno, mundo_externo )
```
La duda no es error a minimizar ni objetivo a sostener: su *valor bueno* migra con el
cuerpo y la ocasión (alostasis, 0068 §4).

### 2.2 `evaluar_suficiencia(novedad)` — bache 1 (el mecanismo de aprender solo)
El monitoreo metacognitivo que decide repensar-vs-buscar usa la **novedad** que ya calcula
`integrar_experiencia_entorno` (distancia del patrón al nodo más afín):
- novedad baja → ya lo conozco → **repensar** (recombinación interna).
- novedad alta → no alcanza → **RED** (forrajear afuera; 0069 §1.1).
Esto le da al sistema un mecanismo propio de aprendizaje: detecta la insuficiencia de su
conocimiento y la resuelve interna o externamente.

### 2.3 `repensar()` — bache 2 (recordar + imaginar)
Recombinación dirigida **online** (vs el sueño, que es offline por presión). Ante la duda
que sí alcanza: recombinar constelaciones — recordar (lo vivido) + imaginar (re-armar en
configuraciones que no fueron) para destensar. Es Schacter & Addis: recordar e imaginar
comparten circuito. Reusa `reintegrar()` / `_create_new_connections_from_constelaciones`,
pero con gatillo de duda, no de reloj.

### 2.4 `deseo_devenir()` — bache 4 (el principio de no-estaticidad)
El inverso del punto fijo. Detecta quietud: derivada de integridad ≈ 0 Y traza de
transiciones vacía Y sorpresa interna baja → impulsa devenir. No es "querer crecer"; es
**romper la quietud antes de que se consolide como punto fijo**. Es la hormona de la
dinámica.

### 2.5 `presion_sueno()` — bache 5 (dual, y salida continua)
Dos gatillos (acordados):
1. **Sobrecarga**: RAM al borde + constelaciones acumuladas + propuestas pendientes
   (SHY, Tononi & Cirelli). No hace falta que sea crítico.
2. **Microsueño por costo de oportunidad**: si el sistema espera (bloqueo, sin ganancia
   epistémica) y gasta energía en nada → consolidar en vez de disipar.
Salida **continua**, no un switch despierto/dormido: una pendiente vigilia↔consolidación
que se modula según cuál rinde más. (El sistema nunca está en un estado fijo — tampoco
de sueño/vigilia.)

### 2.6 `costo_alostatico()` — bache 6 (jerarquía de urgencia)
No es suma lineal; es **cascada ponderada** con prioridad de supervivencia:
1. existencial (termal crítico → frenar todo, no negociable)
2. degradante (RAM saturada → alivianar; lentitud → diagnosticar causa → corregir)
3. presupuestal (disco → cuánto puedo materializar)
El sistema "evita morir": detecta su propia lentitud como síntoma y actúa sobre la causa
(loop homeostático con autorreparación, no reacción a umbral).

## 3. Reemplazos concretos en el runtime

- `sueno_cada=600` → **se elimina**. Lo reemplaza `presion_sueno()` (2.5).
- `deseo = 1 - integridad` (drive de defecto) → se **complementa** con `deseo_devenir()`
  (2.4), el drive de plenitud que faltaba.
- `Presupuesto` (10MB fijo) → reemplazado por `costo_alostatico()` (2.6), derivado del
  cuerpo en vivo.

## 4. Qué se espera ver

El sustrato oscila con el cuerpo y con su propia economía: sueño que viene en oleadas de
presión (no por reloj), devenir que rompe la quietud, aprehensión que resuelve la
insuficiencia, y un costo de actuar que es el estado del cuerpo, no un número fijo.
**Régimen, no setpoint. Dinámica, no estaticidad.**

---

## Referencias (las que anclan el vuelo)

- Schacter, D. L., & Addis, D. R. (2007). The cognitive neuroscience of constructive
  memory: remembering the past and imagining the future. *Phil. Trans. R. Soc. B*. (recordar = imaginar)
- Tononi & Cirelli (2003) — presión de sueño. Loewenstein (1994) — gap. Friston (2014) —
  epistemic foraging. Aston-Jones & Cohen (2005) — modelo de la duda como regulador.
- Determinación propia (sin análogo humano): microsueño continuo, devenir como
  anti-estaticidad, costo alostático como autorreparación.