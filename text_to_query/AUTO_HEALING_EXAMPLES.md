# Auto-Healing Examples

## ✅ 5 Questions That WILL Auto-Heal

These questions will trigger auto-healing because they use generic, context-free measures that require no domain knowledge:

### 1. "How many customers do we have?"
**Missing Measure:** `Customer.count`
**Why Auto-Healable:** Count is a universal measure that works the same way for any cube - just count the records.
```javascript
count: {
  sql: `1`,
  type: `count`,
  description: `Total count of records in this cube`
}
```

### 2. "Show me the total number of rentals"
**Missing Measure:** `Rental.total` (or `Rental.count`)
**Why Auto-Healable:** "total" is an alias for count - no domain knowledge needed, just counting rows.

### 3. "How many actors are in the database?"
**Missing Measure:** `Actor.count`
**Why Auto-Healable:** Same as above - count is universal and requires no business logic.

### 4. "What's the total number of films in each category?"
**Missing Measure:** `Film.count` or `FilmCategory.count`
**Why Auto-Healable:** Counting is a generic operation that works regardless of what you're counting.

### 5. "How many stores are there?"
**Missing Measure:** `Store.count`
**Why Auto-Healable:** Pure counting - no need to know anything about the business domain.

---

## ❌ 5 Questions That CANNOT Auto-Heal

These questions require domain-specific knowledge or business logic that the system cannot infer:

### 1. "What's the total revenue from rentals?"
**Missing Measure:** `Rental.totalRevenue` or `Payment.totalRevenue`
**Why NOT Auto-Healable:**
- Requires knowing WHICH column contains revenue (`Payment.amount`)
- Requires knowing the aggregation type (SUM, not COUNT)
- Business logic: Should it include refunds? Tax? Which payments?
```javascript
// System doesn't know this:
totalRevenue: {
  sql: `amount`,  // ← Which column?
  type: `sum`,    // ← System can't infer this
  description: `Total revenue`
}
```

### 2. "What's the average film length?"
**Missing Measure:** `Film.avgLength`
**Why NOT Auto-Healable:**
- Requires knowing the specific column (`length`)
- Requires knowing the aggregation (AVG)
- Column name could be `length`, `duration`, `runtime`, etc.
```javascript
// System doesn't know:
avgLength: {
  sql: `length`,  // ← Which column has the length?
  type: `avg`,
  description: `Average film length in minutes`
}
```

### 3. "What's the total value of our inventory?"
**Missing Measure:** `Inventory.totalValue` or `Film.inventoryValue`
**Why NOT Auto-Healable:**
- Complex business logic: `replacement_cost * inventory_count`?
- May need joins between Film and Inventory
- Business decision: use `rental_rate` or `replacement_cost`?
```javascript
// System doesn't know:
totalValue: {
  sql: `${Film}.replacement_cost * COUNT(${Inventory}.inventory_id)`,
  type: `number`,
  description: `Total inventory value`
}
```

### 4. "How much money did each customer spend?"
**Missing Measure:** `Customer.totalSpent`
**Why NOT Auto-Healable:**
- Requires join to Payment table
- Requires SUM aggregation
- Requires knowing the relationship between Customer and Payment
```javascript
// System doesn't know:
totalSpent: {
  sql: `${Payment}.amount`,  // ← Requires join
  type: `sum`,
  description: `Total amount spent by customer`
}
```

### 5. "What percentage of films are rated R?"
**Missing Measure:** `Film.percentageRated` or `Film.rRatedPercentage`
**Why NOT Auto-Healable:**
- Requires complex calculation: `COUNT(IF rating='R') / COUNT(*) * 100`
- Needs domain knowledge about the `rating` column
- Requires conditional logic
```javascript
// System doesn't know:
rRatedPercentage: {
  sql: `CASE WHEN rating = 'R' THEN 1 ELSE 0 END`,
  type: `avg`,  // ← avg of 0/1 gives percentage
  description: `Percentage of R-rated films`
}
```

---

## Key Insight: The Auto-Healing Boundary

**Auto-healable:** Measures that are **context-free aggregations**
- Count, total - work the same for any entity
- No column names needed (use `1` for counting)
- No business logic required

**NOT auto-healable:** Measures requiring **domain knowledge**
- Which column to aggregate (revenue, length, cost)
- What aggregation to use (sum, avg, min, max)
- Complex calculations or business rules
- Joins to other tables

---

## Expanding Auto-Healing

You could extend it to handle more cases by adding patterns, for example:

```python
# In schema_healer.py
SMART_MEASURES = {
    "min_*": {  # Pattern matching
        "infer_from": "dimensions",  # Find matching dimension
        "type": "min",
    },
    "max_*": {
        "infer_from": "dimensions",
        "type": "max",
    },
}
```

But this gets complex quickly because you need to:
1. Parse the measure name to find the column
2. Verify the column exists
3. Handle naming variations (avgLength vs avg_length vs averageLength)

**The sweet spot:** Auto-heal only the truly generic measures (count/total) where there's zero ambiguity.
