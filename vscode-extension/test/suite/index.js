const assert = require("node:assert/strict");
const vscode = require("vscode");

async function run() {
  const extension = vscode.extensions.getExtension("devweave.devweave-control-center");
  assert.ok(extension, "DevWeave extension should be discoverable");
  await extension.activate();
  const commands = await vscode.commands.getCommands(true);
  assert.ok(commands.includes("devweave.openDashboard"));
  assert.ok(commands.includes("devweave.refresh"));
  assert.ok(commands.includes("devweave.copyNextAction"));
}

module.exports = { run };
