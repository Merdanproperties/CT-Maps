"""
Identify Torrington properties missing CAMA data
CAMA data includes: owner_name, assessed_value, building_area_sqft, etc.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property

MUNICIPALITY = "Torrington"

def identify_missing_cama_data():
    """Identify properties missing CAMA data"""
    print("\n" + "=" * 60)
    print("Identifying Torrington Properties Missing CAMA Data")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get all Torrington properties
        properties = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).all()
        
        print(f"\nTotal Torrington properties: {len(properties):,}")
        
        # Categorize properties
        missing_owner = []
        missing_assessed_value = []
        missing_building_area = []
        missing_all_cama = []
        has_cama = []
        
        for prop in properties:
            missing_fields = []
            
            if not prop.owner_name or prop.owner_name.strip() == '':
                missing_fields.append('owner_name')
                missing_owner.append(prop.id)
            
            if not prop.assessed_value or prop.assessed_value == 0:
                missing_fields.append('assessed_value')
                missing_assessed_value.append(prop.id)
            
            if not prop.building_area_sqft or prop.building_area_sqft == 0:
                missing_fields.append('building_area_sqft')
                missing_building_area.append(prop.id)
            
            if missing_fields:
                if len(missing_fields) >= 3:  # Missing most CAMA data
                    missing_all_cama.append({
                        'id': prop.id,
                        'parcel_id': prop.parcel_id,
                        'address': prop.address,
                        'missing_fields': missing_fields
                    })
            else:
                has_cama.append(prop.id)
        
        print(f"\n📊 CAMA Data Status Summary:")
        print(f"  ✅ Properties with complete CAMA data: {len(has_cama):,}")
        print(f"  ❌ Missing owner_name: {len(missing_owner):,}")
        print(f"  ❌ Missing assessed_value: {len(missing_assessed_value):,}")
        print(f"  ❌ Missing building_area_sqft: {len(missing_building_area):,}")
        print(f"  ⚠️  Missing most/all CAMA data: {len(missing_all_cama):,}")
        
        # Show sample properties missing all CAMA data
        if missing_all_cama:
            print(f"\n⚠️  Sample Properties Missing CAMA Data (first 10):")
            for item in missing_all_cama[:10]:
                print(f"    ID {item['id']}: {item['address'] or 'No Address'} (Parcel: {item['parcel_id']})")
                print(f"      Missing: {', '.join(item['missing_fields'])}")
        
        return {
            'total': len(properties),
            'has_cama': len(has_cama),
            'missing_owner': len(missing_owner),
            'missing_assessed_value': len(missing_assessed_value),
            'missing_building_area': len(missing_building_area),
            'missing_all_cama': len(missing_all_cama),
            'missing_all_cama_list': missing_all_cama
        }
        
    finally:
        db.close()

if __name__ == "__main__":
    result = identify_missing_cama_data()
    print(f"\n✅ Analysis complete!")
    print(f"   {result['missing_all_cama']:,} properties need CAMA data updates")
