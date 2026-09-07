#!/usr/bin/env bash
# Retired 2026-09-07 after review of the actual queue source.
# The old version is preserved under /home/kaan/followup_20260907/before/.
printf '%s\n' 'STOP: this legacy queue deletes native data, uses stale inputs/binaries, and lacks a verified retention/comparison plan.' >&2
printf '%s\n' 'Do not restart it. Use the reviewed, non-destructive runners after physical and storage preflight.' >&2
exit 78
