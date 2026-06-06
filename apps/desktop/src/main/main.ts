import { app, BrowserWindow, ipcMain, net, protocol, screen, shell } from "electron";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

import { BackendRuntimeManager } from "./backendRuntime.js";
import { openLocalDataDir } from "./localData.js";
import {
  createOverlayMessage,
  createOverlayState,
  type OverlayContentUpdate,
  type OverlayMessage,
  type OverlayState
} from "../shared/overlay.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_PROTOCOL = "app";
let backendRuntime: BackendRuntimeManager | null = null;
let mainWindow: BrowserWindow | null = null;
let overlayWindow: BrowserWindow | null = null;
let overlayEnabled = false;
let overlayMessages: OverlayMessage[] = [];
let overlayUpdatedAt: string | null = null;
const isDevRenderer = () => Boolean(process.env.VITE_DEV_SERVER_URL);

protocol.registerSchemesAsPrivileged([
  {
    scheme: APP_PROTOCOL,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true
    }
  }
]);

process.on("uncaughtException", (error) => {
  console.error("[ReiLink] uncaught exception", error);
});

process.on("unhandledRejection", (reason) => {
  console.error("[ReiLink] unhandled rejection", reason);
});

const registerPackagedRendererProtocol = () => {
  if (isDevRenderer()) return;
  const rendererRoot = path.resolve(__dirname, "../../dist");
  protocol.handle(APP_PROTOCOL, (request) => {
    const requestUrl = new URL(request.url);
    const requestedPath = decodeURIComponent(requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname);
    const filePath = path.normalize(path.join(rendererRoot, requestedPath));
    const relativePath = path.relative(rendererRoot, filePath);
    if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
      console.error("[ReiLink] blocked packaged renderer path", request.url);
      return new Response("Not found", { status: 404 });
    }
    return net.fetch(pathToFileURL(filePath).toString());
  });
};

const overlayState = (): OverlayState =>
  createOverlayState(
    overlayEnabled,
    Boolean(overlayWindow && !overlayWindow.isDestroyed() && overlayWindow.isVisible()),
    overlayMessages,
    overlayUpdatedAt
  );

const broadcastOverlayState = () => {
  const state = overlayState();
  for (const window of BrowserWindow.getAllWindows()) {
    if (!window.isDestroyed()) {
      window.webContents.send("overlay:state", state);
    }
  }
  return state;
};

const overlayRendererUrl = () => {
  const devUrl = process.env.VITE_DEV_SERVER_URL ?? "http://127.0.0.1:5173";
  return isDevRenderer() ? `${devUrl}?overlay=1` : `${APP_PROTOCOL}://./index.html?overlay=1`;
};

const overlayBounds = () => {
  const { workArea } = screen.getPrimaryDisplay();
  const width = 360;
  const height = 168;
  const x = workArea.x + workArea.width - width - 44;
  const preferredY = workArea.y + Math.round(workArea.height * 0.58);
  const y = Math.min(Math.max(workArea.y + 24, preferredY), workArea.y + workArea.height - height - 44);
  return { width, height, x, y };
};

const showOverlayWindow = () => {
  if (!overlayEnabled) return overlayState();
  const window = createOverlayWindow();
  if (!window.isVisible()) {
    window.showInactive();
  }
  window.webContents.send("overlay:state", overlayState());
  return broadcastOverlayState();
};

const hideOverlayWindow = () => {
  if (overlayWindow && !overlayWindow.isDestroyed() && overlayWindow.isVisible()) {
    overlayWindow.hide();
  }
  return broadcastOverlayState();
};

const createOverlayWindow = () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) return overlayWindow;
  const bounds = overlayBounds();
  overlayWindow = new BrowserWindow({
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
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  overlayWindow.setIgnoreMouseEvents(true);
  overlayWindow.setAlwaysOnTop(true, "floating");
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  overlayWindow.on("closed", () => {
    overlayWindow = null;
    broadcastOverlayState();
  });
  overlayWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription) => {
    console.error("[ReiLink] overlay renderer failed to load", { errorCode, errorDescription });
  });
  void overlayWindow.loadURL(overlayRendererUrl()).then(() => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.webContents.send("overlay:state", overlayState());
      if (overlayEnabled) {
        overlayWindow.showInactive();
        broadcastOverlayState();
      }
    }
  });
  return overlayWindow;
};

const setOverlayEnabled = (enabled: boolean) => {
  overlayEnabled = enabled;
  return enabled ? showOverlayWindow() : hideOverlayWindow();
};

const updateOverlayContent = (content: OverlayContentUpdate) => {
  const nextMessage = createOverlayMessage(content, `overlay-${Date.now()}`);
  overlayMessages = [...overlayMessages, nextMessage].slice(-3);
  overlayUpdatedAt = nextMessage.timestamp;
  if (overlayEnabled) {
    const window = createOverlayWindow();
    window.webContents.send("overlay:state", overlayState());
    if (!window.isVisible()) window.showInactive();
  }
  return broadcastOverlayState();
};

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1120,
    height: 780,
    minWidth: 900,
    minHeight: 640,
    backgroundColor: "#111318",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  mainWindow = win;

  win.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    console.error("[ReiLink] renderer failed to load", {
      errorCode,
      errorDescription,
      validatedURL
    });
  });

  win.webContents.on("render-process-gone", (_event, details) => {
    console.error("[ReiLink] renderer process gone", details);
  });

  win.on("closed", () => {
    if (mainWindow === win) mainWindow = null;
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.close();
    }
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL ?? "http://127.0.0.1:5173";
  if (isDevRenderer()) {
    console.log("[ReiLink] loading dev renderer", devUrl);
    win.loadURL(devUrl);
  } else {
    const rendererUrl = `${APP_PROTOCOL}://./index.html`;
    console.log("[ReiLink] loading packaged renderer", rendererUrl);
    win.loadURL(rendererUrl);
  }
};

app.whenReady().then(() => {
  registerPackagedRendererProtocol();
  backendRuntime = new BackendRuntimeManager({
    appUserDataPath: app.getPath("userData"),
    compiledMainDir: __dirname,
    isPackaged: !isDevRenderer()
  });
  backendRuntime.onStatusChange((status) => {
    for (const window of BrowserWindow.getAllWindows()) {
      window.webContents.send("backend-runtime:status", status);
    }
  });
  ipcMain.handle("backend-runtime:get-status", () => backendRuntime?.getStatus());
  ipcMain.handle("backend-runtime:set-auto-start", (_event, enabled: boolean) =>
    backendRuntime?.setAutoStartEnabled(Boolean(enabled))
  );
  ipcMain.handle("local-data:open-dir", () => openLocalDataDir(app.getPath("userData"), shell));
  ipcMain.handle("overlay:get-status", () => overlayState());
  ipcMain.handle("overlay:set-enabled", (_event, enabled: boolean) => setOverlayEnabled(Boolean(enabled)));
  ipcMain.handle("overlay:update-content", (_event, content: OverlayContentUpdate) => updateOverlayContent(content));
  void backendRuntime.ensureBackend();
  createWindow();
});

app.on("before-quit", () => {
  void backendRuntime?.stopStartedBackend();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (!mainWindow || mainWindow.isDestroyed()) createWindow();
});
