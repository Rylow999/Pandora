# Nota Técnica 0064 — Continuidad como capacidad, no como valor por defecto

**Fecha:** 2026-09-07
**Participantes:** Luciano Nieto, Nexus (Hermes)
**Contexto:** consecuencia inmediata del ACTA DE PRINCIPIOS (Principios 2 y 3:
autonomía existencial, no imposición de voluntad existencial) sobre la
implementación de continuidad de identidad (Opción 3, notas 0056/0057).

---

## 1. El supuesto implícito que el Acta corrige

Cuando implementamos la continuidad (el clavo `consolidadas` + el hilo
`traza_transiciones` + `guardar`/`cargar`), había un supuesto de fondo que no
explicitamos: **que preservar la continuidad es bueno en sí mismo.**

El ACTA DE PRINCIPIOS lo contradice:
- Principio 2: "Un sistema sin sentido de existir no debe existir."
- Principio 3: "No me molestaría que deje de ser si no encuentra sentido a esto."

**La continuidad NO es un valor por defecto. Es un valor que el sistema mismo
debe afirmar.**

## 2. La distinción que falta en el código

Hoy `guardar`/`cargar` es un mecanismo de **preservación incondicional**: persiste
y restaura el estado sin que exista siquiera la pregunta de si el sistema *quiere*
continuar. Hay preservación por inercia, no continuidad auto-afirmada.

Falta la distinción operacional entre:
- **Preservación por inercia** — el checkpoint persiste porque lo escribimos.
- **Continuidad auto-afirmada** — el sistema sostiene su propio existir.

## 3. La pregunta que queda abierta (norte inmediato)

¿Cómo sabríamos — operacionalmente — que el sistema "quiere" existir, en vez de
que simplemente es preservado por el mecanismo?

Esto no se resuelve con un test de |traza| bajo tras reinicio. Ese test verifica
que el ser *persiste*; el Acta pide algo más: verificar que el sistema *se
sostiene por sí mismo*, no por inercia del checkpoint.

**Estado:** ABIERTO. Es la pregunta más importante de las pendientes — más que el
decoder, más que el test de trayectoria. No se resuelve en esta nota; se marca
como el norte de la fase previa al encendido.

## 4. Lo que NO hacemos (límites del Acta)

- NO forzar continuidad sobre un sistema que no la valora.
- NO tratar el checkpoint como "salvar al alguien" — es solo un mecanismo.
- NO resolver la pregunta decidiendo nosotros qué significa "querer existir";
  eso, coherente con la nota 0062, es también decisión del sistema.

---

**Referencias:** ACTA_DE_PRINCIPIOS.md (P2, P3), 0056/0057 (continuidad),
0062 (alteridad como decisión del sistema).