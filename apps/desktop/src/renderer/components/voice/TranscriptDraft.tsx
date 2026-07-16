import type { ChangeEventHandler, FormEventHandler } from "react";
import { RotateCcw, Send } from "lucide-react";

import { Button } from "../ui/Button";

type TranscriptDraftProps = {
  busy: boolean;
  hint: string;
  onChange: ChangeEventHandler<HTMLTextAreaElement>;
  onRestart: () => void;
  onSubmit: FormEventHandler<HTMLFormElement>;
  ready: boolean;
  value: string;
};

export function TranscriptDraft({
  busy,
  hint,
  onChange,
  onRestart,
  onSubmit,
  ready,
  value
}: TranscriptDraftProps) {
  return (
    <form className={`transcriptDraft${ready ? " transcriptDraft-ready" : ""}`} onSubmit={onSubmit}>
      <header>
        <div>
          <h3>{ready ? "转写草稿" : "声音草稿"}</h3>
          <span>{ready ? "尚未发送 · 可以编辑" : "说完以后，文字会留在这里"}</span>
        </div>
        {ready ? <span className="transcriptDraftHint">{hint}</span> : null}
      </header>
      <textarea
        aria-label="转写草稿"
        disabled={busy}
        placeholder="还没有留下声音。"
        rows={4}
        value={value}
        onChange={onChange}
      />
      <div className="transcriptDraftActions">
        {ready ? (
          <Button disabled={busy} size="small" variant="quiet" onClick={onRestart}>
            <RotateCcw aria-hidden="true" size={15} strokeWidth={1.7} />
            重新录音
          </Button>
        ) : <span />}
        <Button disabled={busy || !value.trim()} size="small" type="submit" variant="primary">
          <Send aria-hidden="true" size={15} strokeWidth={1.7} />
          发送给 Rei
        </Button>
      </div>
    </form>
  );
}
