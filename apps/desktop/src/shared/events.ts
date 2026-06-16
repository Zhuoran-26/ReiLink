import type { AudioConversionStatusValue } from "./api";
import type { OverlayMessageSource, OverlayPosition } from "./overlay";

export type ReiLinkEvent =
  | { type: "user_message_sent"; timestamp: string; text: string; source?: "text" | "voice_direct"; character_count?: number }
  | { type: "assistant_reply_started"; timestamp: string; message_id?: string }
  | { type: "assistant_reply_segment_shown"; timestamp: string; segment_index: number; text: string }
  | { type: "assistant_reply_completed"; timestamp: string; message_id?: string }
  | { type: "proactive_message_shown"; timestamp: string; trigger_type: string; text: string }
  | { type: "pending_memory_created"; timestamp: string; memory_type: string; text: string }
  | { type: "pending_memory_accepted"; timestamp: string; memory_id: string }
  | { type: "pending_memory_ignored"; timestamp: string; memory_id: string }
  | { type: "game_context_changed"; timestamp: string; game?: string; source?: string }
  | {
      type: "semantic_extraction_traced";
      timestamp: string;
      source?: string;
      confidence?: string;
      fallback_reason?: string | null;
      skip_reason?: string | null;
      parse_error?: string | null;
      applied_updates?: string[];
      llm_shadow_status?: "skipped" | "succeeded" | "failed";
      llm_shadow_confidence?: "high" | "medium" | "low";
      llm_shadow_summary?: string | null;
      llm_shadow_diff?: string | null;
      shadow_trace_id?: string;
      shadow_event_phase?: "scheduled" | "final";
      shadow_event_status?:
        | "shadow_deferred"
        | "shadow_succeeded"
        | "shadow_timeout"
        | "shadow_invalid_json"
        | "shadow_auth_failed"
        | "shadow_provider_unavailable"
        | "shadow_provider_error"
        | "shadow_cancelled"
        | "shadow_expired";
    }
  | {
      type: "game_session_changed";
      timestamp: string;
      game?: string;
      current_boss?: string;
      activity?: string;
      death_count?: number;
      frustration_count?: number;
      last_cleared_boss?: string;
    }
  | { type: "knowledge_used"; timestamp: string; game?: string; topics?: string[] }
  | { type: "model_routed"; timestamp: string; model?: string; route_reason?: string }
  | { type: "backend_status_changed"; timestamp: string; status: string }
  | { type: "runtime_status_changed"; timestamp: string; backend_source?: string; knowledge_source?: string }
  | { type: "overlay_enabled_changed"; timestamp: string; enabled: boolean; visible: boolean }
  | { type: "overlay_settings_changed"; timestamp: string; position: OverlayPosition; opacity: number; max_messages: number }
  | { type: "overlay_window_shown"; timestamp: string; message_count: number }
  | { type: "overlay_window_moved"; timestamp: string; position: OverlayPosition }
  | { type: "overlay_window_hidden"; timestamp: string }
  | { type: "overlay_visibility_suppressed"; timestamp: string; reason: "main_window_active" }
  | { type: "overlay_content_updated"; timestamp: string; source?: OverlayMessageSource; character_count: number; message_count: number }
  | { type: "overlay_error"; timestamp: string; reason: string }
  | { type: "tts_started"; timestamp: string; character_count: number; source?: "assistant_reply" | "test_voice" }
  | { type: "tts_completed"; timestamp: string; character_count: number; source?: "assistant_reply" | "test_voice" }
  | { type: "tts_stopped"; timestamp: string; character_count?: number; reason?: string; source?: "assistant_reply" | "test_voice" }
  | { type: "tts_error"; timestamp: string; character_count?: number; reason?: string; status?: string; source?: "assistant_reply" | "test_voice" }
  | { type: "voice_input_started"; timestamp: string; language?: string }
  | { type: "voice_input_completed"; timestamp: string; character_count: number; is_final?: boolean; language?: string }
  | { type: "voice_input_stopped"; timestamp: string; character_count?: number; reason?: string; status?: string; language?: string }
  | { type: "voice_input_error"; timestamp: string; character_count?: number; reason?: string; status?: string; language?: string }
  | { type: "voice_input_unavailable"; timestamp: string; reason?: string; status?: string; language?: string }
  | { type: "voice_direct_mode_enabled"; timestamp: string }
  | { type: "voice_direct_mode_disabled"; timestamp: string }
  | { type: "voice_transcription_auto_sent"; timestamp: string; character_count: number; provider?: "local_asr" | "web_speech" }
  | { type: "voice_reply_auto_speak_started"; timestamp: string; character_count: number }
  | { type: "audio_capture_started"; timestamp: string; duration_ms?: number }
  | { type: "audio_capture_completed"; timestamp: string; duration_ms: number; size_bytes: number; mime_type?: string }
  | { type: "audio_capture_stopped"; timestamp: string; reason?: string; duration_ms?: number }
  | { type: "audio_capture_error"; timestamp: string; reason?: string; status?: string }
  | { type: "audio_temp_file_cleaned"; timestamp: string; duration_ms?: number; size_bytes?: number; mime_type?: string; temporary_file_cleaned: boolean }
  | { type: "local_asr_transcription_started"; timestamp: string; duration_ms?: number; size_bytes?: number; mime_type?: string; status?: string; language?: string }
  | {
      type: "local_asr_transcription_completed";
      timestamp: string;
      status: string;
      character_count: number;
      language?: string;
      transcript_normalized_to_simplified?: boolean;
      duration_ms?: number;
      size_bytes?: number;
      mime_type?: string;
      audio_format?: string;
      conversion_status?: AudioConversionStatusValue;
      conversion_required?: boolean;
      converted_mime_type?: string;
      converter_configured?: boolean;
      safe_converter_name?: string;
      temporary_file_cleaned?: boolean;
      temporary_input_cleaned?: boolean;
      temporary_converted_cleaned?: boolean;
      binary_name?: string;
      model_name?: string;
    }
  | {
      type: "local_asr_transcription_error";
      timestamp: string;
      status: string;
      reason?: string;
      character_count?: number;
      language?: string;
      transcript_normalized_to_simplified?: boolean;
      duration_ms?: number;
      size_bytes?: number;
      mime_type?: string;
      audio_format?: string;
      conversion_status?: AudioConversionStatusValue;
      conversion_required?: boolean;
      converted_mime_type?: string;
      converter_configured?: boolean;
      safe_converter_name?: string;
      temporary_file_cleaned?: boolean;
      temporary_input_cleaned?: boolean;
      temporary_converted_cleaned?: boolean;
      binary_name?: string;
      model_name?: string;
    };

export type ReiLinkEventType = ReiLinkEvent["type"];
