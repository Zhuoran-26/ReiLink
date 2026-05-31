import { contextBridge, ipcRenderer } from "electron";

import type { BackendRuntimeStatus, ReilinkRuntimeBridge } from "../shared/runtime.js";
import type { IpcRendererEvent } from "electron";

const runtimeBridge: ReilinkRuntimeBridge = {
  getBackendStatus: () => ipcRenderer.invoke("backend-runtime:get-status") as Promise<BackendRuntimeStatus>,
  setBackendAutoStart: (enabled: boolean) =>
    ipcRenderer.invoke("backend-runtime:set-auto-start", enabled) as Promise<BackendRuntimeStatus>,
  onBackendStatus: (callback: (status: BackendRuntimeStatus) => void) => {
    const listener = (_event: IpcRendererEvent, status: BackendRuntimeStatus) => callback(status);
    ipcRenderer.on("backend-runtime:status", listener);
    return () => ipcRenderer.removeListener("backend-runtime:status", listener);
  }
};

contextBridge.exposeInMainWorld("reilinkRuntime", runtimeBridge);
