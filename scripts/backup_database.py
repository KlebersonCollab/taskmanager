"""
Script Avulso de Exemplo: Backup de Banco de Dados
------------------------------------------------------------
Este script pode ser executado diretamente pelo TaskManager Frontend
utilizando a tarefa embutida `system.run_command` ou `system.run_script`.

Exemplo de Payload no Dashboard:
{
  "kwargs": {
    "command": "python scripts/backup_database.py --database producao --compress"
  }
}
"""

from __future__ import annotations

import argparse
import datetime
import sys
import time


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Script de backup de banco de dados")
    parser.add_argument("--database", default="app_db", help="Nome do banco de dados")
    parser.add_argument("--compress", action="store_true", help="Compactar arquivo de backup (.gz)")
    parser.add_argument("--simulate-error", action="store_true", help="Forçar erro para testar DLQ")

    args = parser.parse_args()

    print(f"📦 [Backup Script] Iniciando backup do banco: '{args.database}'...")
    time.sleep(1.5)

    if args.simulate_error:
        print("❌ [Backup Script] ERRO CRÍTICO: Falha na conexão com o storage S3!", file=sys.stderr)
        sys.exit(1)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = ".sql.gz" if args.compress else ".sql"
    backup_file = f"/backups/{args.database}_{now_str}{extension}"

    print("📁 Dump realizado: 450 MB processados.")
    if args.compress:
        print("🗜️ Compressão concluída: 68 MB finais.")
    print(f"✅ Backup gerado com sucesso em: {backup_file}")


if __name__ == "__main__":
    main()
