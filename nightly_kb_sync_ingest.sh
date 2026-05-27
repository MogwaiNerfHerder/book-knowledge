#!/bin/bash
# Nightly KB pipeline (B2): pull bot-created digests from Kiselgolem, ingest into books.db on Nyxturne.
# Idempotent. Installed as launchd job com.cortado.kb-nightly (nightly 03:15).
set -u

BK="/Users/david/work/book_knowledge"
DST="/Users/david/.openclaw/workspace/knowledge/digests/"
SRC="david@Kiselgolem.local:/Users/david/clawd-kiselgolem/knowledge/digests/"
LOGDIR="$BK/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/nightly_kb.log"

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') nightly KB sync+ingest ====="

  # 1. Pull new bot digests from Kiselgolem (never overwrite existing, never delete)
  if /usr/bin/rsync -a --ignore-existing -e /usr/bin/ssh "$SRC" "$DST"; then
    echo "rsync ok"
  else
    echo "rsync FAILED (rc=$?) — Kiselgolem unreachable? proceeding to ingest local digests anyway"
  fi

  cd "$BK" || { echo "FATAL: cannot cd $BK"; exit 1; }

  # 2. Back up books.db, keep the 7 most recent backups
  cp books.db "books.db.bak.$(date +%Y%m%d-%H%M%S)" && echo "db backed up"
  ls -1t books.db.bak.* 2>/dev/null | tail -n +8 | while read -r old; do rm -f "$old"; done

  # 3. Ingest (idempotent — dedups by source_url, then file_path)
  KMP_DUPLICATE_LIB_OK=TRUE /usr/bin/python3 ingest_all_digests.py "$DST" 2>&1 \
    | grep -vE "NotOpenSSLWarning|warnings.warn|HF_TOKEN|Loading weights"

  echo "===== done $(date '+%Y-%m-%d %H:%M:%S') ====="
  echo
} >> "$LOG" 2>&1
