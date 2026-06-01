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
  backend_started_by_app: boolean;
  backend_started_from: "external" | "binary" | "repo" | "none";
  backend_start_error: string | null;
  backend_status: BackendRuntimeState;
  backend_runtime_mode: "auto" | "binary" | "repo";
  backend_project_root: string | null;
  backend_root: string | null;
  backend_python_path: string | null;
  backend_health_url: string;
  backend_retry_count: number;
};

export type ReilinkRuntimeBridge = {
  getBackendStatus: () => Promise<BackendRuntimeStatus>;
  setBackendAutoStart: (enabled: boolean) => Promise<BackendRuntimeStatus>;
  onBackendStatus: (callback: (status: BackendRuntimeStatus) => void) => () => void;
};

declare global {
  interface Window {
    reilinkRuntime?: ReilinkRuntimeBridge;
  }
}
