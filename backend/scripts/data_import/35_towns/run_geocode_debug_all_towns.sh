#!/usr/bin/env bash
# Run geocode+spatial import for each town in towns_35_geocode_spatial.txt (except Avon)
# to generate geocode_debug_{Town}_{timestamp}.xlsx in backend/scripts/data_import/35_towns/logs/
# Usage: from project root:
#   bash backend/scripts/data_import/35_towns/run_geocode_debug_all_towns.sh
# Or in background with log:
#   nohup bash backend/scripts/data_import/35_towns/run_geocode_debug_all_towns.sh > geocode_all_towns.log 2>&1 &
#   tail -f geocode_all_towns.log

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOWNS_FILE="$SCRIPT_DIR/towns_35_geocode_spatial.txt"

cd "$PROJECT_ROOT"
export PYTHONUNBUFFERED=1

while IFS= read -r town; do
  [ -z "$town" ] && continue
  [ "$town" = "Avon" ] && continue
  echo ""
  echo "========== $town =========="
  python3 backend/scripts/data_import/35_towns/import_town_geocode_spatial.py --town "$town" || true
done < "$TOWNS_FILE"

echo ""
echo "Done. Check backend/scripts/data_import/35_towns/logs/ for geocode_debug_*.xlsx"
