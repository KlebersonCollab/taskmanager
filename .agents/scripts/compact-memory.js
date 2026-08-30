#!/usr/bin/env node

/**
 * Memory Graph Validator & Compactor (MemGPT / TiM Protocol)
 * Audits .agents/memory/memory_graph.jsonl for schema compliance,
 * tracks active vs. superseded entities, and optionally compacts archived records.
 */

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');
const MEMORY_FILE = path.join(REPO_ROOT, '.agents', 'memory', 'memory_graph.jsonl');
const ARCHIVE_FILE = path.join(REPO_ROOT, '.agents', 'memory', 'memory_archive.jsonl');

function loadMemoryRecords(filePath) {
  if (!fs.existsSync(filePath)) return [];
  const content = fs.readFileSync(filePath, 'utf8').trim();
  if (!content) return [];

  const lines = content.split('\n').map(l => l.trim()).filter(Boolean);
  const records = [];

  for (let i = 0; i < lines.length; i++) {
    try {
      const record = JSON.parse(lines[i]);
      records.push({ index: i + 1, data: record, raw: lines[i] });
    } catch (err) {
      console.error(`❌ [ERRO DE PARSE] Linha ${i + 1} em ${path.basename(filePath)} contém JSON inválido:`, lines[i]);
    }
  }

  return records;
}

function auditMemory(records) {
  let activeCount = 0;
  let supersededCount = 0;
  let archivedCount = 0;
  let invalidCount = 0;

  const entityNames = new Set();

  for (const item of records) {
    const rec = item.data;

    // Validate standard fields
    if (!['entity', 'relation', 'observation'].includes(rec.type)) {
      console.warn(`⚠️ [TIPO INVÁLIDO] Linha ${item.index}: tipo "${rec.type}" desconhecido.`);
      invalidCount++;
      continue;
    }

    // Default status if missing (backward compatibility)
    const status = rec.status || 'active';
    if (status === 'active') activeCount++;
    else if (status === 'superseded') supersededCount++;
    else if (status === 'archived') archivedCount++;
    else {
      console.warn(`⚠️ [STATUS INVÁLIDO] Linha ${item.index}: status "${status}".`);
      invalidCount++;
    }

    if (rec.type === 'entity' && rec.name) {
      entityNames.add(rec.name);
    }
  }

  console.log('\n📊 [RESUMO DO GRAFO DE MEMÓRIA]');
  console.log(`   • Total de Registros: ${records.length}`);
  console.log(`   • Nós Ativos:         ${activeCount} (serão carregados na reidratação)`);
  console.log(`   • Nós Superseded:     ${supersededCount} (ignorados no contexto ativo)`);
  console.log(`   • Nós Arquivados:     ${archivedCount}`);
  if (invalidCount > 0) {
    console.log(`   • Registros com Aviso:${invalidCount}`);
  }

  return { activeCount, supersededCount, archivedCount, invalidCount };
}

function compactMemory(records) {
  const activeRecords = [];
  const archiveRecords = [];

  for (const item of records) {
    const rec = item.data;
    const status = rec.status || 'active';

    if (status === 'active') {
      activeRecords.push(JSON.stringify(rec));
    } else {
      archiveRecords.push(JSON.stringify(rec));
    }
  }

  if (archiveRecords.length > 0) {
    fs.appendFileSync(ARCHIVE_FILE, archiveRecords.join('\n') + '\n', 'utf8');
    fs.writeFileSync(MEMORY_FILE, activeRecords.join('\n') + '\n', 'utf8');
    console.log(`\n🗜️ [COMPACTAÇÃO CONCLUÍDA] ${archiveRecords.length} registros movidos para ${path.basename(ARCHIVE_FILE)}.`);
  } else {
    console.log('\nℹ️ Nenhum registro superseded/arquivado para compactar.');
  }
}

function main() {
  const shouldCompact = process.argv.includes('--compact');

  if (!fs.existsSync(MEMORY_FILE)) {
    console.log('ℹ️ Arquivo .agents/memory/memory_graph.jsonl ainda não existe.');
    process.exit(0);
  }

  const records = loadMemoryRecords(MEMORY_FILE);
  const stats = auditMemory(records);

  if (shouldCompact && stats.supersededCount + stats.archivedCount > 0) {
    compactMemory(records);
  }
}

main();
