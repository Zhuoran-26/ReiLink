export type BackendRuntimeState =
  | "checking"
  | "starting"
  | "connected"
  | "failed"
  | "not_found"
  | "disabled"
  | "disconnected";

export type BackendRuntimeStatus = {
  backend_auto_start_enabled: boolean;
  backend_started_by_app: boolean;
  backend_start_error: string | null;
  backend_status: BackendRuntimeState;
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
