# Schema Auto-Healing System

## Overview
The text-to-query system now automatically detects missing measures in your Cube.js schema and adds them on-the-fly.

## How It Works

1. **User asks a question** (e.g., "How many films are less than 90 minutes?")
2. **LLM generates a query** that uses `Film.count`
3. **Cube.js returns an error** because `count` measure doesn't exist
4. **Schema Healer automatically**:
   - Detects the missing measure error
   - Adds the `count` measure to `Film.js`
   - Returns a helpful message to the user

## What Gets Auto-Added

Currently supports these common measures:
- **count**: Total count of records (`sql: "1", type: "count"`)
- **total**: Alias for count

## User Workflow

When you encounter a missing measure:

1. The error message will show: **"✨ Schema Auto-Fixed!"**
2. The system tells you: *"Added count to Film cube. Please restart Cube.js server for changes to take effect, then retry your query."*
3. **Restart your Cube.js server**: `Ctrl+C` and restart
4. **Retry your query** - it will now work!

## Files Modified

- `text_to_query/schema_healer.py` - Core healing logic
- `text_to_query/server.py` - Integration with query execution
- `text_to_query/static/index.html` - UI for healing messages
- `cubes/Film.js` - Example: now has a `count` measure

## Example

**Before auto-healing**, `Film.js` had only dimensions:
```javascript
cube(`Film`, {
  dimensions: { ... },
  // No measures!
});
```

**After auto-healing**, it automatically added:
```javascript
cube(`Film`, {
  dimensions: { ... },
  measures: {
    count: {
      sql: `1`,
      type: `count`,
      description: `Total count of records in this cube`,
    },
  },
});
```

## Extending

To add more auto-healable measures, edit `schema_healer.py`:

```python
COMMON_MEASURES = {
    "count": {...},
    "total": {...},
    "avg_length": {  # Add new measure
        "sql": "length",
        "type": "avg",
        "description": "Average length",
    },
}
```

## Benefits

- **No more one-off fixes** - measures are added automatically
- **Self-improving** - schema grows with usage
- **User-friendly** - clear feedback when healing occurs
- **Non-destructive** - only adds missing measures, doesn't modify existing ones
