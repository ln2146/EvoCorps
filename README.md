<div align="center">

  # EvoCorps
  **面向网络舆论去极化的进化式多智能体框架**

    
  [简体中文](README_zh.md) | [English](README.md)

  ![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)
</div>


**EvoCorps** 是一个面向在线舆论去极化的进化多智能体框架，将舆论治理建模为动态社会博弈，并协同完成监控、规划、证据生成与多身份扩散等任务，以实现过程内、闭环的主动干预。

本项目以论文中的方法为核心，采用 Analyst、Strategist、Leader、Amplifier 的角色分工，并结合检索增强的集体认知内核（证据知识库 + 行动-结果记忆），通过闭环进化式学习在环境与对手变化下持续调整策略。系统已在 MOSAIC 社交模拟平台上实现，并在多源新闻流的对抗注入与放大场景中验证了对情绪极化、观点极端化与论证理性度的改善效果。

<div align="center">
  <img src="assets/framework.png" width="100%" alt="EvoCorps Framework"/>
</div>

### ✨ 主要特性：
- **♟️ 具有角色协调的动态团队**: 以 Analyst、Strategist、Leader、Amplifier 的角色分工形成协同干预管线，建模为动态社会博弈中的多角色决策与执行。
- **🧠 检索增强集体认知核心**: 结合证据知识库与行动-结果记忆，实现事实支撑、长期记忆与策略复用。
- **🧬 闭环自适应进化学习系统**: 基于反馈评估持续更新知识与策略，在对抗注入与环境变化下自适应演化。


### 系统干预效果

<div align="center">
  <img src="assets/Sentiment_trajectories.png" width="100%" alt="Sentiment_trajectories"/>
</div>

上述图表展示了在情况 1/2/3/4 下随着时间推移的情绪变化轨迹。虚线标记了在时间点 t = 5 时的情绪趋于稳定。情况 2 继续下降，情况 3 有所缓解，而情况 4 的下降速度较慢，并且相对于情况 2/3 来说趋于稳定。

---

## 📖 目录
- [📂 目录结构](#-目录结构)
- [🚀 快速开始](#-快速开始)
  - [1. 环境配置](#1-环境配置)
  - [2. 配置 API](#2-配置-api)
  - [3. 系统运行步骤](#3-系统运行步骤)
- [⚖️ 伦理声明](#️-伦理声明)

---

## 📂 目录结构

```text
EvoCorps/
├── agent_memory_exports/           # 导出的智能体记忆分析
├── cognitive_memory/               # 认知记忆轨迹
├── config/                         # 运行配置
├── configs/                        # 实验与系统配置
├── data/                           # 数据与样例
├── database/                       # SQLite 数据库
├── evidence_database/              # 证据数据库与检索配置
├── exported_content/               # 导出内容与图表
├── human_study/                    # 人类研究数据与分析
├── models/                         # 模型与权重
├── personas/                       # 人设与角色
├── result/                         # 结果输出
├── scripts/                        # 辅助脚本
├── src/                            # 核心代码
│   ├── agents/                     # Agent 实现
│   ├── config/                     # 配置模块
│   ├── database/                   # 数据库相关模块
│   ├── retriver/                   # 检索相关模块
│   ├── utils_package/              # 工具包
│   ├── main.py                     # 系统主入口
│   ├── start_database_service.py   # 启动数据库服务
│   ├── keys.py                     # API 密钥配置
│   ├── opinion_balance_launcher.py # 独立启动舆论平衡系统
├── requirements.txt                # 依赖列表
├── LICENSE
└── README.md
```

## 🚀 快速开始

### 1. 环境配置

建议使用 Python 3.9+：

```bash
pip install -r requirements.txt
```

### 2. 配置 API
在src\文件夹下新建keys.py文件，复制以下内容，并按实际使用的服务填写 API Key 与 Base URL：
```python
OPENAI_API_KEY = "YOUR_API_KEY"
OPENAI_BASE_URL = "BASE_URL"
```

### 3. 系统运行步骤
- 开启数据库服务
```bash
# 新建终端
python src/start_database_service.py
```

- 启动主程序，按照终端提示信息选择运行场景
```bash
# 新建终端
python src/main.py
```

- 如果需要使用舆论平衡系统,可按照提示执行以下操作
```bash
# 新建终端
python src\opinion_balance_launcher.py
# 输入start，启动监控
start
# 输入auto-status，实时打印行动的日志
auto-status
```

## ⚖️ 伦理声明

本研究在模拟环境中探讨在线讨论去极化的机制，使用的是公开可获取的数据集以及合成智能体之间的交互过程。研究过程中不涉及任何人类受试者实验，也不收集或处理任何可识别个人身份的信息。本研究的主要目标在于加深对平台治理中协调式干预机制的理解，而非开发或部署具有欺骗性的影响行动。

EvoCorps 被定位为一种治理辅助方法，旨在帮助在线平台应对诸如虚假信息传播或对抗性操纵等有组织、恶意的行为。在此类情境下，平台治理主体本身可能需要具备协同能力和风格多样性，以实现有效且适度的响应。因此，本研究将协调能力与响应多样性视为治理机制进行考察，而非将其作为制造人为共识或操纵舆论的工具。

我们明确反对在任何现实世界部署中使用欺骗性策略。尽管本研究的模拟引入了多样化的智能体角色，用以探索影响力动态的理论边界，但任何实际应用都必须严格遵循透明性与问责原则。自动化智能体应被清晰标识为基于人工智能的助手或治理工具（例如经认证的事实核查机器人），不得冒充人类用户，也不得隐瞒其人工属性。

任何受本研究启发的系统部署，都应当与现有的平台治理流程相结合，并遵循平台特定的政策、透明性要求以及持续审计机制。这些保障措施对于降低潜在的非预期危害至关重要，包括差异化影响、用户信任受损，或由自动化判断引发的错误。本研究中 EvoCorps 的预期用途在于支持负责任、透明且可问责的治理干预，而非误导用户或制造虚假共识。

