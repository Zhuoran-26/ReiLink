import type { ChangeEventHandler } from "react";

import type { GameCatalogOption } from "../../../shared/api";
import { Button } from "../ui/Button";

type JourneyGameSelectorProps = {
  busy: boolean;
  canUseDetectedGame: boolean;
  detectedGameName: string;
  manualEnabled: boolean;
  onClearManual: () => void;
  onSelect: ChangeEventHandler<HTMLSelectElement>;
  onUseDetected: () => void;
  options: GameCatalogOption[];
  selectedGameId: string;
};

const optionStatus = (game: GameCatalogOption) => game.support_status === "supported" && game.knowledge_available
  ? "有旅程资料"
  : "暂无本地资料";

export function JourneyGameSelector({
  busy,
  canUseDetectedGame,
  detectedGameName,
  manualEnabled,
  onClearManual,
  onSelect,
  onUseDetected,
  options,
  selectedGameId
}: JourneyGameSelectorProps) {
  const available = options.filter((game) => game.support_status === "supported" && game.knowledge_available);
  const withoutReference = options.filter((game) => game.support_status !== "supported" || !game.knowledge_available);

  return (
    <section aria-label="选择游戏" className="journeyGameSelector">
      <header>
        <h2>选择这段旅程</h2>
        <p>可以跟随自动识别，也可以暂时指定一个游戏。</p>
      </header>
      <label className="journeySelectField">
        <span>当前游戏</span>
        <select aria-label="当前游戏" disabled={busy} value={selectedGameId} onChange={onSelect}>
          <option value="">跟随自动识别与对话</option>
          {options.map((game) => (
            <option key={game.game_id} value={game.game_id}>
              {game.display_name}（{optionStatus(game)}）
            </option>
          ))}
        </select>
      </label>
      <p className="journeyDetectedGame">自动识别：{detectedGameName}</p>
      <div className="journeySelectorActions">
        <Button disabled={busy || !canUseDetectedGame} size="small" onClick={onUseDetected}>
          使用检测结果
        </Button>
        <Button disabled={busy || !manualEnabled} size="small" variant="quiet" onClick={onClearManual}>
          清除手动选择
        </Button>
      </div>
      <div className="journeyCatalog" aria-label="旅程资料范围">
        <div>
          <strong>可以使用旅程资料</strong>
          <span>{available.map((game) => game.display_name).join(" / ") || "还没有"}</span>
        </div>
        <div>
          <strong>暂时没有本地资料</strong>
          <span>{withoutReference.map((game) => game.display_name).join(" / ") || "没有"}</span>
        </div>
      </div>
    </section>
  );
}
