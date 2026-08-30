#!/usr/bin/env node

/**
 * Git Pre-Commit Hook Installer for Spec Drift Prevention
 */

const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '../..');
const hooksDir = path.join(repoRoot, '.git', 'hooks');
const preCommitHookPath = path.join(hooksDir, 'pre-commit');

if (!fs.existsSync(hooksDir)) {
  fs.mkdirSync(hooksDir, { recursive: true });
}

const hookScript = `#!/bin/sh
# Pre-commit hook: Spec Drift Prevention Sensor (Constitutional SDD)
node .agents/scripts/check-spec-drift.js
`;

fs.writeFileSync(preCommitHookPath, hookScript, { mode: 0o755 });
console.log('✅ Git Pre-Commit Hook instalado com sucesso em:', preCommitHookPath);
