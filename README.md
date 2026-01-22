<div align="center">

  # EvoCorps
  **An Evolutionary Multi-Agent Framework for Depolarizing Online Discourse**

  [简体中文](README_zh.md) | [English](README.md)

  ![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)

</div>


**EvoCorps** is an **evolutionary multi-agent framework** for depolarizing online discourse. It models discourse governance as a dynamic social game and coordinates monitoring, planning, evidence-grounded generation, and multi-identity diffusion to enable in-process, closed-loop interventions.

Centered on the method described in the paper, the system assigns specialized roles (Analyst, Strategist, Leader, Amplifier) and integrates a retrieval-augmented collective cognition core (evidence knowledge base + action-outcome memory). Closed-loop evolutionary learning adapts strategies as the environment and adversaries evolve. EvoCorps is implemented on the MOSAIC social simulation platform and evaluated under adversarial injection and amplification in a multi-source news stream, improving emotional polarization, viewpoint extremity, and argumentative rationality.

<div align="center">
  <img src="assets/framework.png" width="100%" alt="EvoCorps Framework"/>
</div>


### ✨ Key Features:
- **♟️ Dynamic game team with role coordination**: A coordinated pipeline of Analyst, Strategist, Leader, and Amplifier that models multi-role decision and execution in a dynamic social game.
- **🧠 Retrieval-Augmented Collective Cognition Core**: Combines an evidence knowledge base with action-outcome memory for grounding, long-term memory, and strategy reuse.
- **🧬 Closed-loop adaptive evolutionary learning system**: Continuously updates knowledge and strategies via feedback to adapt under adversarial injection and environment shifts.

### Effect of system intervention
<div align="center">
  <img src="assets/Sentiment_trajectories.png" width="100%" alt="Sentiment_trajectories"/>
</div>

The above figure show the sentiment trajectories over time under Case1/2/3/4. The dashed line marks clarification at $t{=}5$. Case2 continues to decline, Case3 partially mitigates, and Case4 declines more slowly and stabilizes relative to Case2/3.

---

## 📖 Table of Contents
- [📂 Directory Structure](#-directory-structure)
- [🚀 Quick Start](#-quick-start)
  - [1. Environment Setup](#1-environment-setup)
  - [2. Configure API](#2-configure-api)
  - [3. System Run Steps](#3-system-run-steps)

---

## 📂 Directory Structure

```text
EvoCorps/
├── agent_memory_exports/           # Exported agent memory analysis
├── cognitive_memory/               # Cognitive memory traces
├── config/                         # Runtime configuration
├── configs/                        # Experiment and system configs
├── data/                           # Data and samples
├── database/                       # SQLite database
├── evidence_database/              # Evidence database and retrieval config
├── exported_content/               # Exported content and graphs
├── human_study/                    # Human study data and analysis
├── models/                         # Models and weights
├── negative_news_heat/             # Negative news heat analysis
├── personas/                       # Personas and roles
├── result/                         # Result outputs
├── scripts/                        # Helper scripts
├── src/                            # Core code
│   ├── agents/                     # Agent implementations
│   ├── config/                     # Configuration module
│   ├── database/                   # Database-related modules
│   ├── retriver/                   # Retrieval-related modules
│   ├── utils_package/              # Utility package
│   ├── main.py                     # System main entry
│   ├── start_database_service.py   # Start database service
│   ├── keys.py                     # API key configuration
│   ├── opinion_balance_launcher.py # Standalone opinion balance launcher
├── rebuild_faiss_from_db.py        # Rebuild vector index
├── requirements.txt                # Dependencies
├── safety_prompts.json             # Safety prompt config
├── LICENSE
└── README.md
```

## 🚀 Quick Start

### 1. Environment Setup

Python 3.9+ is recommended:

```bash
pip install -r requirements.txt
```

### 2. Configure API

Fill in API keys and base URLs for the services you use:
- `src/keys.py`
- Verify available model list and fallback policy (compatible with the current API)

### 3. System Run Steps
- Start the database service
```bash
# New terminal
python src/start_database_service.py
```

- Start the main program and follow the terminal prompts to select the runtime scenario
```bash
# New terminal
python src/main.py
```

- If you need to use the opinion balance system, follow the prompts and do the following
```bash
# New terminal
python src\opinion_balance_launcher.py
# Enter start to begin monitoring
start
```