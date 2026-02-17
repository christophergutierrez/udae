"""
LLM-based query error fixer.

When queries fail, attempt to use an LLM to either:
1. Generate a corrected query that avoids the error
2. Explain why the query can't be fixed and provide guidance
"""

import json
import logging
from typing import Dict, Any, Optional

from anthropic import Anthropic

from .config import LLMConfig

logger = logging.getLogger(__name__)


class QueryFixer:
    """Uses LLM to fix query errors or explain why they can't be fixed."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = Anthropic(
            api_key=config.api_key,
            base_url=config.base_url
        )

    def attempt_fix(
        self,
        question: str,
        failed_query: Dict[str, Any],
        error_message: str,
        schema_context: str
    ) -> Dict[str, Any]:
        """
        Attempt to fix a failed query using LLM reasoning.

        Args:
            question: Original user question
            failed_query: The query that failed
            error_message: Error from Cube.js
            schema_context: Schema information for reference

        Returns:
            Dict with:
                - fixed: bool - Whether a fix was found
                - query: dict - Fixed query (if fixed=True)
                - explanation: str - What was fixed or why it can't be fixed
        """
        prompt = self._build_fix_prompt(question, failed_query, error_message, schema_context)

        try:
            logger.info(f"Attempting to fix query error: {error_message[:100]}...")

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            logger.debug(f"LLM fix response: {content[:200]}...")

            # Parse the LLM response
            result = self._parse_fix_response(content)
            return result

        except Exception as e:
            logger.error(f"Error during query fix attempt: {e}")
            return {
                "fixed": False,
                "explanation": f"Could not analyze error: {str(e)}"
            }

    def _build_fix_prompt(
        self,
        question: str,
        failed_query: Dict[str, Any],
        error_message: str,
        schema_context: str
    ) -> str:
        """Build the prompt for the LLM to fix the query."""
        return f"""You are a Cube.js query expert. A query failed and you need to either fix it or explain why it can't be fixed.

USER QUESTION:
{question}

FAILED QUERY:
```json
{json.dumps(failed_query, indent=2)}
```

ERROR MESSAGE:
{error_message}

AVAILABLE SCHEMA:
{schema_context}

INSTRUCTIONS:
Analyze the error and determine if you can fix the query. Common fixable issues:

1. **Wrong cube chosen**: If the error says "No join path exists between X and Y", check if the data exists in a single cube (like CustomerList which has denormalized city/country data)

2. **Invalid join**: If trying to join unrelated tables, see if you can query just one cube that has all needed dimensions

3. **Missing dimension filter**: If the question asks about location/category/status, make sure you're filtering on existing dimensions rather than trying to join

4. **Wrong approach**: Sometimes the LLM chooses to join when it should filter, or vice versa

If you CAN fix it, respond with:
FIXED: true
QUERY: <corrected JSON query>
EXPLANATION: <brief explanation of what you fixed>

If you CANNOT fix it, respond with:
FIXED: false
EXPLANATION: <explain why this query can't work and what the user should do instead>

Examples of good explanations:
- "Fixed: Changed from joining CustomerList+Address to just using CustomerList.city filter, since CustomerList already contains location data"
- "Cannot fix: These tables have no relationship in the database. Try querying Film separately from Payment, or ask about rentals which connects them"

Respond now:"""

    def _parse_fix_response(self, content: str) -> Dict[str, Any]:
        """Parse the LLM's fix response."""
        lines = content.strip().split('\n')
        result = {
            "fixed": False,
            "explanation": ""
        }

        # Look for FIXED: true/false
        for line in lines:
            if line.startswith("FIXED:"):
                result["fixed"] = "true" in line.lower()
                break

        # Extract explanation
        explanation_lines = []
        in_explanation = False
        for line in lines:
            if line.startswith("EXPLANATION:"):
                in_explanation = True
                explanation_lines.append(line.replace("EXPLANATION:", "").strip())
            elif in_explanation and not line.startswith("QUERY:"):
                explanation_lines.append(line.strip())

        result["explanation"] = " ".join(explanation_lines).strip()

        # Extract query if fixed
        if result["fixed"]:
            # Find JSON in the response
            try:
                # Look for QUERY: marker
                query_start = content.find("QUERY:")
                if query_start != -1:
                    json_content = content[query_start + 6:].strip()
                    # Find the JSON object
                    if json_content.startswith("```"):
                        # Remove markdown code blocks
                        json_content = json_content.split("```")[1]
                        if json_content.startswith("json"):
                            json_content = json_content[4:]

                    # Try to parse JSON
                    result["query"] = json.loads(json_content.strip())
                else:
                    # Try to find any JSON in the response
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        result["query"] = json.loads(content[start:end])
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse fixed query JSON: {e}")
                result["fixed"] = False
                result["explanation"] = f"LLM suggested a fix but generated invalid JSON: {result['explanation']}"

        return result
