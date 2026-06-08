import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const loadPreloadBridge = () => {
  let exposedBridge: Record<string, unknown> | null = null;
  const ipcRenderer = {
    invoke: vi.fn(),
    on: vi.fn(),
    removeListener: vi.fn()
  };
  const contextBridge = {
    exposeInMainWorld: vi.fn((_name: string, bridge: Record<string, unknown>) => {
      exposedBridge = bridge;
    })
  };
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  const code = readFileSync(path.join(currentDir, "preload.cjs"), "utf8");
  const context = vm.createContext({
    require: (moduleName: string) => {
      if (moduleName === "electron") return { contextBridge, ipcRenderer };
      throw new Error(`Unexpected preload require: ${moduleName}`);
    }
  });

  new vm.Script(code, { filename: "preload.cjs" }).runInContext(context);

  return { bridge: exposedBridge, contextBridge, ipcRenderer };
};

describe("preload bridge", () => {
  it("exposes the Local ASR native file picker IPC API", () => {
    const { bridge, contextBridge, ipcRenderer } = loadPreloadBridge();
    const request = { kind: "asr_model", currentPath: "/Users/aragoto/models/ggml-base.bin" };

    expect(contextBridge.exposeInMainWorld).toHaveBeenCalledWith("reilinkRuntime", expect.any(Object));
    expect(typeof bridge?.selectLocalFile).toBe("function");

    (bridge?.selectLocalFile as (payload: typeof request) => unknown)(request);

    expect(ipcRenderer.invoke).toHaveBeenCalledWith("local-file:select", request);
  });
});
