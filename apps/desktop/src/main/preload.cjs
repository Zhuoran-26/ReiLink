const { contextBridge, ipcRenderer } = require("electron");

const runtimeBridge = {
  getBackendStatus: () => ipcRenderer.invoke("backend-runtime:get-status"),
  setBackendAutoStart: (enabled) => ipcRenderer.invoke("backend-runtime:set-auto-start", enabled),
  openLocalDataDir: () => ipcRenderer.invoke("local-data:open-dir"),
  getOverlayStatus: () => ipcRenderer.invoke("overlay:get-status"),
  setOverlayEnabled: (enabled) => ipcRenderer.invoke("overlay:set-enabled", enabled),
  updateOverlayContent: (content) => ipcRenderer.invoke("overlay:update-content", content),
  onBackendStatus: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on("backend-runtime:status", listener);
    return () => ipcRenderer.removeListener("backend-runtime:status", listener);
  },
  onOverlayState: (callback) => {
    const listener = (_event, state) => callback(state);
    ipcRenderer.on("overlay:state", listener);
    return () => ipcRenderer.removeListener("overlay:state", listener);
  }
};

contextBridge.exposeInMainWorld("reilinkRuntime", runtimeBridge);
