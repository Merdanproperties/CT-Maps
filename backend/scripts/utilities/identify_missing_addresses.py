"""
Identify Torrington properties missing addresses or with invalid addresses
Addresses must start with a number to display address numbers on the map
"""
import sys
from pathlib import Path
from typing import Optional
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import SessionLocal
from models import Property
from sqlalchemy import func

MUNICIPALITY = "Torrington"

def get_street_number(address: str) -> Optional[str]:
    """Extract street number from address (must start with number)"""
    if not address:
        return None
    match = re.match(r'^(\d+)', address.strip())
    return match.group(1) if match else None

def identify_missing_addresses():
    """Identify properties missing addresses or with invalid addresses"""
    print("\n" + "=" * 60)
    print("Identifying Torrington Properties Missing Addresses")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get all Torrington properties
        properties = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).all()
        
        print(f"\nTotal Torrington properties: {len(properties):,}")
        
        # Categorize properties
        missing_address = []
        invalid_address = []
        valid_address = []
        
        for prop in properties:
            if not prop.address or prop.address.strip() == '':
                missing_address.append({
                    'id': prop.id,
                    'parcel_id': prop.parcel_id,
                    'address': None,
                    'municipality': prop.municipality,
                    'has_geometry': prop.geometry is not None
                })
            else:
                street_number = get_street_number(prop.address)
                if not street_number:
                    invalid_address.append({
                        'id': prop.id,
                        'parcel_id': prop.parcel_id,
                        'address': prop.address,
                        'municipality': prop.municipality,
                        'has_geometry': prop.geometry is not None
                    })
                else:
                    valid_address.append({
                        'id': prop.id,
                        'parcel_id': prop.parcel_id,
                        'address': prop.address,
                        'street_number': street_number
                    })
        
        print(f"\n📊 Address Status Summary:")
        print(f"  ✅ Valid addresses (start with number): {len(valid_address):,}")
        print(f"  ❌ Missing addresses: {len(missing_address):,}")
        print(f"  ⚠️  Invalid addresses (no number at start): {len(invalid_address):,}")
        
        # Show sample invalid addresses
        if invalid_address:
            print(f"\n⚠️  Sample Invalid Addresses (first 10):")
            for item in invalid_address[:10]:
                print(f"    ID {item['id']}: '{item['address']}'")
        
        # Show sample missing addresses
        if missing_address:
            print(f"\n❌ Sample Missing Addresses (first 10):")
            for item in missing_address[:10]:
                print(f"    ID {item['id']}: Parcel {item['parcel_id']}")
        
        return {
            'total': len(properties),
            'valid': len(valid_address),
            'missing': len(missing_address),
            'invalid': len(invalid_address),
            'missing_list': missing_address,
            'invalid_list': invalid_address
        }
        
    finally:
        db.close()

if __name__ == "__main__":
    result = identify_missing_addresses()
    print(f"\n✅ Analysis complete!")
    print(f"   {result['missing']:,} properties need addresses")
    print(f"   {result['invalid']:,} properties need address fixes")
