"""
Quick test for schema healer functionality.
"""

from schema_healer import SchemaHealer


def test_parse_error():
    """Test error message parsing."""
    healer = SchemaHealer()

    error = "'count' not found for path 'Film.count'"
    result = healer.parse_missing_measure_error(error)

    print(f"Parsed error: {result}")
    assert result is not None
    assert result["cube"] == "Film"
    assert result["measure"] == "count"
    print("✓ Error parsing works!")


def test_heal_schema():
    """Test schema healing."""
    healer = SchemaHealer()

    error = "'count' not found for path 'Film.count'"
    result = healer.heal_schema(error)

    print(f"\nHealing result: {result}")

    if result["healed"]:
        print(f"✓ {result['message']}")
        print(f"  File: {result['file_path']}")
    else:
        print(f"✗ Healing failed: {result['message']}")


if __name__ == "__main__":
    print("Testing Schema Healer\n" + "=" * 50)
    test_parse_error()
    test_heal_schema()
    print("\nAll tests complete!")
