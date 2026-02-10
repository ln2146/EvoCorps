<div align="center">

  <div align="center">
    <img src="assets/logoheng.svg" width="100%" alt="EvoCorps logo"/>
  </div>

  **面向网络舆论去极化的进化式多智能体框架**

[简体中文](README.md) | [English](README_EN.md)

  [![Paper](https://img.shields.io/badge/Paper-arXiv-red)](https://arxiv.org/abs/2602.08529)
  ![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)

</div>

<a id="overview"></a>
## ⚡ 项目概述

**EvoCorps** 是一个面向**网络舆论去极化**的**进化式多智能体框架**。它并非传统的舆情检测或事后治理工具，而是在模拟环境中将舆论干预建模为一个**持续演化的社会博弈过程**：系统在传播过程中进行过程内调节，**降低情绪对立、抑制极端观点扩散，并提升整体讨论的理性程度**。

在 EvoCorps 中，**不同智能体分工协作**，模拟现实中的多角色舆论参与者，协同完成**舆论监测、局势建模、干预规划、基于事实的内容生成与多角色传播**等任务。框架内置**检索增强的集体认知机制（论据知识库 + 行动—结果记忆）**，并通过**基于反馈的进化式学习**，使系统能够随环境变化自适应优化干预策略。

<a id="problem"></a>
## 🧩 我们试图解决的问题

在线社交平台的讨论，往往会在“同质性互动 + 推荐机制”的共同作用下逐步分化；当有组织的恶意账号在早期注入并放大情绪化叙事时，这种分化会被进一步加速。

<div align="center">
  <img src="assets/background.svg" width="80%" alt="Motivation: from normal communication to polarization under malicious attack, where passive detection and post-hoc intervention are often belated and weak"/>
</div>

该图概括了我们关注的动机：从正常交流出发，在恶意攻击介入后，群体讨论可能演化为难以调和的对立。由于情绪传播往往快于事实澄清，等到仅依赖被动检测、事后标记、删除时，讨论轨迹常已经固定，干预效果有限。

现有网络舆论相关技术普遍存在以下局限：

1. 以事后检测为主，响应滞后，难以影响传播过程
2. 策略静态，难以应对有组织、持续演化的恶意行为
3. 缺乏闭环反馈，无法评估干预是否真正改变舆论走向

EvoCorps 的目标，是让舆论干预从“发现问题再处理”转向“在传播过程中持续调节”。

<a id="how-it-works"></a>
## 🛠️ EvoCorps 如何工作

舆论监测 → 局势建模 → 干预策略规划 → 基于事实的内容生成 → 多角色传播 → 效果反馈与策略进化

本项目采用 **Analyst、Strategist、Leader、Amplifier** 的角色分工，将“规划—生成—传播—反馈”串联为协同干预流程，并在检索增强的集体认知内核支持下复用论据与历史经验。

<div align="center">
  <img src="assets/framework.svg" width="100%" alt="EvoCorps Framework"/>
</div>

### ✨ 主要特性：
- **♟️ 角色分工明确的协同干预团队**：由 Analyst、Strategist、Leader、Amplifier 分工协作，把“监测与判断 → 制定策略 → 生成内容 → 多角色扩散 → 效果评估”串成一条可执行的闭环流程，让干预能够在传播过程中持续推进与调整。
- **🧠 检索增强的事实与经验支撑**：系统维护证据知识库，并记录每次行动带来的结果；生成内容时优先检索可核查的事实与论据，同时参考历史上更有效的做法，提升内容可靠性与团队一致性。
- **🧬 基于反馈的自适应演化**：每轮结束后评估干预是否让讨论更理性、情绪更稳定、观点更温和，并据此强化有效策略、弱化无效策略，使系统在对抗注入和环境变化下逐步学会更合适的应对方式。


<a id="evaluation"></a>
## 📊 实验验证

我们在 **MOSAIC** 社交模拟平台上对 EvoCorps 进行了系统评估，并在包含**负面新闻传播**与**恶意信息放大**的场景中进行测试。结果表明，在**情绪极化程度**、**观点极端化水平**与**论证理性**等关键指标上，EvoCorps 均优于事后干预方法。

### 系统干预效果（示意图）

<div align="center">
  <img src="assets/Sentiment_trajectories.png" width="100%" alt="Sentiment_trajectories"/>
</div>

上述图表对比了四种设置下的情绪随时间变化情况：Case 1（仅普通用户自然讨论，无恶意水军也无干预）、Case 2（恶意水军放大偏置信息，无防护）、Case 3（在Case 2基础上采用事后审核）、Case 4（在Case 2基础上由EvoCorps进行实时的、角色协同的主动干预）。虚线表示平台开始注入事实澄清的时间点（第5个时间步）；在对抗放大场景中，缺乏保护或仅事后干预的情绪更难恢复，而 EvoCorps能更早拉住下滑趋势，使讨论更快趋于稳定。

---

<a id="interface-preview"></a>
## 📷 界面预览

<div align="center">
<table align="center">
<tr>
<td align="center" width="50%"><strong>🏠 平台首页</strong><br><img src="assets/homepage.gif" width="100%" alt="平台首页"><br>静态与动态模式选择</td>
<td align="center" width="50%"><strong>📈 数据监控</strong><br><img src="assets/datadetect.gif" width="100%" alt="数据监控"><br>查看用户和帖子的详细信息</td>
</tr>
<tr>
<td align="center" width="50%"><strong>🕸️ 关系图谱</strong><br><img src="assets/graph.gif" width="100%" alt="关系图谱"><br>可视化用户、帖子、评论之间的关系网络</td>
<td align="center" width="50%"><strong>💬 采访功能</strong><br><img src="assets/talking.gif" width="100%" alt="采访功能"><br>向模拟用户发送问卷问题并收集回答</td>
</tr>
</table>
</div>

---

## 📖 目录
- [📂 项目结构](#project-structure)
- [🚀 快速开始](#-快速开始)
  - [1. 创建环境](#1-创建环境)
  - [2. 安装依赖包](#2-安装依赖包)
  - [3. 配置 API 与选择模型](#3-配置-api-与选择模型)
  - [4. 系统运行步骤](#4-系统运行步骤)
  - [5. 启动前端可视化界面](#5-启动前端可视化界面)
- [⚖️ 伦理声明](#ethics)
- [📄 引用](#-引用)

---

<a id="project-structure"></a>
## 📂 项目结构

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

### 1. 创建环境

使用 Conda：

```bash
# 创建 conda 环境
conda create -n EvoCorps python=3.12
conda activate EvoCorps
```

### 2. 安装依赖包

基础依赖安装：

```bash
pip install -r requirements.txt
```

### 3. 配置 API 与选择模型
在 `src/keys.py`文件中根据提示填写对应的 API-KEY 与 BASE-URL。并在`src/multi_model_selector.py`中配置相应的模型。
（示例：在`src/keys.py`配置deepseek的API-KEY 与 BASE-URL，那么在`src/multi_model_selector.py`中模型可选择DEFAULT_POOL = ["deepseek-chat"]；在`src/keys.py`配置gemini的API-KEY 与 BASE-URL，那么在`src/multi_model_selector.py`中模型可选择DEFAULT_POOL = ["gemini-2.0-flash"]；embedding模型可选择OpenAI的text-embedding-3-large、智谱的embedding-3等）

### 4. 系统运行步骤
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
python src/opinion_balance_launcher.py
# 输入start，启动监控
start
# 输入auto-status，实时打印行动的日志
auto-status
```

### 5. 启动前端可视化界面

- 启动后端API服务
```bash
# 新建终端
python frontend_api.py
```

- 启动前端开发服务器
```bash
# 新建终端，进入frontend目录
cd frontend
npm install  # 首次运行需要安装依赖
npm run dev
```

- 访问前端界面

打开浏览器访问 `http://localhost:3000` 或 `http://localhost:3001`（根据终端提示的端口）

前端界面提供以下功能：
- **主页**：系统概览和快速导航
- **实验设置**：配置实验参数和启动服务
- **数据监控**：实时查看系统运行状态和统计数据
- **实验管理**：保存和加载实验快照
- **关系图谱**：可视化用户、帖子、评论之间的关系网络
- **采访功能**：向模拟用户发送问卷并收集回答

<a id="ethics"></a>

## ⚖️ 伦理声明

本研究在模拟环境中探讨在线讨论去极化的机制，使用的是公开可获取的数据集以及合成智能体之间的交互过程。研究过程中不涉及任何人类受试者实验，也不收集或处理任何可识别个人身份的信息。本研究的主要目标在于加深对平台治理中协调式干预机制的理解，而非开发或部署具有欺骗性的影响行动。

EvoCorps 被定位为一种治理辅助方法，旨在帮助在线平台应对诸如虚假信息传播或对抗性操纵等有组织、恶意的行为。在此类情境下，平台治理主体本身可能需要具备协同能力和风格多样性，以实现有效且适度的响应。因此，本研究将协调能力与响应多样性视为治理机制进行考察，而非将其作为制造人为共识或操纵舆论的工具。

我们明确反对在任何现实世界部署中使用欺骗性策略。尽管本研究的模拟引入了多样化的智能体角色，用以探索影响力动态的理论边界，但任何实际应用都必须严格遵循透明性与问责原则。自动化智能体应被清晰标识为基于人工智能的助手或治理工具（例如经认证的事实核查机器人），不得冒充人类用户，也不得隐瞒其人工属性。

任何受本研究启发的系统部署，都应当与现有的平台治理流程相结合，并遵循平台特定的政策、透明性要求以及持续审计机制。这些保障措施对于降低潜在的非预期危害至关重要，包括差异化影响、用户信任受损，或由自动化判断引发的错误。本研究中 EvoCorps 的预期用途在于支持负责任、透明且可问责的治理干预，而非误导用户或制造虚假共识。

## 📄 引用

如果您在研究中使用了本项目，请引用我们的论文：

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
