import { spawn } from "node:child_process";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import os from "node:os";
import path from "node:path";

import type { BackendRuntimeStatus, BackendRuntimeState } from "../shared/runtime.js";

type BackendRuntimeConfig = {
  backend_auto_start_enabled?: boolean;
};

type RuntimeLogger = Pick<Console, "error" | "log" | "warn">;

type BackendChildProcess = {
  killed?: boolean;
  kill: (signal?: NodeJS.Signals | number) => boolean;
  once: (event: "exit", listener: (code: number | null, signal: NodeJS.Signals | null) => void) => unknown;
  on: (event: "error", listener: (error: Error) => void) => unknown;
  stdout?: {
    on: (event: "data", listener: (chunk: Buffer | string) => void) => unknown;
  } | null;
  stderr?: {
    on: (event: "data", listener: (chunk: Buffer | string) => void) => unknown;
  } | null;
};

type SpawnBackend = (command: string, args: string[], options: Parameters<typeof spawn>[2]) => BackendChildProcess;

export type BackendRuntimeManagerOptions = {
  appUserDataPath: string;
  compiledMainDir: string;
  env?: NodeJS.ProcessEnv;
  fetchImpl?: typeof fetch;
  healthUrl?: string;
  logger?: RuntimeLogger;
  repoRootCandidates?: string[];
  spawnBackend?: SpawnBackend;
  startupAttempts?: number;
  startupIntervalMs?: number;
};

const DEFAULT_STATUS: BackendRuntimeStatus = {
  backend_auto_start_enabled: true,
  backend_started_by_app: false,
  backend_start_error: null,
  backend_status: "checking"
};

const BACKEND_NOT_FOUND_MESSAGE = "未找到本地后端，请先在项目目录运行 make dev-backend。";
const BACKEND_START_FAILED_MESSAGE = "本地后端启动失败，请在项目目录运行 make dev-backend。";

export class BackendRuntimeManager {
  private readonly appUserDataPath: string;
  private readonly compiledMainDir: string;
  private readonly env: NodeJS.ProcessEnv;
  private readonly fetchImpl: typeof fetch;
  private readonly healthUrl: string;
  private readonly logger: RuntimeLogger;
  private readonly repoRootCandidates: string[];
  private readonly spawnBackend: SpawnBackend;
  private readonly startupAttempts: number;
  private readonly startupIntervalMs: number;
  private readonly listeners = new Set<(status: BackendRuntimeStatus) => void>();
  private child: BackendChildProcess | null = null;
  private ensurePromise: Promise<BackendRuntimeStatus> | null = null;
  private status: BackendRuntimeStatus = { ...DEFAULT_STATUS };

  constructor(options: BackendRuntimeManagerOptions) {
    this.appUserDataPath = options.appUserDataPath;
    this.compiledMainDir = options.compiledMainDir;
    this.env = options.env ?? process.env;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.healthUrl = options.healthUrl ?? "http://127.0.0.1:8000/api/health";
    this.logger = options.logger ?? console;
    this.repoRootCandidates = options.repoRootCandidates ?? [
      this.env.REILINK_REPO_ROOT ?? "",
      process.cwd(),
      this.compiledMainDir
    ];
    this.spawnBackend = options.spawnBackend ?? ((command, args, spawnOptions) => spawn(command, args, spawnOptions));
    this.startupAttempts = options.startupAttempts ?? 40;
    this.startupIntervalMs = options.startupIntervalMs ?? 500;
  }

  getStatus(): BackendRuntimeStatus {
    return { ...this.status };
  }

  onStatusChange(listener: (status: BackendRuntimeStatus) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  async setAutoStartEnabled(enabled: boolean): Promise<BackendRuntimeStatus> {
    await this.saveConfig({ backend_auto_start_enabled: enabled });
    this.updateStatus({ backend_auto_start_enabled: enabled });
    if (enabled) {
      return this.ensureBackend();
    }
    if (this.status.backend_status !== "connected") {
      this.updateStatus({
        backend_started_by_app: Boolean(this.child),
        backend_start_error: "自动启动本地后端已关闭，请手动运行 make dev-backend。",
        backend_status: "disabled"
      });
    }
    return this.getStatus();
  }

  async ensureBackend(): Promise<BackendRuntimeStatus> {
    if (this.ensurePromise) return this.ensurePromise;
    this.ensurePromise = this.ensureBackendInternal().finally(() => {
      this.ensurePromise = null;
    });
    return this.ensurePromise;
  }

  async stopStartedBackend(): Promise<void> {
    const child = this.child;
    if (!child) return;
    this.child = null;
    child.kill("SIGTERM");
    setTimeout(() => {
      if (!child.killed) child.kill("SIGKILL");
    }, 2500).unref?.();
  }

  private async ensureBackendInternal(): Promise<BackendRuntimeStatus> {
    const config = await this.loadConfig();
    const autoStartEnabled = config.backend_auto_start_enabled !== false;
    this.updateStatus({
      backend_auto_start_enabled: autoStartEnabled,
      backend_start_error: null,
      backend_status: "checking"
    });

    if (await this.isBackendHealthy()) {
      this.updateStatus({
        backend_started_by_app: Boolean(this.child),
        backend_start_error: null,
        backend_status: "connected"
      });
      return this.getStatus();
    }

    if (!autoStartEnabled) {
      this.updateStatus({
        backend_started_by_app: false,
        backend_start_error: "自动启动本地后端已关闭，请手动运行 make dev-backend。",
        backend_status: "disabled"
      });
      return this.getStatus();
    }

    const runtime = await this.resolveBackendRuntime();
    if (!runtime) {
      this.updateStatus({
        backend_started_by_app: false,
        backend_start_error: BACKEND_NOT_FOUND_MESSAGE,
        backend_status: "not_found"
      });
      return this.getStatus();
    }

    this.updateStatus({
      backend_started_by_app: true,
      backend_start_error: null,
      backend_status: "starting"
    });
    this.startBackend(runtime);

    if (await this.waitForHealthyBackend()) {
      this.updateStatus({
        backend_started_by_app: true,
        backend_start_error: null,
        backend_status: "connected"
      });
      return this.getStatus();
    }

    await this.stopStartedBackend();
    this.updateStatus({
      backend_started_by_app: false,
      backend_start_error: BACKEND_START_FAILED_MESSAGE,
      backend_status: "failed"
    });
    return this.getStatus();
  }

  private async loadConfig(): Promise<BackendRuntimeConfig> {
    try {
      const raw = JSON.parse(await readFile(this.configPath, "utf8")) as BackendRuntimeConfig;
      return typeof raw === "object" && raw ? raw : {};
    } catch {
      return {};
    }
  }

  private async saveConfig(config: BackendRuntimeConfig): Promise<void> {
    await mkdir(this.appUserDataPath, { recursive: true });
    await writeFile(this.configPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  }

  private get configPath(): string {
    return path.join(this.appUserDataPath, "runtime-settings.json");
  }

  private async isBackendHealthy(): Promise<boolean> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);
    try {
      const response = await this.fetchImpl(this.healthUrl, { signal: controller.signal });
      return response.ok;
    } catch {
      return false;
    } finally {
      clearTimeout(timeout);
    }
  }

  private async waitForHealthyBackend(): Promise<boolean> {
    for (let attempt = 0; attempt < this.startupAttempts; attempt += 1) {
      if (await this.isBackendHealthy()) return true;
      await sleep(this.startupIntervalMs);
    }
    return false;
  }

  private async resolveBackendRuntime(): Promise<{ backendDir: string; pythonPath: string } | null> {
    for (const candidate of this.repoRootCandidates.filter(Boolean)) {
      const repoRoot = await findRepoRoot(candidate);
      if (!repoRoot) continue;
      const backendDir = path.join(repoRoot, "services", "backend");
      const pythonPath = path.join(backendDir, ".venv", os.platform() === "win32" ? "Scripts/python.exe" : "bin/python");
      if (await pathExists(pythonPath)) {
        return { backendDir, pythonPath };
      }
    }
    return null;
  }

  private startBackend(runtime: { backendDir: string; pythonPath: string }) {
    if (this.child) return;
    const args = ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"];
    this.child = this.spawnBackend(runtime.pythonPath, args, {
      cwd: runtime.backendDir,
      env: { ...this.env },
      stdio: "pipe",
      windowsHide: true
    });
    this.child.stdout?.on("data", (chunk) => this.logBackendOutput("log", chunk));
    this.child.stderr?.on("data", (chunk) => this.logBackendOutput("warn", chunk));
    this.child.on("error", (error) => {
      this.logger.error("[ReiLink backend]", sanitizeLogText(error.message));
      this.updateStatus({
        backend_started_by_app: false,
        backend_start_error: BACKEND_START_FAILED_MESSAGE,
        backend_status: "failed"
      });
    });
    this.child.once("exit", () => {
      this.child = null;
      if (this.status.backend_status === "connected" || this.status.backend_status === "starting") {
        this.updateStatus({
          backend_started_by_app: false,
          backend_start_error: "本地后端进程已退出。",
          backend_status: "disconnected"
        });
      }
    });
  }

  private logBackendOutput(level: "log" | "warn", chunk: Buffer | string) {
    const text = sanitizeLogText(String(chunk)).trim();
    if (!text) return;
    this.logger[level](`[ReiLink backend] ${text}`);
  }

  private updateStatus(patch: Partial<BackendRuntimeStatus>) {
    this.status = { ...this.status, ...patch };
    const snapshot = this.getStatus();
    for (const listener of this.listeners) listener(snapshot);
  }
}

async function findRepoRoot(startPath: string): Promise<string | null> {
  let current = path.resolve(startPath);
  while (true) {
    if (await pathExists(path.join(current, "services", "backend", "app", "main.py"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

async function pathExists(target: string): Promise<boolean> {
  try {
    await access(target, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function sanitizeLogText(text: string): string {
  return text
    .replace(/(DEEPSEEK_API_KEY|OPENAI_API_KEY)\s*=\s*([^\s]+)/gi, "$1=<redacted>")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer <redacted>");
}

export const backendRuntimeMessage = {
  notFound: BACKEND_NOT_FOUND_MESSAGE,
  startFailed: BACKEND_START_FAILED_MESSAGE
} satisfies Record<string, string>;

export type { BackendRuntimeStatus, BackendRuntimeState };
