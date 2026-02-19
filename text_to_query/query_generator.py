"""
LLM-powered query generator.

Converts natural language questions to Cube.js queries using an LLM.
"""

import json
import httpx
from typing import Dict, Any, Optional

from .config import LLMConfig

SYSTEM_PROMPT = """You are an expert at converting natural language questions into Cube.js query JSON.

Cube.js Query Format:
{
  "dimensions": ["Cube.dimension_name"],  // Fields to select
  "measures": ["Cube.measure_name"],      // Aggregations
  "filters": [                            // WHERE conditions
    {
      "member": "Cube.field_name",
      "operator": "equals|contains|gte|lte|gt|lt|notEquals",
      "values": ["value"]
    }
  ],
  "order": {                              // ORDER BY
    "Cube.field_name": "asc|desc"
  },
  "limit": 100                            // LIMIT
}

Important Rules:
1. Dimension and measure names use snake_case (e.g., "first_name" not "firstName")
2. Always reference fields as "CubeName.field_name"
3. Use the EXACT cube and field names from the schema
4. For aggregations (count, sum, avg), use measures if available
5. If no measures are defined, you can only query dimensions
6. Keep queries focused - don't add unnecessary fields
7. Use appropriate operators: equals, contains, gte (>=), lte (<=), gt (>), lt (<)
8. For text search, use "contains" operator
9. Default limit to 50 unless user specifies otherwise
10. NEVER include a "joins" key - joins are defined in the schema, not in queries

Response Format:
Return ONLY a valid JSON object with the query. No explanation, no markdown, just JSON.

If the question is unclear or cannot be answered with available data, return:
{
  "error": "Explanation of why query cannot be generated"
}
"""


class QueryGenerator:
    """Generates Cube.js queries from natural language using LLM."""

    def __init__(self, config: LLMConfig):
        self.config = config

    async def generate_query(
        self,
        question: str,
        schema_context: str,
        conversation_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Generate a Cube.js query from a natural language question.

        Args:
            question: Natural language question
            schema_context: Formatted schema description
            conversation_history: Previous messages for context

        Returns:
            Dict with either "query" or "error" key
        """
        # Build the full prompt
        user_prompt = f"{SYSTEM_PROMPT}\n\n"
        user_prompt += f"# Available Schema\n\n{schema_context}\n\n"
        user_prompt += f"# User Question\n\n{question}\n\n"
        user_prompt += "Generate the Cube.js query JSON:"

        # Make API request
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.config.construct_url("messages"),
                    headers=self.config.get_headers(),
                    json={
                        "model": self.config.model,
                        "max_tokens": self.config.max_tokens,
                        "temperature": self.config.temperature,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract the generated query
                content = data["content"][0]["text"]

                # Try to parse as JSON
                try:
                    # Remove markdown code blocks if present
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()

                    query = json.loads(content)

                    # Validate query structure
                    if "error" in query:
                        return {"error": query["error"], "raw_response": content}

                    return {
                        "query": query,
                        "raw_response": content,
                        "model": self.config.model,
                    }

                except json.JSONDecodeError as e:
                    return {
                        "error": f"Failed to parse LLM response as JSON: {str(e)}",
                        "raw_response": content,
                    }

            except httpx.HTTPError as e:
                return {"error": f"HTTP error communicating with LLM: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

    async def refine_query(
        self,
        original_question: str,
        original_query: Dict,
        feedback: str,
        schema_context: str,
    ) -> Dict[str, Any]:
        """
        Refine a query based on user feedback.

        Args:
            original_question: Original natural language question
            original_query: Previously generated query
            feedback: User feedback on what to change
            schema_context: Schema description

        Returns:
            Dict with refined query or error
        """
        user_prompt = f"{SYSTEM_PROMPT}\n\n"
        user_prompt += f"# Available Schema\n\n{schema_context}\n\n"
        user_prompt += f"# Original Question\n\n{original_question}\n\n"
        user_prompt += f"# Previous Query\n\n{json.dumps(original_query, indent=2)}\n\n"
        user_prompt += f"# User Feedback\n\n{feedback}\n\n"
        user_prompt += "Generate the refined Cube.js query JSON:"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.config.construct_url("messages"),
                    headers=self.config.get_headers(),
                    json={
                        "model": self.config.model,
                        "max_tokens": self.config.max_tokens,
                        "temperature": self.config.temperature,
                        "messages": [{"role": "user", "content": user_prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()

                content = data["content"][0]["text"]

                # Clean and parse
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                query = json.loads(content)

                if "error" in query:
                    return {"error": query["error"], "raw_response": content}

                return {
                    "query": query,
                    "raw_response": content,
                    "model": self.config.model,
                }

            except Exception as e:
                return {"error": f"Failed to refine query: {str(e)}"}
