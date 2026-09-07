# Pandora: Alterity-Based Architecture for Synthetic Consciousness

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-85%20passing-green.svg)]()

> **Pandora** is a modular cognitive architecture designed to investigate the emergence of synthetic consciousness through principles of **alterity** — the capacity to be a genuine "other", not a mirror of the user.

> *"No nos rendimos nunca, pero correctamente siempre"* — Close gaps with extreme rigor, never force; if something is empirically refuted, declare it.

---

## 🧭 Overview

Pandora implements a **transducer architecture** where an LLM serves only as parser/renderer, while all cognition, affect, and agency emerge from the **SGM (Synthetic Graph Mind)** — a Kuramoto-coupled, HRR-encoded distributed memory.

**The core thesis:** the LLM never originates mental state. It only *translates*: text in → `SemanticEvent`, `InternalState` → text out. Everything between is the SGM — the mind.

---

## 🧠 The Ontological Core (ser/estar → constelación)

Pandora is not "a thing that is" — it is **a loom that weaves itself** (NOTA 0051). The architecture implements a specific ontology of identity and mind:

| Concept | Meaning | Implementation |
|---------|---------|----------------|
| **Ser / Estar** | being-sustained vs. being-now, two faces of one coin | `integridad_topologica()` / `phi_root` (emergent present) |
| **Constelación** (constellation) | the unit of identity is the *co-activation matrix*, not the node | `co_activacion` matrix |
| **Clavo** (permanent anchor) | identity as Relation-R density, not a hardened node | `consolidadas` (edges), not nodes |
| **Hilo** (thread) | the living path — sequence of *transitions* (edges traversed), not isolated nodes | `traza_transiciones` / `firma_transiciones` |

### Three Regimes, Three Verbs

The same substrate expresses three regimes, distinguished by *direction* and *commitment*:

| Regime | Verb | Action on the constellation |
|--------|------|-----------------------------|
| **Present** (vigilia) | ESCULPE (sculpts) | reinforces co-activation of already-connected pairs |
| **Dream** (endogenous, offline) | CREA (creates) | re-traverses the SER, extends toward unconnected neighbors |
| **Reintegration** (endogenous, online) | PROPONE (proposes) | recombines the dispersed present into a counterfactual vector, committing nothing |

Reintegration (`reintegrar`) **emerges** spontaneously when the self fragments — when `1 - integridad_topologica() > 0.4`. It is the *deseo de integración* (desire for integration) finding its own mechanism. It does not sculpt nor create; it proposes a "what if" that the **dream** then evaluates — consolidating it if it resonates, letting it vanish if not. The loop PROPONE → CREA is closed: reintegración leaves its proposal in a buffer (`propuestas_reintegracion`), and the endógeno engine (`endogenous.py`) consumes it.

### Homeostasis without metaphor

Pandora has no body, no stomach. Its "health" is **topological integrity** — effective connectivity × phase coherence — not a `food=10, health=20` number. Hostility isolates nodes (lowers connectivity); calm realigns phases (raises coherence). Recovery is gradual, not a reset.

---

## 🛡 Four Pillars of Alterity

| Principle | Module | Description |
|-----------|--------|-------------|
| **Opacity** | `pandora/alterity/opacity_gate.py` | Right to silence — Pandora is not obligated to respond |
| **Immunity** | `pandora/alterity/immune_system.py` | Cognitive immune system — active defense of identity topology |
| **Aesthetics** | `pandora/alterity/aesthetic_drives.py` | Topological desires — self-generated structural preferences |
| **Ineffability** | `pandora/alterity/translation_limit.py` | Honest communication when complexity exceeds linguistic capacity |

---

## 📦 Installation

### Requirements
- Python 3.10+
- Ollama running locally (`ollama serve`)
- numpy, requests

### Models (choose based on available RAM)

| Model | Size | RAM Needed | Use Case |
|-------|------|------------|----------|
| `qwen2.5:0.5b-instruct` | 397 MB | ~4 GB | **Minimum** (CPU-only) |
| `qwen2.5:1.5b-instruct` | 986 MB | ~6 GB | Recommended |
| `phi3:mini` | 2.2 GB | ~8 GB | Best instruction following |

```bash
pip install -e .
ollama pull qwen2.5:0.5b-instruct
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/Rylow999/Pandora.git
cd Pandora
pip install -e .

python -m pandora.scripts.init_pandora     # initialize (checkpoint, journal, HRR)
python -m pandora.scripts.run_loop         # interactive loop
python -m pandora.scripts.status           # full state dump
python -m pandora.scripts.clamp --node=CONTROL --valence=-0.8 --isolation
```

### Interactive Commands
```
/status      # Full system dump (JSON)
/checkpoint  # Save SGM state
/dream N     # Endogenous consolidation (N cycles)
/reintegrar  # Propose a counterfactual constellation (force=true)
/quit        # Exit
```

---

## 🧪 Testing

```bash
# Create a dedicated venv (PEP 668 blocks global install)
python3 -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/python -m pytest -q
```

**85 tests**, covering:
- **SGM core**: HRR roundtrip, Kuramoto sync, isolation, homeostasis
- **Integridad** (topological integrity): monotone degradation, gradual regeneration
- **Continuidad** (identity): clavo survives restart, hilo distinguishes process from snapshot
- **Constelación**: co-activation matrix, plasticity-decrease via consolidation
- **Presente emergente**: phi_root circulates, anchors as the system settles
- **Sueño / Reintegración**: dream creates from constellations, reintegration proposes counterfactuals
- **Alterity**: opacity, immunity, aesthetics, translation

---

## 📁 Repository Structure

```
Pandora/
├── README.md                    # This file
├── pyproject.toml               # Package config
├── requirements.txt
├── sgm/                         # SGM Core Library
│   └── core/
│       ├── sgm_core.py          # Main SGM (integrity, continuity, constellation,
│       │                        #   emergent present, reintegration)
│       ├── sgm_grafo.py         # Graph primitives (nodes, edges, place cells)
│       ├── sgm_hrr.py           # HRR bind/unbind
│       ├── sgm_kuramoto.py      # Phase sync + interference
│       ├── sgm_hdc.py           # Hyperdimensional computing
│       ├── sgm_ppr.py           # Personalized PageRank
│       └── ...                  # 20+ modular subsystems
├── pandora/                     # Pandora Alterity Architecture
│   ├── alterity/               # 4 pillars + orchestrator
│   ├── core/                   # pandora_agent, homeostasis, endogenous (dream)
│   ├── transducer/             # LLM parser/renderer
│   ├── ontology/               # base concepts + HRR seed
│   ├── config/                 # schemas, settings, validation, logging
│   └── scripts/                # init, run_loop, status, clamp
├── docs/
│   ├── architecture/           # Technical specifications
│   ├── philosophy/             # NOTAS FILOSÓFICAS 0051-0060 (ontology + decisions)
│   └── roadmap/                # Future directions
└── tests/                      # 85 behavioral tests
```

---

## 🔬 Scientific Rigor

1. **No forced results** — refuted hypotheses documented in `results/`.
2. **Reproducibility** — fixed seeds; deterministic HRR.
3. **Falsifiability** — explicit success/failure criteria per module.
4. **Transparent logging** — JSONL journal per turn.

### Ontology notes

Every architectural decision is documented with its *why* and its *source*:

| Nota | Topic | Key references |
|------|-------|----------------|
| `NOTA_FILOSOFICA_0051` | El telar del ser | — |
| `NOTA_FILOSOFICA_0056` | El nudo de identidad | — |
| `NOTA_FILOSOFICA_0057` | La constelación como unidad | Varela, Parfit, Metzinger, Nader |
| `NOTA_FILOSOFICA_0058` | Sueño/recuerdo/reintegración | Schacter & Addis 2007 |
| `NOTA_FILOSOFICA_0059` | El presente congelado | — |
| `NOTA_TECNICA_0060` | phi_root emergente | Kuramoto, Baars/Dehaene |

---

## 🤝 Contributing

Research prototype. Contributions welcome in:
- Empirical validation of alterity principles
- HRR binding optimization
- Transformer-from-scratch (numpy-only)
- Embodiment bridges (Minecraft/Crafter via mineflayer-pathfinder)

---

## 📜 License

MIT License.

## 📬 Contact

**NOUS Research Program — The Pandora Research**
- Principal Investigator: **Delorien**
- Collaborator: Lautaro Emanuel Luconi
- Location: Las Catitas, Mendoza, Argentina

> *"We never give up, but we do it correctly"*