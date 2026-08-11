#!/bin/sh
# Run the Directus scrape once a day at a fixed UTC time, forever.
#
# WHY A SLEEP LOOP AND NOT CRON
# -----------------------------
# This replaces the systemd timer that ran the job on mema3
# (copertine-scrape.timer, OnCalendar=*-*-* 08:00:00 UTC). Under Dokploy there
# is no host unit to install — everything must be git-defined and shipped in
# the image — and adding cron to the image would mean a second process
# supervisor, its own log sink, and no way to see the next fire time. This is
# the same shape as pdfmanifesto's `janitor` sidecar.
#
# WHY IT COMPUTES THE DELAY INSTEAD OF `sleep 86400`
# --------------------------------------------------
# A fixed 24h sleep drifts by however long the scrape took, every single day,
# so the fire time walks forward and eventually crosses the publish boundary.
# That boundary is the whole point of the schedule: il manifesto publishes an
# edition's cover at Rome-local midnight, i.e. 22:00-23:00 UTC the day before,
# so 08:00 UTC is a deliberate buffer after it has settled. Recomputing the
# target from the wall clock each iteration keeps the fire time exact and makes
# the container restart-safe — it re-derives the next slot rather than
# restarting a 24h countdown.
#
# CATCH-UP: systemd's Persistent=true re-ran a missed slot after a reboot. Here
# the equivalent is COP_SCRAPE_LOOKBACK_DAYS (`-n`), which re-fetches the last
# N days on every run. The upsert is keyed on edition_id, so re-fetching is
# idempotent and a container that was down for a day self-heals on its next
# run without any missed-run bookkeeping.
set -eu

SCRAPE_AT="${COP_SCRAPE_AT_UTC:-08:00}"
LOOKBACK="${COP_SCRAPE_LOOKBACK_DAYS:-3}"

log() { echo "$(date -u +%FT%TZ) scrape-loop: $*"; }

case "$SCRAPE_AT" in
    [0-2][0-9]:[0-5][0-9]) ;;
    *) log "FATAL: COP_SCRAPE_AT_UTC='$SCRAPE_AT' is not HH:MM"; exit 1 ;;
esac

log "daily scrape at ${SCRAPE_AT} UTC, lookback ${LOOKBACK} day(s)"

# Run immediately on start when asked. Off by default: a redeploy would
# otherwise fire an unscheduled scrape, and with `pull_policy: always` in the
# compose file redeploys are routine.
if [ "${COP_SCRAPE_ON_START:-false}" = "true" ]; then
    log "COP_SCRAPE_ON_START=true — running once now"
    python src/sd2.py -n "$LOOKBACK" || log "scrape failed (exit $?), continuing"
fi

while true; do
    now=$(date -u +%s)
    # Today's slot; if it has already passed, tomorrow's.
    target=$(date -u -d "$(date -u +%F) ${SCRAPE_AT}:00" +%s)
    [ "$target" -le "$now" ] && target=$((target + 86400))

    delay=$((target - now))
    log "next run at $(date -u -d "@${target}" +%FT%TZ) (in ${delay}s)"
    sleep "$delay"

    log "running: sd2.py -n ${LOOKBACK}"
    # Never exit on a failed scrape: one bad day (Directus down, a malformed
    # edition) must not take the container out of the schedule for good.
    # restart: unless-stopped would bring it back, but into a crash loop that
    # retries far faster than once a day.
    if python src/sd2.py -n "$LOOKBACK"; then
        log "scrape completed"
    else
        log "scrape FAILED (exit $?) — will retry at the next scheduled slot"
    fi
done
