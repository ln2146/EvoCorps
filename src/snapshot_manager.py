"""
时间步快照管理器

功能：
1. 在每个tick结束时保存数据库快照
2. 从任意tick恢复状态
3. 管理快照存储空间
"""

import os
import shutil
import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class SnapshotManager:
    """时间步快照管理器"""

    def __init__(self, project_root: str, simulation_db_path: str):
        """
        初始化快照管理器

        Args:
            project_root: 项目根目录
            simulation_db_path: 当前模拟数据库路径
        """
        self.project_root = project_root
        self.simulation_db_path = simulation_db_path

        # 快照存储目录
        self.snapshots_dir = os.path.join(project_root, "snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)

        # 元数据文件
        self.metadata_file = os.path.join(self.snapshots_dir, "metadata.json")

        # 当前会话ID
        self.session_id = None

    def create_session(self, parent_session_id: Optional[str] = None, parent_tick: Optional[int] = None) -> str:
        """
        创建新的快照会话

        Args:
            parent_session_id: 父快照会话ID（从哪个快照恢复的）
            parent_tick: 父快照的起始tick

        Returns:
            session_id: 会话ID
        """
        # 清理旧会话的快照
        self.cleanup_old_snapshots()

        # 创建新会话ID
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建会话目录
        session_dir = os.path.join(self.snapshots_dir, self.session_id)
        os.makedirs(session_dir, exist_ok=True)

        # 初始化元数据
        metadata = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "ticks": {},
            "parent_session_id": parent_session_id,
            "parent_tick": parent_tick
        }

        self._save_metadata(metadata)

        # 同时写入 session 目录的 metadata（list_saved_snapshots 读取的是这个文件）
        session_metadata_path = os.path.join(session_dir, "metadata.json")
        with open(session_metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        if parent_session_id:
            logger.info(f"📦 创建新快照会话: {self.session_id} (继承自 {parent_session_id} tick {parent_tick})")
        else:
            logger.info(f"📦 创建新快照会话: {self.session_id}")
        return self.session_id

    def save_tick_snapshot(self, tick: int, additional_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存指定tick的快照

        Args:
            tick: 时间步编号
            additional_info: 额外信息（如配置、状态等）

        Returns:
            是否保存成功
        """
        if not self.session_id:
            logger.error("❌ 快照会话未初始化，请先调用 create_session()")
            return False

        try:
            # 创建tick快照目录
            tick_dir = os.path.join(self.snapshots_dir, self.session_id, f"tick_{tick}")
            os.makedirs(tick_dir, exist_ok=True)

            # 复制数据库文件
            snapshot_db_path = os.path.join(tick_dir, "simulation.db")

            # 确保源文件存在
            if not os.path.exists(self.simulation_db_path):
                logger.error(f"❌ 源数据库不存在: {self.simulation_db_path}")
                return False

            # 执行 WAL checkpoint，确保所有数据写入主数据库文件
            try:
                import sqlite3
                conn = sqlite3.connect(self.simulation_db_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()
                logger.debug(f"✅ 已执行 WAL checkpoint")
            except Exception as checkpoint_err:
                logger.warning(f"WAL checkpoint 失败（继续复制）: {checkpoint_err}")

            # 复制数据库
            shutil.copy2(self.simulation_db_path, snapshot_db_path)

            # 保存额外信息
            if additional_info:
                info_file = os.path.join(tick_dir, "info.json")
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(additional_info, f, ensure_ascii=False, indent=2)

            # 更新全局元数据
            metadata = self._load_metadata()
            metadata["ticks"][str(tick)] = {
                "tick": tick,
                "timestamp": datetime.now().isoformat(),
                "db_path": snapshot_db_path,
                "info_file": info_file if additional_info else None
            }
            self._save_metadata(metadata)

            # 同时更新会话目录下的元数据（用于list_sessions读取）
            session_metadata_path = os.path.join(self.snapshots_dir, self.session_id, "metadata.json")
            session_metadata = self._load_session_metadata(self.session_id)
            session_metadata["ticks"][str(tick)] = {
                "tick": tick,
                "timestamp": datetime.now().isoformat(),
                "db_path": snapshot_db_path,
                "info_file": info_file if additional_info else None
            }
            with open(session_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(session_metadata, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 已保存 tick {tick} 的快照")
            return True

        except Exception as e:
            logger.error(f"❌ 保存 tick {tick} 快照失败: {e}")
            return False

    def restore_from_tick(self, tick: int, session_id: Optional[str] = None) -> Optional[str]:
        """
        从指定tick恢复数据库

        Args:
            tick: 要恢复到的tick
            session_id: 会话ID（如果不指定则使用当前会话）

        Returns:
            恢复的数据库路径，失败返回None
        """
        try:
            # 确定使用的会话
            target_session = session_id or self.session_id
            if not target_session:
                logger.error("❌ 未指定会话ID且当前没有活动会话")
                return None

            # 查找快照路径
            snapshot_db_path = os.path.join(
                self.snapshots_dir,
                target_session,
                f"tick_{tick}",
                "simulation.db"
            )

            if not os.path.exists(snapshot_db_path):
                logger.error(f"❌ 快照不存在: {snapshot_db_path}")
                return None

            # 关闭当前数据库连接（如果需要）
            # 注意：调用者需要确保没有打开的数据库连接

            # 备份当前数据库
            if os.path.exists(self.simulation_db_path):
                backup_path = f"{self.simulation_db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.simulation_db_path, backup_path)
                logger.info(f"📋 已备份当前数据库到: {backup_path}")

            # 恢复快照
            shutil.copy2(snapshot_db_path, self.simulation_db_path)

            logger.info(f"✅ 成功从 tick {tick} 恢复数据库")
            return self.simulation_db_path

        except Exception as e:
            logger.error(f"❌ 恢复 tick {tick} 失败: {e}")
            return None

    def list_available_ticks(self, session_id: Optional[str] = None) -> List[int]:
        """
        列出可用的tick

        Args:
            session_id: 会话ID（如果不指定则列出所有会话）

        Returns:
            可用的tick列表
        """
        try:
            if session_id:
                # 列出特定会话的tick
                session_dir = os.path.join(self.snapshots_dir, session_id)
                if not os.path.exists(session_dir):
                    return []

                ticks = []
                for item in os.listdir(session_dir):
                    if item.startswith("tick_"):
                        tick_num = int(item.split("_")[1])
                        ticks.append(tick_num)
                return sorted(ticks)
            else:
                # 列出所有会话的tick
                metadata = self._load_metadata()
                ticks = []
                for tick_str in metadata.get("ticks", {}).keys():
                    ticks.append(int(tick_str))
                return sorted(ticks)

        except Exception as e:
            logger.error(f"❌ 列出可用tick失败: {e}")
            return []

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有快照会话

        Returns:
            会话信息列表
        """
        try:
            sessions = []
            if not os.path.exists(self.snapshots_dir):
                return sessions

            for session_id in os.listdir(self.snapshots_dir):
                session_dir = os.path.join(self.snapshots_dir, session_id)
                if not os.path.isdir(session_dir):
                    continue

                # 读取会话元数据
                metadata_path = os.path.join(session_dir, "metadata.json")
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        session_metadata = json.load(f)
                        sessions.append(session_metadata)
                else:
                    # 如果没有元数据文件，创建基本信息
                    tick_count = len([d for d in os.listdir(session_dir) if d.startswith("tick_")])
                    sessions.append({
                        "session_id": session_id,
                        "created_at": "Unknown",
                        "tick_count": tick_count
                    })

            # 按创建时间排序
            sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return sessions

        except Exception as e:
            logger.error(f"❌ 列出会话失败: {e}")
            return []

    def cleanup_old_snapshots(self, keep_sessions: int = 5) -> None:
        """
        清理旧的快照会话，保留最近的几个

        Args:
            keep_sessions: 保留的会话数量
        """
        try:
            sessions = self.list_sessions()

            if len(sessions) <= keep_sessions:
                return

            # 删除旧的会话
            sessions_to_delete = sessions[keep_sessions:]
            for session in sessions_to_delete:
                session_id = session.get("session_id")
                session_dir = os.path.join(self.snapshots_dir, session_id)

                if os.path.exists(session_dir):
                    shutil.rmtree(session_dir)
                    logger.info(f"🗑️  已删除旧快照会话: {session_id}")

        except Exception as e:
            logger.error(f"❌ 清理旧快照失败: {e}")

    def cleanup_all_snapshots(self) -> None:
        """
        清理所有快照（在启动main.py时调用）
        """
        try:
            if os.path.exists(self.snapshots_dir):
                shutil.rmtree(self.snapshots_dir)
                os.makedirs(self.snapshots_dir, exist_ok=True)
                logger.info("🗑️  已清理所有快照数据")

        except Exception as e:
            logger.error(f"❌ 清理所有快照失败: {e}")

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典
        """
        try:
            metadata_file = os.path.join(self.snapshots_dir, session_id, "metadata.json")
            if not os.path.exists(metadata_file):
                return None

            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"❌ 获取会话信息失败: {e}")
            return None

    def save_named_snapshot(self, name: str, description: str = "") -> Dict[str, Any]:
        """
        将当前会话保存为命名快照

        Args:
            name: 快照名称
            description: 快照描述

        Returns:
            保存结果，包含 success, snapshot_id, message
        """
        try:
            # 如果没有当前会话，尝试找到最近的有 tick 数据的会话
            if not self.session_id:
                # 查找最近的有 tick 数据的会话
                latest_session = None
                latest_tick_count = 0
                latest_session_time = ""

                if os.path.exists(self.snapshots_dir):
                    for session_id in os.listdir(self.snapshots_dir):
                        session_dir = os.path.join(self.snapshots_dir, session_id)
                        if not os.path.isdir(session_dir):
                            continue

                        # 方法1：从 metadata.json 读取 tick 数量
                        metadata_path = os.path.join(session_dir, "metadata.json")
                        tick_count = 0
                        if os.path.exists(metadata_path):
                            try:
                                with open(metadata_path, 'r', encoding='utf-8') as f:
                                    metadata = json.load(f)
                                tick_count = len(metadata.get("ticks", {}))
                            except:
                                pass

                        # 方法2：如果没有 metadata.json，直接计算 tick 目录数量
                        if tick_count == 0:
                            for item in os.listdir(session_dir):
                                if item.startswith("tick_") and os.path.isdir(os.path.join(session_dir, item)):
                                    tick_count += 1

                        # 选择 tick 数量最多的会话，如果相同则选择最新的
                        if tick_count > 0:
                            session_time = session_id.split("_")[0] + session_id.split("_")[1] if "_" in session_id else "0"
                            if tick_count > latest_tick_count or (tick_count == latest_tick_count and session_time > latest_session_time):
                                latest_tick_count = tick_count
                                latest_session = session_id
                                latest_session_time = session_time

                if latest_session and latest_tick_count > 0:
                    self.session_id = latest_session
                    logger.info(f"📌 使用已有会话: {self.session_id} (包含 {latest_tick_count} 个 tick)")
                else:
                    # 如果没有找到有 tick 数据的会话，创建新会话
                    self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                    session_dir = os.path.join(self.snapshots_dir, self.session_id)
                    os.makedirs(session_dir, exist_ok=True)
                    logger.info(f"📌 创建新会话: {self.session_id}")

            session_dir = os.path.join(self.snapshots_dir, self.session_id)
            metadata_path = os.path.join(session_dir, "metadata.json")

            # 读取现有元数据或创建新的
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "session_id": self.session_id,
                    "created_at": datetime.now().isoformat(),
                    "ticks": {}
                }

            # 读取当前数据库统计信息
            db_stats = self._get_db_stats(self.simulation_db_path)

            # 更新元数据
            metadata["name"] = name
            metadata["description"] = description
            metadata["saved_at"] = datetime.now().isoformat()
            metadata["total_users"] = db_stats.get("total_users", 0)
            metadata["total_posts"] = db_stats.get("total_posts", 0)
            metadata["total_comments"] = db_stats.get("total_comments", 0)

            # 保存元数据
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # 同时更新全局元数据
            global_metadata = self._load_metadata()
            global_metadata["name"] = name
            global_metadata["description"] = description
            global_metadata["saved_at"] = datetime.now().isoformat()
            global_metadata["total_users"] = db_stats.get("total_users", 0)
            global_metadata["total_posts"] = db_stats.get("total_posts", 0)
            self._save_metadata(global_metadata)

            logger.info(f"✅ 已保存命名快照: {name} (ID: {self.session_id})")

            return {
                "success": True,
                "snapshot_id": self.session_id,
                "message": f"快照 '{name}' 保存成功"
            }

        except Exception as e:
            logger.error(f"❌ 保存命名快照失败: {e}")
            return {
                "success": False,
                "snapshot_id": None,
                "message": f"保存失败: {str(e)}"
            }

    def list_saved_snapshots(self) -> List[Dict[str, Any]]:
        """
        列出所有可用快照（含详细预览）

        包括：
        1. 已命名的快照（有 name 字段）
        2. 未命名但有 tick 数据的会话
        3. 继承关系：如果会话有父快照，合并显示父快照的 tick

        Returns:
            已保存快照列表，包含详细预览信息
        """
        try:
            # 先加载所有会话的元数据，用于处理继承关系
            all_metadata = {}
            if os.path.exists(self.snapshots_dir):
                for session_id in os.listdir(self.snapshots_dir):
                    session_dir = os.path.join(self.snapshots_dir, session_id)
                    if not os.path.isdir(session_dir):
                        continue
                    metadata_path = os.path.join(session_dir, "metadata.json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            all_metadata[session_id] = json.load(f)

            snapshots = []
            if not os.path.exists(self.snapshots_dir):
                return snapshots

            for session_id in os.listdir(self.snapshots_dir):
                session_dir = os.path.join(self.snapshots_dir, session_id)
                if not os.path.isdir(session_dir):
                    continue

                metadata = all_metadata.get(session_id, {})

                # 构建 ticks 列表（用于详细预览）
                ticks = []
                ticks_data = metadata.get("ticks", {})

                # 检查是否有父快照
                parent_session_id = metadata.get("parent_session_id")
                parent_tick = metadata.get("parent_tick")

                # 如果 metadata 中没有 ticks 数据，从目录结构读取
                if not ticks_data:
                    for item in os.listdir(session_dir):
                        if item.startswith("tick_") and os.path.isdir(os.path.join(session_dir, item)):
                            try:
                                tick_num = int(item.replace("tick_", ""))
                                tick_dir = os.path.join(session_dir, item)
                                info_path = os.path.join(tick_dir, "info.json")
                                tick_info = {"tick": tick_num, "timestamp": "", "user_count": 0, "post_count": 0, "inherited": False}
                                if os.path.exists(info_path):
                                    with open(info_path, 'r', encoding='utf-8') as f:
                                        info_data = json.load(f)
                                    tick_info["timestamp"] = info_data.get("timestamp", "")
                                    tick_info["user_count"] = info_data.get("user_count", 0)
                                    tick_info["post_count"] = info_data.get("post_count", 0)
                                    # 添加详细用户统计
                                    tick_info["normal_users"] = info_data.get("normal_users", 0)
                                    tick_info["malicious_users"] = info_data.get("malicious_users", 0)
                                    tick_info["leader_users"] = info_data.get("leader_users", 0)
                                    tick_info["amplifier_users"] = info_data.get("amplifier_users", 0)
                                ticks.append(tick_info)
                            except:
                                pass
                else:
                    for tick_str, tick_info in sorted(ticks_data.items(), key=lambda x: int(x[0])):
                        tick_num = int(tick_str)
                        user_count = tick_info.get("user_count", 0)
                        post_count = tick_info.get("post_count", 0)

                        # 如果 metadata 中没有 user_count/post_count，从 info.json 读取
                        if user_count == 0 or post_count == 0:
                            # 优先从 tick 目录直接读取 info.json
                            direct_info_path = os.path.join(session_dir, f"tick_{tick_num}", "info.json")
                            info_file = tick_info.get("info_file", "")
                            info_path = direct_info_path if os.path.exists(direct_info_path) else info_file
                            if info_path and os.path.exists(info_path):
                                try:
                                    with open(info_path, 'r', encoding='utf-8') as f:
                                        info_data = json.load(f)
                                    user_count = info_data.get("user_count", user_count)
                                    post_count = info_data.get("post_count", post_count)
                                except:
                                    pass

                        ticks.append({
                            "tick": tick_num,
                            "timestamp": tick_info.get("timestamp", ""),
                            "user_count": user_count,
                            "post_count": post_count,
                            "inherited": False
                        })

                # 如果有父快照，合并父快照的 ticks（tick 1 到 parent_tick）
                if parent_session_id and parent_tick:
                    parent_metadata = all_metadata.get(parent_session_id, {})
                    parent_ticks_data = parent_metadata.get("ticks", {})

                    current_tick_nums = {t["tick"] for t in ticks}
                    for tick_str, tick_info in sorted(parent_ticks_data.items(), key=lambda x: int(x[0])):
                        tick_num = int(tick_str)
                        if tick_num <= parent_tick and tick_num not in current_tick_nums:
                            user_count = tick_info.get("user_count", 0)
                            post_count = tick_info.get("post_count", 0)
                            if user_count == 0 or post_count == 0:
                                # 优先从父快照 tick 目录直接读取 info.json
                                parent_info_path = os.path.join(self.snapshots_dir, parent_session_id, f"tick_{tick_num}", "info.json")
                                info_file = tick_info.get("info_file", "")
                                info_path = parent_info_path if os.path.exists(parent_info_path) else info_file
                                if info_path and os.path.exists(info_path):
                                    try:
                                        with open(info_path, 'r', encoding='utf-8') as f:
                                            info_data = json.load(f)
                                        user_count = info_data.get("user_count", user_count)
                                        post_count = info_data.get("post_count", post_count)
                                    except:
                                        pass
                            ticks.append({
                                "tick": tick_num,
                                "timestamp": tick_info.get("timestamp", ""),
                                "user_count": user_count,
                                "post_count": post_count,
                                "inherited": True,
                                "source_session": parent_session_id
                            })

                ticks.sort(key=lambda x: x["tick"])

                # 跳过没有任何 tick 数据的会话
                if not ticks:
                    continue

                # 使用命名快照的名称，或者使用会话 ID 作为默认名称
                snapshot_name = metadata.get("name", "")
                if not snapshot_name:
                    # 未命名快照，使用时间戳作为显示名称
                    try:
                        date_part, time_part = session_id.split("_")
                        snapshot_name = f"未命名快照 ({date_part} {time_part[:2]}:{time_part[2:]})"
                    except:
                        snapshot_name = f"未命名快照 ({session_id})"

                # 如果 metadata 中没有 total_users/total_posts，从最后一个 tick 推算
                total_users = metadata.get("total_users", 0)
                total_posts = metadata.get("total_posts", 0)
                total_comments = metadata.get("total_comments", 0)
                if (total_users == 0 or total_posts == 0) and ticks:
                    last_tick = max(ticks, key=lambda t: t["tick"])
                    if total_users == 0:
                        total_users = last_tick.get("user_count", 0)
                    if total_posts == 0:
                        total_posts = last_tick.get("post_count", 0)

                snapshot_info = {
                    "id": session_id,
                    "name": snapshot_name,
                    "description": metadata.get("description", ""),
                    "created_at": metadata.get("created_at", ""),
                    "saved_at": metadata.get("saved_at", ""),
                    "tick_count": len(ticks),
                    "total_users": total_users,
                    "total_posts": total_posts,
                    "total_comments": total_comments,
                    "ticks": ticks,
                    "is_named": bool(metadata.get("name")),  # 标记是否为命名快照
                    "parent_session_id": parent_session_id,
                    "parent_tick": parent_tick
                }
                snapshots.append(snapshot_info)

            # 按保存时间排序（最新的在前）
            snapshots.sort(key=lambda x: x.get("saved_at", "") or x.get("created_at", ""), reverse=True)
            return snapshots

        except Exception as e:
            logger.error(f"❌ 列出已保存快照失败: {e}")
            return []

    def get_saved_snapshot_detail(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个已保存快照的详细信息

        Args:
            session_id: 会话ID

        Returns:
            快照详细信息，包含所有 tick
        """
        try:
            metadata = self.get_session_info(session_id)
            if not metadata:
                return None

            # 如果没有 name 字段，说明不是已保存的命名快照
            if not metadata.get("name"):
                return None

            # 构建 ticks 列表
            ticks = []
            ticks_data = metadata.get("ticks", {})
            for tick_str, tick_info in sorted(ticks_data.items(), key=lambda x: int(x[0])):
                ticks.append({
                    "tick": int(tick_str),
                    "timestamp": tick_info.get("timestamp", ""),
                    "user_count": tick_info.get("user_count", 0),
                    "post_count": tick_info.get("post_count", 0)
                })

            return {
                "id": session_id,
                "name": metadata.get("name", session_id),
                "description": metadata.get("description", ""),
                "created_at": metadata.get("created_at", ""),
                "saved_at": metadata.get("saved_at", ""),
                "tick_count": len(ticks),
                "total_users": metadata.get("total_users", 0),
                "total_posts": metadata.get("total_posts", 0),
                "total_comments": metadata.get("total_comments", 0),
                "ticks": ticks
            }

        except Exception as e:
            logger.error(f"❌ 获取快照详情失败: {e}")
            return None

    def _get_db_stats(self, db_path: str) -> Dict[str, int]:
        """
        从数据库读取统计信息

        Args:
            db_path: 数据库路径

        Returns:
            统计信息字典
        """
        try:
            if not os.path.exists(db_path):
                return {"total_users": 0, "total_posts": 0, "total_comments": 0}

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取用户数
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            # 获取帖子数
            cursor.execute("SELECT COUNT(*) FROM posts")
            total_posts = cursor.fetchone()[0]

            # 获取评论数
            cursor.execute("SELECT COUNT(*) FROM comments")
            total_comments = cursor.fetchone()[0]

            conn.close()

            return {
                "total_users": total_users,
                "total_posts": total_posts,
                "total_comments": total_comments
            }

        except Exception as e:
            logger.error(f"❌ 读取数据库统计失败: {e}")
            return {"total_users": 0, "total_posts": 0, "total_comments": 0}

    def _load_metadata(self) -> Dict[str, Any]:
        """加载元数据"""
        try:
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"❌ 加载元数据失败: {e}")

        # 返回默认元数据
        return {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "ticks": {}
        }

    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存元数据失败: {e}")

    def _load_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """加载会话级别的元数据"""
        try:
            session_metadata_path = os.path.join(self.snapshots_dir, session_id, "metadata.json")
            if os.path.exists(session_metadata_path):
                with open(session_metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"❌ 加载会话元数据失败: {e}")

        # 返回默认会话元数据
        return {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "ticks": {}
        }

    def delete_snapshot(self, session_id: str) -> Dict[str, Any]:
        """
        删除指定的快照会话

        Args:
            session_id: 要删除的会话ID

        Returns:
            删除结果，包含 success, message
        """
        try:
            session_dir = os.path.join(self.snapshots_dir, session_id)

            if not os.path.exists(session_dir):
                logger.error(f"❌ 快照不存在: {session_id}")
                return {
                    "success": False,
                    "message": f"快照不存在: {session_id}"
                }

            # 删除整个会话目录
            shutil.rmtree(session_dir)
            logger.info(f"🗑️ 已删除快照会话: {session_id}")

            # 更新全局元数据，移除该会话的记录
            metadata = self._load_metadata()
            if "ticks" in metadata:
                # 移除属于该会话的 tick 记录
                ticks_to_remove = [
                    tick_str for tick_str, tick_info in metadata.get("ticks", {}).items()
                    if tick_info.get("session_id") == session_id
                ]
                for tick_str in ticks_to_remove:
                    del metadata["ticks"][tick_str]

            # 如果删除的是当前会话，清除 session_id
            if self.session_id == session_id:
                self.session_id = None

            self._save_metadata(metadata)

            return {
                "success": True,
                "message": f"快照 '{session_id}' 已删除"
            }

        except Exception as e:
            logger.error(f"❌ 删除快照失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }

    def delete_all_snapshots(self) -> Dict[str, Any]:
        """
        删除所有快照

        Returns:
            删除结果，包含 success, message, deleted_count
        """
        try:
            sessions = self.list_sessions()
            deleted_count = 0

            for session in sessions:
                session_id = session.get("session_id")
                session_dir = os.path.join(self.snapshots_dir, session_id)

                if os.path.exists(session_dir):
                    shutil.rmtree(session_dir)
                    deleted_count += 1
                    logger.info(f"🗑️ 已删除快照会话: {session_id}")

            # 清空全局元数据
            metadata = {
                "session_id": None,
                "created_at": datetime.now().isoformat(),
                "ticks": {}
            }
            self._save_metadata(metadata)
            self.session_id = None

            return {
                "success": True,
                "message": f"已删除 {deleted_count} 个快照",
                "deleted_count": deleted_count
            }

        except Exception as e:
            logger.error(f"❌ 删除所有快照失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}",
                "deleted_count": 0
            }


def create_snapshot_manager(project_root: str, simulation_db_path: str) -> SnapshotManager:
    """
    创建快照管理器实例

    Args:
        project_root: 项目根目录
        simulation_db_path: 模拟数据库路径

    Returns:
        SnapshotManager实例
    """
    return SnapshotManager(project_root, simulation_db_path)
