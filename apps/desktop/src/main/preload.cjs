const { contextBridge, ipcRenderer } = require("electron");

const runtimeBridge = {
  getBackendStatus: () => ipcRenderer.invoke("backend-runtime:get-status"),
  setBackendAutoStart: (enabled) => ipcRenderer.invoke("backend-runtime:set-auto-start", enabled),
  openLocalDataDir: () => ipcRenderer.invoke("local-data:open-dir"),
  onBackendStatus: (callback) => {
    const listener = (_event, status) => callback(status);
    ipcRenderer.on("backend-runtime:status", listener);
    return () => ipcRenderer.removeListener("backend-runtime:status", listener);
  }
};

contextBridge.exposeInMainWorld("reilinkRuntime", runtimeBridge);
