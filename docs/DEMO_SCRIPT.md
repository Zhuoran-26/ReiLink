# ReiLink Demo Script

## 中文

### Demo 1: 基础陪伴聊天

目标：展示 minimal persona（克制人格）如何用中文短句回应，而不是像客服、心理咨询师或通用 AI。

用户输入：

- 你好
- 我今天有点烦
- 你是不是在关心我

观察点：

- 回复应安静、短、中文自然。
- 不应出现“作为 AI”“我会尽力理解你”等模板句。
- 不应把情绪问题扩写成心理咨询。
- 可以表达轻微关心，但保持距离。

### Demo 2: Game Session State

目标：展示 game session state（游戏会话状态）如何跟踪当前 Boss、死亡次数和通关状态。

用户输入：

- 我现在卡在女武神
- 又死了
- 还是没过
- 终于过了

观察点：

- `current_boss`（当前 Boss）应识别为女武神。
- `death_count`（死亡次数）应随反复失败增加。
- “还是没过”不应被误判为已通关。
- “终于过了”应更新 `last_cleared_boss`（最近通过 Boss）。
- Game Session Debug 中能看到状态变化。

### Demo 3: Pending Memory

目标：展示 pending memory（待确认记忆）如何避免未经确认就写入长期记忆。

用户输入：

- 我不喜欢长篇攻略
- 我不想召骨灰，感觉像作弊

观察点：

- 应生成待确认记忆，而不是直接进入长期记忆。
- 用户可以选择 Accept / Ignore。
- Accept 后，记忆会进入 prompt summary（提示摘要）。
- Pending memory 不应直接注入 prompt。

### Demo 4: Multi-game Knowledge

目标：展示 multi-game knowledge catalog（多游戏知识目录）能在不同游戏知识包之间切换。

用户输入：

- 我在玩艾尔登法环，Margit 怎么打
- 我在玩空洞骑士，螳螂领主怎么打

观察点：

- `game_id`（游戏 ID）应从 `elden_ring` 切换到 `hollow_knight`。
- Knowledge Debug 应显示不同 `knowledge_path`（知识文件路径）。
- `snippet_titles`（命中的知识标题）应来自对应游戏。
- 空洞骑士问题不应使用 Elden Ring snippets。

### Demo 5: Manual Game Context

目标：展示 manual game context override（手动当前游戏覆盖）如何处理自动检测失败或误判。

展示步骤：

- 在 Settings 中手动选择艾尔登法环。
- 查看 Game Context 中 `active_source`（当前来源）显示为手动选择。
- 清除手动选择。
- 通过用户消息切换到空洞骑士。
- 选择或提到未支持游戏，观察 fallback。

观察点：

- manual override 优先级最高。
- 自动检测结果仍可展示，但不能覆盖手动选择。
- 未支持游戏应显示“暂未支持知识库 / 仅使用模型回答”。
- 不应误用 Elden Ring 知识。

### Demo 6: Proactive Companion

目标：展示 proactive companion（主动陪伴）如何低频触发，并遵守冷却和阻断规则。

展示步骤：

- 在 Settings 中打开主动陪伴。
- 使用 idle（空闲）或 repeated death（反复死亡）场景触发。
- 查看 Proactive Debug 中的 `cooldown_remaining_seconds`（冷却剩余）和 `block_reason`（阻断原因）。
- 触发后保持静默，确认需要用户活动后才继续触发。

观察点：

- 主动消息应短、安静、低频。
- 主动消息不应进入 pending memory。
- 主动消息不应改变 game session state。
- Debug 中应标记主动触发原因。

## English

### Demo 1: Basic Companion Chat

Goal: show how the minimal persona responds in concise Chinese without sounding like customer support, therapy, or a generic AI assistant.

User inputs:

- 你好
- 我今天有点烦
- 你是不是在关心我

What to observe:

- Replies should be quiet, short, and natural in Chinese.
- Avoid templated phrases such as "as an AI" or over-explaining empathy.
- Do not turn emotional moments into counseling.
- Light care is acceptable, but the tone should remain restrained.

### Demo 2: Game Session State

Goal: show how game session state tracks the active boss, death count, and clear status.

User inputs:

- 我现在卡在女武神
- 又死了
- 还是没过
- 终于过了

What to observe:

- `current_boss` should become Malenia / 女武神.
- `death_count` should increase after repeated failures.
- “还是没过” should not be treated as cleared.
- “终于过了” should update `last_cleared_boss`.
- Game Session Debug should reflect each state change.

### Demo 3: Pending Memory

Goal: show how pending memory prevents unconfirmed facts from entering long-term memory.

User inputs:

- 我不喜欢长篇攻略
- 我不想召骨灰，感觉像作弊

What to observe:

- The app should create pending memory instead of writing long-term memory directly.
- The user can Accept or Ignore each candidate.
- Accepted memory appears in the prompt summary.
- Pending memory should not be injected directly into prompts.

### Demo 4: Multi-game Knowledge

Goal: show that the multi-game knowledge catalog can switch between separate game packs.

User inputs:

- 我在玩艾尔登法环，Margit 怎么打
- 我在玩空洞骑士，螳螂领主怎么打

What to observe:

- `game_id` should switch from `elden_ring` to `hollow_knight`.
- Knowledge Debug should show different `knowledge_path` values.
- `snippet_titles` should come from the matching game pack.
- Hollow Knight questions should not use Elden Ring snippets.

### Demo 5: Manual Game Context

Goal: show how manual game context override helps when auto detection is unavailable or wrong.

Steps:

- Select Elden Ring manually in Settings.
- Confirm Game Context shows `active_source` as manual.
- Clear the manual selection.
- Switch to Hollow Knight through a user message.
- Select or mention an unsupported game and observe fallback behavior.

What to observe:

- Manual override has the highest priority.
- Auto detection is still visible but cannot override manual selection.
- Unsupported games should show model-only fallback.
- Elden Ring knowledge must not be reused for unsupported games.

### Demo 6: Proactive Companion

Goal: show how proactive companion messages trigger quietly and respect cooldown / blocking rules.

Steps:

- Enable proactive companion in Settings.
- Trigger an idle or repeated-death scenario.
- Inspect `cooldown_remaining_seconds` and `block_reason` in Proactive Debug.
- Stay idle after one proactive message and confirm the system waits for user activity.

What to observe:

- Proactive messages should be short, quiet, and low-frequency.
- Proactive messages should not enter pending memory.
- Proactive messages should not change game session state.
- Debug should show why a proactive message was or was not sent.
