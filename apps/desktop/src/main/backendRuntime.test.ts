import { EventEmitter } from "node:events";
import { access, chmod, mkdtemp, mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { BackendRuntimeManager } from "./backendRuntime";

class FakeBackendProcess extends EventEmitter {
  killed = false;
  stdout = new EventEmitter();
  stderr = new EventEmitter();
  kill = vi.fn((signal?: NodeJS.Signals | number) => {
    this.killed = true;
    this.emit("exit", 0, typeof signal === "string" ? signal : null);
    return true;
  });
}

const okResponse = { ok: true, status: 200 } as Response;
const failedResponse = { ok: false, status: 500 } as Response;
const closedPortCheck = () => vi.fn(async () => false);

const createRepoRoot = async (withVenv = true) => {
  const repoRoot = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-"));
  await mkdir(path.join(repoRoot, "services", "backend", "app"), { recursive: true });
  await mkdir(path.join(repoRoot, "data", "knowledge", "games"), { recursive: true });
  await mkdir(path.join(repoRoot, "data", "personas"), { recursive: true });
  await writeFile(path.join(repoRoot, "services", "backend", "app", "main.py"), "", "utf8");
  await writeFile(path.join(repoRoot, "data", "knowledge", "games", "catalog.json"), "{\"games\":[]}\n", "utf8");
  await writeFile(path.join(repoRoot, "data", "personas", "rei_like.json"), "{}\n", "utf8");
  if (withVenv) {
    await mkdir(path.join(repoRoot, "services", "backend", ".venv", "bin"), { recursive: true });
    await writeFile(path.join(repoRoot, "services", "backend", ".venv", "bin", "python"), "", "utf8");
  }
  return repoRoot;
};

const createBundledResources = async () => {
  const resourcesPath = await mkdtemp(path.join(os.tmpdir(), "reilink-resources-"));
  const backendBinary = path.join(resourcesPath, "backend", "reilink-backend");
  const knowledgeDir = path.join(resourcesPath, "knowledge", "games");
  const personasDir = path.join(resourcesPath, "personas");
  await mkdir(path.dirname(backendBinary), { recursive: true });
  await writeFile(backendBinary, "", "utf8");
  await chmod(backendBinary, 0o755);
  await mkdir(path.join(knowledgeDir, "elden_ring"), { recursive: true });
  await writeFile(path.join(knowledgeDir, "catalog.json"), "{\"games\":[]}\n", "utf8");
  await writeFile(path.join(knowledgeDir, "elden_ring", "snippets.json"), "[]\n", "utf8");
  await mkdir(personasDir, { recursive: true });
  await writeFile(path.join(personasDir, "rei_like.json"), "{}\n", "utf8");
  return { backendBinary, knowledgeDir, resourcesPath };
};

const createManager = async (
  options: Partial<ConstructorParameters<typeof BackendRuntimeManager>[0]> = {},
  withVenv = true
) => {
  const repoRoot = await createRepoRoot(withVenv);
  const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
  const manager = new BackendRuntimeManager({
    appUserDataPath,
    backendBinaryCandidates: [],
    compiledMainDir: repoRoot,
    repoRootCandidates: [repoRoot],
    startupAttempts: 2,
    startupIntervalMs: 1,
    logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
    portOpenCheck: closedPortCheck(),
    ...options
  });
  return { manager, repoRoot };
};

describe("BackendRuntimeManager", () => {
  it("locates backend root from REILINK_PROJECT_ROOT", async () => {
    const repoRoot = await createRepoRoot();
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      backendBinaryCandidates: [],
      compiledMainDir: path.join(os.tmpdir(), "not-reilink"),
      cwd: os.tmpdir(),
      env: { REILINK_PROJECT_ROOT: repoRoot },
      fetchImpl,
      homeDir: os.tmpdir(),
      repoRootCandidates: undefined,
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_project_root).toBe(repoRoot);
    expect(status.backend_root).toBe(path.join(repoRoot, "services", "backend"));
    expect(status.backend_started_from).toBe("repo");
    expect(spawnBackend).toHaveBeenCalled();
  });

  it("does not start a process when the backend is already healthy", async () => {
    const spawnBackend = vi.fn();
    const { manager } = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(okResponse),
      spawnBackend
    });

    const status = await manager.ensureBackend();
    await manager.stopStartedBackend();

    expect(status.backend_status).toBe("external_backend_detected");
    expect(status.backend_started_by_app).toBe(false);
    expect(status.backend_started_from).toBe("external");
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("starts configured backend binary before repo backend when binary exists", async () => {
    const repoRoot = await createRepoRoot();
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const binaryPath = path.join(repoRoot, "services", "backend", "dist", "reilink-backend");
    await mkdir(path.dirname(binaryPath), { recursive: true });
    await writeFile(binaryPath, "", "utf8");
    await chmod(binaryPath, 0o755);
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      backendBinaryCandidates: [binaryPath],
      compiledMainDir: repoRoot,
      fetchImpl,
      repoRootCandidates: [repoRoot],
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_binary_exists).toBe(true);
    expect(status.backend_binary_path).toBe(binaryPath);
    expect(status.backend_started_from).toBe("configured_binary");
    expect(spawnBackend).toHaveBeenCalledWith(
      binaryPath,
      [],
      expect.objectContaining({
        cwd: path.dirname(binaryPath),
        stdio: "pipe",
        windowsHide: true
      })
    );
  });

  it("falls back to repo backend when configured binary is missing", async () => {
    const repoRoot = await createRepoRoot();
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const missingBinary = path.join(repoRoot, "services", "backend", "dist", "missing-backend");
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      backendBinaryCandidates: [missingBinary],
      compiledMainDir: repoRoot,
      env: { REILINK_BACKEND_BINARY: missingBinary },
      fetchImpl,
      repoRootCandidates: [repoRoot],
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_binary_exists).toBe(false);
    expect(status.backend_binary_path).toBe(missingBinary);
    expect(status.backend_started_from).toBe("repo");
    expect(spawnBackend).toHaveBeenCalledWith(
      expect.stringContaining(path.join("services", "backend", ".venv", "bin", "python")),
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      expect.objectContaining({
        cwd: expect.stringContaining(path.join("services", "backend")),
        env: expect.objectContaining({
          REILINK_DATA_DIR: expect.stringContaining("reilink-runtime-user-"),
          REILINK_RESOURCE_DIR: path.join(repoRoot, "data"),
          REILINK_KNOWLEDGE_DIR: path.join(repoRoot, "data", "knowledge", "games")
        })
      })
    );
  });

  it("falls back from missing configured binary to bundled backend binary", async () => {
    const repoRoot = await createRepoRoot();
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const { backendBinary, resourcesPath } = await createBundledResources();
    const missingBinary = path.join(repoRoot, "configured", "missing-backend");
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      compiledMainDir: repoRoot,
      env: { REILINK_BACKEND_BINARY: missingBinary },
      fetchImpl,
      repoRootCandidates: [repoRoot],
      resourcesPath,
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_started_from).toBe("bundled_binary");
    expect(status.backend_binary_path).toBe(backendBinary);
    expect(spawnBackend).toHaveBeenCalledWith(backendBinary, [], expect.any(Object));
  });

  it("starts bundled backend binary before repo backend when bundled binary exists", async () => {
    const repoRoot = await createRepoRoot();
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const { backendBinary, knowledgeDir, resourcesPath } = await createBundledResources();
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      compiledMainDir: repoRoot,
      fetchImpl,
      repoRootCandidates: [repoRoot],
      resourcesPath,
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_binary_path).toBe(backendBinary);
    expect(status.backend_started_from).toBe("bundled_binary");
    expect(status.bundled_backend_binary_path).toBe(backendBinary);
    expect(status.bundled_backend_exists).toBe(true);
    expect(status.knowledge_source).toBe("bundled");
    expect(status.knowledge_path).toBe(knowledgeDir);
    expect(status.user_data_dir).toBe(path.join(appUserDataPath, "data"));
    await expect(access(path.join(appUserDataPath, "data", "memory"))).resolves.toBeUndefined();
    await expect(access(path.join(appUserDataPath, "data", "session"))).resolves.toBeUndefined();
    await expect(access(path.join(appUserDataPath, "data", "settings"))).resolves.toBeUndefined();
    await expect(access(path.join(appUserDataPath, "data", "logs"))).resolves.toBeUndefined();
    expect(spawnBackend).toHaveBeenCalledWith(
      backendBinary,
      [],
      expect.objectContaining({
        env: expect.objectContaining({
          REILINK_DATA_DIR: path.join(appUserDataPath, "data"),
          REILINK_KNOWLEDGE_DIR: knowledgeDir,
          REILINK_PROJECT_ROOT: repoRoot,
          REILINK_RESOURCE_DIR: resourcesPath
        })
      })
    );
  });

  it("prefers external then configured binary then bundled binary then repo", async () => {
    const repoRoot = await createRepoRoot();
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const { backendBinary: bundledBinary, resourcesPath } = await createBundledResources();
    const configuredBinary = path.join(repoRoot, "configured", "reilink-backend");
    await mkdir(path.dirname(configuredBinary), { recursive: true });
    await writeFile(configuredBinary, "", "utf8");
    await chmod(configuredBinary, 0o755);
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      compiledMainDir: repoRoot,
      env: { REILINK_BACKEND_BINARY: configuredBinary },
      fetchImpl,
      repoRootCandidates: [repoRoot],
      resourcesPath,
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_started_from).toBe("configured_binary");
    expect(status.backend_binary_path).toBe(configuredBinary);
    expect(status.bundled_backend_binary_path).toBe(bundledBinary);
    expect(spawnBackend).toHaveBeenCalledWith(configuredBinary, [], expect.any(Object));
  });

  it("starts local backend when health check fails then becomes healthy", async () => {
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const { manager } = await createManager({ fetchImpl, spawnBackend });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_started_by_app).toBe(true);
    expect(status.backend_started_from).toBe("repo");
    expect(spawnBackend).toHaveBeenCalledWith(
      expect.stringContaining(path.join("services", "backend", ".venv", "bin", "python")),
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
      expect.objectContaining({
        cwd: expect.stringContaining(path.join("services", "backend")),
        stdio: "pipe",
        windowsHide: true
      })
    );
  });

  it("reports missing backend venv without spawning", async () => {
    const spawnBackend = vi.fn();
    const { manager, repoRoot } = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      spawnBackend
    }, false);

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("missing_venv");
    expect(status.backend_project_root).toBe(repoRoot);
    expect(status.backend_root).toBe(path.join(repoRoot, "services", "backend"));
    expect(status.backend_start_error).toBe("未找到 backend venv，请先创建 services/backend/.venv 或手动运行 make dev-backend。");
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("reports missing project root without spawning", async () => {
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
    const spawnBackend = vi.fn();
    const manager = new BackendRuntimeManager({
      appUserDataPath,
      backendBinaryCandidates: [],
      compiledMainDir: path.join(os.tmpdir(), "not-reilink"),
      cwd: os.tmpdir(),
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      homeDir: os.tmpdir(),
      repoRootCandidates: [path.join(os.tmpdir(), "not-reilink")],
      spawnBackend,
      startupAttempts: 1,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
      portOpenCheck: closedPortCheck()
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("missing_project_root");
    expect(status.backend_start_error).toBe("未找到 ReiLink 项目目录，请设置 REILINK_PROJECT_ROOT 或手动运行 make dev-backend。");
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("reports health timeout and stops the app-started backend", async () => {
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const { manager } = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("health_timeout");
    expect(status.backend_start_error).toBe("后端启动超时，请查看 Electron main process 日志或手动运行 make dev-backend。");
    expect(child.kill).toHaveBeenCalledWith("SIGTERM");
  });

  it("reports port occupied when health endpoint is not ReiLink but the port is open", async () => {
    const spawnBackend = vi.fn();
    const portOpenCheck = vi.fn(async () => true);
    const { manager } = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      portOpenCheck,
      spawnBackend
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("port_occupied");
    expect(status.backend_start_error).toBe("端口 8000 已被占用，但不是可用的 ReiLink backend。");
    expect(portOpenCheck).toHaveBeenCalledWith("127.0.0.1", 8000);
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("respects disabled auto-start and does not spawn", async () => {
    const spawnBackend = vi.fn();
    const { manager } = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      spawnBackend
    });

    const status = await manager.setAutoStartEnabled(false);

    expect(status.backend_auto_start_enabled).toBe(false);
    expect(status.backend_status).toBe("disabled");
    expect(status.backend_start_error).toBe("自动启动已关闭，请手动运行 make dev-backend。");
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("does not kill an external backend on quit", async () => {
    const spawnBackend = vi.fn();
    const { manager } = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(okResponse),
      spawnBackend
    });
    await manager.ensureBackend();

    await manager.stopStartedBackend();

    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("only stops a backend process started by the app", async () => {
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const { manager } = await createManager({ fetchImpl, spawnBackend });
    await manager.ensureBackend();

    await manager.stopStartedBackend();

    expect(child.kill).toHaveBeenCalledWith("SIGTERM");
  });
});
