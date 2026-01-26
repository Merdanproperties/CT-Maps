"""
Verify that missing properties are imported with geometry and appear on map
Checks "12 MARGERIE ST" and overall property counts
"""
import sys
from pathlib import Path
from sqlalchemy import or_, func, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property

MUNICIPALITY = "Torrington"
EXPECTED_GEOCOUNT = 14723  # Expected from geodatabase

def verify_property_counts(db):
    """Verify total property count matches expected"""
    print("\n" + "=" * 60)
    print("Verifying Property Counts")
    print("=" * 60)
    
    total = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%")
    ).count()
    
    with_geometry = db.query(Property).filter(
        Property.municipality.ilike(f"%{MUNICIPALITY}%"),
        Property.geometry.isnot(None)
    ).count()
    
    without_geometry = total - with_geometry
    
    print(f"\nTotal properties in database: {total:,}")
    print(f"Properties with geometry: {with_geometry:,}")
    print(f"Properties without geometry: {without_geometry:,}")
    print(f"Expected from geodatabase: {EXPECTED_GEOCOUNT:,}")
    
    if with_geometry >= EXPECTED_GEOCOUNT * 0.95:
        print(f"✅ Property count with geometry is acceptable (within 5% of expected)")
    else:
        print(f"⚠️  Property count with geometry is significantly lower than expected")
    
    return {
        'total': total,
        'with_geometry': with_geometry,
        'without_geometry': without_geometry
    }

def verify_specific_property(db, address: str):
    """Verify a specific property exists and has geometry"""
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
        
        # Check geometry
        has_geometry = prop.geometry is not None
        if has_geometry:
            # Get centroid to verify geometry is valid
            try:
                result = db.execute(text(
                    'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                    'ST_Y(ST_Centroid(geometry)) as lat, '
                    'ST_IsValid(geometry) as is_valid '
                    'FROM properties WHERE id = :id'
                ), {'id': prop.id}).fetchone()
                
                if result:
                    lon, lat, is_valid = result
                    print(f"  ✅ Has geometry: lon={lon:.6f}, lat={lat:.6f}, valid={is_valid}")
                else:
                    print(f"  ⚠️  Has geometry but couldn't get centroid")
            except Exception as e:
                print(f"  ⚠️  Geometry error: {e}")
        else:
            print(f"  ❌ No geometry")
        
        # Check CAMA data
        has_owner = bool(prop.owner_name and prop.owner_name.strip())
        has_assessed = bool(prop.assessed_value and prop.assessed_value > 0)
        
        print(f"  Owner: {prop.owner_name if has_owner else '❌ Missing'}")
        print(f"  Assessed Value: ${prop.assessed_value:,.0f}" if has_assessed else "  Assessed Value: ❌ Missing")
        
        if has_geometry and has_owner and has_assessed:
            print(f"  ✅ Property is complete and will appear on map!")
            return True
        else:
            print(f"  ⚠️  Property is missing some data")
            return False

def verify_search_functionality(db):
    """Verify search works for imported properties"""
    print("\n" + "=" * 60)
    print("Verifying Search Functionality")
    print("=" * 60)
    
    test_queries = [
        "12 MARGERIE ST",
        "12 Margerie",
        "Margerie"
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
                has_geom = "✅" if prop.geometry else "❌"
                print(f"    {has_geom} {prop.address} (Parcel: {prop.parcel_id})")
        else:
            print(f"  ⚠️  No results found")

def main():
    """Main verification function"""
    print("\n" + "=" * 60)
    print("Verifying Missing Properties Import")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Verify counts
        counts = verify_property_counts(db)
        
        # Verify specific property
        verify_specific_property(db, "12 MARGERIE ST")
        
        # Verify search
        verify_search_functionality(db)
        
        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"\nTotal Properties: {counts['total']:,}")
        print(f"With Geometry: {counts['with_geometry']:,} ({counts['with_geometry']/counts['total']*100:.1f}%)")
        print(f"Without Geometry: {counts['without_geometry']:,}")
        
        if counts['with_geometry'] >= EXPECTED_GEOCOUNT * 0.95:
            print("\n✅ All verifications passed!")
        else:
            print("\n⚠️  Some verifications need attention")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
