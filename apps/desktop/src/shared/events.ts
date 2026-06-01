export type ReiLinkEvent =
  | { type: "user_message_sent"; timestamp: string; text: string }
  | { type: "assistant_reply_started"; timestamp: string; message_id?: string }
  | { type: "assistant_reply_segment_shown"; timestamp: string; segment_index: number; text: string }
  | { type: "assistant_reply_completed"; timestamp: string; message_id?: string }
  | { type: "proactive_message_shown"; timestamp: string; trigger_type: string; text: string }
  | { type: "pending_memory_created"; timestamp: string; memory_type: string; text: string }
  | { type: "pending_memory_accepted"; timestamp: string; memory_id: string }
  | { type: "pending_memory_ignored"; timestamp: string; memory_id: string }
  | { type: "game_context_changed"; timestamp: string; game?: string; source?: string }
  | { type: "game_session_changed"; timestamp: string; game?: string; current_boss?: string; activity?: string }
  | { type: "knowledge_used"; timestamp: string; game?: string; topics?: string[] }
  | { type: "model_routed"; timestamp: string; model?: string; route_reason?: string }
  | { type: "backend_status_changed"; timestamp: string; status: string }
  | { type: "runtime_status_changed"; timestamp: string; backend_source?: string; knowledge_source?: string };

export type ReiLinkEventType = ReiLinkEvent["type"];
