#!/bin/bash

# Validate Changes Script - Run before committing to ensure nothing breaks
# This script validates type safety, data structures, and backward compatibility

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "🔍 Validating changes before commit..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to check for errors
check_error() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ $1${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    else
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    fi
}

check_warning() {
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠️  $1${NC}"
        WARNINGS=$((WARNINGS + 1))
        return 1
    else
        return 0
    fi
}

# 1. Check TypeScript compilation
echo "1. Checking TypeScript compilation..."
cd "$FRONTEND_DIR"
if npm run build --silent > /dev/null 2>&1; then
    echo -e "${GREEN}✅ TypeScript compiles successfully${NC}"
else
    echo -e "${RED}❌ TypeScript compilation errors found${NC}"
    npm run build 2>&1 | head -20
    ERRORS=$((ERRORS + 1))
fi

# 2. Check for linting errors
echo ""
echo "2. Checking for linting errors..."
if npm run lint --silent > /dev/null 2>&1; then
    echo -e "${GREEN}✅ No linting errors${NC}"
else
    echo -e "${YELLOW}⚠️  Linting warnings found${NC}"
    npm run lint 2>&1 | head -20
    WARNINGS=$((WARNINGS + 1))
fi

# 3. Check Python syntax
echo ""
echo "3. Checking Python syntax..."
cd "$BACKEND_DIR"
if python3 -m py_compile main.py 2>/dev/null; then
    echo -e "${GREEN}✅ Python syntax valid${NC}"
else
    echo -e "${RED}❌ Python syntax errors${NC}"
    python3 -m py_compile main.py
    ERRORS=$((ERRORS + 1))
fi

# 4. Check for required files
echo ""
echo "4. Checking required files..."
REQUIRED_FILES=(
    "frontend/src/types/property.ts"
    "frontend/src/utils/developmentSafety.ts"
    "frontend/src/components/PropertyCard.tsx"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo -e "${GREEN}✅ $file exists${NC}"
    else
        echo -e "${RED}❌ Required file missing: $file${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# 5. Check for breaking changes in PropertyCard
echo ""
echo "5. Checking PropertyCard for safe patterns..."
if grep -q "getSafeValue" "$FRONTEND_DIR/src/components/PropertyCard.tsx"; then
    echo -e "${GREEN}✅ PropertyCard uses safe value getters${NC}"
else
    echo -e "${YELLOW}⚠️  PropertyCard may not use safe value getters${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# 6. Check for PropertyNormalizer usage
if grep -q "PropertyNormalizer" "$FRONTEND_DIR/src/components/PropertyCard.tsx"; then
    echo -e "${GREEN}✅ PropertyCard uses PropertyNormalizer${NC}"
else
    echo -e "${YELLOW}⚠️  PropertyCard may not normalize data${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Summary
echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All validations passed! Safe to commit.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Validations passed with $WARNINGS warning(s)${NC}"
    echo "Review warnings above before committing."
    exit 0
else
    echo -e "${RED}❌ Validation failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    echo "Please fix errors before committing."
    exit 1
fi
