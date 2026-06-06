import type { BrowserWindow, BrowserWindowConstructorOptions } from "electron";

type OverlayBounds = {
  width: number;
  height: number;
  x: number;
  y: number;
};

export const createOverlayWindowOptions = (bounds: OverlayBounds, preloadPath: string): BrowserWindowConstructorOptions => ({
  ...bounds,
  frame: false,
  transparent: true,
  alwaysOnTop: true,
  skipTaskbar: true,
  resizable: false,
  minimizable: false,
  maximizable: false,
  fullscreenable: false,
  focusable: false,
  show: false,
  hasShadow: false,
  backgroundColor: "#00000000",
  webPreferences: {
    preload: preloadPath,
    contextIsolation: true,
    nodeIntegration: false
  }
});

export const configureOverlayWindowForClickThrough = (
  window: Pick<BrowserWindow, "setAlwaysOnTop" | "setIgnoreMouseEvents" | "setVisibleOnAllWorkspaces">
) => {
  window.setIgnoreMouseEvents(true);
  window.setAlwaysOnTop(true, "floating");
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
};
