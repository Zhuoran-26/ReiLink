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
  | { type: "runtime_status_changed"; timestamp: string; backend_source?: string; knowledge_source?: string }
  | { type: "tts_started"; timestamp: string; character_count: number; source?: "assistant_reply" | "test_voice" }
  | { type: "tts_completed"; timestamp: string; character_count: number; source?: "assistant_reply" | "test_voice" }
  | { type: "tts_stopped"; timestamp: string; character_count?: number; reason?: string; source?: "assistant_reply" | "test_voice" }
  | { type: "tts_error"; timestamp: string; character_count?: number; reason?: string; status?: string; source?: "assistant_reply" | "test_voice" }
  | { type: "voice_input_started"; timestamp: string; language?: string }
  | { type: "voice_input_completed"; timestamp: string; character_count: number; is_final?: boolean; language?: string }
  | { type: "voice_input_stopped"; timestamp: string; character_count?: number; reason?: string; status?: string; language?: string }
  | { type: "voice_input_error"; timestamp: string; character_count?: number; reason?: string; status?: string; language?: string }
  | { type: "voice_input_unavailable"; timestamp: string; reason?: string; status?: string; language?: string }
  | { type: "audio_capture_started"; timestamp: string; duration_ms?: number }
  | { type: "audio_capture_completed"; timestamp: string; duration_ms: number; size_bytes: number; mime_type?: string }
  | { type: "audio_capture_stopped"; timestamp: string; reason?: string; duration_ms?: number }
  | { type: "audio_capture_error"; timestamp: string; reason?: string; status?: string }
  | { type: "audio_temp_file_cleaned"; timestamp: string; duration_ms?: number; size_bytes?: number; mime_type?: string; temporary_file_cleaned: boolean }
  | { type: "local_asr_transcription_started"; timestamp: string; duration_ms?: number; size_bytes?: number; mime_type?: string; status?: string }
  | {
      type: "local_asr_transcription_completed";
      timestamp: string;
      status: string;
      character_count: number;
      duration_ms?: number;
      size_bytes?: number;
      mime_type?: string;
      temporary_file_cleaned?: boolean;
      binary_name?: string;
      model_name?: string;
    }
  | {
      type: "local_asr_transcription_error";
      timestamp: string;
      status: string;
      reason?: string;
      character_count?: number;
      duration_ms?: number;
      size_bytes?: number;
      mime_type?: string;
      temporary_file_cleaned?: boolean;
      binary_name?: string;
      model_name?: string;
    };

export type ReiLinkEventType = ReiLinkEvent["type"];
