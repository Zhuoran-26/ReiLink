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

const okResponse = { ok: true } as Response;
const failedResponse = { ok: false } as Response;

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
  return new BackendRuntimeManager({
    appUserDataPath,
    compiledMainDir: repoRoot,
    repoRootCandidates: [repoRoot],
    startupAttempts: 2,
    startupIntervalMs: 1,
    logger: { error: vi.fn(), log: vi.fn(), warn: vi.fn() },
    ...options
  });
};

describe("BackendRuntimeManager", () => {
  it("does not start a process when the backend is already healthy", async () => {
    const spawnBackend = vi.fn();
    const manager = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(okResponse),
      spawnBackend
    });

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("connected");
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
    const manager = await createManager({ fetchImpl, spawnBackend });

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

  it("reports missing local backend runtime without spawning", async () => {
    const spawnBackend = vi.fn();
    const manager = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      spawnBackend
    }, false);

    const status = await manager.ensureBackend();

    expect(status.backend_status).toBe("not_found");
    expect(status.backend_started_by_app).toBe(false);
    expect(status.backend_start_error).toBe("未找到本地后端，请先在项目目录运行 make dev-backend。");
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("respects disabled auto-start and does not spawn", async () => {
    const spawnBackend = vi.fn();
    const manager = await createManager({
      fetchImpl: vi.fn().mockResolvedValue(failedResponse),
      spawnBackend
    });

    const status = await manager.setAutoStartEnabled(false);

    expect(status.backend_auto_start_enabled).toBe(false);
    expect(status.backend_status).toBe("disabled");
    expect(spawnBackend).not.toHaveBeenCalled();
  });

  it("only stops a backend process started by the app", async () => {
    const child = new FakeBackendProcess();
    const spawnBackend = vi.fn(() => child);
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce(failedResponse)
      .mockResolvedValueOnce(okResponse);
    const manager = await createManager({ fetchImpl, spawnBackend });
    await manager.ensureBackend();

    await manager.stopStartedBackend();

    expect(child.kill).toHaveBeenCalledWith("SIGTERM");
  });
});
