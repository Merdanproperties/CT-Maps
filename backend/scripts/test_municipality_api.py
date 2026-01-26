#!/usr/bin/env python3
"""
Test script to verify backend API correctly handles municipality + time_since_sale without bbox.
This verifies that the backend returns only properties from the selected municipality.
"""

import requests
import json
import sys

def test_municipality_api():
    """Test that municipality filter works correctly without bbox"""
    base_url = 'http://localhost:8000/api/search/'
    
    print("Testing Backend API - Municipality Filter")
    print("=" * 60)
    
    # Test 1: Torrington only (no bbox)
    print("\n1. Torrington only (no bbox):")
    try:
        response = requests.get(base_url, params={
            'municipality': 'Torrington',
            'page_size': 100
        })
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"   Total: {total:,}")
            print(f"   Expected: 12,688")
            if total == 12688:
                print("   ✓ Correct")
            else:
                print(f"   ✗ Incorrect (expected 12,688, got {total:,})")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 2: Torrington + Last 2 Years (no bbox)
    print("\n2. Torrington + 'Last 2 Years' (no bbox):")
    try:
        response = requests.get(base_url, params={
            'municipality': 'Torrington',
            'time_since_sale': 'Last 2 Years',
            'page_size': 100
        })
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"   Total: {total:,}")
            print(f"   Expected: 819")
            if total == 819:
                print("   ✓ Correct")
            else:
                print(f"   ✗ Incorrect (expected 819, got {total:,})")
            
            # Check if any properties are from other municipalities
            properties = data.get('properties', [])
            non_torrington = [p for p in properties if 'torrington' not in p.get('municipality', '').lower()]
            if non_torrington:
                print(f"   ✗ Found {len(non_torrington)} properties NOT in Torrington:")
                for p in non_torrington[:5]:
                    print(f"      - {p.get('address', 'N/A')}, {p.get('municipality', 'N/A')}")
            else:
                print("   ✓ All properties are in Torrington")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 3: Torrington + 2-5 Years Ago (no bbox)
    print("\n3. Torrington + '2-5 Years Ago' (no bbox):")
    try:
        response = requests.get(base_url, params={
            'municipality': 'Torrington',
            'time_since_sale': '2-5 Years Ago',
            'page_size': 100
        })
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"   Total: {total:,}")
            print(f"   Expected: 2,163")
            if total == 2163:
                print("   ✓ Correct")
            else:
                print(f"   ✗ Incorrect (expected 2,163, got {total:,})")
            
            # Check if any properties are from other municipalities
            properties = data.get('properties', [])
            non_torrington = [p for p in properties if 'torrington' not in p.get('municipality', '').lower()]
            if non_torrington:
                print(f"   ✗ Found {len(non_torrington)} properties NOT in Torrington:")
                for p in non_torrington[:5]:
                    print(f"      - {p.get('address', 'N/A')}, {p.get('municipality', 'N/A')}")
            else:
                print("   ✓ All properties are in Torrington")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    # Test 4: Torrington + 2-5 Years Ago WITH bbox (should show incorrect results)
    print("\n4. Torrington + '2-5 Years Ago' WITH bbox (to verify bbox causes issues):")
    try:
        # Use a bbox that includes Bridgeport area
        bbox = "-73.3,41.1,-73.0,41.3"  # Approximate Bridgeport area
        response = requests.get(base_url, params={
            'municipality': 'Torrington',
            'time_since_sale': '2-5 Years Ago',
            'bbox': bbox,
            'page_size': 100
        })
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"   Total: {total:,}")
            print(f"   Note: With bbox, this should show incorrect results")
            
            # Check if any properties are from other municipalities
            properties = data.get('properties', [])
            non_torrington = [p for p in properties if 'torrington' not in p.get('municipality', '').lower()]
            if non_torrington:
                print(f"   ⚠ Found {len(non_torrington)} properties NOT in Torrington (this is the bug):")
                for p in non_torrington[:5]:
                    print(f"      - {p.get('address', 'N/A')}, {p.get('municipality', 'N/A')}")
            else:
                print("   ✓ All properties are in Torrington (unexpected if bbox is applied)")
        else:
            print(f"   ✗ Error: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("\nNote: Check the console logs in the browser to see what parameters")
    print("are actually being sent from the frontend.")

if __name__ == '__main__':
    test_municipality_api()
