import type { BrowserWindow, BrowserWindowConstructorOptions } from "electron";

const PACKAGED_RENDERER_BASE_URL = "app://./index.html";
const PACKAGED_RENDERER_CACHE_PARAM = "renderer_cache_key";

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

export const createPackagedRendererUrl = (cacheKey: string | number = Date.now()) => {
  const url = new URL(PACKAGED_RENDERER_BASE_URL);
  url.searchParams.set(PACKAGED_RENDERER_CACHE_PARAM, String(cacheKey));
  return url.toString();
};

export const restoreMainWindowForActivation = (
  window: Pick<BrowserWindow, "isDestroyed" | "isMinimized" | "isVisible" | "restore" | "showInactive">
) => {
  if (window.isDestroyed()) return false;
  if (window.isMinimized()) window.restore();
  else if (!window.isVisible()) window.showInactive();
  return true;
};
