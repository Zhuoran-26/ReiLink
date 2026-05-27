from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserEmotion:
    label: str | None
    description: str | None

    @property
    def detected(self) -> bool:
        return self.label is not None


_FRUSTRATION = ("烦", "崩溃", "破防", "红温", "气死", "不想打", "受不了", "难受")
_DEATH_LOOP = ("又死", "一直死", "死太多", "打不过", "卡住", "还是不行", "过不去")
_AFFECTION = ("喜欢你", "在意你", "想你", "喜欢我", "关心我", "在意我")
_DEPENDENCY = ("陪我", "别走", "不要走", "你在吗", "还在吗", "觉得我烦", "会不会烦")
_TIRED = ("累了", "困了", "不想动", "眼睛累", "打了很久", "凌晨", "很晚", "不想说话", "挂着你")
_SELF_DOUBT = ("我是不是很菜", "我太菜", "我不行", "我好菜", "我很没用")


def detect_user_emotion(message: str) -> UserEmotion:
    if any(word in message for word in _AFFECTION):
        return UserEmotion("affection", "用户在表达喜欢或靠近")
    if any(word in message for word in _DEPENDENCY):
        return UserEmotion("dependency", "用户在确认陪伴或依赖感")
    if any(word in message for word in _TIRED):
        return UserEmotion("tired", "用户有疲惫感")
    if any(word in message for word in _SELF_DOUBT):
        return UserEmotion("self_doubt", "用户在否定自己")
    if any(word in message for word in _FRUSTRATION):
        return UserEmotion("frustrated", "用户有烦躁或挫败感")
    if any(word in message for word in _DEATH_LOOP):
        return UserEmotion("death_loop", "用户在反复失败或死亡循环里")
    return UserEmotion(None, None)


def wants_detailed_strategy(message: str) -> bool:
    return any(word in message for word in ("详细说", "完整攻略", "具体讲", "怎么配装"))


def build_companion_policy(message: str, intent: str) -> str:
    emotion = detect_user_emotion(message)
    detailed = wants_detailed_strategy(message)
    lines = [
        "Companion-first Response Policy:",
        "- 回复优先级：当前用户情绪 > 当前用户问题 > 当前游戏上下文 > 知识库 > 长期记忆 > Rei 气质。",
        "- 不要先进入攻略说明。用户有情绪信号时，第一句先接住状态；第二句如果需要，再给一个很短的建议。",
        "- 接住状态不是安慰模板，要回应用户此刻的话。",
    ]
    if emotion.detected:
        lines.append(f"- 当前检测到的情绪信号：{emotion.label}（{emotion.description}）。")
    else:
        lines.append("- 当前没有明显情绪信号，正常回答即可。")
    if any(word in message for word in ("不是", "没告诉过", "沒告訴過", "你是不是忘记", "你是不是忘記", "忘记了", "忘記了")):
        lines.append("- 当前用户可能在纠正事实或追问记忆边界。先收住，不要继续猜；不知道就简短承认不知道。")
    if intent.startswith("elden_ring"):
        lines.extend(
            [
                "- 艾尔登法环相关回答默认只给 1 个关键点，不写完整攻略段落。",
                "- 除非用户明确要求详细说、完整攻略、具体讲、怎么配装，否则总长度不要超过 2 句。",
                "- 玩家说死了、烦了、还是不行、打不过时，先回应状态，再指出一个问题，最后只给一个短建议。",
                "- 少用攻略站语气：先保证、输出、连段、方向、节奏、机制、建议、如果……那么……。",
                "- 更自然地说：别急、少打一刀、先活下来、等他真的落下来再滚、你太早动了、这次只练躲。",
            ]
        )
        if detailed:
            lines.append("- 用户明确要求细讲，可以多给一点，但仍然保持清楚和克制。")
    return "\n".join(lines)
