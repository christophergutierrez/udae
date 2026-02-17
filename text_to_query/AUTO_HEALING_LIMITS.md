# Auto-Healing: What Can and Cannot Be Fixed

## ✅ CAN Auto-Heal

### 1. Missing Generic Measures
**Example:** "How many actors are there?"
**Error:** `'count' not found for path 'Actor.count'`
**Fix:** Automatically adds:
```javascript
count: { sql: `1`, type: `count`, description: `Total count of records` }
```
**User sees:** ✨ Auto-Healed! Results shown immediately.

---

## ❌ CANNOT Auto-Heal (With Helpful Explanations)

### 2. Missing Domain-Specific Measures
**Example:** "What's our total revenue?"
**Error:** `'amount' not found for path 'Payment.amount'`
**Why can't fix:**
- Don't know which column to aggregate
- Don't know aggregation type (SUM? AVG?)
- Requires business logic knowledge

**User sees:**
```
⚠️ Cannot Auto-Fix
'amount' is missing from Payment cube. This measure requires domain
knowledge (which column? what aggregation type?) and must be added manually.
```

---

### 3. Missing Join Paths (NEW!)
**Example:** "How many actors are there per state?"
**Error:** `Can't find join path to join 'Actor', 'Address'`
**Why can't fix:**
- Don't know if tables are actually related in database
- Don't know which columns to join on
- Don't know relationship type (1:1, 1:many, many:many)
- Query might be semantically impossible

**User sees:**
```
🔗 Cannot Auto-Fix
No join path exists between Actor and Address. This requires understanding
your database schema to add proper join relationships.
Tip: Check if these tables are actually related, or try querying separately.
```

---

## Technical Complexity

| Error Type | Complexity | Can Auto-Fix? | Reasoning |
|-----------|-----------|---------------|-----------|
| Missing `count` | ⭐ Easy | ✅ Yes | Generic, same for all cubes |
| Missing `totalRevenue` | ⭐⭐⭐ Hard | ❌ No | Need column name + aggregation |
| Missing `avgLength` | ⭐⭐⭐ Hard | ❌ No | Need column name + AVG type |
| Missing join path | ⭐⭐⭐⭐ Very Hard | ❌ No | Need FK relationships + schema knowledge |

---

## Why Join Healing is So Hard

**Missing Count (Easy):**
```javascript
// Same for every cube - just add it!
count: { sql: `1`, type: `count` }
```

**Missing Join (Impossible):**
```javascript
// Too many unknowns:
joins: {
  Address: {
    // What relationship? belongsTo? hasMany?
    relationship: "???",

    // What columns? Need to know foreign keys!
    sql: `${CUBE}.??? = ${Address}.???`
  }
}
```

You'd need to:
1. Query the database for foreign key relationships
2. Determine if join makes semantic sense
3. Find intermediate tables for indirect joins (Actor → Staff → Address?)
4. Add joins to BOTH cube files
5. Restart Cube.js

---

## Real Example: Actor + Address

In the Pagila (DVD rental) database:
- **Customers** have addresses ✅
- **Staff** have addresses ✅
- **Actors** DO NOT have addresses ❌

Actors are just names in the actor table. They don't "live" anywhere in the system.

**The query "actors per state" is semantically impossible.**

---

## Alternative: Suggest Valid Queries

Instead of auto-healing impossible queries, we help users understand:

**User asks:** "How many actors are there per state?"

**System responds:**
```
🔗 Cannot Auto-Fix
No join path exists between Actor and Address.

💡 Did you mean one of these instead?
- "How many customers are there per state?" (Customer → Address)
- "How many staff members are there per state?" (Staff → Address)
- "How many actors are there?" (Actor alone, no geography)
```

---

## Future Enhancement Ideas

### 1. Auto-Detect Foreign Keys
Query the database metadata to find foreign key relationships:
```sql
SELECT * FROM information_schema.key_column_usage
WHERE table_name = 'actor'
```

### 2. Suggest Join Paths
If Actor → Staff → Address path exists, suggest:
```
"To join Actor to Address, you need to go through Staff table"
```

### 3. Learn from Schema
Parse the database schema to understand all relationships, then auto-generate join suggestions.

---

## Current Status

✅ **Auto-heals:** Missing generic measures (`count`, `total`)
✅ **Explains:** Why domain-specific measures can't be fixed
✅ **Explains:** Why join paths can't be added
🎯 **Next step:** Suggest alternative valid queries based on schema
