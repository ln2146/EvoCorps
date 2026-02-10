<div align="center">

  <div align="center">
    <img src="assets/logoheng.svg" width="100%" alt="EvoCorps logo"/>
  </div>

  **An Evolutionary Multi-Agent Framework for Depolarizing Online Discourse**

[简体中文](README.md) | [English](README_EN.md)

  [![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/abs/2602.08529)
  ![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)

</div>

<a id="overview"></a>
## ⚡ Overview

**EvoCorps** is an evolutionary multi-agent framework for depolarizing online discourse. Rather than focusing only on detection or post-hoc moderation, it treats interventions as a continuing process and supports in-process adjustments during propagation—reducing affective confrontation, curbing the spread of extreme viewpoints, and improving the overall rationality of discussion in a simulated environment.

EvoCorps organizes heterogeneous agents to simulate real-world roles in discourse participation, covering monitoring, situation modeling, intervention planning, evidence-grounded response generation, and multi-persona diffusion. It is supported by a retrieval-augmented cognition core (argument knowledge base + action–outcome memory) and improved via feedback-driven evolutionary learning, so strategies can adapt as the environment changes.

<a id="problem"></a>
## 🧩 Problem We Target

Online discourse can gradually split under homophilous interactions and engagement-driven recommendation. When coordinated malicious accounts inject and amplify emotionally charged narratives early, polarization accelerates.

<div align="center">
  <img src="assets/background.svg" width="80%" alt="Motivation: from normal communication to polarization under malicious attack, where passive detection and post-hoc intervention are often belated and weak"/>
</div>

This figure summarizes our motivation: starting from normal communication, malicious injection can push discussions toward an irreconcilable divide. Because emotional signals often spread faster than factual clarification, relying only on passive detection or post-hoc labeling/removal is frequently too late to change the trajectory.

Common limitations in existing approaches include:

1. Post-hoc detection dominates, with inherent response latency
2. Static strategies struggle against organized and evolving adversaries
3. Weak closed-loop feedback makes it hard to tell whether interventions truly change outcomes

EvoCorps aims to shift from “detect, then react” to “continuously regulate during propagation.”

<a id="how-it-works"></a>
## 🛠️ How EvoCorps Works

Monitoring → Situation modeling → Intervention planning → Evidence-grounded generation → Multi-persona diffusion → Feedback and strategy evolution

EvoCorps uses four roles—**Analyst, Strategist, Leader, Amplifier**—to connect “plan → generate → diffuse → evaluate” into an executable workflow, and to reuse arguments and experience through retrieval-augmented cognition.

<div align="center">
  <img src="assets/framework.svg" width="100%" alt="EvoCorps Framework"/>
</div>


### ✨ Key Features:
- **♟️ Clear role division with closed-loop coordination**: A four-role team runs as a loop—monitor & assess → plan → generate → diffuse → evaluate—so interventions can be adjusted continuously during propagation.
- **🧠 Evidence- and experience-grounded responses**: The system maintains an argument/evidence base and records what each intervention led to, prioritizing verifiable points and reusing patterns that worked better in past rounds.
- **🧬 Feedback-driven adaptation**: After each round, EvoCorps evaluates whether discussions become calmer and more moderate, then strengthens effective strategies and weakens ineffective ones over time.

<a id="evaluation"></a>
## 📊 Evaluation

We evaluate EvoCorps on the **MOSAIC** social simulation platform under scenarios with negative news streams and adversarial amplification. Results show that EvoCorps improves key indicators including emotional polarization, viewpoint extremity, and argumentative rationality compared to post-hoc baselines.

### Intervention Effect (Illustration)
<div align="center">
  <img src="assets/Sentiment_trajectories.png" width="100%" alt="Sentiment_trajectories"/>
</div>

The figure compares sentiment trajectories over time under four settings: Case 1 (only ordinary users; no adversary and no intervention), Case 2 (coordinated malicious amplification; no protection), Case 3 (post-hoc review on top of Case 2), and Case 4 (EvoCorps proactive, role-coordinated in-process intervention on top of Case 2). The dashed line marks when factual clarification starts to be injected (time step 5). Under adversarial amplification, sentiment is harder to recover with no protection or post-hoc intervention only, while EvoCorps stabilizes earlier and trends more steadily.

---

<a id="interface-preview"></a>
## 📷 Interface Preview

<div align="center">
<table align="center">
<tr>
<td align="center" width="50%"><strong>🏠 Platform Homepage</strong><br><img src="assets/homepage.gif" width="100%" alt="Platform Homepage"><br>Static and dynamic mode selection</td>
<td align="center" width="50%"><strong>📈 Data Monitoring</strong><br><img src="assets/datadetect.gif" width="100%" alt="Data Monitoring"><br>View detailed information about users and posts</td>
</tr>
<tr>
<td align="center" width="50%"><strong>🕸️ Relationship Graph</strong><br><img src="assets/graph.gif" width="100%" alt="Relationship Graph"><br>Visualize the network of users, posts, and comments</td>
<td align="center" width="50%"><strong>💬 Interview Feature</strong><br><img src="assets/talking.gif" width="100%" alt="Interview Feature"><br>Send questionnaire questions to simulated users and collect responses</td>
</tr>
</table>
</div>

---

## 📖 Table of Contents
- [📂 Project Structure](#project-structure)
- [🚀 Quick Start](#-quick-start)
  - [1. Create Environment](#1-create-environment)
  - [2. Install Dependencies](#2-install-dependencies)
  - [3. Configure API](#3-configure-api)
  - [4. System Run Steps](#4-system-run-steps)
- [⚖️ Ethics Statement](#ethics-statement)

---

<a id="project-structure"></a>
## 📂 Project Structure

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
├── LICENSE
└── README.md
```

## 🚀 Quick Start

### 1. Create Environment

Using Conda:

```bash
# Create a conda environment
conda create -n your_conda_name python=3.12
conda activate your_conda_name
```

### 2. Install Dependencies

Base dependency installation:

```bash
pip install -r requirements.txt
```

### 3. Configure API & Select Models

Fill in the corresponding API-KEY and BASE-URL in `src/keys.py`, and configure the models in `src/multi_model_selector.py`.
(Example: if you configure DeepSeek API-KEY and BASE-URL in `src/keys.py`, you can set `DEFAULT_POOL = ["deepseek-chat"]` in `src/multi_model_selector.py`; if you configure Gemini API-KEY and BASE-URL, you can set `DEFAULT_POOL = ["gemini-2.0-flash"]`; for embeddings you can use OpenAI `text-embedding-3-large`, Zhipu `embedding-3`, etc.)


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
python src/opinion_balance_launcher.py
# Enter start to begin monitoring
start
# Enter auto-status to print the action logs in real time
auto-status
```

### 5. Launch Frontend Visualization Interface

- Start the backend API service
```bash
# New terminal
python frontend_api.py
```

- Start the frontend development server
```bash
# New terminal, navigate to frontend directory
cd frontend
npm install  # Install dependencies on first run
npm run dev
```

- Access the frontend interface

Open your browser and visit `http://localhost:3000` or `http://localhost:3001` (check the port shown in terminal)

The frontend interface provides the following features:
- **Home**: System overview and quick navigation
- **Experiment Settings**: Configure experiment parameters and launch services
- **Data Monitoring**: Real-time system status and statistics
- **Experiment Management**: Save and load experiment snapshots
- **Relationship Graph**: Visualize the network of users, posts, and comments
- **Interview Feature**: Send questionnaires to simulated users and collect responses

<a id="ethics"></a>

## ⚖️ Ethics Statement

This work investigates mechanisms for online discourse depolarization in a simulated environment, utilizing publicly available datasets and synthetic agent interactions. It does not involve experiments with human subjects and does not collect or process personally identifying information. The primary goal of this research is to advance understanding of coordinated intervention mechanisms for platform governance, rather than to develop or deploy deceptive influence campaigns.

EvoCorps is framed as a governance-assistance approach for online platforms facing coordinated and malicious activities such as disinformation campaigns or adversarial manipulation. In such settings, platform governance actors may themselves require coordinated capabilities and stylistic diversity to respond effectively and proportionately. Our study therefore examines coordination and response diversity as governance mechanisms, not as tools for artificial consensus formation or manipulation.

We explicitly oppose the use of deceptive strategies in any real-world deployment. Although our simulations introduce diverse agent personas to explore theoretical boundaries of influence dynamics, any practical application must adhere strictly to principles of transparency and accountability. Automated agents should be clearly identified as AI-based assistants or governance tools, such as certified fact-checking bots, and must not impersonate human users or conceal their artificial nature.

Any deployment of systems inspired by this work should be integrated with existing platform governance processes and subject to platform-specific policies, transparency requirements, and continuous auditing. Such safeguards are necessary to mitigate unintended harms, including disparate impacts, erosion of user trust, or errors arising from automated judgments. The intended use of EvoCorps is to support responsible, transparent, and accountable governance interventions, rather than to mislead users or manufacture false consensus.

## 📄 Citation

If you use this project in your research, please cite our paper:

```bibtex
@misc{lin2026evocorpsevolutionarymultiagentframework,
      title={EvoCorps: An Evolutionary Multi-Agent Framework for Depolarizing Online Discourse}, 
      author={Ning Lin and Haolun Li and Mingshu Liu and Chengyun Ruan and Kaibo Huang and Yukun Wei and Zhongliang Yang and Linna Zhou},
      year={2026},
      eprint={2602.08529},
      archivePrefix={arXiv},
      primaryClass={cs.MA},
      url={https://arxiv.org/abs/2602.08529}, 
}
```
