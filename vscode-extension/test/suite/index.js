const assert = require("node:assert/strict");
const { writeFile } = require("node:fs/promises");
const vscode = require("vscode");

async function run() {
  const extension = vscode.extensions.getExtension("devweave.devweave-control-center");
  assert.ok(extension, "DevWeave extension should be discoverable");
  await extension.activate();
  const commands = await vscode.commands.getCommands(true);
  for (const command of [
    "devweave.openControlCenter",
    "devweave.startRun",
    "devweave.resumeRun",
    "devweave.steer",
    "devweave.interrupt",
    "devweave.cancel"
  ]) {
    assert.ok(commands.includes(command), `missing governed command ${command}`);
  }
  assert.ok(!commands.includes("devweave.copyNextAction"));
  assert.ok(!commands.includes("devweave.wikiBootstrap"));
  await vscode.commands.executeCommand("devweave.openControlCenter");
  await delay(1_500);
  await captureWorkbench();
}

async function captureWorkbench() {
  const port = Number(process.env.DEVWEAVE_SMOKE_DEBUG_PORT);
  const output = process.env.DEVWEAVE_SMOKE_SCREENSHOT;
  assert.ok(Number.isSafeInteger(port) && port > 0, "missing local CDP port");
  assert.ok(output, "missing smoke screenshot path");
  const targets = await retry(async () => {
    const response = await fetch(`http://127.0.0.1:${port}/json/list`);
    if (!response.ok) throw new Error(`CDP discovery returned ${response.status}`);
    const value = await response.json();
    if (!Array.isArray(value) || value.length === 0) throw new Error("CDP target list is empty");
    return value;
  });
  const target = targets.find((item) => item.type === "page" && item.webSocketDebuggerUrl)
    ?? targets.find((item) => item.webSocketDebuggerUrl);
  assert.ok(target?.webSocketDebuggerUrl, "VS Code workbench CDP target is unavailable");
  const client = await CdpClient.connect(target.webSocketDebuggerUrl);
  try {
    await client.call("Page.enable");
    const captured = await client.call("Page.captureScreenshot", { format: "png", fromSurface: true });
    assert.equal(typeof captured.data, "string");
    const png = Buffer.from(captured.data, "base64");
    assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
    await writeFile(output, png, { flag: "wx" });
  } finally {
    client.close();
  }
}

class CdpClient {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    socket.addEventListener("message", (event) => {
      const value = JSON.parse(String(event.data));
      const pending = this.pending.get(value.id);
      if (!pending) return;
      this.pending.delete(value.id);
      if (value.error) pending.reject(new Error(value.error.message));
      else pending.resolve(value.result ?? {});
    });
  }

  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("CDP connection timed out")), 10_000);
      socket.addEventListener("open", () => { clearTimeout(timeout); resolve(); }, { once: true });
      socket.addEventListener("error", () => { clearTimeout(timeout); reject(new Error("CDP connection failed")); }, { once: true });
    });
    return new CdpClient(socket);
  }

  call(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`${method} timed out`));
      }, 15_000);
      this.pending.set(id, {
        resolve: (value) => { clearTimeout(timeout); resolve(value); },
        reject: (error) => { clearTimeout(timeout); reject(error); }
      });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() { this.socket.close(); }
}

async function retry(action) {
  let last;
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try { return await action(); } catch (error) { last = error; }
    await delay(100);
  }
  throw last;
}

function delay(milliseconds) { return new Promise((resolve) => setTimeout(resolve, milliseconds)); }

module.exports = { run };
