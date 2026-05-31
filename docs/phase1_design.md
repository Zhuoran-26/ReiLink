# ReiLink Phase 1 Design

## 中文

### 说明

这是早期 Phase 1 设计记录，保留用于说明 ReiLink 从单游戏 MVP 演进到当前多游戏 MVP 的路径。当前真实状态请优先参考：

- `docs/PROJECT_STATUS.md`
- `docs/ARCHITECTURE.md`
- `README.md`

### 早期目标

Phase 1 的目标是先跑通一个本地桌面 AI companion MVP：

- 检测 `eldenring.exe`。
- 在非 Windows 平台返回安全 idle 状态。
- 加载 Rei-like 原创 persona。
- 从本地 Elden Ring 样例知识中检索事实片段。
- 通过可替换 LLM provider 生成回复。
- 将会话保存到本地 JSONL。
- 提供 React desktop UI。

### 当前演进

这些早期目标已经扩展为：

- Multi-game Knowledge Catalog。
- Knowledge Pack Manifest。
- Elden Ring 与 Hollow Knight sample packs。
- Local Game Detector。
- Manual Game Context Control。
- Pending Memory confirmation。
- Prompt Preview 与 Debug Dashboard。

仍然保持不变的原则：

- 不使用官方角色名、台词、声音或视觉资产。
- 保持 LLM-first。
- Knowledge 只提供 factual context，不直接生成 Rei 回复。

## English

### Note

This is an early Phase 1 design note kept to show how ReiLink evolved from a single-game MVP into the current multi-game MVP. For the current source of truth, prefer:

- `docs/PROJECT_STATUS.md`
- `docs/ARCHITECTURE.md`
- `README.md`

### Early Goal

Phase 1 aimed to prove a runnable local desktop AI companion MVP:

- Detect `eldenring.exe`.
- Return a safe idle state on non-Windows platforms.
- Load an original Rei-like persona.
- Retrieve factual snippets from local Elden Ring sample knowledge.
- Generate replies through a replaceable LLM provider.
- Save conversations to local JSONL.
- Provide a React desktop UI.

### Current Evolution

Those early goals have since expanded into:

- Multi-game Knowledge Catalog.
- Knowledge Pack Manifest.
- Elden Ring and Hollow Knight sample packs.
- Local Game Detector.
- Manual Game Context Control.
- Pending Memory confirmation.
- Prompt Preview and Debug Dashboard.

Principles that remain unchanged:

- Do not use official character names, protected lines, voices, or visual assets.
- Keep generation LLM-first.
- Knowledge provides factual context only and does not directly generate Rei replies.
