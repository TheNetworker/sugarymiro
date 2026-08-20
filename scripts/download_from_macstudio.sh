#!/usr/bin/env bash
# download_from_macstudio.sh — pull this project's GITIGNORED artifacts back from the Mac Studio.
#
# The mirror image of upload_to_macstudio.sh. Tracked code comes from GitHub; this
# brings back what git does not carry and what the Studio produced: harvest output,
# rendered images, transcripts, model artifacts.
#
# Reads the same `.macstudio-sync` manifest at the repo root (one path per line,
# relative to the repo root, `#` for comments). No manifest, no sync.
#
#   /Volumes/DATA/Dev_Projects_Local/<project>/<path>  ->  ~/Dev_Projects_Local/<project>/<path>
#
# Usage:
#   ./scripts/download_from_macstudio.sh                # pull everything in the manifest
#   ./scripts/download_from_macstudio.sh --dry-run      # show what would transfer
#   ./scripts/download_from_macstudio.sh --delete       # mirror deletions (OPT-IN, destructive)
#   ./scripts/download_from_macstudio.sh --path artifacts/2026-08
#   ./scripts/download_from_macstudio.sh --host macstudio-tail
set -euo pipefail

REMOTE_ROOT="${MACSTUDIO_ROOT:-/Volumes/DATA/Dev_Projects_Local}"
HOST=""
DRY_RUN=0
DO_DELETE=0
PATHS=()

log() { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --delete)  DO_DELETE=1; shift ;;
        --host)    HOST="${2:?--host needs a value}"; shift 2 ;;
        --path)    PATHS+=("${2:?--path needs a value}"); shift 2 ;;
        -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
        *)         die "unknown argument: $1 (see --help)" ;;
    esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO_ROOT" ]] || die "not inside a git repository"
PROJECT="$(basename "$REPO_ROOT")"
MANIFEST="$REPO_ROOT/.macstudio-sync"

pick_host() {
    local candidates=("macstudio" "macstudio-tail")
    [[ -n "$HOST" ]] && candidates=("$HOST")
    for h in "${candidates[@]}"; do
        if ssh -o BatchMode=yes -o ConnectTimeout=6 "$h" true 2>/dev/null; then
            printf '%s' "$h"; return 0
        fi
    done
    return 1
}

if [[ ${#PATHS[@]} -eq 0 ]]; then
    [[ -f "$MANIFEST" ]] || die "no .macstudio-sync manifest at $MANIFEST"
    while IFS= read -r line; do
        line="${line%%#*}"
        # Trim with parameter expansion, NOT xargs: xargs parses shell quoting, so a
        # manifest line like  data/it's/  hits an unterminated quote and silently
        # becomes empty — the path is then skipped while the script still says "done".
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -n "$line" ]] && PATHS+=("$line")
    done < "$MANIFEST"
fi
[[ ${#PATHS[@]} -gt 0 ]] || die "nothing to sync — manifest is empty"

TARGET_HOST="$(pick_host)" || die "Mac Studio unreachable over macstudio and macstudio-tail"
log "project: $PROJECT"
log "host   : $TARGET_HOST"
log "remote : $REMOTE_ROOT/$PROJECT"
log "paths  : ${PATHS[*]}"
[[ $DO_DELETE -eq 1 ]] && log "MODE   : --delete (LOCAL files absent on the Studio WILL be removed)"

rsync_opts=(-az --partial --human-readable --info=stats2)
[[ $DRY_RUN  -eq 1 ]] && rsync_opts+=(--dry-run --itemize-changes)
[[ $DO_DELETE -eq 1 ]] && rsync_opts+=(--delete)

ssh "$TARGET_HOST" "test -d '$REMOTE_ROOT/$PROJECT'" \
    || die "$REMOTE_ROOT/$PROJECT does not exist on $TARGET_HOST — nothing to pull"

failed=0
for rel in "${PATHS[@]}"; do
    remote_path="$REMOTE_ROOT/$PROJECT/${rel%/}"
    if ! ssh "$TARGET_HOST" "test -e '$remote_path'"; then
        log "SKIP  $rel (not present on the Studio)"
        continue
    fi
    remote_count=$(ssh "$TARGET_HOST" "find '$remote_path' -type f 2>/dev/null | wc -l" | tr -d ' ')
    dst="$REPO_ROOT/${rel%/}"

    if ssh "$TARGET_HOST" "test -d '$remote_path'"; then
        mkdir -p "$dst"
        srcspec="$TARGET_HOST:$remote_path/"; dstspec="$dst/"
    else
        mkdir -p "$(dirname "$dst")"
        srcspec="$TARGET_HOST:$remote_path"; dstspec="$dst"
    fi

    log "PULL  $rel  ($remote_count remote files)"
    if rsync "${rsync_opts[@]}" "$srcspec" "$dstspec"; then
        if [[ $DRY_RUN -eq 0 ]]; then
            # rsync can exit 0 having skipped files under a subdirectory; compare counts.
            local_count=$(find "$dst" -type f 2>/dev/null | wc -l | tr -d ' ')
            if [[ "$local_count" -lt "$remote_count" ]]; then
                log "  *** COUNT MISMATCH: remote=$remote_count local=$local_count — re-run"
                failed=1
            else
                log "  verified: remote=$remote_count local=$local_count"
            fi
        fi
    else
        log "  *** rsync FAILED for $rel"
        failed=1
    fi
done

[[ $failed -eq 0 ]] || die "one or more paths failed to sync"
log "done."
