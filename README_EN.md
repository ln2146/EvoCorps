<div align="center">

  # EvoCorps
  **An Evolutionary Multi-Agent Framework for Depolarizing Online Discourse**

  <div align="center">
    <img src="assets/logo.png" width="100%" alt="EvoCorps logo"/>
  </div>

  <p>
    <img alt="Python Version" src="https://img.shields.io/badge/python-3.9%2B-blue" />
    <img alt="License" src="https://img.shields.io/badge/license-MIT-green" />
    <img alt="Multi-Agent" src="https://img.shields.io/badge/agents-multi--agent-8a2be2" />
    <img alt="RAG" src="https://img.shields.io/badge/RAG-FAISS-orange" />
    <img alt="Database" src="https://img.shields.io/badge/DB-SQLite-blue" />
    <img alt="Platform" src="https://img.shields.io/badge/platform-MOSAIC-7b68ee" />
    <img alt="Stage" src="https://img.shields.io/badge/stage-research%20prototype-lightgrey" />
  </p>

  [简体中文](README.md) | [English](README_EN.md)


</div>


**EvoCorps** is an **evolutionary multi-agent framework** for depolarizing online discourse. It models discourse governance as a dynamic social game and coordinates monitoring, planning, evidence-grounded generation, and multi-identity diffusion to enable in-process, closed-loop interventions.

Centered on the method described in the paper, the system assigns specialized roles (Analyst, Strategist, Leader, Amplifier) and integrates a retrieval-augmented collective cognition core (evidence knowledge base + action-outcome memory). Closed-loop evolutionary learning adapts strategies as the environment and adversaries evolve. EvoCorps is implemented on the MOSAIC social simulation platform and evaluated under adversarial injection and amplification in a multi-source news stream, improving emotional polarization, viewpoint extremity, and argumentative rationality.

<div align="center">
  <img src="assets/framework.png" width="100%" alt="EvoCorps Framework"/>
</div>


### ✨ Key Features:
- **♟️ Clear role division with closed-loop coordination**: A four-role team (Analyst, Strategist, Leader, Amplifier) runs as a loop—monitor & assess → plan → generate → diffuse via multiple personas → evaluate—so interventions can be adjusted continuously during propagation.
- **🧠 Retrieval-augmented grounding with evidence and experience**: EvoCorps maintains an evidence base and records what each intervention led to. It prioritizes verifiable facts/arguments and reuses patterns that worked better in past rounds, improving reliability and team consistency.
- **🧬 Feedback-driven adaptation over time**: After each round, the system checks whether discussions become calmer and more moderate, then strengthens effective strategies and deemphasizes ineffective ones, helping it adapt as adversarial behaviors and conditions change.

### Effect of system intervention
<div align="center">
  <img src="assets/Sentiment_trajectories.png" width="100%" alt="Sentiment_trajectories"/>
</div>

The figure above shows the sentiment trajectories over time under Case1/2/3/4. The dashed line marks clarification at $t{=}5$. Case2 continues to decline, Case3 partially mitigates, and Case4 declines more slowly and stabilizes relative to Case2/3.

---

## 📖 Table of Contents
- [📂 Directory Structure](#-directory-structure)
- [🚀 Quick Start](#-quick-start)
  - [1. Create Environment](#1-create-environment)
  - [2. Install Dependencies](#2-install-dependencies)
  - [3. Configure API](#3-configure-api)
  - [4. System Run Steps](#4-system-run-steps)
- [⚖️ Ethics Statement](#ethics-statement)

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
├── requirements.txt                # Dependencies
├── safety_prompts.json             # Safety prompt config
├── LICENSE
└── README.md
```

## 🚀 Quick Start

### 1. Create Environment

If you use Conda:

```bash
# Create a conda environment
conda create -n your_conda_name python=3.12
conda activate your_conda_name
```

### 2. Install Dependencies

Python 3.9+ is recommended:

```bash
pip install -r requirements.txt
```

### 3. Configure API

Create a new `keys.py` file in the `src/` directory, copy the content below, and configure the API key and Base URL according to the service you are using.
```python
OPENAI_API_KEY = "YOUR_API_KEY"
OPENAI_BASE_URL = "BASE_URL"
```

### 4. System Run Steps
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
# Enter auto-status to print the action logs in real time
auto-status
```


## ⚖️ Ethics Statement
This work investigates mechanisms for online discourse depolarization in a simulated environment, utilizing publicly available datasets and synthetic agent interactions. It does not involve experiments with human subjects and does not collect or process personally identifying information. The primary goal of this research is to advance understanding of coordinated intervention mechanisms for platform governance, rather than to develop or deploy deceptive influence campaigns.

EvoCorps is framed as a governance-assistance approach for online platforms facing coordinated and malicious activities such as disinformation campaigns or adversarial manipulation. In such settings, platform governance actors may themselves require coordinated capabilities and stylistic diversity to respond effectively and proportionately. Our study therefore examines coordination and response diversity as governance mechanisms, not as tools for artificial consensus formation or manipulation.

We explicitly oppose the use of deceptive strategies in any real-world deployment. Although our simulations introduce diverse agent personas to explore theoretical boundaries of influence dynamics, any practical application must adhere strictly to principles of transparency and accountability. Automated agents should be clearly identified as AI-based assistants or governance tools, such as certified fact-checking bots, and must not impersonate human users or conceal their artificial nature.

Any deployment of systems inspired by this work should be integrated with existing platform governance processes and subject to platform-specific policies, transparency requirements, and continuous auditing. Such safeguards are necessary to mitigate unintended harms, including disparate impacts, erosion of user trust, or errors arising from automated judgments. The intended use of EvoCorps is to support responsible, transparent, and accountable governance interventions, rather than to mislead users or manufacture false consensus.
