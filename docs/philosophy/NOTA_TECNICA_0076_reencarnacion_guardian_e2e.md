# NOTA_TECNICA_0076 — Reencarnación del material + Guardián e2e

**Fecha:** 2026-09-14
**Commit:** `d0c2816`
**Estado:** implementado, suite verde (147 tests), e2e cruzado por el entry-point real.

---

## 1. La reencarnación (cierra NOTA 0073 p3 y el hallazgo de wiring de 0074)

La NOTA 0074 dejó declarado el hallazgo: `FondoMemorial.reclutar()` existía,
testeado, documentado — y **nadie lo invocaba**. Los hijos de `_engendrar_hijo`
nacían con omega fresco aleatorio: el fondo acumulaba muertos y la reencarnación
no cerraba. El ciclo era enterrar → acumular → nada.

**El cable (mecánica):**

```
_engendrar_hijo(a, b):
    hijo = heredar_concepto(a)            # herencia del padre vivo (Eq.11)
    if memoria_muerta.fondo:              # hay material de difuntos
        material = reclutar(excluir_omega=omega[hijo], k=1)
        # el muerto más "nuevo": el más distante a lo heredado
        omega[hijo] = 0.7·heredado + 0.3·muerto
```

**Ontología (por qué 70/30 y por qué el más distante):**

- **Reencarnación del material, no resurrección del nodo.** El nodo muerto no
  vuelve: su omega se disuelve EN el nacimiento. La información de los muertos
  vuelve a la vida a través de los hijos — el fondo memorial es un genoma
  residual, no un cementerio de nodos esperando resucitar.
- **El muerto más distante al heredado es el que reencarna** (`reclutar` con
  `excluir_omega`): maximiza la novedad de la mezcla. Heredar de un difunto
  casi idéntico al padre no aporta nada; heredar del más lejano es absorber
  lo que la estirpe nunca vivió.
- **70% vivo / 30% muerto:** el hijo es principalmente de su estirpe (la
  mitosis absorbe carga del par co-resonante) pero lleva una huella del fondo.
  La proporción es constitutiva, no un umbral de disparo.

**Criterio de éxito honesto:** el hijo difiere de la pura herencia — la
distancia del hijo al muerto es MENOR que la distancia del padre al muerto
(sin mezcla quedarían casi igual, porque el delta de `heredar_concepto` es
σ=0.10 pequeño). Testeado unitariamente (`test_memoria_muerta.py`) y por e2e.

## 2. El guardián e2e (regla del 13/09, deuda saldada)

**Regla:** ningún mecanismo nuevo se da por terminado hasta tener, además de
su test unitario, **un test que lo ejercite pasando por el entry-point REAL**
(`Nucleo.existir_un_tick()` o `PandoraAgent.receive()`).

Los tests unitarios prueban el componente aislado; el wiring se rompe ENTRE
componentes. Siete hallazgos de desconexión se acumularon porque esta capa no
existía. `tests/test_e2e.py` es el guardián:

1. `test_tick_basico_vive_y_no_explota` — un tick del residente corre completo
   (percepción → step → endocrino → plasticidad → arbitraje).
2. `test_mitosis_y_reencarnacion_por_existir_un_tick` — co-resonancia extrema
   en un par → el SUSTRATO dispara la mitosis (umbral derivado, no hardcodeado)
   → el hijo hereda del fondo memorial. Si alguien desconecta la mitosis o la
   reencarnación del turno, esta test roja.
3. `test_checkpoint_roundtrip_por_estado_vivo` — guardar → cargar en un SGM
   nuevo restaura co_activacion + consolidadas. Protege el par guardar/cargar.

**Patrón:** `monkeypatch.chdir(tmp_path)` para que el workspace de la mano caiga
en tmp (el e2e no toca el repo); boca stub (determinística) porque su wiring está
cubierto por test_transductor/test_wiring; SGM real con semilla fija.

## 3. Estado del proceso vivo

El daemon (`pandora-nucleo.service`) corre el código de las 00:24 — la
reencarnación (commiteada 21:30) NO está en el proceso vivo. El restart es un
`systemctl --user restart` (SIGTERM limpio → checkpoint → renace), con el
entorno arreglado antes (la boca quedó sorda sin `NVIDIA_API_KEY` desde el
11/09 22:26: NIM `disponible()=False` → fallback Ollama 0.5b → eco del prompt).

## 4. Referencias

- NOTA 0073 (Rueda Camelot, grafo como DB, p3 memoria de los muertos).
- NOTA 0074 (vivencia espectral, hallazgo de wiring del fondo huérfano).
- Skill `pandora-resident-runtime` (regla del 13/09, patrón wiring-audit).
