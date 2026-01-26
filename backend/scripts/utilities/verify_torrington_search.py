"""
Verify all Torrington properties are searchable and have complete data
Tests search for "12 MARGERIE ST", "Margerie", etc.
Checks that properties have address numbers on map and complete CAMA data
"""
import sys
from pathlib import Path
from typing import Optional
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property
from sqlalchemy import or_, func

MUNICIPALITY = "Torrington"
EXPECTED_TOTAL = 14715  # Expected number of properties from Excel

def get_street_number(address: str) -> Optional[str]:
    """Extract street number from address (must start with number)"""
    if not address:
        return None
    match = re.match(r'^(\d+)', address.strip())
    return match.group(1) if match else None

def verify_property_counts(db):
    """Verify total property count matches expected"""
    print("\n" + "=" * 60)
    print("Verifying Property Counts")
    print("=" * 60)
    
    total = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).count()
    
    print(f"\nTotal properties in database: {total:,}")
    print(f"Expected from Excel: {EXPECTED_TOTAL:,}")
    
    if total >= EXPECTED_TOTAL * 0.95:  # Allow 5% variance
        print(f"✅ Property count is acceptable (within 5% of expected)")
    else:
        print(f"⚠️  Property count is significantly lower than expected")
    
    return total

def verify_addresses(db):
    """Verify all properties have valid addresses"""
    print("\n" + "=" * 60)
    print("Verifying Addresses")
    print("=" * 60)
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    valid_addresses = 0
    missing_addresses = 0
    invalid_addresses = 0
    
    for prop in properties:
        if not prop.address or prop.address.strip() == '':
            missing_addresses += 1
        else:
            street_number = get_street_number(prop.address)
            if street_number:
                valid_addresses += 1
            else:
                invalid_addresses += 1
    
    print(f"\n✅ Valid addresses (start with number): {valid_addresses:,}")
    print(f"❌ Missing addresses: {missing_addresses:,}")
    print(f"⚠️  Invalid addresses (no number at start): {invalid_addresses:,}")
    
    if missing_addresses == 0 and invalid_addresses == 0:
        print(f"\n✅ All properties have valid addresses!")
    else:
        print(f"\n⚠️  {missing_addresses + invalid_addresses:,} properties need address fixes")
    
    return {
        'valid': valid_addresses,
        'missing': missing_addresses,
        'invalid': invalid_addresses
    }

def verify_cama_data(db):
    """Verify all properties have CAMA data"""
    print("\n" + "=" * 60)
    print("Verifying CAMA Data")
    print("=" * 60)
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).all()
    
    complete_cama = 0
    missing_owner = 0
    missing_assessed_value = 0
    missing_building_area = 0
    
    for prop in properties:
        has_owner = bool(prop.owner_name and prop.owner_name.strip())
        has_assessed = bool(prop.assessed_value and prop.assessed_value > 0)
        has_building_area = bool(prop.building_area_sqft and prop.building_area_sqft > 0)
        
        if has_owner and has_assessed and has_building_area:
            complete_cama += 1
        else:
            if not has_owner:
                missing_owner += 1
            if not has_assessed:
                missing_assessed_value += 1
            if not has_building_area:
                missing_building_area += 1
    
    print(f"\n✅ Complete CAMA data: {complete_cama:,}")
    print(f"❌ Missing owner_name: {missing_owner:,}")
    print(f"❌ Missing assessed_value: {missing_assessed_value:,}")
    print(f"❌ Missing building_area_sqft: {missing_building_area:,}")
    
    completion_rate = (complete_cama / len(properties) * 100) if properties else 0
    print(f"\n📊 CAMA Data Completion Rate: {completion_rate:.1f}%")
    
    if completion_rate >= 95:
        print(f"✅ CAMA data is complete!")
    else:
        print(f"⚠️  CAMA data needs improvement")
    
    return {
        'complete': complete_cama,
        'missing_owner': missing_owner,
        'missing_assessed_value': missing_assessed_value,
        'missing_building_area': missing_building_area,
        'completion_rate': completion_rate
    }

def test_search_queries(db):
    """Test search functionality for specific queries"""
    print("\n" + "=" * 60)
    print("Testing Search Queries")
    print("=" * 60)
    
    test_queries = [
        "12 MARGERIE ST",
        "12 Margerie",
        "Margerie",
        "MARGERIE ST",
        "margerie"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing search: '{query}'")
        
        search_term = f"%{query}%"
        normalized_q = query.upper().strip()
        normalized_q = normalized_q.replace(' ST ', ' STREET ').replace(' ST,', ' STREET,').replace(' ST', ' STREET')
        normalized_search_term = f"%{normalized_q}%"
        
        results = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).filter(
            or_(
                Property.address.ilike(search_term),
                func.upper(Property.address).ilike(normalized_search_term),
                Property.parcel_id.ilike(search_term)
            )
        ).all()
        
        print(f"  Found {len(results)} properties")
        
        if results:
            for prop in results[:5]:  # Show first 5
                print(f"    - {prop.address} (Parcel: {prop.parcel_id})")
                if prop.owner_name:
                    print(f"      Owner: {prop.owner_name}")
        else:
            print(f"  ⚠️  No results found")

def verify_specific_property(db, address: str):
    """Verify a specific property exists and has complete data"""
    print("\n" + "=" * 60)
    print(f"Verifying Specific Property: {address}")
    print("=" * 60)
    
    search_term = f"%{address}%"
    normalized_q = address.upper().strip()
    normalized_q = normalized_q.replace(' ST ', ' STREET ').replace(' ST,', ' STREET,').replace(' ST', ' STREET')
    normalized_search_term = f"%{normalized_q}%"
    
    properties = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).filter(
        or_(
            Property.address.ilike(search_term),
            func.upper(Property.address).ilike(normalized_search_term)
        )
    ).all()
    
    if not properties:
        print(f"❌ Property not found: {address}")
        return False
    
    print(f"✅ Found {len(properties)} property(ies) matching '{address}'")
    
    for prop in properties:
        print(f"\n  Property ID: {prop.id}")
        print(f"  Address: {prop.address}")
        print(f"  Parcel ID: {prop.parcel_id}")
        
        # Check address number
        street_number = get_street_number(prop.address)
        if street_number:
            print(f"  ✅ Address number: {street_number}")
        else:
            print(f"  ⚠️  Address doesn't start with number")
        
        # Check CAMA data
        has_owner = bool(prop.owner_name and prop.owner_name.strip())
        has_assessed = bool(prop.assessed_value and prop.assessed_value > 0)
        has_building_area = bool(prop.building_area_sqft and prop.building_area_sqft > 0)
        
        print(f"  Owner: {prop.owner_name if has_owner else '❌ Missing'}")
        print(f"  Assessed Value: ${prop.assessed_value:,.0f}" if has_assessed else "  Assessed Value: ❌ Missing")
        print(f"  Building Area: {prop.building_area_sqft:,.0f} sqft" if has_building_area else "  Building Area: ❌ Missing")
        
        if street_number and has_owner and has_assessed and has_building_area:
            print(f"  ✅ Property is complete and searchable!")
            return True
        else:
            print(f"  ⚠️  Property is missing some data")
            return False

def main():
    """Main verification function"""
    print("\n" + "=" * 60)
    print("Torrington Property Verification")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Verify counts
        total = verify_property_counts(db)
        
        # Verify addresses
        address_stats = verify_addresses(db)
        
        # Verify CAMA data
        cama_stats = verify_cama_data(db)
        
        # Test search queries
        test_search_queries(db)
        
        # Verify specific property
        verify_specific_property(db, "12 MARGERIE ST")
        
        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"\nTotal Properties: {total:,}")
        print(f"Valid Addresses: {address_stats['valid']:,} ({address_stats['valid']/total*100:.1f}%)")
        print(f"Complete CAMA Data: {cama_stats['complete']:,} ({cama_stats['completion_rate']:.1f}%)")
        
        if address_stats['valid'] == total and cama_stats['completion_rate'] >= 95:
            print("\n✅ All verifications passed!")
        else:
            print("\n⚠️  Some verifications need attention")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
