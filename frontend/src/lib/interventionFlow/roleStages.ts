import type { Role } from './logRouter'

export type RoleStageLabel = string

const ROLE_STAGES: Record<Role, readonly RoleStageLabel[]> = {
  Analyst: ['内容识别', '评论抽样', '极端度', '情绪度', '干预判定', '监测评估'],
  Strategist: ['确认告警', '检索历史', '生成方案', '选择策略', '输出指令'],
  Leader: ['解析指令', '检索论据', '生成候选', '投票选优', '发布评论'],
  Amplifier: ['启动集群', '生成回应', '点赞放大', '扩散完成'],
}

export function getRoleStages(role: Role): readonly RoleStageLabel[] {
  return ROLE_STAGES[role]
}

export function formatRoleStagesTooltip(role: Role) {
  return getRoleStages(role).join(' -> ')
}
