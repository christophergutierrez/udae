# Text-to-Query Examples

Example natural language questions you can ask.

## Simple Queries

### List Data
```
"Show me all customers"
"List all films"
"What actors are in the database?"
```

### With Limits
```
"Show me 10 customers"
"List the first 20 films"
"Give me 5 actors"
```

## Filtered Queries

### Text Filters
```
"Show me customers in California"
"Find actors whose last name is Smith"
"List films with 'love' in the title"
```

### Numeric Filters
```
"Show me films longer than 120 minutes"
"List films with rental rate above 4 dollars"
"Find films released after 2000"
```

### Category Filters
```
"Show me R-rated films"
"List PG-13 movies"
"Find films rated G or PG"
```

### Boolean Filters
```
"Show me active customers"
"List inactive customers"
```

## Sorted Queries

### Ascending
```
"Show me customers sorted by name"
"List films alphabetically"
"Order actors by last name"
```

### Descending
```
"Show me the longest films"
"List films by length, longest first"
"What are the most expensive films to rent?"
```

### Top N
```
"Show me the top 10 longest films"
"What are the 5 shortest movies?"
"List the top 20 customers by name"
```

## Multi-Table Queries

### Customer + Location
```
"Show me customers and their cities"
"List customers with their addresses"
"What customers are in each country?"
```

### Film + Category
```
"Show me films and their categories"
"List action films"
"What horror movies do we have?"
```

### Customer + Rentals + Films
```
"Show me customers and the films they rented"
"List rentals with customer names and film titles"
"What films did John Smith rent?"
```

### Actor + Films
```
"Show me actors and their films"
"List films starring Tom Hanks"
"What movies is Jennifer Lawrence in?"
```

## Complex Queries

### Multiple Filters
```
"Show me action films rated R released after 2000"
"List PG-13 comedies longer than 100 minutes"
"Find active customers in California"
```

### Geographic Analysis
```
"How many customers are in each country?"
"Show me customer distribution by city"
"List stores and their locations"
```

### Combined Conditions
```
"Show me long R-rated action films"
"List recent PG films under 90 minutes"
"Find customers in California who are active"
```

## Business Questions

### Customer Analysis
```
"Who are our customers?"
"Where are most of our customers located?"
"How many customers do we have?"
"Show me customer distribution by country"
```

### Film Catalog
```
"What films do we have?"
"Show me our film categories"
"What are our longest films?"
"List films by rating"
```

### Inventory
```
"What films are available in each store?"
"Show me inventory by location"
```

### Staff & Stores
```
"Show me our staff members"
"List stores and their addresses"
"What staff work at each store?"
```

## API Examples

### Using curl

**Simple query:**
```bash
curl -X POST http://localhost:5001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me customers in California", "execute": true}'
```

**Generate without executing:**
```bash
curl -X POST http://localhost:5001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me top 10 films", "execute": false}'
```

**Execute pre-built query:**
```bash
curl -X POST http://localhost:5001/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "dimensions": ["Customer.first_name", "Customer.last_name"],
      "limit": 10
    }
  }'
```

**Get schema:**
```bash
curl http://localhost:5001/api/schema
```

### Using Python

```python
import requests

# Ask a question
response = requests.post('http://localhost:5001/api/query', json={
    'question': 'Show me customers in California',
    'execute': True
})

data = response.json()
if data['success']:
    print(f"Found {data['count']} results")
    for row in data['results']:
        print(row)
```

### Using JavaScript

```javascript
async function askQuestion(question) {
    const response = await fetch('http://localhost:5001/api/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            question: question,
            execute: true
        })
    });

    const data = await response.json();

    if (data.success) {
        console.log(`Found ${data.count} results`);
        console.table(data.results);
    } else {
        console.error(data.error);
    }
}

// Use it
askQuestion('Show me top 10 longest films');
```

## Expected Query Formats

### Simple Selection
**Question:** "Show me customers"
**Generated Query:**
```json
{
  "dimensions": ["Customer.first_name", "Customer.last_name", "Customer.email"],
  "limit": 50
}
```

### With Filter
**Question:** "Show me customers in California"
**Generated Query:**
```json
{
  "dimensions": ["Customer.first_name", "Customer.last_name"],
  "filters": [{
    "member": "Address.district",
    "operator": "equals",
    "values": ["California"]
  }],
  "limit": 50
}
```

### With Sorting
**Question:** "Show me the longest films"
**Generated Query:**
```json
{
  "dimensions": ["Film.title", "Film.length", "Film.rating"],
  "order": {
    "Film.length": "desc"
  },
  "limit": 50
}
```

### Complex Multi-Table
**Question:** "Show me action films released after 2000"
**Generated Query:**
```json
{
  "dimensions": [
    "Film.title",
    "Film.release_year",
    "Film.rating",
    "Category.name"
  ],
  "filters": [
    {
      "member": "Category.name",
      "operator": "equals",
      "values": ["Action"]
    },
    {
      "member": "Film.release_year",
      "operator": "gte",
      "values": ["2000"]
    }
  ],
  "limit": 50
}
```

## Tips for Better Results

### Be Specific
❌ "Show me data"
✅ "Show me customer names and emails"

### Use Table Names
❌ "Show me people"
✅ "Show me customers"

### Specify Limits
❌ "Show all films" (might return thousands)
✅ "Show me the top 20 films"

### Use Clear Operators
✅ "films longer than 100 minutes"
✅ "customers in California"
✅ "films released after 2000"
✅ "names starting with 'A'"

### Break Down Complex Questions
Instead of: "Show me all active customers in California who rented action films in the last month"

Try:
1. "Show me active customers in California"
2. Then refine: "add their rental history"
3. Then refine: "only action films"

## Common Issues

### "No results found"
- Check your filter values (case-sensitive)
- Try broader search first, then narrow down
- Use "contains" instead of "equals" for partial matches

### "Query failed"
- Question might be ambiguous
- Try simpler version first
- Check available cubes with GET /api/schema

### "Invalid query"
- LLM might have misunderstood question
- Be more specific about which tables/fields
- Use field names from the schema

## Testing Queries

Use the web interface at http://localhost:5001 to:
- See generated queries before execution
- View results in formatted tables
- Iterate on questions
- Copy queries for API use

Or use the API for programmatic testing:
```bash
# Generate query without executing
curl -X POST http://localhost:5001/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "your question", "execute": false}' | jq .
```
