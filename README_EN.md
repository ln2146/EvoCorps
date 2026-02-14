<div align="center">

  <div align="center">
    <img src="assets/logoheng.svg" width="100%" alt="EvoCorps logo"/>
  </div>

  **An Evolutionary Multi-Agent Framework for Depolarizing Online Discourse**

[简体中文](README.md) | [English](README_EN.md)

  [![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/abs/2602.08529)
  [![Hugging Face Datasets](https://img.shields.io/badge/Datasets-5%20Released-yellow)](https://huggingface.co/loge2146)
  ![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)
  ![Multi-Agent](https://img.shields.io/badge/agents-multi--agent-8a2be2)

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
<tr>
<td align="center" width="50%"><strong>▶️ Run System</strong><br><img src="assets/start.gif" width="100%" alt="Run System"><br>Run system, launch malicious attacks, post-hoc intervention, opinion balance</td>
<td align="center" width="50%"><strong>🔍 Real-time Analysis</strong><br><img src="assets/move.gif" width="100%" alt="Real-time Analysis"><br>Real-time view of post popularity, metric changes, trends, intervention flow, comment analysis</td>
</tr>
</table>
</div>

---

## 📖 Table of Contents
- [📂 Project Structure](#project-structure)
- [🚀 Quick Start](#-quick-start)
  - [1. Create Environment](#1-create-environment)
  - [2. Install Dependencies](#2-install-dependencies)
  - [3. Configure API & Select Models](#3-configure-api--select-models)
  - [4. Start Backend API](#4-start-backend-api)
  - [5. Launch Frontend Visualization Interface](#5-launch-frontend-visualization-interface)
- [📦 Datasets](#-datasets)
- [📄 Citation](#-citation)
- [⚖️ Ethics Statement](#ethics)
- [📮 Contact](#contact)

---

<a id="project-structure"></a>
## 📂 Project Structure

```text
EvoCorps/
├── assets/                         # Project assets (images, icons, etc.)
├── cognitive_memory/               # Cognitive memory traces (complete cycle records)
├── configs/                        # Experiment and system configurations
├── data/                           # News data
├── database/                       # SQLite database
├── evidence_database/              # Evidence database and retrieval configuration
├── experiments/                    # Experiment output directory
├── frontend/                       # Frontend visualization interface
├── personas/                       # Persona and role database
├── src/                            # Core code
│   ├── agents/                     # Agent implementations
│   ├── config/                     # Configuration module
│   ├── database/                   # Database-related modules
│   ├── main.py                     # System main entry
│   ├── simulation.py               # Simulation core logic
│   ├── database_service.py         # Database service
│   ├── start_database_service.py   # Start database service
│   ├── keys.py                     # API key configuration
│   ├── multi_model_selector.py     # Multi-model selector
│   ├── opinion_balance_launcher.py # Opinion balance system launcher
│   ├── opinion_balance_manager.py  # Opinion balance manager
│   ├── malicious_bot_manager.py    # Malicious bot manager
│   ├── agent_user.py               # Agent user
│   ├── post.py                     # Post module
│   ├── comment.py                  # Comment module
│   └── ...                         # Other core modules
├── frontend_api.py                 # Frontend API service
├── requirements.txt                # Python dependencies
├── safety_prompts.json             # Safety prompt configuration
├── LICENSE                         # MIT License
├── README.md                       # Chinese README
└── README_EN.md                    # English README
```

## 🚀 Quick Start

### 1. Create Environment

Using Conda:

```bash
# Create a conda environment
conda create -n EvoCorps python=3.12
conda activate EvoCorps
```

### 2. Install Dependencies

Base dependency installation:

```bash
pip install -r requirements.txt
```

### 3. Configure API & Select Models

Fill in the corresponding API-KEY and BASE-URL in `src/keys.py`, and configure the models in `src/multi_model_selector.py`.
(Example: if you configure DeepSeek API-KEY and BASE-URL in `src/keys.py`, you can set `DEFAULT_POOL = ["deepseek-chat"]` in `src/multi_model_selector.py`; if you configure Gemini API-KEY and BASE-URL, you can set `DEFAULT_POOL = ["gemini-2.0-flash"]`; for embeddings you can use OpenAI `text-embedding-3-large`, Zhipu `embedding-3`, etc.)

### 4. Start Backend API

- Start the backend API service
```bash
# New terminal
python frontend_api.py
```

### 5. Launch Frontend Visualization Interface

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


## 📦 Datasets

To ensure reproducibility and transparency, all datasets used in this project and described in the paper have been publicly released on the Hugging Face Hub.

| Dataset | Type | Primary Usage | Link |
|----------|------|---------------|------|
| evocorps-misinformation-news | News Corpus | Malicious amplification scenario construction | https://huggingface.co/datasets/loge2146/evocorps-misinformation-news |
| evocorps-neutral-news | News Corpus | Baseline simulation environment | https://huggingface.co/datasets/loge2146/evocorps-neutral-news |
| evocorps-positive-personas | Persona Data | Positive agent modeling | https://huggingface.co/datasets/loge2146/evocorps-positive-personas |
| evocorps-neutral-personas | Persona Data | Neutral agent modeling | https://huggingface.co/datasets/loge2146/evocorps-neutral-personas |
| evocorps-negative-personas | Persona Data | Negative agent modeling | https://huggingface.co/datasets/loge2146/evocorps-negative-personas |

We welcome researchers and developers to use these datasets. Please cite our paper if used.


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


<a id="ethics"></a>

## ⚖️ Ethics Statement

This work investigates mechanisms for online discourse depolarization in a simulated environment, utilizing publicly available datasets and synthetic agent interactions. It **does not involve experiments with human subjects** and **does not collect or process personally identifying information**. The primary goal of this research is to advance understanding of coordinated intervention mechanisms for platform governance, **rather than to develop or deploy deceptive influence campaigns**.

EvoCorps is framed as a governance-assistance approach for online platforms facing coordinated and malicious activities such as disinformation campaigns or adversarial manipulation. In such settings, platform governance actors may themselves require coordinated capabilities and stylistic diversity to respond effectively and proportionately. Our study therefore examines coordination and response diversity as governance mechanisms, not as tools for artificial consensus formation or manipulation.

**We explicitly oppose the use of deceptive strategies in any real-world deployment.** Although our simulations introduce diverse agent personas to explore theoretical boundaries of influence dynamics, any practical application must adhere strictly to principles of **transparency and accountability**. **Automated agents should be clearly identified as AI-based assistants or governance tools, such as certified fact-checking bots, and must not impersonate human users or conceal their artificial nature.**

Any deployment of systems inspired by this work should be integrated with existing platform governance processes and subject to platform-specific policies, transparency requirements, and continuous auditing. **Such safeguards are necessary to mitigate unintended harms**, including disparate impacts, erosion of user trust, or errors arising from automated judgments. The intended use of EvoCorps is to support responsible, transparent, and accountable governance interventions, rather than to mislead users or manufacture false consensus.

<a id="contact"></a>
## 📮 Contact

- Email: 2146289682@qq.com
