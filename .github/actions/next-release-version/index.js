const { execFileSync } = require('node:child_process');
const { appendFileSync } = require('node:fs');

function nextVersion(releases) {
  if (!Array.isArray(releases) || releases.length === 0) {
    throw new Error('Expected at least one channel release; cannot determine next version');
  }
  const version = releases[0]?.semver;
  const match = typeof version === 'string'
    && /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.exec(version);
  if (!match) {
    throw new Error('Latest channel release must have an X.Y.Z version');
  }
  return `${match[1]}.${match[2]}.${BigInt(match[3]) + 1n}`;
}

function run(env = process.env, execute = execFileSync, append = appendFileSync) {
  const channel = env.INPUT_CHANNEL?.trim();
  const app = env.INPUT_APP?.trim();
  if (!channel || !app || !env.GITHUB_OUTPUT) {
    throw new Error('channel, app, and GITHUB_OUTPUT are required');
  }
  const result = execute('replicated', [
    'channel', 'releases', channel, '--app', app,
    '--page', '1', '--page-size', '1', '-o', 'json',
  ], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  const version = nextVersion(JSON.parse(result));
  append(env.GITHUB_OUTPUT, `version=${version}\n`);
  return version;
}

if (require.main === module) {
  try {
    console.log(`Next release version: ${run()}`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = { nextVersion, run };
