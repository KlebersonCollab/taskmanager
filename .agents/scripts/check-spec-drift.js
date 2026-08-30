#!/usr/bin/env node

/**
 * Spec Drift Detector — Pre-Commit & Audit Sensor
 * Enforces Constitutional Spec-Driven Development (CSDD).
 * 
 * Verifies that all staged code modifications are explicitly declared in
 * an active feature task specification under `.specs/features/<id>/tasks.md`.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const REPO_ROOT = path.resolve(__dirname, '../..');

// Exempt prefixes/patterns (governance, specs, configs, documentation)
const EXEMPT_PATTERNS = [
  /^\.specs\//,
  /^\.agents\//,
  /^docs\//,
  /\.md$/i,
  /\.json$/i,
  /\.yml$/i,
  /\.yaml$/i,
  /\.gitignore$/,
  /^LICENSE$/,
  /^\.cursor/,
  /^\.continue/,
  /^\.devin/,
  /^\.github/,
  /^\.aider/,
  /^\.cline/,
  /^\.windsurf/,
  /^\.goose/,
  /^\.junie/,
  /^\.openhands/
];

function isExempt(filePath) {
  const normalized = filePath.replace(/\\/g, '/');
  return EXEMPT_PATTERNS.some(pattern => pattern.test(normalized));
}

function getStagedFiles() {
  try {
    const output = execSync('git diff --cached --name-only', { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
    if (!output) return [];
    return output.split('\n').map(f => f.trim()).filter(Boolean);
  } catch (err) {
    return [];
  }
}

function getDeclaredTargetFiles() {
  const specsFeaturesDir = path.join(REPO_ROOT, '.specs', 'features');
  if (!fs.existsSync(specsFeaturesDir)) return new Set();

  const declaredFiles = new Set();
  const featureDirs = fs.readdirSync(specsFeaturesDir);

  for (const featureDir of featureDirs) {
    const tasksFile = path.join(specsFeaturesDir, featureDir, 'tasks.md');
    if (!fs.existsSync(tasksFile)) continue;

    const content = fs.readFileSync(tasksFile, 'utf8');
    const lines = content.split('\n');

    for (const line of lines) {
      if (!line.startsWith('|') || line.includes('Target Files') || line.includes('---')) continue;
      const columns = line.split('|').map(c => c.trim()).filter(Boolean);
      
      // In 7-column schema: Status (0), ID (1), Type (2), Description (3), Target Files (4), Dependencies (5), Evidence (6)
      // In 5-column schema: Status (0), ID (1), Description (2), Target Files (3), Evidence (4)
      let targetColumn = '';
      if (columns.length >= 7) {
        targetColumn = columns[4];
      } else if (columns.length >= 5) {
        targetColumn = columns[3];
      }

      if (targetColumn) {
        const matches = targetColumn.match(/`([^`]+)`/g);
        if (matches) {
          matches.forEach(m => {
            const cleanPath = m.replace(/`/g, '').trim().replace(/\\/g, '/');
            if (cleanPath) declaredFiles.add(cleanPath);
          });
        } else {
          targetColumn.split(',').forEach(p => {
            const cleanPath = p.trim().replace(/\\/g, '/');
            if (cleanPath) declaredFiles.add(cleanPath);
          });
        }
      }
    }
  }

  return declaredFiles;
}

function checkSpecDrift() {
  console.log('\n🔍 [SPEC DRIFT SENSOR] Verificando conformidade entre código e especificações...');
  const stagedFiles = getStagedFiles();

  if (stagedFiles.length === 0) {
    console.log('ℹ️ Nenhum arquivo staged no Git. Verificação ignorada.\n');
    process.exit(0);
  }

  const codeFiles = stagedFiles.filter(f => !isExempt(f));

  if (codeFiles.length === 0) {
    console.log('✅ [SPEC DRIFT OK] Apenas artefatos de governança/specs/docs foram alterados.\n');
    process.exit(0);
  }

  const declaredTargets = getDeclaredTargetFiles();
  const driftingFiles = [];

  for (const file of codeFiles) {
    const normalizedFile = file.replace(/\\/g, '/');
    let isCovered = false;

    for (const declared of declaredTargets) {
      if (declared.endsWith('/') && normalizedFile.startsWith(declared)) {
        isCovered = true;
        break;
      }
      if (declared === normalizedFile || normalizedFile.endsWith(declared)) {
        isCovered = true;
        break;
      }
    }

    if (!isCovered) {
      driftingFiles.push(file);
    }
  }

  if (driftingFiles.length > 0) {
    console.error('\n❌ [SPEC DRIFT DETECTADO] Commit bloqueado!');
    console.error('Os seguintes arquivos de implementação NÃO estão declarados em nenhum tasks.md ativo em .specs/features/:');
    driftingFiles.forEach(f => console.error(`   - ${f}`));
    console.error('\n📋 Como Resolver:');
    console.error('   1. Use o skill `sdd-planner` para criar ou atualizar a especificação da feature em `.specs/features/<feature-id>/`.');
    console.error('   2. Adicione os arquivos acima na coluna `Target Files` do arquivo `tasks.md`.');
    console.error('   3. Faça o stage do `tasks.md` atualizado e repita o commit.\n');
    process.exit(1);
  }

  console.log('✅ [SPEC DRIFT OK] Todos os arquivos alterados estão devidamente cobertos pelas especificações ativas.\n');
  process.exit(0);
}

checkSpecDrift();
