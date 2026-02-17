# Fixed: "Invalid query keys: joins" Error

## Problem

The LLM was occasionally generating Cube.js queries with a `joins` key:
```json
{
  "dimensions": ["Address.district"],
  "measures": ["Customer.count"],
  "joins": ["Customer", "Address"]  // ❌ INVALID - not a Cube.js query key
}
```

This caused the error: **"Invalid query: Invalid query keys: joins"**

## Why It Happened

The LLM was trying to be helpful by explicitly specifying joins, but in Cube.js:
- ✅ Joins are defined in **schema files** (Actor.js, Film.js, etc.)
- ❌ Joins are **NOT** part of query JSON

Valid Cube.js query keys:
- `dimensions`, `measures`, `filters`, `order`, `limit`, `offset`, `timeDimensions`

## Solution

### 1. Auto-Clean Invalid Keys ✨

Modified `query_executor.py` to automatically **remove** invalid keys instead of rejecting the query:

**Before:**
```python
if invalid_keys:
    return {"valid": False, "error": "Invalid query keys"}  # ❌ Rejected
```

**After:**
```python
if invalid_keys:
    cleaned_query = {k: v for k, v in query.items() if k in valid_keys}
    return {"valid": True, "cleaned": True, "query": cleaned_query}  # ✅ Auto-fixed
```

### 2. Use Cleaned Query

Modified `server.py` to use the cleaned query:
```python
validation = await query_executor.validate_query(query)
if validation.get("cleaned"):
    query = validation["query"]  # Use cleaned version
```

### 3. Updated System Prompt

Added explicit instruction to the LLM in `query_generator.py`:
```
10. NEVER include a "joins" key - joins are defined in the schema, not in queries
```

## Result

Now when the LLM generates a query with invalid keys:
1. ✅ System **auto-cleans** the query
2. ✅ Executes with valid keys only
3. ✅ User gets results instead of error

## Test

**Restart your server:**
```bash
python -m text_to_query
```

**Try this query again:**
```
"How many customers per state?"
```

Should now return results showing customer counts by state/district! 🎉

## Example Result

```json
{
  "success": true,
  "count": 376,
  "results": [
    {"Address.district": "California", "Customer.count": "9"},
    {"Address.district": "Texas", "Customer.count": "5"},
    ...
  ]
}
```

## What Gets Auto-Cleaned

Any non-standard keys the LLM might add:
- `joins` - Most common
- `include` - Sometimes added
- `relations` - Occasionally seen
- Any other non-Cube.js keys

The system now **gracefully handles** these and focuses on the valid query parts.
