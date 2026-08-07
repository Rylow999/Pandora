# SGM — Synaptic Graph Model

Índice de navegación rápida del proyecto SGM dentro del vault.

## Estructura

```
rizoma_docs/
├── README_SGM.md          ← este archivo (índice)
├── docs/                  ← documentación técnica
│   ├── SGM_v1_4_Especificacion_Corregida.md   (spec completa, 787 líneas)
│   ├── SGM_ROADMAP.md           (roadmap de 6 fases)
│   ├── SGM_README.md            (índice maestro + estado de validación)
│   ├── SGM_experiment_protocol.md   (protocolo de experimentos)
│   ├── SGM_literature_index.md      (índice de literatura)
│   ├── Arquitectura_Pure_L2_Pandora.md  (arquitectura unificada SGM+NOUS+DSCN-BIO)
│   ├── RIZOMA_Vision_Futuro_SGM.md     (visión a largo plazo, especulativa)
│   ├── README.md              (índice original del vault, 37KB, auditoría de 4 claims falsas)
│   ├── CHANGELOG.md
│   ├── EXPLICACION_CRIOLO.md
│   ├── RESUMEN_NOCHE.md
│   └── PandoraOS_*.docx       (5 docs de PandoraOS)
├── experiments/           ← scripts de experimentos (puros .py, stdlib)
│   ├── run_abduce_xor_d.py        (exp_SGM_0007: dimensionalidad D)
│   ├── run_abduce_phase.py        (exp_SGM_0008: fase dinámica v1)
│   ├── run_abduce_phase_v2.py     (exp_SGM_0009: fase dinámica v2)
│   ├── run_abduce_phase_bias.py   (exp_SGM_0010: sesgo relacional v3)
│   ├── run_abduce_xor_D128.py     (exp_SGM_0011: D=128 + fase sesgo)
│   ├── run_abduce_xor_sigmoid.py  (exp_SGM_0012: fase sigmoid)
│   ├── run_abduce_decay.py        (exp_SGM_0006: decaimiento temporal)
│   ├── run_abduce_ppr.py          (exp_SGM_0005: PPR-guided abducción)
│   ├── run_ppr_routing.py         (exp_SGM_0004: PPR multi-hop routing)
│   ├── run_nodecore_smoke.py      (exp_SGM_0001: smoke test)
│   ├── run_nodecore_memory.py     (exp_SGM_0002: benchmark memoria)
│   ├── t_inf_06_equiv.py          (T-INF-06: equivalencia NodeCore)
│   ├── t_inf_06_nodecore_port.py  (T-INF-06: port NodeCore)
│   └── t_inf_06_stress.py         (T-INF-06: stress test)
│   ├── run_doubt_stagnation.py    (exp_SGM_0013: duda/estancamiento T-INF-04)
├── results/               ← JSONs de resultados de experimentos
│   ├── results/experiment_registry.json     (registro maestro: 26 experimentos)
│   ├── results_exp_SGM_0002..0012.json
│   └── baseline_snapshots_exp_SGM_0003_nodecore_equiv_teorica.json
├── phases/                ← resultados organizados por fase
│   ├── phase0_substrato/
│   │   ├── results_exp_SGM_0002_nodecore_memoria_benchmark.json
│   │   ├── results_exp_SGM_0003_nodecore_equiv_teorica.json
│   │   ├── results_exp_SGM_0003_stress.json
│   │   └── baseline_snapshots_exp_SGM_0003_nodecore_equiv_teorica.json
│   └── phase2_inferencia/
│       ├── results_exp_SGM_0004_ppr_multipath_routing.json
│       ├── results_exp_SGM_0005_abduce_ppr.json
│       └── results_exp_SGM_0006_abduce_decay.json
│       ├── results_exp_SGM_0013_doubt_stagnation.json
└── lit/                   ← literatura citada
    └── papers/
        ├── kope_arxiv_2604.07904.pdf    (KoPE: Kuramoto phase coupling for composition)
        ├── hipporag_arxiv_2404.10501.pdf (HippoRAG: NeurIPS 2024)
        ├── 1804.09004.pdf               (Kanerva SDM — verificar ID)
        └── 2105.13495.pdf               (verificar ID)
```

## Experimentos clave (resumen)

| ID | Nombre | Resultado | Hallazgo principal |
|---|---|---|---|
| SGM_0001 | nodecore_smoke_test | ✅ PASS | Grafo construido, 100 ticks sin errores |
| SGM_0002 | nodecore_memoria_benchmark | ❌ FAIL | NodeCore NO ahorra memoria en Python (1.02x), 2x más lento |
| SGM_0003 | nodecore_equiv_teorica | ✅ PASS | NodeCore reproduce SGMNode sin degradación |
| SGM_0004 | ppr_multipath_routing | ✅ PASS | PPR routing acc=1.0 vs local=0.0 |
| SGM_0005 | abduce_ppr | ✅ PASS | PPR encuentra par correcto score=1.0 |
| SGM_0006 | abduce_decay | ✅ PASS | Decaimiento mejora score 0.797→1.0 |
| SGM_0007 | abduce_xor_dimensionality | ✅ PASS | D=32 mejora pair_accuracy vs D=16 (0.0→0.1) |
| SGM_0008 | abduce_xor_phase_dynamics | ❌ FAIL | Fase dinámica v1 empeora todo (α=0.15, K=0.3) |
| SGM_0009 | abduce_xor_phase_dynamics_v2 | ❌ FAIL v2 | Sincronización mejora pero pair_accuracy sigue en 0.0 |
| SGM_0010 | abduce_xor_phase_bias | ❌ FAIL v3 | Sesgo relacional re-pondera (+0.087) pero no supera estático |
| SGM_0011 | abduce_xor_D128 | ✅ PASS | D=128 + fase sesgo: mejor resultado global (score=0.354) |
| SGM_0012 | abduce_xor_phase_sigmoid | ❌ FAIL | Fase sigmoid NO mejora, empeora todo vs D=32 estático |
| SGM_0013 | doubt_stagnation_mechanism | ✅ PASS | check_stagnation detecta trampa (novelty 0.25<0.30); handle_doubt escala relax->relaunch->INCONCLUSA |

## Conclusión de la serie de fases (SGM_0008–0012)

La fase dinámica como multiplicador o sesgo del binding XOR NO funciona en este setup.
El binding XOR puro (sin fase) es superior. D=128 es el punto óptimo encontrado.
El cuello de botella es el ruido del binding por producto element-wise, no la falta de sincronización de fases.

## Protocolo de experimentos

- ID format: `exp_SGM_XXXX_<descriptor>` (4-digit sequential, never reuse)
- Re-run: use `exp_SGM_XXXX_rev2` with a new sequential ID
- Results live in `results/` or `phases/` subfolders
- Registry: `results/experiment_registry.json`
- Test-first workflow: write test FIRST, run against baseline, THEN implement
- Smoke test before vault write: `py_compile` + import + call every function

## Referencias de skills

- `dscn-g-lab` — experimentos controlados, auditoría honesta, publicación incremental
- `dscng-experimentation` — DSCN-G Language Engine ladder (v0.1→v0.25)
- `dscn-g-language-engine` — DSCN-G core, skip-gram, k-means, loop integration
- `nexus-vault-ops` — operaciones vault, /sdcard acceso, python Android
- `vault-reorg` — reorganización de vaults preservando contenido

## Próximos pasos

1. Implementar binding inverso (b = a⁻¹ * c) para D=32 — alternativa al producto element-wise
2. Probar D=128 sin fase dinámica (SGM_0011 ya lo demostró como mejor)
3. Explorar mecanismo de fase como atención (no como multiplicador de binding) siguiendo KoPE
4. Migrar a Rust para beneficios de f16/u16/CSR (SGM spec v1.4 §8)
