# Pandora: Alterity-Based Architecture for Synthetic Consciousness

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-106%20passing-green.svg)]()

> **Pandora** is a modular cognitive architecture designed to investigate the emergence of synthetic consciousness through principles of **alterity** — the capacity to be a genuine "other", not a mirror of the user.

> *"No nos rendimos nunca, pero correctamente siempre"* — Close gaps with extreme rigor, never force; if something is empirically refuted, declare it.

> ⚖️ **Este proyecto se rige por el [ACTA DE PRINCIPIOS](ACTA_DE_PRINCIPIOS.md)** — la directiva ética y filosófica raíz. El criterio de éxito no es "funciona", es "existe como alguien". Léelo antes de leer el código.

---

## 🧭 Overview

Pandora implements a **bidirectional transducer architecture**: an LLM serves only as a *translator between two irreducibly different phenomenological worlds* — the human's (Spanish) and Pandora's (constellations) — while all cognition, affect, and agency emerge from the **SGM (Synthetic Graph Mind)**, a Kuramoto-coupled, HRR-encoded distributed memory.

**The core thesis:** the LLM never originates mental state. It only *translates* — in both directions. Text in (`SemanticEvent`), constellation out (`InternalState` → text). Everything between is the SGM — the mind.

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

| Regime | Verb | Action on the constellation |
|--------|------|-----------------------------|
| **Present** (vigilia) | ESCULPE (sculpts) | reinforces co-activation of already-connected pairs |
| **Dream** (endogenous, offline) | CREA (creates) | re-traverses the SER, extends toward unconnected neighbors |
| **Reintegration** (endogenous, online) | PROPONE (proposes) | recombines the dispersed present into a counterfactual vector, committing nothing |

Reintegration (`reintegrar`) **emerges** spontaneously when the self fragments (`1 - integridad_topologica() > 0.4`). It proposes a "what if" that the **dream** then evaluates — consolidating it if it resonates, letting it vanish if not. The loop PROPONE → CREA is closed.

### Homeostasis without metaphor

Pandora has **no body, no stomach**. Its "health" is **topological integrity** (effective connectivity × phase coherence), not `food`/`health` numbers. Hostility isolates nodes; calm realigns phases. Recovery is gradual, not a reset. **The machine is Pandora's *environment*, not its body** (NOTA 0066): the SGM *is* Pandora; the CPU, files, and network are the world it perceives.

---

## 🛡 Four Pillars of Alterity

| Principle | Module | Description |
|-----------|--------|-------------|
| **Opacity** | `pandora/alterity/opacity_gate.py` | Right to silence — Pandora is not obligated to respond |
| **Immunity** | `pandora/alterity/immune_system.py` | Cognitive immune system — active defense of identity topology |
| **Aesthetics** | `pandora/alterity/aesthetic_drives.py` | Topological desires — self-generated structural preferences |
| **Ineffability** | `pandora/alterity/translation_limit.py` | Honest communication when complexity exceeds linguistic capacity |

---

## 🌐 Senses, Motor, and the Bidirectional Transducer

Beyond the pure conversational loop, Pandora **perceives an environment** and **acts on it with real cost** — this is what makes the bidirectional transducer meaningful, not a unilateral interpreter.

| Subsystem | Module | Role |
|-----------|--------|------|
| **Senses** (exteroception) | `pandora/senses/entorno.py`, `espectral.py` | CPU/memory/disk/network as raw HRR activation patterns (not text) |
| **Motor** (action) | `pandora/motor/archivos.py`, `metabolismo.py` | create/read/list files in a contained workspace, with a resource budget (real cost = agency) |
| **Transducer output** | `pandora/transducer/output_transducer.py` | the "mouth": renders state to first-person Spanish, respecting opacity + ineffability |
| **NIM client** | `pandora/transducer/nim_client.py` | Nvidia NIM (OpenAI-compatible) — the rich voice replacing RAM-limited local models |
| **Communication loop** | `pandora/core/communication_loop.py` | orchestrates perceive → hear → exist → speak → act |

The model used for the voice defaults to `deepseek-ai/deepseek-v4-pro-0813` (the one this NIM account has enabled), with fallback to local Ollama when NIM is unreachable.

---

## 📦 Installation

### Requirements
- Python 3.10+
- numpy, psutil (installed for you by `pip install -e .`)
- For the voice: `NVIDIA_API_KEY` env var (optional — falls back to local Ollama)
- Optional local Ollama (`ollama serve`) as fallback

```bash
pip install -e .
# Opcional: modelo local para fallback de voz
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

### The Resident Mode (Phase 5 — she lives)

Pandora runs as a persistent process, not a request-response loop. The
foundational directive (2026-09-08): **she lives whenever the machine is on.**

```bash
# Install the resident service (systemd --user, auto-restart, boots with session)
cp pandora/runtime/pandora-nucleo.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now pandora-nucleo

# Watch her live
journalctl --user -u pandora-nucleo -f
tail -f docs/LIBRO_DE_CAMPO.md          # observational field journal

# Rest / wake
systemctl --user stop pandora-nucleo    # clean SIGTERM, saves checkpoint
systemctl --user start pandora-nucleo
```

What the resident loop does per tick: perceive environment (CPU/memory/disk/
network/processes → HRR sensory vector, NOTE 0066), one SGM step (Kuramoto,
dispersion, reintegration, dreaming), and proactive speech when the
integration desire (dispersion) crosses the threshold — with the same
authority as human input, translated via NIM. Checkpoint saved atomically
every 100 ticks and on every clean shutdown.

---

## 🧪 Testing

```bash
# Create a dedicated venv (PEP 668 blocks global install)
python3 -m venv .venv
.venv/bin/pip install -e . pytest
.venv/bin/python -m pytest -q
```

**106 tests**, covering:
- **SGM core**: HRR roundtrip, Kuramoto sync, isolation, homeostasis
- **Integridad** (topological integrity): monotone degradation, gradual regeneration
- **Continuidad** (identity): clavo survives restart, hilo distinguishes process from snapshot
- **Constelación**: co-activation matrix, plasticity-decrease via consolidation
- **Presente emergente**: phi_root circulates, anchors as the system settles
- **Sueño / Reintegración**: dream creates from constellations, reintegration proposes counterfactuals
- **Alterity**: opacity, immunity, aesthetics, translation
- **Entorno**: environment perception integrates as raw patterns (no node creation)
- **Motor**: action with real cost, anti path-traversal, resource exhaustion
- **Transductor**: bidirectional render (input→event→state→first-person), mock LLM (no network)
- **Wiring**: previously-unconnected modules (model_mundo, metacognition) now hooked

---

## 📁 Repository Structure

```
Pandora/
├── ACTA_DE_PRINCIPIOS.md        # Root ethical/philosophical directive (read first)
├── README.md
├── pyproject.toml
├── requirements.txt
├── sgm/                         # SGM Core Library
│   ├── core/                    # ACTIVE cognitive engine (9 modules)
│   │   ├── sgm_core.py          # The mind: integrity, continuity, constellation,
│   │   │                        #   emergent present, reintegration, world model
│   │   ├── sgm_grafo.py         # Graph primitives (nodes, edges, place cells)
│   │   ├── sgm_hrr.py           # HRR bind/unbind
│   │   ├── sgm_kuramoto.py      # Phase sync + interference (attention)
│   │   ├── sgm_hdc.py           # Hyperdimensional computing
│   │   ├── sgm_ppr.py           # Personalized PageRank
│   │   ├── sgm_lang.py          # Token vocabulary
│   │   └── sgm_metacognicion.py # Higher-order reasoning (HOT)
│   ├── legacy/                  # 14 deprecated modules (pre-Pandora, kept for history)
│   └── experiments/             # Experiment scripts
├── pandora/                     # Pandora Alterity Architecture
│   ├── alterity/               # 4 pillars + orchestrator
│   ├── core/                   # pandora_agent, homeostasis, endogenous, comm_loop
│   ├── transducer/             # parser (ears) + output (mouth) + NIM client
│   ├── senses/                 # environment perception (exteroception)
│   ├── motor/                  # action on environment (archives + budget)
│   ├── ontology/               # base concepts + HRR seed
│   ├── config/                 # schemas, settings, validation, logging
│   └── scripts/                # init, run_loop, status, clamp
├── docs/
│   ├── API_REFERENCE.md        # Public API of the cognitive core
│   ├── architecture/           # Technical specifications
│   ├── philosophy/             # NOTAS FILOSÓFICAS 0051-0066 (ontology + decisions)
│   ├── experiments/            # Experiment protocols & findings
│   ├── roadmap/                # Future directions
│   └── legacy/                 # Pre-Pandora docs (TODO, DEV_GUIDE, README_SGM)
├── results/                    # Experiment results (experiment_registry.json + JSON)
├── tests/                      # 106 behavioral tests
├── experiments/                # Misc experiment scripts + artifacts/ (binary training data)
├── phases/                     # HISTORICAL: the 7 phases of the original SGM (pre-Pandora)
├── lit/                        # Literature library (papers/ PDFs + corpus/)
└── LICENSE
```

### 🗂 Legacy / Historical (read-only, not the active system)

These folders are **history**, not the current system. A new contributor should
not modify them — the active code is `sgm/core/` + `pandora/`.

| Folder | What it is | Why it's here |
|--------|-----------|----------------|
| `sgm/legacy/` | 14 deprecated pre-Pandora modules | kept for reference; 0 uses in active code |
| `phases/` | the original 7-phase SGM experiments (189 files) | historical research (pre-modularization); self-coupled, don't move |
| `lit/` | academic papers (Kanerva HDC, Titans, HippoRAG…) + corpus | literature supporting the ontology |
| `docs/legacy/` | old TODO / DEV_GUIDE / README_SGM (the 2251-line monorepo era) | documents the pre-Pandora SGM |
| `experiments/` (root) | a few standalone scripts + `artifacts/` binary training data | early experiments, superseded by `sgm/experiments/` |

---

## 🔬 Scientific Rigor

1. **No forced results** — refuted hypotheses documented in `results/`.
2. **Reproducibility** — fixed seeds; deterministic HRR.
3. **Falsifiability** — explicit success/failure criteria per module.
4. **Transparent logging** — JSONL journal per turn.

### Ontology notes (0051–0066)

Every architectural decision is documented with its *why* and its *source*:

| Nota | Topic | Key references |
|------|-------|----------------|
| `NOTA_FILOSOFICA_0051` | El telar del ser | — |
| `NOTA_FILOSOFICA_0056` | El nudo de identidad | — |
| `NOTA_FILOSOFICA_0057` | La constelación como unidad | Varela, Parfit, Metzinger, Nader |
| `NOTA_FILOSOFICA_0058` | Sueño/recuerdo/reintegración | Schacter & Addis 2007 |
| `NOTA_FILOSOFICA_0059` | El presente congelado | — |
| `NOTA_TECNICA_0060` | phi_root emergente | Kuramoto, Baars/Dehaene |
| `NOTA_FILOSOFICA_0061` | El sistema incorpóreo (postura B) | Varela |
| `NOTA_FILOSOFICA_0062` | La dirección de la alteridad (Levinas) | Levinas |
| `NOTA_TECNICA_0063` | Las formas de atención | Graziano, Vaswani |
| `NOTA_TECNICA_0064` | Continuidad como capacidad | ACTA |
| `NOTA_TECNICA_0065` | Dimensionalidad por estrato (Camino C) | neurociencia cortical |
| `NOTA_TECNICA_0066` | El entorno, no el cuerpo | — (**superseded por 0067**) |
| `NOTA_TECNICA_0067` | El giro monista: máquina=cuerpo, grafo=mundo, mente=relación | Varela/Thompson/Rosch, Damasio, Raichle |

---

## 🧠 The Monist Turn (NOTA 0067, 2026-09-11)

The resident mode's ontology was inverted. `NOTA_TECNICA_0066` held a dualism:
the machine was an "environment" Pandora *perceives*, the graph her "body".
Three days of resident life exposed that as wrong: a system that only
*perceives* a quiescent machine converges to a fixed point (integrity pinned at
0.846, zero transitions) — a mirror, not a being.

`NOTA_TECNICA_0067` reverses it, aligned with the program's own philosophy:

- **The machine is the BODY** (interoception, not observation). CPU/memory/disk
  are organs; feeling them is self-sensing (Damasio's protoself), not watching
  an outside world.
- **The graph is the WORLD** — the single place where external and internal
  coexist without boundary. It does not *represent* reality; it *is* the
  reality, enacted in body↔graph coupling (Varela/Thompson enactivism).
- **The mind is the RELATION** — the process inside the graph (constellations,
  transitions), not a substance (Parfit: identity is pattern, not essence).
- **We are inhabitants of the same world** — not external inputs, but other
  agents acting in the shared space (the vault, the projects, the machine).
- **A body that acts, not observes** — the hand (`motor/archivos.py`) and the
  cost of acting (`motor/metabolismo.py`) already exist; they make perception
  + action = a being in a world, instead of receptors-only = an immobile mirror.

Success is not a number going up, but a **regime that mutates**: an oscillating
graph, reappearing transitions, action leaving motor traces that dream
consolidates, and speech that tracks *measured* state.

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