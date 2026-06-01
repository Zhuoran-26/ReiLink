import { EventEmitter } from "node:events";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
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

const createRepoRoot = async (withVenv = true) => {
  const repoRoot = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-"));
  await mkdir(path.join(repoRoot, "services", "backend", "app"), { recursive: true });
  await writeFile(path.join(repoRoot, "services", "backend", "app", "main.py"), "", "utf8");
  if (withVenv) {
    await mkdir(path.join(repoRoot, "services", "backend", ".venv", "bin"), { recursive: true });
    await writeFile(path.join(repoRoot, "services", "backend", ".venv", "bin", "python"), "", "utf8");
  }
  return repoRoot;
};

const createManager = async (
  options: Partial<ConstructorParameters<typeof BackendRuntimeManager>[0]> = {},
  withVenv = true
) => {
  const repoRoot = await createRepoRoot(withVenv);
  const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-runtime-user-"));
  const manager = new BackendRuntimeManager({
    appUserDataPath,
    compiledMainDir: repoRoot,
    repoRootCandidates: [repoRoot],
    startupAttempts: 2,
    startupIntervalMs: 1,
    logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
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
      compiledMainDir: path.join(os.tmpdir(), "not-reilink"),
      cwd: os.tmpdir(),
      env: { REILINK_PROJECT_ROOT: repoRoot },
      fetchImpl,
      homeDir: os.tmpdir(),
      repoRootCandidates: undefined,
      spawnBackend,
      startupAttempts: 2,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() }
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
    expect(status.backend_project_root).toBe(repoRoot);
    expect(status.backend_root).toBe(path.join(repoRoot, "services", "backend"));
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
    expect(spawnBackend).not.toHaveBeenCalled();
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
      compiledMainDir: path.join(os.tmpdir(), "not-reilink"),
      cwd: os.tmpdir(),
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      homeDir: os.tmpdir(),
      repoRootCandidates: [path.join(os.tmpdir(), "not-reilink")],
      spawnBackend,
      startupAttempts: 1,
      startupIntervalMs: 1,
      logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() }
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
