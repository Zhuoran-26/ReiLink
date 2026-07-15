import { BookMarked } from "lucide-react";

import { JourneyCard } from "./JourneyCard";

type JourneyReferenceProps = {
  available: boolean;
  gameName: string | null;
  usedRecently: boolean;
};

export function JourneyReference({ available, gameName, usedRecently }: JourneyReferenceProps) {
  return (
    <section aria-label="旅程参考" className="journeyReference">
      <header>
        <h2>旅程参考</h2>
        <p>Rei 能查阅的旅程资料，会安静地留在这里。</p>
      </header>
      <JourneyCard label="当前旅程参考状态">
        <div className="journeySectionLabel">
          <BookMarked aria-hidden="true" size={15} strokeWidth={1.65} />
          <span>{gameName ?? "尚未选择旅程"}</span>
        </div>
        <h3>{available ? "已有资料可以参考" : "暂时没有本地资料"}</h3>
        <p>
          {available
            ? "需要的时候，Rei 可以参考这段旅程已有的本地资料。"
            : "Rei 会先根据现在的对话回应，不会假装知道没有记录的内容。"}
        </p>
      </JourneyCard>
      <div className="journeyReferenceNote">
        <strong>最近一次对话</strong>
        <span>{usedRecently ? "Rei 参考了相关资料。" : "没有需要翻阅的旅程资料。"}</span>
      </div>
    </section>
  );
}
