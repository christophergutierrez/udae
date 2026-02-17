# Migration: Schema Healing → Query Fixing

**Date:** February 2026
**Status:** Complete

## What Changed

### **OLD Approach (Removed): Schema Healing**
- Modified `.js` schema files on disk when measures were missing
- Required Docker restart to reload schemas
- Fragile, could corrupt schemas
- Only handled missing measures

### **NEW Approach (Implemented): Query Fixing**
- LLM analyzes failed queries and generates corrected versions
- Works entirely in memory (no file modifications)
- Instant retry (no restart needed)
- Handles many error types (wrong joins, wrong cubes, missing measures)

## Files Changed

### Added:
- `text_to_query/query_fixer.py` - LLM-based query error analysis and fixing

### Modified:
- `text_to_query/server.py` - Replaced `execute_with_healing()` with `execute_with_fixing()`
- `text_to_query/static/index.html` - Updated UI for fix status (auto_fixed, fix_attempted)
- `semantic_layer/cube_generator.py` - All cubes now auto-generate `count` measure + proper primary keys

### Deprecated (kept for reference):
- `text_to_query/AUTO_HEALING_EXAMPLES.md`
- `text_to_query/AUTO_HEALING_LIMITS.md`
- `text_to_query/ENHANCED_AUTO_HEALING.md`
- `text_to_query/SCHEMA_HEALING.md`
- `text_to_query/schema_healer.py` - Only used for error parsing now

### Created:
- `scripts/reset_cube.sh` - Idempotent schema regeneration from OpenMetadata

## How It Works Now

### Query Succeeds:
```
User Question → LLM generates query → Cube.js executes → Results ✅
```

### Query Fails (Fixable):
```
User Question → LLM generates query → Cube.js fails
                                      ↓
                             Query Fixer analyzes error
                                      ↓
                             Generates corrected query
                                      ↓
                             Cube.js executes → Results ✅
                             (UI shows: "✨ Auto-Fixed!")
```

### Query Fails (Not Fixable):
```
User Question → LLM generates query → Cube.js fails
                                      ↓
                             Query Fixer analyzes error
                                      ↓
                             Explains why it can't work
                             (UI shows: "🔧 Fix Attempted: [explanation]")
```

## Key Benefits

| Schema Healing | Query Fixing |
|----------------|--------------|
| ❌ Modifies files | ✅ Memory-only |
| ❌ Needs restart | ✅ Instant |
| ❌ Can corrupt | ✅ Safe |
| ❌ Single error type | ✅ Many error types |
| ❌ Manual fixes lost on regen | ✅ No manual fixes needed |

## Test Examples

**Port 5001** now has categorized examples:

1. **✅ Working Examples** - Work out of the box
2. **🔧 Broken but Can Fix** - "What countries have the most customers?"
   - LLM fixes by using CustomerList instead of joining Customer+Country
3. **❌ Broken and Can't Fix** - "What countries have the most actors?"
   - LLM explains Actors aren't linked to Countries in schema

## Architecture Change

**Before:**
```
Query fails → schema_healer.py → Modify Film.js → Restart Docker → Retry
```

**After:**
```
Query fails → query_fixer.py → Generate better query → Instant retry
```

## For Future Developers

- Schema healing is **disabled** - don't try to re-enable it
- Use `./scripts/reset_cube.sh` to regenerate schemas from OpenMetadata
- All cubes auto-generate `count` measures (no manual additions needed)
- Query errors are handled by `query_fixer.py` with LLM intelligence
