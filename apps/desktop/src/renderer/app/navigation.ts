export type WorkspaceId = "home" | "memory" | "game" | "voice" | "overlay" | "settings" | "debug" | "presentation";

export const WORKSPACE_LABELS: Record<WorkspaceId, string> = {
  home: "聊天",
  memory: "回忆",
  game: "旅程",
  voice: "声音",
  overlay: "悬浮层",
  settings: "设置",
  debug: "开发者工具",
  presentation: "未来展示"
};

export const WORKSPACE_SUBTITLES: Record<WorkspaceId, string> = {
  home: "和 Rei 安静地说说话",
  memory: "整理确认过的回忆与最近旅程",
  game: "当前游戏、本局进度与旅程记录",
  voice: "语音输入、输出与对话方式",
  overlay: "低打扰的游戏陪伴位置",
  settings: "体验偏好、模型与本地数据",
  debug: "安全的事件、运行状态与诊断信息",
  presentation: "未来的呈现方式与角色状态"
};
