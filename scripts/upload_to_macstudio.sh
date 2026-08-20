#!/usr/bin/env bash
# upload_to_macstudio.sh — push this project's GITIGNORED artifacts to the Mac Studio.
#
# Tracked code syncs through GitHub (`git push` / the 04:45 pull job on the Studio).
# This script covers only what git deliberately does NOT carry: generated artifacts,
# datasets, model outputs, .env files — the payload that used to ride OneDrive before
# dev projects moved to ~/Dev_Projects_Local on 2026-08-20.
#
# WHAT gets synced is declared in `.macstudio-sync` at the repo root — one path per
# line, relative to the repo root, `#` for comments. No manifest, no sync: the script
# refuses rather than guessing, so it can never silently ship the wrong tree.
#
#   # .macstudio-sync
#   artifacts/
#   data/raw/
#   .env
#
# Remote layout mirrors local exactly:
#   ~/Dev_Projects_Local/<project>/<path>  ->  /Volumes/DATA/Dev_Projects_Local/<project>/<path>
#
# Usage:
#   ./scripts/upload_to_macstudio.sh                 # sync everything in the manifest
#   ./scripts/upload_to_macstudio.sh --dry-run       # show what would transfer
#   ./scripts/upload_to_macstudio.sh --delete        # mirror deletions (OPT-IN, destructive)
#   ./scripts/upload_to_macstudio.sh --path artifacts/2026-08  # one subtree, ignore manifest
#   ./scripts/upload_to_macstudio.sh --host macstudio-tail     # force the Tailscale route
set -euo pipefail

REMOTE_ROOT="${MACSTUDIO_ROOT:-/Volumes/DATA/Dev_Projects_Local}"
HOST=""
DRY_RUN=0
DO_DELETE=0
PATHS=()

log()  { printf '%s %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift ;;
        --delete)  DO_DELETE=1; shift ;;
        --host)    HOST="${2:?--host needs a value}"; shift 2 ;;
        --path)    PATHS+=("${2:?--path needs a value}"); shift 2 ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *)         die "unknown argument: $1 (see --help)" ;;
    esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$REPO_ROOT" ]] || die "not inside a git repository"
PROJECT="$(basename "$REPO_ROOT")"
MANIFEST="$REPO_ROOT/.macstudio-sync"

# Pick a reachable host: LAN first, then Tailscale. Both are ~/.ssh/config aliases.
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
    [[ -f "$MANIFEST" ]] || die "no .macstudio-sync manifest at $MANIFEST
Create one listing the gitignored paths to sync, e.g.:
  printf 'artifacts/\\ndata/\\n' > '$MANIFEST'"
    while IFS= read -r line; do
        line="${line%%#*}"                      # strip comments
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
[[ $DO_DELETE -eq 1 ]] && log "MODE   : --delete (remote files absent locally WILL be removed)"

rsync_opts=(-az --partial --human-readable --info=stats2)
[[ $DRY_RUN  -eq 1 ]] && rsync_opts+=(--dry-run --itemize-changes)
[[ $DO_DELETE -eq 1 ]] && rsync_opts+=(--delete)

ssh "$TARGET_HOST" "mkdir -p '$REMOTE_ROOT/$PROJECT'" \
    || die "cannot create $REMOTE_ROOT/$PROJECT on $TARGET_HOST (is /Volumes/DATA mounted?)"

failed=0
for rel in "${PATHS[@]}"; do
    src="$REPO_ROOT/${rel%/}"
    if [[ ! -e "$src" ]]; then
        log "SKIP  $rel (not present locally)"
        continue
    fi
    # Count before/after: rsync can drop files under a subdirectory and still exit 0
    # (errno 11 on a busy volume), so a bare rc=0 is not proof the transfer completed.
    local_count=$(find "$src" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [[ -d "$src" ]]; then
        ssh "$TARGET_HOST" "mkdir -p '$REMOTE_ROOT/$PROJECT/${rel%/}'"
        srcspec="$src/"; dstspec="$TARGET_HOST:$REMOTE_ROOT/$PROJECT/${rel%/}/"
    else
        ssh "$TARGET_HOST" "mkdir -p \"\$(dirname '$REMOTE_ROOT/$PROJECT/$rel')\""
        srcspec="$src"; dstspec="$TARGET_HOST:$REMOTE_ROOT/$PROJECT/$rel"
    fi

    log "PUSH  $rel  ($local_count local files)"
    if rsync "${rsync_opts[@]}" "$srcspec" "$dstspec"; then
        if [[ $DRY_RUN -eq 0 ]]; then
            remote_count=$(ssh "$TARGET_HOST" "find '$REMOTE_ROOT/$PROJECT/${rel%/}' -type f 2>/dev/null | wc -l" | tr -d ' ')
            if [[ "$remote_count" -lt "$local_count" ]]; then
                log "  *** COUNT MISMATCH: local=$local_count remote=$remote_count — re-run"
                failed=1
            else
                log "  verified: local=$local_count remote=$remote_count"
            fi
        fi
    else
        log "  *** rsync FAILED for $rel"
        failed=1
    fi
done

[[ $failed -eq 0 ]] || die "one or more paths failed to sync"
log "done."
