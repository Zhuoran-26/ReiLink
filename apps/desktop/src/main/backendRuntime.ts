import { spawn } from "node:child_process";
import { constants } from "node:fs";
import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import { createConnection } from "node:net";
import os from "node:os";
import path from "node:path";

import type { BackendRuntimeState, BackendRuntimeStatus } from "../shared/runtime.js";

type BackendRuntimeConfig = {
  backend_auto_start_enabled?: boolean;
};

type RuntimeLogger = Pick<Console, "error" | "log" | "warn">;
type BackendRuntimeMode = "auto" | "binary" | "repo";
type BackendStartedFrom = BackendRuntimeStatus["backend_started_from"];
type BinaryStartedFrom = Extract<BackendStartedFrom, "configured_binary" | "bundled_binary">;
type KnowledgeSource = BackendRuntimeStatus["knowledge_source"];

type BackendChildProcess = {
  killed?: boolean;
  kill: (signal?: NodeJS.Signals | number) => boolean;
  once: (event: "exit", listener: (code: number | null, signal: NodeJS.Signals | null) => void) => unknown;
  on: (event: "error", listener: (error: Error) => void) => unknown;
  pid?: number;
  stdout?: {
    on: (event: "data", listener: (chunk: Buffer | string) => void) => unknown;
  } | null;
  stderr?: {
    on: (event: "data", listener: (chunk: Buffer | string) => void) => unknown;
  } | null;
};

type SpawnBackend = (command: string, args: string[], options: Parameters<typeof spawn>[2]) => BackendChildProcess;

type HealthCheckResult = {
  ok: boolean;
  error?: string;
  statusCode?: number;
};

type BackendStartRuntime = {
  args: string[];
  backendDir: string | null;
  binaryPath: string | null;
  command: string;
  cwd: string;
  knowledgeDir: string | null;
  knowledgeSource: KnowledgeSource;
  projectRoot: string | null;
  pythonPath: string | null;
  resourceDir: string | null;
  source: Exclude<BackendStartedFrom, "external" | "none">;
  userDataDir: string;
};

type BackendRepoResolution =
  | (BackendStartRuntime & { source: "repo"; status: "ready" })
  | {
      backendDir: string | null;
      message: string;
      projectRoot: string | null;
      pythonPath: string | null;
      status: "missing_project_root" | "missing_venv";
    };

type BackendBinaryCandidate = {
  path: string;
  source: BinaryStartedFrom;
};

type BackendBinaryCandidateInput = string | BackendBinaryCandidate;

type BackendBinaryResolution =
  | (BackendStartRuntime & { source: BinaryStartedFrom; status: "ready" })
  | {
      binaryPath: string | null;
      message: string;
      status: "not_found";
    };

export type BackendRuntimeManagerOptions = {
  appUserDataPath: string;
  backendBinaryCandidates?: BackendBinaryCandidateInput[];
  compiledMainDir: string;
  cwd?: string;
  env?: NodeJS.ProcessEnv;
  fetchImpl?: typeof fetch;
  healthUrl?: string;
  homeDir?: string;
  isPackaged?: boolean;
  logger?: RuntimeLogger;
  portOpenCheck?: (host: string, port: number) => Promise<boolean>;
  repoRootCandidates?: string[];
  resourcesPath?: string;
  spawnBackend?: SpawnBackend;
  startupAttempts?: number;
  startupIntervalMs?: number;
};

const DEFAULT_HEALTH_URL = "http://127.0.0.1:8000/api/health";
const PROJECT_ROOT_NOT_FOUND_MESSAGE =
  "未找到 ReiLink 项目目录，请设置 REILINK_PROJECT_ROOT 或手动运行 make dev-backend。";
const BACKEND_BINARY_NOT_FOUND_MESSAGE = "未找到 backend binary，已回退到本地源码后端。";
const BACKEND_BINARY_ONLY_NOT_FOUND_MESSAGE = "未找到 backend binary，请设置 REILINK_BACKEND_BINARY 或改用 auto/repo 模式。";
const BACKEND_VENV_NOT_FOUND_MESSAGE =
  "未找到 backend venv，请先创建 services/backend/.venv 或手动运行 make dev-backend。";
const BACKEND_START_FAILED_MESSAGE = "后端启动失败，请在项目目录运行 make dev-backend。";
const BACKEND_HEALTH_TIMEOUT_MESSAGE = "后端启动超时，请查看 Electron main process 日志或手动运行 make dev-backend。";
const BACKEND_PORT_OCCUPIED_MESSAGE = "端口 8000 已被占用，但不是可用的 ReiLink backend。";
const AUTO_START_DISABLED_MESSAGE = "自动启动已关闭，请手动运行 make dev-backend。";
const BACKEND_EXITED_MESSAGE = "本地后端进程已退出。";
const MAX_BACKEND_LOG_LINES_PER_STREAM = 20;

const createDefaultStatus = (
  appMode: "dev" | "packaged",
  healthUrl: string,
  runtimeMode: BackendRuntimeMode,
  userDataDir: string,
  bundledBackendBinaryPath: string | null
): BackendRuntimeStatus => ({
  backend_auto_start_enabled: true,
  backend_app_mode: appMode,
  backend_binary_exists: false,
  backend_binary_path: null,
  bundled_backend_binary_path: bundledBackendBinaryPath,
  bundled_backend_exists: false,
  backend_started_by_app: false,
  backend_started_from: "none",
  backend_start_error: null,
  backend_status: "checking",
  backend_runtime_mode: runtimeMode,
  backend_project_root: null,
  backend_root: null,
  backend_python_path: null,
  backend_health_url: healthUrl,
  backend_retry_count: 0,
  knowledge_path: null,
  knowledge_source: "missing",
  user_data_dir: userDataDir
});

export class BackendRuntimeManager {
  private readonly appMode: "dev" | "packaged";
  private readonly appUserDataPath: string;
  private readonly backendBinaryCandidates: BackendBinaryCandidate[];
  private readonly backendRuntimeMode: BackendRuntimeMode;
  private readonly compiledMainDir: string;
  private readonly cwd: string;
  private readonly env: NodeJS.ProcessEnv;
  private readonly fetchImpl: typeof fetch;
  private readonly healthUrl: string;
  private readonly homeDir: string;
  private readonly logger: RuntimeLogger;
  private readonly portOpenCheck: (host: string, port: number) => Promise<boolean>;
  private readonly repoRootCandidates: string[];
  private readonly resourcesPath: string;
  private readonly spawnBackend: SpawnBackend;
  private readonly startupAttempts: number;
  private readonly startupIntervalMs: number;
  private readonly userDataDir: string;
  private readonly listeners = new Set<(status: BackendRuntimeStatus) => void>();
  private backendLogLines = { stderr: 0, stdout: 0 };
  private child: BackendChildProcess | null = null;
  private ensurePromise: Promise<BackendRuntimeStatus> | null = null;
  private spawnErrorMessage: string | null = null;
  private status: BackendRuntimeStatus;

  constructor(options: BackendRuntimeManagerOptions) {
    this.appUserDataPath = options.appUserDataPath;
    this.compiledMainDir = options.compiledMainDir;
    this.cwd = options.cwd ?? process.cwd();
    this.env = options.env ?? process.env;
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.healthUrl = options.healthUrl ?? DEFAULT_HEALTH_URL;
    this.homeDir = options.homeDir ?? os.homedir();
    this.logger = options.logger ?? console;
    this.portOpenCheck = options.portOpenCheck ?? isTcpPortOpen;
    this.appMode = options.isPackaged ? "packaged" : "dev";
    this.backendRuntimeMode = normalizeRuntimeMode(this.env.REILINK_BACKEND_RUNTIME);
    this.resourcesPath = options.resourcesPath ?? getElectronResourcesPath();
    this.userDataDir = path.join(this.appUserDataPath, "data");
    this.repoRootCandidates = uniquePaths(options.repoRootCandidates ?? this.defaultRepoRootCandidates());
    this.backendBinaryCandidates = normalizeBackendBinaryCandidates(
      options.backendBinaryCandidates ?? this.defaultBackendBinaryCandidates()
    );
    this.spawnBackend = options.spawnBackend ?? ((command, args, spawnOptions) => spawn(command, args, spawnOptions));
    this.startupAttempts = options.startupAttempts ?? 60;
    this.startupIntervalMs = options.startupIntervalMs ?? 500;
    this.status = createDefaultStatus(
      this.appMode,
      this.healthUrl,
      this.backendRuntimeMode,
      this.userDataDir,
      this.defaultBundledBackendBinaryPath()
    );
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
    this.logRuntime("auto-start setting changed", { enabled });
    this.updateStatus({ backend_auto_start_enabled: enabled });
    if (enabled) {
      return this.ensureBackend();
    }
    if (this.status.backend_status !== "connected" && this.status.backend_status !== "external_backend_detected") {
      this.updateStatus({
        backend_started_by_app: Boolean(this.child),
        backend_started_from: this.child ? this.status.backend_started_from : "none",
        backend_start_error: AUTO_START_DISABLED_MESSAGE,
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
    if (!child) {
      this.logRuntime("quit requested; no app-started backend to stop");
      return;
    }
    this.logRuntime("stopping app-started backend", { source: this.status.backend_started_from });
    this.child = null;
    terminateBackendProcess(child, "SIGTERM");
    setTimeout(() => {
      if (!child.killed) terminateBackendProcess(child, "SIGKILL");
    }, 2500).unref?.();
  }

  private async ensureBackendInternal(): Promise<BackendRuntimeStatus> {
    const config = await this.loadConfig();
    const autoStartEnabled = config.backend_auto_start_enabled !== false;
    const bundledBackendBinaryPath = this.defaultBundledBackendBinaryPath();
    const bundledBackendExists = Boolean(
      bundledBackendBinaryPath && (await pathExists(bundledBackendBinaryPath, constants.X_OK))
    );
    const initialKnowledge = await this.resolveKnowledgeRuntime(null);
    this.logRuntime("ensure backend", {
      appMode: this.appMode,
      autoStartEnabled,
      binaryCandidates: this.backendBinaryCandidates,
      bundledBackendBinaryPath,
      bundledBackendExists,
      healthUrl: this.healthUrl,
      knowledgeSource: initialKnowledge.source,
      repoRootCandidates: this.repoRootCandidates,
      runtimeMode: this.backendRuntimeMode
    });
    this.updateStatus({
      backend_auto_start_enabled: autoStartEnabled,
      bundled_backend_binary_path: bundledBackendBinaryPath,
      bundled_backend_exists: bundledBackendExists,
      knowledge_path: initialKnowledge.dir,
      knowledge_source: initialKnowledge.source,
      backend_retry_count: 0,
      backend_start_error: null,
      backend_status: "checking"
    });

    const initialHealth = await this.checkBackendHealth("initial");
    if (initialHealth.ok) {
      this.logRuntime("external backend detected", { healthUrl: this.healthUrl });
      this.updateStatus({
        backend_started_by_app: false,
        backend_started_from: "external",
        backend_start_error: null,
        backend_status: "external_backend_detected"
      });
      return this.getStatus();
    }

    if (await this.isHealthPortOpen()) {
      this.logRuntime("port occupied by non-ReiLink backend", {
        healthUrl: this.healthUrl,
        statusCode: initialHealth.statusCode
      });
      this.updateStatus({
        backend_started_by_app: false,
        backend_started_from: "none",
        backend_start_error: BACKEND_PORT_OCCUPIED_MESSAGE,
        backend_status: "port_occupied"
      });
      return this.getStatus();
    }

    if (!autoStartEnabled) {
      this.logRuntime("auto-start disabled; not spawning backend");
      this.updateStatus({
        backend_started_by_app: false,
        backend_started_from: "none",
        backend_start_error: AUTO_START_DISABLED_MESSAGE,
        backend_status: "disabled"
      });
      return this.getStatus();
    }

    if (this.backendRuntimeMode !== "repo") {
      const binary = await this.resolveBackendBinary();
      if (binary.status === "ready") {
        const result = await this.tryStartRuntime(binary);
        if (result.backend_status === "connected" || this.backendRuntimeMode === "binary") return result;
        this.logRuntime("binary backend failed; trying repo fallback", {
          binaryPath: binary.binaryPath,
          status: result.backend_status,
          startError: result.backend_start_error
        });
      } else {
        this.logRuntime("backend binary missing", binary);
        this.updateStatus({
          backend_binary_exists: false,
          backend_binary_path: binary.binaryPath,
          backend_start_error: this.backendRuntimeMode === "binary" ? BACKEND_BINARY_ONLY_NOT_FOUND_MESSAGE : BACKEND_BINARY_NOT_FOUND_MESSAGE
        });
        if (this.backendRuntimeMode === "binary") {
          this.updateStatus({
            backend_started_by_app: false,
            backend_started_from: "none",
            backend_status: "not_found"
          });
          return this.getStatus();
        }
      }
    }

    const repoRuntime = await this.resolveRepoBackendRuntime();
    if (repoRuntime.status !== "ready") {
      this.logRuntime("repo backend runtime missing", repoRuntime);
      this.updateStatus({
        backend_project_root: repoRuntime.projectRoot,
        backend_python_path: repoRuntime.pythonPath,
        backend_root: repoRuntime.backendDir,
        backend_started_by_app: false,
        backend_started_from: "none",
        backend_start_error: repoRuntime.message,
        backend_status: repoRuntime.status
      });
      return this.getStatus();
    }

    return this.tryStartRuntime(repoRuntime);
  }

  private async tryStartRuntime(runtime: BackendStartRuntime): Promise<BackendRuntimeStatus> {
    await this.ensureWritableDataDirs(runtime.userDataDir);
    this.updateStatus({
      backend_binary_exists:
        runtime.source === "configured_binary" || runtime.source === "bundled_binary" ? true : this.status.backend_binary_exists,
      backend_binary_path: runtime.binaryPath ?? this.status.backend_binary_path,
      bundled_backend_exists:
        runtime.source === "bundled_binary" ? true : this.status.bundled_backend_exists,
      backend_project_root: runtime.projectRoot,
      knowledge_path: runtime.knowledgeDir,
      knowledge_source: runtime.knowledgeSource,
      backend_python_path: runtime.pythonPath,
      backend_root: runtime.backendDir,
      backend_started_by_app: true,
      backend_started_from: runtime.source,
      backend_start_error: null,
      backend_status: "starting",
      user_data_dir: runtime.userDataDir
    });
    if (!this.startBackend(runtime)) {
      this.updateStatus({
        backend_started_by_app: false,
        backend_started_from: "none",
        backend_start_error: this.spawnErrorMessage ?? BACKEND_START_FAILED_MESSAGE,
        backend_status: "spawn_failed"
      });
      return this.getStatus();
    }

    const waitResult = await this.waitForHealthyBackend();
    if (waitResult === "healthy") {
      this.logRuntime("app-started backend connected", {
        retryCount: this.status.backend_retry_count,
        source: runtime.source
      });
      this.updateStatus({
        backend_started_by_app: true,
        backend_started_from: runtime.source,
        backend_start_error: null,
        backend_status: "connected"
      });
      return this.getStatus();
    }

    if (waitResult === "spawn_failed") {
      await this.stopStartedBackend();
      this.updateStatus({
        backend_started_by_app: false,
        backend_started_from: "none",
        backend_start_error: this.spawnErrorMessage ?? BACKEND_START_FAILED_MESSAGE,
        backend_status: "spawn_failed"
      });
      return this.getStatus();
    }

    await this.stopStartedBackend();
    this.logRuntime("backend health timeout", {
      healthUrl: this.healthUrl,
      retryCount: this.status.backend_retry_count,
      source: runtime.source
    });
    this.updateStatus({
      backend_started_by_app: false,
      backend_started_from: "none",
      backend_start_error: BACKEND_HEALTH_TIMEOUT_MESSAGE,
      backend_status: "health_timeout"
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

  private async checkBackendHealth(label: string): Promise<HealthCheckResult> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);
    try {
      const response = await this.fetchImpl(this.healthUrl, { signal: controller.signal });
      const result = { ok: response.ok, statusCode: response.status };
      this.logRuntime("health check", { label, ok: result.ok, statusCode: result.statusCode, url: this.healthUrl });
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.logRuntime("health check failed", { error: message, label, url: this.healthUrl });
      return { ok: false, error: message };
    } finally {
      clearTimeout(timeout);
    }
  }

  private async waitForHealthyBackend(): Promise<"healthy" | "spawn_failed" | "timeout"> {
    for (let attempt = 1; attempt <= this.startupAttempts; attempt += 1) {
      if (this.spawnErrorMessage) return "spawn_failed";
      this.updateStatus({ backend_retry_count: attempt });
      const health = await this.checkBackendHealth(`startup-${attempt}`);
      if (health.ok) return "healthy";
      await sleep(this.startupIntervalMs);
    }
    return this.spawnErrorMessage ? "spawn_failed" : "timeout";
  }

  private async isHealthPortOpen(): Promise<boolean> {
    const healthUrl = new URL(this.healthUrl);
    const port = Number(healthUrl.port || (healthUrl.protocol === "https:" ? 443 : 80));
    return this.portOpenCheck(healthUrl.hostname, port);
  }

  private async resolveBackendBinary(): Promise<BackendBinaryResolution> {
    for (const candidate of this.backendBinaryCandidates) {
      if (!(await pathExists(candidate.path, constants.X_OK))) continue;
      const projectRoot = await this.resolveProjectRoot();
      const knowledge = await this.resolveKnowledgeRuntime(projectRoot);
      const resourceDir = await this.resolveResourceRuntime(projectRoot);
      this.logRuntime("resolved backend binary", { binaryPath: candidate.path, projectRoot, resourceDir, source: candidate.source });
      return {
        args: [],
        backendDir: null,
        binaryPath: candidate.path,
        command: candidate.path,
        cwd: path.dirname(candidate.path),
        knowledgeDir: knowledge.dir,
        knowledgeSource: knowledge.source,
        projectRoot,
        pythonPath: null,
        resourceDir,
        source: candidate.source,
        userDataDir: this.userDataDir,
        status: "ready"
      };
    }
    return {
      binaryPath: this.backendBinaryCandidates[0]?.path ?? null,
      message: this.backendRuntimeMode === "binary" ? BACKEND_BINARY_ONLY_NOT_FOUND_MESSAGE : BACKEND_BINARY_NOT_FOUND_MESSAGE,
      status: "not_found"
    };
  }

  private async resolveRepoBackendRuntime(): Promise<BackendRepoResolution> {
    this.logRuntime("resolving repo backend runtime", { candidates: this.repoRootCandidates });
    const projectRoot = await this.resolveProjectRoot();
    if (!projectRoot) {
      return {
        backendDir: null,
        message: PROJECT_ROOT_NOT_FOUND_MESSAGE,
        projectRoot: null,
        pythonPath: null,
        status: "missing_project_root"
      };
    }

    const backendDir = path.join(projectRoot, "services", "backend");
    const pythonPath = path.join(backendDir, ".venv", os.platform() === "win32" ? "Scripts/python.exe" : "bin/python");
    this.logRuntime("resolved repo backend paths", {
      backendDir,
      cwd: backendDir,
      pythonPath
    });
    if (!(await pathExists(pythonPath))) {
      return {
        backendDir,
        message: BACKEND_VENV_NOT_FOUND_MESSAGE,
        projectRoot,
        pythonPath,
        status: "missing_venv"
      };
    }
    const knowledge = await this.resolveKnowledgeRuntime(projectRoot);
    const resourceDir = await this.resolveResourceRuntime(projectRoot);
    return {
      args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      backendDir,
      binaryPath: null,
      command: pythonPath,
      cwd: backendDir,
      knowledgeDir: knowledge.dir,
      knowledgeSource: knowledge.source,
      projectRoot,
      pythonPath,
      resourceDir,
      source: "repo",
      userDataDir: this.userDataDir,
      status: "ready"
    };
  }

  private async resolveProjectRoot(): Promise<string | null> {
    for (const candidate of this.repoRootCandidates) {
      const repoRoot = await findRepoRoot(candidate);
      if (!repoRoot) continue;
      this.logRuntime("resolved project root", { candidate, projectRoot: repoRoot });
      return repoRoot;
    }
    return null;
  }

  private startBackend(runtime: BackendStartRuntime) {
    if (this.child) {
      this.logRuntime("backend child already exists; not spawning another");
      return true;
    }
    this.backendLogLines = { stderr: 0, stdout: 0 };
    this.spawnErrorMessage = null;
    this.logRuntime("spawning backend", {
      args: runtime.args,
      command: runtime.command,
      cwd: runtime.cwd,
      source: runtime.source
    });
    try {
      const env = { ...this.env };
      if (runtime.projectRoot && !env.REILINK_PROJECT_ROOT) {
        env.REILINK_PROJECT_ROOT = runtime.projectRoot;
      }
      env.REILINK_DATA_DIR = runtime.userDataDir;
      if (runtime.knowledgeDir) {
        env.REILINK_KNOWLEDGE_DIR = runtime.knowledgeDir;
      }
      if (runtime.resourceDir) {
        env.REILINK_RESOURCE_DIR = runtime.resourceDir;
      }
      this.child = this.spawnBackend(runtime.command, runtime.args, {
        cwd: runtime.cwd,
        detached: process.platform !== "win32",
        env,
        stdio: "pipe",
        windowsHide: true
      });
    } catch (error) {
      this.spawnErrorMessage = `${BACKEND_START_FAILED_MESSAGE} ${error instanceof Error ? error.message : String(error)}`;
      this.logRuntime("spawn threw", { error: this.spawnErrorMessage });
      return false;
    }
    this.child.stdout?.on("data", (chunk) => this.logBackendOutput("stdout", chunk));
    this.child.stderr?.on("data", (chunk) => this.logBackendOutput("stderr", chunk));
    this.child.on("error", (error) => {
      this.spawnErrorMessage = `${BACKEND_START_FAILED_MESSAGE} ${error.message}`;
      this.logger.error("[ReiLink backend runtime] spawn error", sanitizeLogText(error.message));
      this.updateStatus({
        backend_started_by_app: false,
        backend_started_from: "none",
        backend_start_error: this.spawnErrorMessage,
        backend_status: "spawn_failed"
      });
    });
    this.child.once("exit", (code, signal) => {
      this.logRuntime("backend process exited", { code, signal, source: runtime.source });
      this.child = null;
      if (this.status.backend_status === "connected" || this.status.backend_status === "starting") {
        this.spawnErrorMessage = this.status.backend_status === "starting" ? BACKEND_START_FAILED_MESSAGE : this.spawnErrorMessage;
        this.updateStatus({
          backend_started_by_app: false,
          backend_started_from: "none",
          backend_start_error: this.status.backend_status === "starting" ? BACKEND_START_FAILED_MESSAGE : BACKEND_EXITED_MESSAGE,
          backend_status: this.status.backend_status === "starting" ? "spawn_failed" : "disconnected"
        });
      }
    });
    return true;
  }

  private logBackendOutput(stream: "stderr" | "stdout", chunk: Buffer | string) {
    const text = sanitizeLogText(String(chunk)).trim();
    if (!text || this.backendLogLines[stream] >= MAX_BACKEND_LOG_LINES_PER_STREAM) return;
    const lines = text.split(/\r?\n/).filter(Boolean);
    for (const line of lines) {
      if (this.backendLogLines[stream] >= MAX_BACKEND_LOG_LINES_PER_STREAM) return;
      this.backendLogLines[stream] += 1;
      const level = stream === "stderr" ? "warn" : "log";
      this.logger[level](`[ReiLink backend ${stream}] ${line}`);
    }
  }

  private updateStatus(patch: Partial<BackendRuntimeStatus>) {
    this.status = { ...this.status, ...patch };
    const snapshot = this.getStatus();
    this.logRuntime("status", {
      startedByApp: snapshot.backend_started_by_app,
      startedFrom: snapshot.backend_started_from,
      status: snapshot.backend_status,
      knowledgeSource: snapshot.knowledge_source,
      retryCount: snapshot.backend_retry_count,
      startError: snapshot.backend_start_error
    });
    for (const listener of this.listeners) listener(snapshot);
  }

  private defaultRepoRootCandidates(): string[] {
    return [
      this.env.REILINK_PROJECT_ROOT ?? "",
      this.env.REILINK_REPO_ROOT ?? "",
      this.cwd,
      this.compiledMainDir,
      this.resourcesPath,
      path.join(this.homeDir, "Desktop", "ReiLink"),
      path.join(this.homeDir, "ReiLink")
    ];
  }

  private defaultBackendBinaryCandidates(): BackendBinaryCandidate[] {
    const binaryName = os.platform() === "win32" ? "reilink-backend.exe" : "reilink-backend";
    const candidates: BackendBinaryCandidate[] = [];
    if (this.env.REILINK_BACKEND_BINARY) {
      candidates.push({ path: this.env.REILINK_BACKEND_BINARY, source: "configured_binary" });
    }
    const bundledPath = this.defaultBundledBackendBinaryPath(binaryName);
    if (bundledPath) candidates.push({ path: bundledPath, source: "bundled_binary" });
    return candidates;
  }

  private defaultBundledBackendBinaryPath(binaryName = os.platform() === "win32" ? "reilink-backend.exe" : "reilink-backend"): string | null {
    if (this.resourcesPath) return path.join(this.resourcesPath, "backend", binaryName);
    return path.resolve(this.compiledMainDir, "..", "..", "..", "backend", binaryName);
  }

  private defaultBundledKnowledgeGamesDir(): string | null {
    if (this.resourcesPath) return path.join(this.resourcesPath, "knowledge", "games");
    return path.resolve(this.compiledMainDir, "..", "..", "..", "knowledge", "games");
  }

  private async resolveKnowledgeRuntime(projectRoot: string | null): Promise<{ dir: string | null; source: KnowledgeSource }> {
    const bundledKnowledge = this.defaultBundledKnowledgeGamesDir();
    if (bundledKnowledge && (await pathExists(path.join(bundledKnowledge, "catalog.json")))) {
      return { dir: bundledKnowledge, source: "bundled" };
    }
    if (projectRoot) {
      const repoKnowledge = path.join(projectRoot, "data", "knowledge", "games");
      if (await pathExists(path.join(repoKnowledge, "catalog.json"))) {
        return { dir: repoKnowledge, source: "repo" };
      }
    }
    return { dir: null, source: "missing" };
  }

  private async resolveResourceRuntime(projectRoot: string | null): Promise<string | null> {
    if (this.resourcesPath && (await pathExists(path.join(this.resourcesPath, "personas", "rei_like.json")))) {
      return this.resourcesPath;
    }
    if (projectRoot) {
      const repoData = path.join(projectRoot, "data");
      if (await pathExists(path.join(repoData, "personas", "rei_like.json"))) {
        return repoData;
      }
    }
    return null;
  }

  private async ensureWritableDataDirs(userDataDir: string): Promise<void> {
    await Promise.all(
      ["", "memory", "session", "settings", "logs", "conversations"].map((child) =>
        mkdir(path.join(userDataDir, child), { recursive: true })
      )
    );
  }

  private logRuntime(message: string, details?: Record<string, unknown>) {
    const suffix = details ? ` ${sanitizeLogText(JSON.stringify(details))}` : "";
    this.logger.log(`[ReiLink backend runtime] ${message}${suffix}`);
  }
}

async function findRepoRoot(startPath: string): Promise<string | null> {
  let current = path.resolve(startPath);
  while (true) {
    if (await pathExists(path.join(current, "data", "knowledge", "games", "catalog.json"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

async function isTcpPortOpen(host: string, port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = createConnection({ host, port });
    const finish = (open: boolean) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(open);
    };
    socket.setTimeout(500);
    socket.once("connect", () => finish(true));
    socket.once("error", () => finish(false));
    socket.once("timeout", () => finish(false));
  });
}

async function pathExists(target: string, mode: number = constants.F_OK): Promise<boolean> {
  try {
    await access(target, mode);
    return true;
  } catch {
    return false;
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function terminateBackendProcess(child: BackendChildProcess, signal: NodeJS.Signals): boolean {
  if (process.platform !== "win32" && child.pid) {
    try {
      process.kill(-child.pid, signal);
      return true;
    } catch {
      return child.kill(signal);
    }
  }
  return child.kill(signal);
}

function sanitizeLogText(text: string): string {
  return text
    .replace(/(DEEPSEEK_API_KEY|OPENAI_API_KEY)\s*=\s*([^\s",}]+)/gi, "$1=<redacted>")
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer <redacted>");
}

function uniquePaths(paths: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const candidate of paths.filter(Boolean)) {
    const resolved = path.resolve(candidate);
    if (seen.has(resolved)) continue;
    seen.add(resolved);
    result.push(resolved);
  }
  return result;
}

function normalizeBackendBinaryCandidates(candidates: BackendBinaryCandidateInput[]): BackendBinaryCandidate[] {
  const seen = new Set<string>();
  const result: BackendBinaryCandidate[] = [];
  for (const candidate of candidates) {
    const rawPath = typeof candidate === "string" ? candidate : candidate.path;
    if (!rawPath) continue;
    const resolved = path.resolve(rawPath);
    if (seen.has(resolved)) continue;
    seen.add(resolved);
    result.push({
      path: resolved,
      source: typeof candidate === "string" ? "configured_binary" : candidate.source
    });
  }
  return result;
}

function normalizeRuntimeMode(value: string | undefined): BackendRuntimeMode {
  const normalized = String(value || "auto").trim().toLowerCase();
  if (normalized === "binary" || normalized === "repo") return normalized;
  return "auto";
}

function getElectronResourcesPath() {
  const maybeProcess = process as NodeJS.Process & { resourcesPath?: string };
  return maybeProcess.resourcesPath ?? "";
}

export const backendRuntimeMessage = {
  autoStartDisabled: AUTO_START_DISABLED_MESSAGE,
  binaryMissing: BACKEND_BINARY_NOT_FOUND_MESSAGE,
  binaryOnlyMissing: BACKEND_BINARY_ONLY_NOT_FOUND_MESSAGE,
  healthTimeout: BACKEND_HEALTH_TIMEOUT_MESSAGE,
  missingProjectRoot: PROJECT_ROOT_NOT_FOUND_MESSAGE,
  missingVenv: BACKEND_VENV_NOT_FOUND_MESSAGE,
  portOccupied: BACKEND_PORT_OCCUPIED_MESSAGE,
  startFailed: BACKEND_START_FAILED_MESSAGE
} satisfies Record<string, string>;

export type { BackendRuntimeState, BackendRuntimeStatus };
