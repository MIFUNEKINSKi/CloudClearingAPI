"""
Quick test to validate non-linear confidence multiplier implementation.

This verifies that the new quadratic scaling formula produces the expected
multipliers across the confidence range (50% to 95%).
"""

def calculate_confidence_multiplier(confidence: float) -> float:
    """
    Non-linear confidence multiplier (v2.4.1 refinement).
    
    Quadratic scaling below 85% for steeper penalties,
    linear above for diminishing returns.
    """
    if confidence >= 0.85:
        # Linear scaling above 85%: 0.97 to 1.00
        multiplier = 0.97 + (confidence - 0.85) * 0.30  # 0.85→0.97, 0.95→1.00
    elif confidence >= 0.50:
        # Quadratic scaling between 50% and 85%: 0.70 to 0.97
        # Normalize to [0, 1] range where 0.50→0, 0.85→1
        normalized_conf = (confidence - 0.50) / 0.35
        # Apply power function: stronger penalties at low confidence
        multiplier = 0.70 + 0.27 * (normalized_conf ** 1.2)
    else:
        # Below 50% confidence: apply floor of 0.70
        multiplier = 0.70
    
    # Clamp to ensure bounds (0.70 to 1.00)
    return max(0.70, min(1.00, multiplier))


def test_confidence_multiplier():
    """Test the confidence multiplier across expected range"""
    
    print("=" * 70)
    print("Non-Linear Confidence Multiplier Test")
    print("=" * 70)
    print(f"{'Confidence':<12} {'Multiplier':<12} {'Expected Range':<20} {'Status':<10}")
    print("-" * 70)
    
    test_cases = [
        (0.50, 0.70, 0.70, "Low (50%)"),
        (0.60, 0.759, 0.761, "Poor (60%)"),
        (0.70, 0.837, 0.839, "Medium (70%)"),
        (0.75, 0.879, 0.881, "Good (75%)"),
        (0.80, 0.923, 0.925, "Very Good (80%)"),
        (0.85, 0.97, 0.97, "Excellent (85%)"),
        (0.90, 0.985, 0.985, "Outstanding (90%)"),
        (0.95, 1.00, 1.00, "Perfect (95%)"),
    ]
    
    all_passed = True
    
    for confidence, min_expected, max_expected, label in test_cases:
        multiplier = calculate_confidence_multiplier(confidence)
        status = "✅ PASS" if min_expected <= multiplier <= max_expected else "❌ FAIL"
        
        if status == "❌ FAIL":
            all_passed = False
        
        print(f"{label:<12} {multiplier:.3f}        {min_expected:.3f} - {max_expected:.3f}       {status}")
    
    print("=" * 70)
    
    # Test boundary conditions
    print("\nBoundary Conditions:")
    print("-" * 70)
    
    edge_cases = [
        (0.20, "Below minimum (20%)"),
        (0.50, "Minimum valid (50%)"),
        (0.84, "Just below threshold (84%)"),
        (0.85, "Threshold (85%)"),
        (0.86, "Just above threshold (86%)"),
        (0.95, "Maximum (95%)"),
        (1.00, "Above maximum (100%)"),
    ]
    
    for confidence, label in edge_cases:
        multiplier = calculate_confidence_multiplier(confidence)
        print(f"{label:<30} → {multiplier:.4f}")
    
    print("=" * 70)
    
    # Compare OLD vs NEW formula
    print("\nComparative Analysis (OLD Linear vs NEW Non-Linear):")
    print("-" * 70)
    print(f"{'Confidence':<12} {'OLD Linear':<15} {'NEW Non-Linear':<15} {'Difference':<12}")
    print("-" * 70)
    
    for conf in [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        old_multiplier = 0.7 + (conf * 0.3)  # Old linear formula
        new_multiplier = calculate_confidence_multiplier(conf)
        diff = new_multiplier - old_multiplier
        diff_pct = (diff / old_multiplier) * 100
        
        print(f"{conf:.0%}          {old_multiplier:.4f}          {new_multiplier:.4f}          {diff:+.4f} ({diff_pct:+.1f}%)")
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ All tests PASSED! Non-linear confidence multiplier working correctly.")
    else:
        print("\n❌ Some tests FAILED! Review implementation.")
    
    return all_passed


if __name__ == "__main__":
    test_confidence_multiplier()
