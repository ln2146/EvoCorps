# 时间控制与沙盘快照功能使用说明

## 功能概述

时间控制与沙盘快照系统允许您：
1. 在模拟过程中自动保存每个时间步（tick）的完整状态
2. 从任意时间步恢复并继续模拟
3. 对比不同策略下的模拟结果

## 工作流程

### 1. 运行主模拟并保存快照

```bash
python src/main.py
```

- 程序会自动清理所有旧快照数据
- 在模拟运行过程中，每个tick结束后会自动保存快照
- 快照保存在 `snapshots/` 目录下

**输出示例：**
```
🗑️  已清理所有旧快照数据
✅ 快照系统已启动，将在每个时间步结束后自动保存
✅ 已保存 tick 1 的快照
✅ 已保存 tick 2 的快照
...
```

### 2. 使用对比模式从快照恢复

```bash
python src/comparison.py
```

程序会显示所有可用的快照会话：

```
📦 可用的快照会话
============================================================

[1] 会话ID: 20240306_143022
    创建时间: 2024-03-06T14:30:22
    快照数量: 10 个tick
    可用tick: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
============================================================

请选择会话编号 (1-1, 或输入 'q' 退出):
```

选择会话和tick后：

```
会话 20240306_143022 中可用的tick:
可用tick: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

请选择要恢复的tick (或输入 'q' 退出): 5

✅ 已选择 tick 5
   时间戳: 2024-03-06T14:30:27
   用户数: 20
   帖子数: 45
```

恢复完成后，模拟会从该tick继续运行。

## 使用场景

### 场景1：策略对比

**目标：** 对比启用和禁用意见平衡系统的效果

1. **运行基准实验：**
   ```bash
   python src/main.py
   ```
   - 选择：禁用意见平衡系统
   - 运行10个tick

2. **从tick 5恢复并启用干预：**
   ```bash
   python src/comparison.py
   ```
   - 选择从tick 5恢复
   - 启用意见平衡系统
   - 继续运行5个tick

3. **对比结果：**
   - tick 1-5：无干预的基准数据
   - tick 6-10：有干预的对比数据

### 场景2：参数调优

**目标：** 测试不同的攻击协调模式

1. **运行初始模拟：**
   ```bash
   python src/main.py
   ```
   - 启用恶意水军
   - 选择默认攻击模式
   - 运行到tick 5

2. **恢复并改变策略：**
   ```bash
   python src/comparison.py
   ```
   - 从tick 5恢复
   - 通过API切换攻击模式：
     ```bash
     curl -X POST http://127.0.0.1:8001/control/attack-mode \
       -H "Content-Type: application/json" \
       -d '{"mode": "swarm"}'
     ```

### 场景3：平行宇宙实验

**目标：** 从同一个时间点创建不同的发展路径

1. **运行基础模拟：**
   ```bash
   python src/main.py
   ```
   - 运行10个tick，建立"基准宇宙"

2. **创建宇宙A（无干预）：**
   ```bash
   python src/comparison.py
   ```
   - 从tick 10恢复
   - 禁用所有干预系统
   - 运行10个tick

3. **创建宇宙B（强力干预）：**
   ```bash
   python src/comparison.py
   ```
   - 从tick 10恢复
   - 启用所有干预系统
   - 运行10个tick

## 文件结构

```
EVOCROPS/new_Evocorps/
├── snapshots/                          # 快照存储目录
│   ├── 20240306_143022/               # 会话目录（时间戳）
│   │   ├── metadata.json              # 会话元数据
│   │   ├── tick_1/                    # tick 1快照
│   │   │   ├── simulation.db          # 数据库快照
│   │   │   └── info.json              # 附加信息
│   │   ├── tick_2/
│   │   └── ...
│   └── 20240306_151530/               # 另一个会话
├── src/
│   ├── snapshot_manager.py            # 快照管理模块
│   ├── simulation.py                  # 模拟引擎（已修改）
│   ├── main.py                        # 主程序（已修改）
│   └── comparison.py                  # 对比模式（新增）
└── database/
    └── simulation.db                  # 当前使用的数据库
```

## API控制

即使在使用comparison.py时，您仍可以通过API实时控制系统：

```bash
# 切换恶意攻击
curl -X POST http://127.0.0.1:8001/control/attack \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 切换事实核查
curl -X POST http://127.0.0.1:8001/control/aftercare \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 查看当前状态
curl http://127.0.0.1:8001/control/status
```

## 注意事项

1. **快照大小：** 每个快照包含完整的数据库副本，会占用磁盘空间
   - 默认保留最近5个会话
   - 可在 `snapshot_manager.py` 中调整 `keep_sessions` 参数

2. **恢复时机：** 恢复快照会覆盖当前的 `database/simulation.db`
   - 恢复前会自动备份当前数据库
   - 备份文件命名：`simulation.db.backup_YYYYMMDD_HHMMSS`

3. **并发限制：** 确保在恢复快照时没有其他进程正在使用数据库

4. **时间步连续性：** 从tick N恢复后，新的tick会从N+1开始编号

## 故障排除

### 问题：没有找到快照
**解决方案：** 确保先运行 `main.py` 生成快照数据

### 问题：恢复失败
**解决方案：**
1. 确保数据库服务正在运行
2. 检查磁盘空间是否充足
3. 查看日志文件了解详细错误信息

### 问题：comparison.py找不到快照
**解决方案：**
- 检查 `snapshots/` 目录是否存在
- 确认会话ID和tick编号正确

## 技术细节

### 快照内容
每个tick快照包含：
- 完整的SQLite数据库（用户、帖子、互动等）
- 时间戳信息
- 用户数量
- 帖子数量
- 其他状态信息

### 恢复过程
1. 关闭现有数据库连接
2. 备份当前数据库
3. 复制快照数据库到 `database/simulation.db`
4. 重新初始化模拟系统
5. 从指定tick继续运行

### 性能影响
- 保存快照：每个tick约需0.1-0.5秒（取决于数据库大小）
- 恢复快照：通常在1秒内完成
- 磁盘空间：每个快照约1-10MB（取决于数据量）
