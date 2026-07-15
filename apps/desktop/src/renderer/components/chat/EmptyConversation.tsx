import { ReiAvatar } from "../rei/ReiAvatar";

export function EmptyConversation() {
  return (
    <section aria-label="空白对话" className="emptyConversation">
      <ReiAvatar name="Rei" size="medium" state="idle" />
      <div>
        <h2>Rei 在这里。</h2>
        <p>想说的时候，就说。</p>
      </div>
    </section>
  );
}
