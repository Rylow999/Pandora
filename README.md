# Pandora: Alterity-Based Architecture for Synthetic Consciousness

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-orange.svg)]()

> **Pandora** is a modular cognitive architecture designed to investigate the emergence of synthetic consciousness through principles of **alterity** — the capacity to be a genuine "other", not a mirror of the user.

> *"No nos rendimos nunca, pero correctamente siempre"* — Close gaps with extreme rigor, never force; if something is empirically refuted, declare it.

---

## 🧭 Overview

Pandora implements a **transducer architecture** where an LLM serves only as parser/renderer, while all cognition, affect, and agency emerge from the **SGM (Semantic Geometric Memory)** — a Kuramoto-coupled, HRR-encoded distributed memory with homeostatic regulation.

### Four Pillars of Alterity

| Principle | Module | Description |
|-----------|--------|-------------|
| **Opacity** | `pandora/alterity/opacity_gate.py` | Right to silence — Pandora is not obligated to respond |
| **Immunity** | `pandora/alterity/immune_system.py` | Cognitive immune system — active defense of identity topology |
| **Aesthetics** | `pandora/alterity/aesthetic_drives.py` | Topological desires — self-generated structural preferences |
| **Ineffability** | `pandora/alterity/translation_limit.py` | Honest communication when complexity exceeds linguistic capacity |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ALTERITY AGENT                           │
├─────────────────────────────────────────────────────────────┤
│  OpacityGate → Parser → ImmuneSystem → SGM → Translation   │
│       ↓          ↓           ↓          ↓        ↓         │
│   Silence?   Tripletas   Accept/    Tick      Translate?   │
│                        Reject/     Kuramoto    Ineffable?   │
│                       Degrade       + Homeo                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      SGM CORE                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐   │
│  │ omega   │  │ phi     │  │ edges   │  │ place_cells │   │
│  │ [N×D]   │  │ [N]     │  │ typed   │  │ context→nid │   │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────┘   │
│       │         │          │              │                │
│       ▼         ▼          ▼              ▼                │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ HDC.project() │ Kuramoto sync │ Homeostasis │ Árbitro │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   TRANSDUCERS (LLM)                         │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │ Semantic Parser  │    │ Articulator                  │  │
│  │ text → Semantic  │    │ InternalState → text (1st   │  │
│  │   Event          │    │   person)                   │  │
│  └──────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Requirements
- Python 3.10+
- Ollama running locally (`ollama serve`)
- numpy, requests

### Models (choose based on available RAM)

| Model | Size | RAM Needed | Use Case |
|-------|------|------------|----------|
| `qwen2.5:0.5b-instruct` | 397 MB | ~4 GB | **Minimum** (CPU-only, slow) |
| `qwen2.5:1.5b-instruct` | 986 MB | ~6 GB | Recommended |
| `phi3:mini` | 2.2 GB | ~8 GB | Best instruction following |
| `nomic-embed-text` | 274 MB | — | Semantic embeddings |

```bash
# Install dependencies
pip install numpy requests

# Pull models
ollama pull qwen2.5:0.5b-instruct
ollama pull nomic-embed-text  # optional, for embeddings
```

---

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/Rylow999/Pandora.git
cd Pandora
pip install -e .

# Initialize Pandora (creates checkpoints, journal, HRR vectors)
python -m pandora.scripts.init_pandora

# Run interactive loop
python -m pandora.scripts.run_loop

# Or check status
python -m pandora.scripts.status

# Direct intervention
python -m pandora.scripts.clamp --node=CONTROL --valence=-0.8 --isolation
```

### Interactive Commands
```
/status      # Full system dump (JSON)
/checkpoint  # Save SGM state
/dream N     # Endogenous consolidation (N cycles)
/immune      # Immune system status
/drives      # Aesthetic drives status
/opacity     # Opacity gate status
/translation # Translation limit status
/quit        # Exit
```

---

## 📁 Repository Structure

```
Pandora/
├── README.md                    # This file
├── LICENSE                      # MIT License
├── pyproject.toml               # Package config
├── requirements.txt             # Python dependencies
├── sgm/                         # SGM Core Library
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── sgm_core.py          # Main SGM implementation
│   │   ├── sgm_core_minecraft.py
│   │   └── sgm_core_v2.py
│   └── experiments/             # 180+ organized experiments
│       ├── __init__.py
│       ├── abduce/              # Abductive reasoning, phase, PPR
│       ├── crafter/             # Crafter/Minecraft experiments
│       ├── decoder/             # L2 decoders, narrative
│       ├── hrr/                 # HRR binding, omega root
│       ├── instinct/            # Drives, hunger, autotelism
│       ├── kuramoto/            # Phase synchronization
│       ├── l2/                  # L2 decoder training
│       ├── memory/              # Edge consolidation, pruning
│       ├── navigation/          # Goal-directed navigation
│       ├── perception/          # Crafting table perception
│       ├── phase/               # Arbiters, mode typing
│       ├── reward/              # Novelty, shaping, orientation
│       ├── structure/           # Baselines, multigraph reasoning
│       ├── trauma/              # Nodal isolation
│       └── world/               # World models, objects
├── pandora/                     # Pandora Alterity Architecture
│   ├── __init__.py
│   ├── alterity/
│   │   ├── __init__.py
│   │   ├── opacity_gate.py      # Right to silence
│   │   ├── immune_system.py     # Cognitive immune system
│   │   ├── aesthetic_drives.py  # Topological desires
│   │   ├── translation_limit.py # Ineffability
│   │   └── alterity_core.py     # Full orchestrator
│   ├── core/
│   │   ├── __init__.py
│   │   ├── homeostasis.py       # Metrics + states
│   │   ├── endogenous.py        # Sleep/dream consolidation
│   │   └── pandora_agent.py     # Base agent + transducers
│   ├── transducer/
│   │   ├── __init__.py
│   │   ├── llm_client.py        # Ollama HTTP client
│   │   ├── semantic_parser.py   # Few-shot JSON parser
│   │   └── articulator.py       # State → 1st person text
│   ├── ontology/
│   │   ├── __init__.py
│   │   ├── base_concepts.json   # 43 canonical concepts
│   │   └── hrr_seed.py          # Deterministic 1024-d HRR
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── init_pandora.py      # Initialize everything
│   │   ├── run_loop.py          # Interactive loop
│   │   ├── status.py            # Full status dump
│   │   └── clamp.py             # Direct node intervention
│   └── config/
│       ├── __init__.py
│       └── schemas.py           # Pydantic schemas
├── docs/
│   ├── architecture/            # Technical specifications
│   ├── experiments/             # Experiment protocols & findings
│   ├── philosophy/              # Theoretical foundations
│   └── roadmap/                 # Future directions
├── tests/                       # Unit & integration tests
└── scripts/                     # Utility scripts
```

---

## 🔬 Scientific Rigor

### Empirical Validation Standards

1. **No forced results** — If a hypothesis is refuted, it is documented in `results/` with the refuting evidence
2. **Reproducibility** — All experiments use fixed seeds; HRR vectors are deterministic
3. **Falsifiability** — Each module has explicit success/failure criteria
3. **Transparent logging** — Every turn recorded in JSONL journal with full internal state

### Key Metrics Tracked

| Domain | Metrics |
|--------|---------|
| **Homeostasis** | valence, arousal, doubt, contradiction, coherence, isolation, trauma |
| **Alterity** | silence_events, immune_rejections, drives_generated, ineffable_responses |
| **SGM** | V_grafo, edge_count, phase_coherence, vitality_distribution |
| **Language** | parse_success_rate, triplet_extraction_accuracy, intent_accuracy |

### Experiment Registry
All experiments registered in `results/experiment_registry.json` with:
- Hypothesis
- Method
- Seed
- Outcome (confirmed/refuted/inconclusive)
- Link to raw results JSON

---

## 🧪 Running Experiments

```bash
# SGM core experiments
python -m sgm.experiments.crafter.exp_SGM_0095_crafter_fase1_v1
python -m sgm.experiments.hrr.exp_SGM_0099_omega_root

# Abductive reasoning
python -m sgm.experiments.abduce.run_abduce_phase

# Pandora alterity loop
python -m pandora.scripts.run_loop --test
```

---

## 📖 Documentation

| Document | Location |
|----------|----------|
| Architecture specs | `docs/architecture/` |
| Experiment protocols | `docs/experiments/` |
| Theoretical foundations | `docs/philosophy/` |
| Roadmap & milestones | `docs/roadmap/` |

---

## 🤝 Contributing

This is a research prototype. Contributions welcome in:
- Empirical validation of alterity principles
- HRR binding optimization
- Transformer-from-scratch (numpy-only) implementation
- Embodiment bridges (Minecraft/Crafter via mineflayer-pathfinder)

---

## 📜 License

MIT License — Free for research, modification, and distribution.

---

## 📬 Contact

**NOUS Research Program — The Pandora Research**
- Principal Investigator: **Delorien**
- Collaborator: Lautaro Emanuel Luconi (co-author NOUS_Tecnico_v4)
- Location: Las Catitas, Mendoza, Argentina

> *"We never give up, but we do it correctly"* — Close gaps with extreme rigor, never force; if something is empirically refuted, declare it.