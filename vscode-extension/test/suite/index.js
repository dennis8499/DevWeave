const assert = require("node:assert/strict");
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
}

module.exports = { run };
