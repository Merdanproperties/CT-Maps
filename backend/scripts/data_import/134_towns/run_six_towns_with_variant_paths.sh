#!/usr/bin/env bash
# Run the 6 towns that have filename variants (cleaned Excel + CSV paths).
# Ensure Postgres is running before running this script.
# Usage: from project root (CT Maps): bash backend/scripts/data_import/134_towns/run_six_towns_with_variant_paths.sh
# To follow output: tail -f backend/scripts/data_import/134_towns/logs/six_towns_import_*.log

set -e
cd "$(dirname "$0")/../../../../"
CLEANED="/Users/jacobmermelstein/Desktop/CT Data/2025 Post Duplicate Clean"
CSV_DIR="/Users/jacobmermelstein/Desktop/CT Data/2025 Parcel Collection"
LOG="backend/scripts/data_import/134_towns/logs/six_towns_import_$(date +%Y%m%d_%H%M%S).log"
mkdir -p backend/scripts/data_import/134_towns/logs

echo "Log file: $LOG"
echo "Tail with: tail -f $LOG"
echo ""

{
  echo "=== Six towns import started $(date) ==="
  python3 backend/scripts/data_import/134_towns/import_town_optimized.py "Barkhamsted" --cleaned-excel "$CLEANED/Barkhamstead_CAMA_2025_CLEANED.xlsx" --csv "$CSV_DIR/Barkhamstead_CAMA_2025.csv"
  echo "---"
  python3 backend/scripts/data_import/134_towns/import_town_optimized.py "Franklin" --cleaned-excel "$CLEANED/Franklin_OPM7_100L_CLEANED.xlsx" --csv "$CSV_DIR/Franklin_OPM7_100L.csv"
  echo "---"
  python3 backend/scripts/data_import/134_towns/import_town_optimized.py "New Fairfield" --cleaned-excel "$CLEANED/New Fairfield__CAMA_2025_CLEANED.xlsx" --csv "$CSV_DIR/New Fairfield__CAMA_2025.csv"
  echo "---"
  python3 backend/scripts/data_import/134_towns/import_town_optimized.py "Winchester" --cleaned-excel "$CLEANED/Winsted_CAMA_2025_CLEANED.xlsx" --csv "$CSV_DIR/Winsted_CAMA_2025.csv"
  echo "---"
  python3 backend/scripts/data_import/134_towns/import_town_optimized.py "Wolcott" --cleaned-excel "$CLEANED/Wolcott_2025_CAMA_CLEANED.xlsx" --csv "$CSV_DIR/Wolcott_2025_CAMA.csv"
  echo "---"
  python3 backend/scripts/data_import/134_towns/import_town_optimized.py "Woodbridge" --cleaned-excel "$CLEANED/Woobridge_CAMA_2025_CLEANED.xlsx" --csv "$CSV_DIR/Woobridge_CAMA_2025.csv"
  echo "=== Six towns import finished $(date) ==="
} 2>&1 | tee "$LOG"
