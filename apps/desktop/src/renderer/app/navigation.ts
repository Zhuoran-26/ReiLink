export type WorkspaceId = "home" | "chat" | "memory" | "game" | "voice" | "overlay" | "settings" | "debug" | "presentation";

export const WORKSPACE_LABELS: Record<WorkspaceId, string> = {
  home: "首页",
  chat: "聊天",
  memory: "回忆",
  game: "旅程",
  voice: "声音",
  overlay: "悬浮层",
  settings: "设置",
  debug: "开发者工具",
  presentation: "未来展示"
};

export const WORKSPACE_SUBTITLES: Record<WorkspaceId, string> = {
  home: "回到和 Rei 一起留下旅程痕迹的地方",
  chat: "和 Rei 安静地说说话",
  memory: "整理确认过的回忆与最近旅程",
  game: "游戏里的脚步，会慢慢留在这里。",
  voice: "让声音慢下来，Rei 会在这里听。",
  overlay: "低打扰的游戏陪伴位置",
  settings: "体验偏好、模型与本地数据",
  debug: "安全的事件、运行状态与诊断信息",
  presentation: "未来的呈现方式与角色状态"
};
