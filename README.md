# 🃏 MTG Feature Model Generator & Variability Analysis

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Flamapy](https://img.shields.io/badge/Flamapy-Feature%20Models-orange.svg)](https://github.com/flamapy/flamapy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A modular, production-grade Python pipeline designed to extract **Magic: The Gathering (MTG)** card data historically and automate the generation of **Feature Models (UVL)** using **Flamapy**, enabling software product line engineering and evolutionary analysis of game design spaces.

---

## 🏗️ Architecture

The system follows a strict **Separation of Concerns** principle and is decoupled into three independent, offline-capable phases:

1. **Phase 1 (Network Extraction):** Connects to the `mtgsdk` API with exponential backoff retries and atomic writes, caching raw expansion metadata and card products into clean CSV files.
2. **Phase 2 (Variant Transformation):** Operates completely offline, reading local CSVs, cleaning properties, and aggregating distinct feature variations into `.dat` variant files per expansion.
3. **Phase 3 (UVL Generation):** Applies the **Strategy Pattern** via a `VariationManager` and a polymorphic registry to inject expansion-specific variants and numerical AST range constraints into a static base feature model template, producing independent `.uvl` models.

```text
[ Phase 1: Download ]        [ Phase 2: Variants ]        [ Phase 3: UVL Generation ]
MTG API ──(Atomic CSVs)──> Local Products ──(Aggregate)──> .dat Files ──(Flamapy)──> .uvl Models
```

---

## 📁 Repository Structure

```text
mtg_project/
├── data/                       # Local data cache (auto-generated)
│   ├── expansions/             # Expansion metadata CSVs
│   ├── products/               # Unique card collection CSVs per expansion
│   └── variants/               # Aggregated property variants (.dat files)
│
├── uvl_models/                 # Feature Models
│   ├── templates/
│   │   └── base.uvl            # Static base feature model template (input)
│   └── generated/              # Output UVL models per expansion (auto-generated)
│
├── mtg_variability/            # Source code package
│   ├── extraction/
│   │   ├── api_client.py       # API connection & retry logic
│   │   ├── download_pipeline.py# Phase 1: Network extraction pipeline
│   │   ├── variant_pipeline.py # Phase 2: Local variant extraction pipeline
│   │   └── transformers.py     # Pure transformation & data cleaning functions
│   │
│   └── uvl_generator/
│       ├── manager.py          # VariationManager (Registry Pattern)
│       ├── pipeline.py         # Phase 3: UVL generation pipeline
│       ├── uvl_utils.py        # AST range constraints & feature group helpers
│       └── strategies/         # Polymorphic variation injection strategies
│           ├── base_strategy.py
│           ├── alternative_strategy.py
│           └── combat_stat_strategy.py
│
├── main.py                     # Global orchestration entrypoint
└── requirements.txt            # Project dependencies
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites

Ensure you have Python 3.10+ installed on your system.

### 2. Clone the Repository & Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-username/mtg-variability-analysis.git
cd mtg-variability-analysis

# Create and activate a virtual environment (recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 How to Run

All data directories and output folders will be automatically created upon execution. Make sure your static base model template is placed at `uvl_models/templates/base.uvl`.

Run the full end-to-end pipeline using the root orchestrator:

```bash
python main.py
```

### Execution Phases inside `main.py`

- **Phase 1 (Download):** Fetches card datasets from the remote API and caches them locally as CSVs. (Can be toggled off if local CSVs already exist).
- **Phase 2 (Variants):** Processes local CSVs offline to generate distinct variant distribution files (`.dat`).
- **Phase 3 (UVL Generation):** Parses variant files, applies the strategy registry, and exports valid Feature Models (`.uvl`) to `uvl_models/generated/`.

---

## 🔬 Reproducibility & Research Note

Thanks to the local caching mechanism, once Phase 1 has been executed, subsequent executions of Phases 2 and 3 operate 100% offline, ensuring full reproducibility for software engineering research and longitudinal design space evolution analysis.

---

## 📄 License

This project is licensed under the terms of the MIT License.
