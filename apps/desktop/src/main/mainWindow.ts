import type { BrowserWindow, BrowserWindowConstructorOptions } from "electron";

export const createMainWindowOptions = (preloadPath: string): BrowserWindowConstructorOptions => ({
  width: 1120,
  height: 780,
  minWidth: 900,
  minHeight: 640,
  backgroundColor: "#111318",
  webPreferences: {
    preload: preloadPath,
    contextIsolation: true,
    nodeIntegration: false
  }
});

export const restoreMainWindowForActivation = (
  window: Pick<BrowserWindow, "focus" | "isDestroyed" | "isMinimized" | "restore" | "show">
) => {
  if (window.isDestroyed()) return false;
  if (window.isMinimized()) window.restore();
  window.show();
  window.focus();
  return true;
};
