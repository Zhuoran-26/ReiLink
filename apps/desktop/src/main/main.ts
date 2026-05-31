import { app, BrowserWindow, ipcMain, net, protocol } from "electron";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

import { BackendRuntimeManager } from "./backendRuntime.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const APP_PROTOCOL = "app";
let backendRuntime: BackendRuntimeManager | null = null;
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
  const rendererRoot = path.resolve(__dirname, "../dist");
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

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1120,
    height: 780,
    minWidth: 900,
    minHeight: 640,
    backgroundColor: "#111318",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

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
    compiledMainDir: __dirname
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
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
