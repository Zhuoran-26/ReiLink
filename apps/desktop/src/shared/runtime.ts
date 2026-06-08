export type BackendRuntimeState =
  | "checking"
  | "starting"
  | "connected"
  | "external_backend_detected"
  | "missing_project_root"
  | "missing_venv"
  | "spawn_failed"
  | "health_timeout"
  | "port_occupied"
  | "failed"
  | "not_found"
  | "disabled"
  | "disconnected";

export type BackendRuntimeStatus = {
  backend_auto_start_enabled: boolean;
  backend_app_mode: "dev" | "packaged";
  backend_binary_exists: boolean;
  backend_binary_path: string | null;
  bundled_backend_binary_path: string | null;
  bundled_backend_exists: boolean;
  backend_started_by_app: boolean;
  backend_started_from: "external" | "configured_binary" | "bundled_binary" | "repo" | "none";
  backend_start_error: string | null;
  backend_status: BackendRuntimeState;
  backend_runtime_mode: "auto" | "binary" | "repo";
  backend_project_root: string | null;
  backend_root: string | null;
  backend_python_path: string | null;
  backend_health_url: string;
  backend_retry_count: number;
  knowledge_path: string | null;
  knowledge_source: "bundled" | "repo" | "missing";
  user_data_dir: string;
};

export type OpenLocalDataDirResult = {
  ok: boolean;
  path: string;
  error: string | null;
};

export type LocalFilePickerKind = "asr_binary" | "asr_model" | "asr_converter";

export type LocalFilePickerRequest = {
  kind: LocalFilePickerKind;
  currentPath?: string;
};

export type LocalFilePickerResult = {
  canceled: boolean;
  path: string | null;
};

export type ReilinkRuntimeBridge = {
  getBackendStatus: () => Promise<BackendRuntimeStatus>;
  setBackendAutoStart: (enabled: boolean) => Promise<BackendRuntimeStatus>;
  openLocalDataDir: () => Promise<OpenLocalDataDirResult>;
  selectLocalFile: (request: LocalFilePickerRequest) => Promise<LocalFilePickerResult>;
  getOverlayStatus: () => Promise<OverlayState>;
  setOverlayEnabled: (enabled: boolean) => Promise<OverlayState>;
  setOverlayConfig: (config: OverlayConfigUpdate) => Promise<OverlayState>;
  updateOverlayContent: (content: OverlayContentUpdate) => Promise<OverlayState>;
  onBackendStatus: (callback: (status: BackendRuntimeStatus) => void) => () => void;
  onOverlayState: (callback: (state: OverlayState) => void) => () => void;
};

declare global {
  interface Window {
    reilinkRuntime?: ReilinkRuntimeBridge;
  }
}
import type { OverlayConfigUpdate, OverlayContentUpdate, OverlayState } from "./overlay.js";
