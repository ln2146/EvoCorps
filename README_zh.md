<div align="center">

  # EvoCorps

    
  [简体中文](README_zh.md) | [English](README.md)

  ![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
  ![License](https://img.shields.io/badge/license-MIT-green)
</div>
---

**EvoCorps** 是一个面向在线舆论去极化的进化多智能体框架，将舆论治理建模为动态社会博弈，并协同完成监控、规划、证据生成与多身份扩散等任务，以实现过程内、闭环的主动干预。

本项目以论文中的方法为核心，采用 Analyst、Strategist、Leader、Amplifier 的角色分工，并结合检索增强的集体认知内核（证据知识库 + 行动-结果记忆），通过闭环进化式学习在环境与对手变化下持续调整策略。系统已在 MOSAIC 社交模拟平台上实现，并在多源新闻流的对抗注入与放大场景中验证了对情绪极化、观点极端化与论证理性度的改善效果。

<div align="center">
  <img src="assets/framework.png" width="100%" alt="EvoCorps Framework"/>
</div>

### ✨ 主要特性：
- **♟️ 具有角色协调的动态团队**: 以 Analyst、Strategist、Leader、Amplifier 的角色分工形成协同干预管线，建模为动态社会博弈中的多角色决策与执行。
- **🧠 检索增强集体认知核心 (Retrieval-Augmented Collective Cognition Core)**: 结合证据知识库与行动-结果记忆，实现事实支撑、长期记忆与策略复用。
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

---

## 📂 目录结构

```text
EvoCorps/
├── config/                         # 运行配置
├── configs/                        # 实验与系统配置
├── data/                           # 数据与样例
├── database/                       # SQLite 数据库
├── evidence_database/              # 证据库与检索配置
├── exported_content/               # 导出内容
├── logs/                           # 运行日志
├── models/                         # 模型与权重相关
├── personas/                       # 人设与角色设定
├── scripts/                        # 辅助脚本
├── src/                            # 核心代码
│   ├── agents/                     # Agent 实现
│   ├── config/                     # 配置模块
│   ├── database/                   # 数据库相关模块
│   ├── retriver/                   # 检索相关模块
│   ├── utils_package/              # 工具包
│   ├── main.py                     # 系统运行主程序
│   ├── start_database_service.py   # 启动数据库服务程序
│   ├── keys.py                     # 密钥配置文件
│   └── opinion_balance_launcher.py # 独立的舆论平衡系统启动程序
├── demo_opinion_balance.py         # 完整流程演示
├── rebuild_faiss_from_db.py        # 向量索引重建
├── requirements.txt                # 依赖列表
├── sentiment_analysis_timestep.py  # 情感分析脚本
└── safety_prompts.json             # 安全提示配置
```

## 🚀 快速开始

### 1. 环境配置

建议使用 Python 3.9+：

```bash
pip install -r requirements.txt
```

### 2. 配置 API

请按实际使用的服务填写 API Key 与 Base URL：

- `evidence_database/config.py`
- `src/keys.py`
- `src/multi_model_selector.py`
  - 确认可用模型列表与回退策略（与当前 API 兼容）

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
```
