import type { BrowserWindow, BrowserWindowConstructorOptions } from "electron";

import { normalizeOverlayPosition, type OverlayPosition } from "../shared/overlay.js";

type OverlayBounds = {
  width: number;
  height: number;
  x: number;
  y: number;
};

type OverlayWorkArea = OverlayBounds;

export type OverlayVisibilityContext = {
  overlayEnabled: boolean;
  mainWindowFocused: boolean;
  appActive: boolean;
};

const OVERLAY_WINDOW_WIDTH = 360;
const OVERLAY_WINDOW_HEIGHT = 168;
const OVERLAY_EDGE_MARGIN = 44;
const OVERLAY_MIN_EDGE_MARGIN = 24;
const OVERLAY_MIDDLE_Y_RATIO = 0.58;

const clampToWorkArea = (value: number, min: number, max: number) => {
  const safeMax = Math.max(min, max);
  return Math.min(Math.max(value, min), safeMax);
};

export const calculateOverlayBounds = (
  workArea: OverlayWorkArea,
  position: OverlayPosition
): OverlayBounds => {
  const safePosition = normalizeOverlayPosition(position);
  const width = OVERLAY_WINDOW_WIDTH;
  const height = OVERLAY_WINDOW_HEIGHT;
  const xMin = workArea.x + OVERLAY_MIN_EDGE_MARGIN;
  const xMax = workArea.x + workArea.width - width - OVERLAY_MIN_EDGE_MARGIN;
  const yMin = workArea.y + OVERLAY_MIN_EDGE_MARGIN;
  const yMax = workArea.y + workArea.height - height - OVERLAY_MIN_EDGE_MARGIN;
  const preferredX = safePosition.endsWith("-left")
    ? workArea.x + OVERLAY_EDGE_MARGIN
    : workArea.x + workArea.width - width - OVERLAY_EDGE_MARGIN;
  const preferredY = safePosition.startsWith("top-")
    ? workArea.y + OVERLAY_EDGE_MARGIN
    : safePosition.startsWith("bottom-")
      ? workArea.y + workArea.height - height - OVERLAY_EDGE_MARGIN
      : workArea.y + Math.round((workArea.height - height) * OVERLAY_MIDDLE_Y_RATIO);

  return {
    width,
    height,
    x: clampToWorkArea(preferredX, xMin, xMax),
    y: clampToWorkArea(preferredY, yMin, yMax)
  };
};

export const shouldOverlayBeVisible = ({
  overlayEnabled,
  mainWindowFocused,
  appActive
}: OverlayVisibilityContext) => overlayEnabled && !mainWindowFocused && !appActive;

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
