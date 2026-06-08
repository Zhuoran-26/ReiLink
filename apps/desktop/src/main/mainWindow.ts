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
  window: Pick<BrowserWindow, "isDestroyed" | "isMinimized" | "isVisible" | "restore" | "showInactive">
) => {
  if (window.isDestroyed()) return false;
  if (window.isMinimized()) window.restore();
  else if (!window.isVisible()) window.showInactive();
  return true;
};
