#!/bin/sh
# Cut our basemap: OpenStreetMap for Sarawak (and the edges of Brunei and
# Kalimantan around it) as one vector tileset, data/sarawak.pmtiles, from
# Protomaps' daily planet build. Only the tiles inside the box are fetched.
# Zoom 14 is the deepest level stored; the map scales those up beyond it.
# GitHub Pages caps a file at 100 MB, so keep an eye on the size.
#
# Needs the pmtiles CLI (brew install pmtiles).
# Usage: sh scripts/build_basemap.sh [YYYYMMDD]   (default: yesterday's build)
set -e
cd "$(dirname "$0")/.."
DAY=${1:-$(date -v-1d +%Y%m%d 2>/dev/null || date -d yesterday +%Y%m%d)}
pmtiles extract "https://build.protomaps.com/$DAY.pmtiles" data/sarawak.pmtiles \
  --bbox=109.4,0.8,115.8,5.15 --maxzoom=14
ls -lh data/sarawak.pmtiles
