"""
Test cases for auto-healing feature.
"""

from schema_healer import SchemaHealer


def test_healable_measure():
    """Test a measure that can be auto-healed."""
    healer = SchemaHealer()

    error = "'count' not found for path 'Actor.count'"
    result = healer.heal_schema(error)

    print("\n=== HEALABLE MEASURE TEST ===")
    print(f"Error: {error}")
    print(f"Result: {result}")
    print(f"✓ Can heal: {result['healed']}")


def test_non_healable_measure():
    """Test a measure that cannot be auto-healed."""
    healer = SchemaHealer()

    error = "'totalRevenue' not found for path 'Payment.totalRevenue'"
    result = healer.heal_schema(error)

    print("\n=== NON-HEALABLE MEASURE TEST ===")
    print(f"Error: {error}")
    print(f"Result: {result}")
    print(f"✗ Cannot heal: {not result['healed']}")

    # Check what gets parsed
    parsed = healer.parse_missing_measure_error(error)
    print(f"Parsed info: {parsed}")


def test_another_non_healable():
    """Test another non-healable measure."""
    healer = SchemaHealer()

    error = "'avgLength' not found for path 'Film.avgLength'"
    result = healer.heal_schema(error)

    print("\n=== ANOTHER NON-HEALABLE TEST ===")
    print(f"Error: {error}")
    print(f"Result: {result}")
    print(f"Measure: {result.get('measure', 'N/A')}")
    print(f"Message: {result.get('message', 'N/A')}")


if __name__ == "__main__":
    print("Testing Auto-Healing Features")
    print("=" * 60)

    test_healable_measure()
    test_non_healable_measure()
    test_another_non_healable()

    print("\n" + "=" * 60)
    print("All tests complete!")
