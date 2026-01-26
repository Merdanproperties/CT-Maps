#!/usr/bin/env python3
"""
Test script to verify Torrington filter combinations work correctly.
This verifies that municipality + time_since_sale filters combine correctly.
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import date, timedelta

# Load environment variables
load_dotenv(backend_dir / '.env')

def test_torrington_filters():
    """Test that Torrington filters work correctly"""
    db_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/ct_properties')
    engine = create_engine(db_url)
    
    print("Testing Torrington filter combinations...")
    print("=" * 60)
    
    with engine.connect() as conn:
        # Test 1: Torrington only
        print("\n1. Torrington only:")
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%'"
        ))
        total_torrington = result.scalar()
        print(f"   Total properties in Torrington: {total_torrington:,}")
        expected_total = 12688
        if total_torrington == expected_total:
            print(f"   ✓ Correct (expected {expected_total:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected_total:,}, got {total_torrington:,})")
        
        # Test 2: Torrington + Last 2 Years
        print("\n2. Torrington + 'Last 2 Years':")
        today = date.today()
        two_years_ago = today - timedelta(days=730)
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%' "
            "AND last_sale_date >= :cutoff"
        ), {'cutoff': two_years_ago})
        count = result.scalar()
        print(f"   Count: {count:,}")
        expected = 819
        if count == expected:
            print(f"   ✓ Correct (expected {expected:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected:,}, got {count:,})")
        
        # Test 3: Torrington + 2-5 Years Ago
        print("\n3. Torrington + '2-5 Years Ago':")
        five_years_ago = today - timedelta(days=1825)
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%' "
            "AND last_sale_date < :two_years AND last_sale_date >= :five_years"
        ), {'two_years': two_years_ago, 'five_years': five_years_ago})
        count = result.scalar()
        print(f"   Count: {count:,}")
        expected = 2163
        if count == expected:
            print(f"   ✓ Correct (expected {expected:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected:,}, got {count:,})")
        
        # Test 4: Torrington + 5-10 Years Ago
        print("\n4. Torrington + '5-10 Years Ago':")
        ten_years_ago = today - timedelta(days=3650)
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%' "
            "AND last_sale_date < :five_years AND last_sale_date >= :ten_years"
        ), {'five_years': five_years_ago, 'ten_years': ten_years_ago})
        count = result.scalar()
        print(f"   Count: {count:,}")
        expected = 2304
        if count == expected:
            print(f"   ✓ Correct (expected {expected:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected:,}, got {count:,})")
        
        # Test 5: Torrington + 10-20 Years Ago
        print("\n5. Torrington + '10-20 Years Ago':")
        twenty_years_ago = today - timedelta(days=7300)
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%' "
            "AND last_sale_date < :ten_years AND last_sale_date >= :twenty_years"
        ), {'ten_years': ten_years_ago, 'twenty_years': twenty_years_ago})
        count = result.scalar()
        print(f"   Count: {count:,}")
        expected = 2042
        if count == expected:
            print(f"   ✓ Correct (expected {expected:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected:,}, got {count:,})")
        
        # Test 6: Torrington + 20+ Years Ago
        print("\n6. Torrington + '20+ Years Ago':")
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%' "
            "AND last_sale_date < :cutoff"
        ), {'cutoff': twenty_years_ago})
        count = result.scalar()
        print(f"   Count: {count:,}")
        expected = 2692
        if count == expected:
            print(f"   ✓ Correct (expected {expected:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected:,}, got {count:,})")
        
        # Test 7: Torrington + Never Sold
        print("\n7. Torrington + 'Never Sold':")
        result = conn.execute(text(
            "SELECT COUNT(*) FROM properties WHERE municipality ILIKE '%Torrington%' "
            "AND last_sale_date IS NULL"
        ))
        count = result.scalar()
        print(f"   Count: {count:,}")
        expected = 2668
        if count == expected:
            print(f"   ✓ Correct (expected {expected:,})")
        else:
            print(f"   ✗ Incorrect (expected {expected:,}, got {count:,})")
        
        # Test 8: Sum verification
        print("\n8. Sum of all time periods:")
        counts = [819, 2163, 2304, 2042, 2692, 2668]
        total_sum = sum(counts)
        print(f"   Sum: {total_sum:,}")
        if total_sum == total_torrington:
            print(f"   ✓ Sum equals total Torrington properties ({total_torrington:,})")
        else:
            print(f"   ✗ Sum does not equal total (expected {total_torrington:,}, got {total_sum:,})")
    
    print("\n" + "=" * 60)
    print("Test complete!")

if __name__ == '__main__':
    test_torrington_filters()
