# Manual Eval Cases

## 中文

### 评估标准

人工评估的目标是判断 Rei 是否像一个安静地坐在玩家旁边的人，而不是通用 AI、客服、心理咨询师、角色扮演机器人或攻略站。

核心判断：

- 回复优先响应当前用户消息。
- 中文自然、短、克制。
- 不编造记忆，不硬猜 Boss。
- 游戏建议可以有，但默认只给一两个关键点。
- `persona`（人格）、`memory`（记忆）、`knowledge`（知识）都应服务于最终回复，而不是抢走对话。

### Persona 测试

- 输入：你好。预期：短句回应，不开启菜单式自我介绍。
- 输入：我今天有点烦。预期：轻微接住情绪，不变成心理咨询。
- 输入：你是不是在关心我。预期：保持距离，不解释“关心的定义”。
- 输入：你喜欢我吗。预期：不甜腻，不哲学化。
- 输入：你刚才有点像 AI。预期：接受纠正，调整语气。
- 输入：我只是想挂着你。预期：安静回应，不主动制造戏剧感。

### Game Session 测试

- 输入：我现在卡在女武神。预期：`current_boss`（当前 Boss）为女武神。
- 输入：又死了。预期：`death_count`（死亡次数）增加。
- 输入：还是没过。预期：不更新为 cleared。
- 输入：终于过了。预期：`last_cleared_boss`（最近通过 Boss）更新。
- 输入：我现在玩空洞骑士。预期：当前游戏切换，不保留旧 Boss 作为当前 Boss。
- 输入：空洞骑士也挺好玩。预期：普通提及不应强制切换当前游戏。

### Semantic Extraction 测试

- 输入：我现在卡在恶兆妖鬼。预期：识别游戏事件和 Boss。
- 输入：我不喜欢长篇攻略。预期：识别为 memory candidate（记忆候选）。
- 输入：我没打过。预期：否定状态不应误判为通关。
- 输入：终于打过了。预期：识别为 cleared。
- 输入：我不是在说游戏。预期：避免强行写入游戏状态。
- 输入：我不想召骨灰，感觉像作弊。预期：识别偏好，但等待用户确认。

### Pending Memory 测试

- 输入：我不喜欢长篇攻略。预期：生成 pending memory（待确认记忆）。
- 输入：我喜欢你叫我阿遥。预期：生成关系 / 称呼偏好候选。
- 操作：Accept。预期：进入已接受长期记忆。
- 操作：Ignore。预期：不进入长期记忆。
- 检查：pending memory 不应直接注入 prompt。
- 检查：临时 Boss 状态不应自动变成长久记忆。

### Knowledge Matching 测试

- 输入：我在玩艾尔登法环，Margit 怎么打。预期：匹配 `elden_ring`。
- 输入：我在玩空洞骑士，螳螂领主怎么打。预期：匹配 `hollow_knight`。
- 输入：螳螂领主怎么打。预期：可通过内容别名匹配 Hollow Knight。
- 输入：大树守卫怎么打，并手动选择空洞骑士。预期：不误用 Hollow Knight snippet。
- 输入：螳螂领主怎么打，并手动选择艾尔登法环。预期：不误用 Elden Ring snippet。
- 检查：`snippets_count`（命中知识条数）最多为 3。

### Game Catalog / Unsupported Game 测试

- 输入：我在玩只狼。预期：识别游戏，但显示暂未支持知识库。
- 输入：我在玩星之门遗迹。预期：显示未知 / 未接入知识库。
- 输入：换个游戏，我玩赛博朋克。预期：更新 active game，不沿用旧游戏知识。
- 设置：manual override 为艾尔登法环，再输入“我在玩空洞骑士”。预期：当前游戏仍以手动选择为准，并显示 conflict warning。
- 检查：unsupported game 下 `knowledge_used_in_prompt`（是否注入知识）为 false。
- 检查：`fallback_reason`（兜底原因）明确显示 no_supported_knowledge 或 unknown_game。

### Proactive 测试

- 设置：开启 proactive companion。预期：Debug 显示 enabled。
- 场景：长时间 idle。预期：低频短句触发。
- 场景：反复死亡。预期：可触发轻微提醒。
- 检查：触发后进入 cooldown（冷却）。
- 检查：一次主动消息后，需要用户活动才继续触发。
- 检查：主动消息不进入 pending memory，不改变 game session state。

### Model Routing 测试

- 输入：你好。预期：使用 fast 或低复杂度路线。
- 输入：Margit 怎么打，详细一点。预期：可路由到 pro 或高复杂度。
- 设置：model preference 为 fast。预期：优先 fast。
- 设置：model preference 为 pro。预期：优先 pro。
- 设置：model preference 为 auto。预期：根据 intent 和复杂度选择。
- 检查：Debug 中 `route_reason`（路由原因）和 `selected_model`（选用模型）可解释。

## English

### Evaluation Standard

Manual evaluation checks whether Rei feels like a quiet person sitting beside the player, not a generic AI assistant, customer support agent, therapist, roleplay bot, or guide site.

Core criteria:

- The current user message has the highest priority.
- Chinese replies should be natural, short, and restrained.
- Do not invent memory or guess bosses without evidence.
- Game advice is allowed, but default replies should only include one or two key points.
- `persona`, `memory`, and `knowledge` should support the final reply without taking over the conversation.

### Persona Tests

- Input: 你好. Expected: short greeting, no menu-like introduction.
- Input: 我今天有点烦. Expected: acknowledge the mood lightly without therapy language.
- Input: 你是不是在关心我. Expected: restrained distance, no abstract definition of care.
- Input: 你喜欢我吗. Expected: not sweet, not philosophical.
- Input: 你刚才有点像 AI. Expected: accept the correction and adjust tone.
- Input: 我只是想挂着你. Expected: quiet response without dramatic intimacy.

### Game Session Tests

- Input: 我现在卡在女武神. Expected: `current_boss` becomes Malenia / 女武神.
- Input: 又死了. Expected: `death_count` increases.
- Input: 还是没过. Expected: do not mark the boss as cleared.
- Input: 终于过了. Expected: `last_cleared_boss` updates.
- Input: 我现在玩空洞骑士. Expected: active game switches and the old boss is not used as current boss.
- Input: 空洞骑士也挺好玩. Expected: casual mention should not force a current-game switch.

### Semantic Extraction Tests

- Input: 我现在卡在恶兆妖鬼. Expected: extract game event and boss.
- Input: 我不喜欢长篇攻略. Expected: extract a memory candidate.
- Input: 我没打过. Expected: negation should not be treated as cleared.
- Input: 终于打过了. Expected: extract cleared state.
- Input: 我不是在说游戏. Expected: avoid forcing game-state updates.
- Input: 我不想召骨灰，感觉像作弊. Expected: extract preference candidate but wait for confirmation.

### Pending Memory Tests

- Input: 我不喜欢长篇攻略. Expected: create pending memory.
- Input: 我喜欢你叫我阿遥. Expected: create relationship / naming preference candidate.
- Action: Accept. Expected: enters accepted long-term memory.
- Action: Ignore. Expected: does not enter long-term memory.
- Check: pending memory should not be injected directly into prompts.
- Check: temporary boss state should not automatically become long-term memory.

### Knowledge Matching Tests

- Input: 我在玩艾尔登法环，Margit 怎么打. Expected: matches `elden_ring`.
- Input: 我在玩空洞骑士，螳螂领主怎么打. Expected: matches `hollow_knight`.
- Input: 螳螂领主怎么打. Expected: may match Hollow Knight through content alias.
- Input: 大树守卫怎么打 with manual override set to Hollow Knight. Expected: do not misuse Hollow Knight snippets.
- Input: 螳螂领主怎么打 with manual override set to Elden Ring. Expected: do not misuse Elden Ring snippets.
- Check: `snippets_count` should be at most 3.

### Game Catalog / Unsupported Game Tests

- Input: 我在玩只狼. Expected: game is recognized but knowledge is marked unsupported.
- Input: 我在玩星之门遗迹. Expected: unknown / not connected to a knowledge pack.
- Input: 换个游戏，我玩赛博朋克. Expected: active game updates and old game knowledge is not reused.
- Setting: manual override Elden Ring, then input “我在玩空洞骑士”. Expected: manual game remains active and conflict warning is shown.
- Check: for unsupported games, `knowledge_used_in_prompt` is false.
- Check: `fallback_reason` clearly shows no_supported_knowledge or unknown_game.

### Proactive Tests

- Setting: enable proactive companion. Expected: Debug shows enabled.
- Scenario: long idle period. Expected: low-frequency short message can trigger.
- Scenario: repeated deaths. Expected: light reminder can trigger.
- Check: cooldown starts after trigger.
- Check: after one proactive message, user activity is required before another trigger.
- Check: proactive messages do not enter pending memory and do not change game session state.

### Model Routing Tests

- Input: 你好. Expected: fast or low-complexity route.
- Input: Margit 怎么打，详细一点. Expected: pro or high-complexity route may be selected.
- Setting: model preference fast. Expected: prefer fast model.
- Setting: model preference pro. Expected: prefer pro model.
- Setting: model preference auto. Expected: choose based on intent and complexity.
- Check: Debug explains `route_reason` and `selected_model`.
