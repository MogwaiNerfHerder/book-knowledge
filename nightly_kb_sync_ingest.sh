#!/bin/bash
# Nightly KB pipeline (B2): ingest user digests (openclaw) + bot-created digests
# (Kiselgolem workspaces) into books.db on Nyxturne. The bot workspace is the
# ONE copy of each bot digest — pull into a temp staging just long enough to
# ingest, then discard. Never duplicate bot digests into openclaw.
# Idempotent (ingest dedups by source_url, then file_path).
# Installed as launchd job com.cortado.kb-nightly (nightly 03:15).
set -u

BK="/Users/david/work/book_knowledge"
OPENCLAW="/Users/david/.openclaw/workspace/knowledge/digests/"
SRC="david@Kiselgolem.local:/Users/david/clawd-kiselgolem/knowledge/digests/"
STAGING="/tmp/kb_nightly_staging"
LOGDIR="$BK/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/nightly_kb.log"

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') nightly KB sync+ingest ====="

  # 1. Pull bot digests into TEMP staging only — never into openclaw.
  rm -rf "$STAGING" && mkdir -p "$STAGING"
  if /usr/bin/rsync -a -e /usr/bin/ssh "$SRC" "$STAGING/"; then
    echo "rsync to staging ok ($(find "$STAGING" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ') bot digests staged)"
  else
    echo "rsync FAILED (rc=$?) — Kiselgolem unreachable? proceeding with openclaw ingest only"
  fi

  cd "$BK" || { echo "FATAL: cannot cd $BK"; exit 1; }

  # 2. Back up books.db, keep the 7 most recent backups
  cp books.db "books.db.bak.$(date +%Y%m%d-%H%M%S)" && echo "db backed up"
  ls -1t books.db.bak.* 2>/dev/null | tail -n +8 | while read -r old; do rm -f "$old"; done

  # 3. Ingest user's own digests from openclaw (idempotent).
  echo "--- ingest openclaw digests ---"
  KMP_DUPLICATE_LIB_OK=TRUE /usr/bin/python3 ingest_all_digests.py "$OPENCLAW" 2>&1 \
    | grep -vE "NotOpenSSLWarning|warnings.warn|HF_TOKEN|Loading weights"

  # 4. Ingest bot digests from STAGING. ingest dedups by source_url first, so the
  #    transient staging file_path won't cause duplicates across nights.
  if [ -d "$STAGING" ] && [ -n "$(find "$STAGING" -maxdepth 1 -name '*.md' -print -quit)" ]; then
    echo "--- ingest staged bot digests ---"
    KMP_DUPLICATE_LIB_OK=TRUE /usr/bin/python3 ingest_all_digests.py "$STAGING" 2>&1 \
      | grep -vE "NotOpenSSLWarning|warnings.warn|HF_TOKEN|Loading weights"
  fi

  # 5. Clean up staging — bot workspace is the one copy.
  rm -rf "$STAGING"

  echo "===== done $(date '+%Y-%m-%d %H:%M:%S') ====="
  echo
} >> "$LOG" 2>&1
