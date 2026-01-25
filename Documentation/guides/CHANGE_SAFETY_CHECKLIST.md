# Change Safety Checklist

Use this checklist before making any changes to ensure nothing breaks.

## ✅ Pre-Change Checklist

### Before Adding New Fields

- [ ] **Update `types/property.ts`** - Add field to interface (make optional)
- [ ] **Update `PropertyNormalizer.normalize()`** - Add normalization logic
- [ ] **Update `PropertyNormalizer.getSafeValue()`** - Add default value
- [ ] **Test with missing field** - Verify component handles null/undefined
- [ ] **Test with old data** - Verify backward compatibility
- [ ] **Run validation** - `./scripts/validate_changes.sh`

### Before Modifying PropertyCard

- [ ] **Use `getSafeValue()`** - Never access `property.field` directly
- [ ] **Add null checks** - `{value != null && <div>{value}</div>}`
- [ ] **Provide defaults** - `getSafeValue('field', 'default')`
- [ ] **Test with partial data** - Some fields missing
- [ ] **Test with null values** - All fields null
- [ ] **Check console** - No warnings in development

### Before Adding Features

- [ ] **Make it optional** - Use feature flags or optional props
- [ ] **Add graceful fallback** - If feature fails, use old behavior
- [ ] **Test feature off** - Verify old behavior still works
- [ ] **Test feature on** - Verify new behavior works
- [ ] **Document changes** - Update relevant docs

### Before Changing API

- [ ] **Keep old fields** - Don't remove, make optional instead
- [ ] **Add new fields** - As optional, with defaults
- [ ] **Update normalizer** - Handle both old and new formats
- [ ] **Test old responses** - Verify still works
- [ ] **Test new responses** - Verify new features work

## 🔍 Validation Commands

```bash
# Run full validation
./scripts/validate_changes.sh

# Check TypeScript
cd frontend && npm run build

# Check linting
cd frontend && npm run lint

# Check Python
cd backend && python3 -m py_compile main.py
```

## 🛡️ Safety Patterns

### ✅ DO

```typescript
// Use safe getters
const value = getSafeValue('field', 'default')

// Check before rendering
{getSafeValue('field') != null && <div>{value}</div>}

// Use normalized data
const normalized = PropertyNormalizer.normalize(property)

// Validate in development
DevelopmentSafety.validatePropertyBeforeRender(property, 'Component')
```

### ❌ DON'T

```typescript
// Don't access directly
const value = property.field  // ❌ Can be undefined

// Don't assume field exists
<div>{property.new_field}</div>  // ❌ Breaks if missing

// Don't remove required fields
interface Property {
  // address removed  // ❌ Breaks old data
}

// Don't change types without migration
assessed_value: string  // ❌ Was number
```

## 📝 Quick Reference

### Adding a New Field

1. Add to `PropertyExtended` interface (optional)
2. Add to `PropertyNormalizer.normalize()`
3. Use `getSafeValue('new_field', default)` in components
4. Test with missing data

### Modifying Layout

1. Use conditional rendering
2. Check data exists before rendering
3. Provide fallbacks
4. Test with various data states

### Adding Functionality

1. Make it optional/feature-flagged
2. Add graceful degradation
3. Test with feature on/off
4. Document changes

## 🚨 Red Flags

If you see these, STOP and fix:

- ❌ Direct property access: `property.field`
- ❌ Missing null checks: `{property.field}`
- ❌ Required fields removed
- ❌ Type changes without migration
- ❌ No defaults for new fields
- ❌ Breaking existing functionality

## ✅ Green Flags

These indicate safe changes:

- ✅ Using `getSafeValue()`
- ✅ Null checks before rendering
- ✅ Optional new fields
- ✅ Backward compatible
- ✅ Default values provided
- ✅ Validation in place

---

**Remember**: When in doubt, make it optional, add defaults, and test with missing data!
