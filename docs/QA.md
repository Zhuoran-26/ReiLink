# Manual QA Pack / Regression Scenarios v1

## 中文

这份 QA Pack 用于在继续开发 Voice Input、Live2D、Overlay、embedding RAG 之前，快速回归 ReiLink 当前已经稳定的交互底座。它覆盖手动检查、packaged app smoke、Knowledge Retrieval、Voice Output、Event Stream / Debug 隐私，以及 release 前 runtime sanity。

配套机器可读场景文件：

- `docs/qa/retrieval_scenarios.json`

### 1. 基础启动检查

#### Dev App

- 启动 backend：`make dev-backend`。
- 启动 desktop：`make dev-desktop`。
- 主界面不是黑屏。
- 主聊天区、输入框、设置区、右侧面板正常显示。
- `curl http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}`。
- Settings Panel 可见。
- Debug Panel 可见。
- `事件流 / Event Stream` 标题可见，默认折叠，展开后能看到事件或“暂无事件”。
- Local Data controls 显示用户数据目录，memory / session 写入用户数据目录，不写入 `.app`。
- `.env` 不出现在 UI、Event Stream、Raw JSON 或 packaged resources 中。

#### Packaged `.app`

- 如 backend 代码、schema、knowledge loading 或 runtime 发生变化，先运行 `make package-backend`。
- 运行 `make package-desktop`。
- 直接打开 `apps/desktop/release/ReiLink-darwin-<arch>/ReiLink.app`，不要打开 dev renderer。
- UI 不是黑屏。
- 后端最终显示已连接，或 health endpoint 返回 `{"status":"ok"}`。
- packaged app 使用内置 backend binary 或健康的外部 backend，启动来源显示为用户可读摘要。
- bundled knowledge resources 可用。
- Settings Panel、Debug Panel、Event Stream 可见。
- `.env`、API key、memory、session 和用户数据不复制进 `.app`。
- app 退出后，由 app 自启动的 backend 没有残留进程。

### 2. Voice Output 回归检查

- `语音输出 / Voice Output` 默认关闭。
- `测试语音 / Test Voice` 按钮可见。
- `语速 / Rate` 和 `音量 / Volume` 控件可见。
- 默认关闭时，assistant 回复不会播放语音。
- 点击 `测试语音 / Test Voice` 后，语音开始前显示准备状态。
- Test Voice 只有在 `utterance.onstart` 后才记录“语音开始播放”。
- Test Voice 正常结束后记录“语音播放完成”。
- 播放中显示正在播放。
- 播放中 `停止语音 / Stop Voice` 可见。
- 点击 Stop Voice 可以停止当前播放，并记录“语音已停止”。
- 播放中发送新用户消息会停止当前语音。
- 关闭 Voice Output 会停止当前语音。
- Voice Output 开启时，assistant 最终回复会触发语音播放。
- 如果 5 秒内没有真实开始播放，Event Stream 显示“语音播放失败”或等价中文摘要。
- 更换系统语音包后，Test Voice 仍应允许失败并显示可理解错误，不应卡死 UI。
- Event Stream 不显示完整 assistant 回复文本。
- Event Stream 不显示完整测试语音文本。
- Event Stream 不显示 raw prompt、API key、`.env`、Authorization、完整路径或长 internal payload。

### 3. Knowledge Retrieval 回归检查

#### Elden Ring 命中

示例输入：

- `Margit 怎么打？`
- `Tree Sentinel 有什么打法？`（若当前 sample pack 尚无 Tree Sentinel 条目，用 `水鸟乱舞怎么躲？` 做稳定回归）
- `Elden Ring 里 Margit 有什么注意点？`

期望：

- selected game 为 Elden Ring / 艾尔登法环。
- retrieval status 为 `used`。
- Event Stream 显示“已使用本地知识”。
- Debug Panel 显示 matched terms、score、snippet preview。
- prompt/context 中有截断后的本地知识块。
- 不显示完整 knowledge entry 正文。
- 不显示 API key、raw prompt、`.env` 或完整本地路径。

#### Hollow Knight 命中

示例输入：

- `Hornet 怎么打？`
- `Hollow Knight 里 Greenpath 要注意什么？`

期望：

- selected game 为 Hollow Knight / 空洞骑士。
- retrieval status 为 `used`。
- Event Stream 显示“已使用本地知识”。
- 不误用 Elden Ring knowledge。

#### 跨游戏显式切换

当前上下文为 Elden Ring，用户输入：

- `我在玩 Hollow Knight，Hornet 怎么打？`

期望：

- 使用 Hollow Knight knowledge。
- 不使用 Elden Ring knowledge。
- Debug / Event Stream 显示可读中文摘要。
- 如果手动选择当前游戏，手动选择优先，并显示冲突或当前来源摘要。

#### 闲聊不触发 knowledge

示例输入：

- `今天有点累`
- `你在吗`
- `陪我聊一会`
- `谢谢`
- `我先休息一下`

期望：

- retrieval status 为 `not_game_related`。
- 不注入 knowledge prompt。
- Event Stream 可显示“这次不是游戏知识问题”。
- Rei 正常陪伴式回复。
- 不强行引用攻略。

#### 低相关不注入

示例输入：

- `这个东西怎么弄`
- `刚才那个有点难`
- `我不知道下一步怎么办`

期望：

- 如果只有弱命中，retrieval status 为 `below_threshold`。
- 不注入 knowledge prompt。
- 不强行引用攻略。
- Event Stream 和 Debug Panel 显示“相关性不足，未使用”或等价中文摘要。

#### no_pack 场景

示例输入：

- `我在玩只狼，弦一郎怎么打？`

期望：

- selected game 可识别为 Sekiro / 只狼。
- retrieval status 为 `no_pack`。
- 不崩溃。
- 不注入空 knowledge 模板。
- Event Stream 显示安全中文摘要。

#### not_found 场景

示例输入：

- 在当前游戏为 Elden Ring 时输入：`艾尔登法环里完全不存在的月光蘑菇钥匙在哪？`

期望：

- selected game 为 Elden Ring / 艾尔登法环。
- retrieval status 为 `not_found`。
- 不注入空 knowledge 模板。
- 不强行编知识包内容。

### 4. Debug / Event Stream 隐私检查

必须不能出现：

- API key value。
- Authorization header。
- `.env` 完整路径。
- backend binary 完整路径。
- complete local filesystem paths。
- raw prompt。
- full assistant reply。
- full Test Voice text。
- full knowledge pack content。
- long backend/internal payload。

允许出现：

- `api_key_loaded: true/false`。
- selected game。
- retrieval status。
- result count。
- matched terms。
- score。
- snippet preview。
- TTS lifecycle 摘要。
- backend health summary。

### 5. Packaged `.app` Release Smoke Checklist

- 如果 backend 代码、schema、knowledge loading 或 runtime 发生变化，重新运行 `make package-backend`。
- 重新运行 `make package-desktop`。
- 直接打开 packaged `ReiLink.app`，不是 dev renderer。
- UI 非黑屏。
- backend 自启动，或复用健康外部 backend。
- bundled knowledge resources 可用。
- `语音输出 / Voice Output` 和 `测试语音 / Test Voice` 可见。
- Knowledge Retrieval 可用。
- Event Stream 不泄露敏感内容。
- memory / session 写入用户数据目录，不写入 `.app`。
- `.env` 不复制进 `.app`。
- app 退出后，自启动 backend 无残留。

### 6. Release 前 Runtime Sanity

- `make lint`
- `make test-desktop`
- `make typecheck`
- `git diff --check`
- `make test-backend`
- `make validate-knowledge`
- 如果 e2e 已存在：`cd apps/desktop && npm run test:e2e`
- 如果 runtime / packaging / backend binary / knowledge loading 变更：`make package-backend && make package-desktop`
- packaged `.app` smoke 至少覆盖：非黑屏、backend health ok、bundled knowledge、Voice Output controls、Event Stream privacy。

### 7. Known Limitations

- `below_threshold` 依赖当前知识包内容和评分阈值，手动测试时可优先用机器可读场景文件里的弱相关示例。
- `no_pack` 依赖 catalog 中仍有 planned / unsupported 游戏；当前可用 `只狼` 做手动场景。
- 当前跨游戏切换更稳定的表达是“我在玩/换个游戏”；在已有 Elden Ring 上下文时，`Hollow Knight 里的 Hornet 怎么打？` 这种所属格问法可能不会切换知识包，应作为后续检索改进候选。
- Voice Output 的真实播放取决于系统语音包和浏览器 speech synthesis 支持；失败必须被 UI 允许并可见，不应被视为崩溃。
- Manual QA 不替代 automated tests；它用于 release 前的人眼回归与打包行为确认。

## English

This QA Pack is a reusable manual regression checklist for ReiLink before future Voice Input, Live2D, Overlay, and embedding RAG work. It focuses on the current foundations: local runtime, Voice Output, Knowledge Retrieval, Event Stream, Debug privacy, and packaged app smoke testing.

Machine-readable scenarios live at:

- `docs/qa/retrieval_scenarios.json`

Use the Chinese checklist above as the source of truth for manual runs. Keep results short and concrete: pass/fail, exact app mode, exact commit, and any visible privacy issue.
