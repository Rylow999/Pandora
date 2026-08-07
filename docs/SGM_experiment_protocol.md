# Protocolo de Experimentación SGM
## Convención de IDs, formato de registro y workflow

**Autor:** Luciano Benjamás Nieto  
**Fecha:** 2 de agosto de 2026  
**Versión:** 1.0 (definitivo)  
**Regla de oro:** Una vez que un experimento recibe su ID, NUNCA se reusa. Si se re-corre, es `exp_XXXX_rev2`.

---

## 1. Convención de Nombres de Experimentos

### Formato canónico

```
exp_SGM_XXXX_<descriptor>
```

Donde:
- `SGM` = proyecto (Synaptic Graph Model)
- `XXXX` = número secuencial de 4 dígitos, **único e irrepetible** (0001 en adelante)
- `<descriptor>` = nombre descriptivo corto que identifique el mecanismo bajo prueba

### Ejemplos

```
exp_SGM_0001_nodecore_smoke_test       # Fase 0 — smoke test de NodeCore
exp_SGM_0002_nodecore_memoria          # Fase 0 — benchmark memoria NodeCore vs SGMNode
exp_SGM_0003_nodecore_equiv_teorica    # Fase 0 — T-INF-06 baseline SGMNode
exp_SGM_0004_nodecore_equiv_practica    # Fase 0 — T-INF-06 NodeCore
```

### Reglas

1. **IDs son inmutables**: `exp_SGM_0001` siempre se refiere a la MISMA corrida con la MISMA seed/config.
2. **Si se re-corre**: `exp_SGM_0001_rev2`, `exp_SGM_0001_rev3`, etc. Cada revisión es un experimento NEW con su propio ID, pero con `_rev` que enlaza a la versión original.
3. **El descriptor va en snake_case_minúscula**, descriptivo de qué se mide no de cómo.
4. **Nunca reutilizar un ID para un experimento distinto**. Ni siquiera si el anterior falló.

---

## 2. Registro de Experimento (`results/experiment_registry.json`)

Cada experimento crea una entrada en `results/experiment_registry.json`. El registro se escribe **antes** de correr, no después.

### Formato

```json
{
  "experiment_id": "exp_SGM_0001",
  "name": "nodecore_smoke_test",
  "phase": "Fase 0 — Sustrato mínimo",
  "date_created": "2026-08-02",
  "date_run": null,
  "status": "designed",
  "hypothesis": "NodeCore + EdgeTable reproducirá los resultados de SGMNode sobre v0.14d sin degradación > 5%",
  "config": {
    "D": 16,
    "K": 10,
    "epochs": 3,
    "seed": 42,
    "corpus": "donquijote_20k_tokens"
  },
  "script": "phase0_nodecore/run_nodecore_smoke.py",
  "results_file": "phase0_nodecore/results_nodecore_smoke.json",
  "test_target": "T-INF-06",
  "baseline_for": [],
  "variant_of": null
}
```

### Estados posibles
- `designed` — escrito el plan, no corrió
- `running` — en background
- `done` — resultados JSON escritos
- `error` — falló, con error_message
- `archived` — revisado y cerrado

---

## 3. Workflow de Experimento (obligatorio, siempre)

1. **Claim → Test**: escribir el test de equivalencia primero. El test corre contra el BASELINE (SGMNode o el experimento previo validado) y produce un número que queda registrado.
2. **Registrar**: crear la entrada en `results/experiment_registry.json` con estado `designed`, antes de tocar código.
3. **Smoketest**: `py_compile` + `python3 -c "import run_X as m; print(m.minimal_call())"` antes de background.
4. **Correr en background** con `notify_on_complete=true` (nunca foreground si >60s).
5. **Escribir results_*.json** con: hypothesis, experiment_id, config exacta, seed, todos los números.
6. **Cotejar**: abrir el JSON y verificar que cada número del registro concuerde.
7. **Marcar archived** en el registry.
8. **Sync al vault**: `su -c cp` + `chown root:everybody` + `chmod 664`.

---

## 4. Mapping: viejas convenciones → nuevas

El LANGUAGE-ENGINE usó `v0.X` como ID. Eso fue el caos. Mapeo:

| Convención vieja | Problema | Convención nueva |
|------------------|----------|------------------|
| `v0.14d` (audit) vs `v0.14d` (no audit) | Mismo ID, distinto resultado | `exp_SGM_0047_nodecore_equiv` |
| `v0.3 REAL` vs `v0.3 REAL v2` | Versiones sin claridad | `exp_SGM_0033_hibernate_real_v1`, `exp_SGM_0034_hibernate_real_v2` |
| `v0.21 v8` vs `v0.21 v8b` vs `v0.21 v8c` | Subvariantes sin ID | `exp_SGM_0067_overSmoothing_a`, `exp_SGM_0068_overSmoothing_b` |
| Reusar `v0.14d_borrar` sin clave | Dos corridas distintas, mismo nombre | `exp_SGM_0051_borrar_contenido`, `exp_SGM_0092_borrar_contenido_v2` |

**Regla:** cada corrida nueva = nuevo ID. Si un experimento reusa configuración de otro, usa `variant_of: "exp_SGM_XXXX"`.
