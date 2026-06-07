import { createMainWindowOptions, restoreMainWindowForActivation } from "./mainWindow";

describe("main window", () => {
  it("keeps the ReiLink main window as a normal desktop app window", () => {
    const options = createMainWindowOptions("/tmp/preload.cjs");

    expect(options.skipTaskbar).toBeUndefined();
    expect(options.focusable).toBeUndefined();
    expect(options.alwaysOnTop).toBeUndefined();
    expect(options.show).toBeUndefined();
    expect(options.transparent).toBeUndefined();
    expect(options.frame).toBeUndefined();
    expect(options.webPreferences).toMatchObject({
      contextIsolation: true,
      nodeIntegration: false,
      preload: "/tmp/preload.cjs"
    });
  });

  it("restores and focuses the main window when the app is activated", () => {
    const window = {
      focus: vi.fn(),
      isDestroyed: vi.fn(() => false),
      isMinimized: vi.fn(() => true),
      restore: vi.fn(),
      show: vi.fn()
    };

    expect(restoreMainWindowForActivation(window)).toBe(true);

    expect(window.restore).toHaveBeenCalledOnce();
    expect(window.show).toHaveBeenCalledOnce();
    expect(window.focus).toHaveBeenCalledOnce();
  });

  it("does not touch destroyed windows during activation", () => {
    const window = {
      focus: vi.fn(),
      isDestroyed: vi.fn(() => true),
      isMinimized: vi.fn(() => true),
      restore: vi.fn(),
      show: vi.fn()
    };

    expect(restoreMainWindowForActivation(window)).toBe(false);

    expect(window.restore).not.toHaveBeenCalled();
    expect(window.show).not.toHaveBeenCalled();
    expect(window.focus).not.toHaveBeenCalled();
  });
});
