"""
Generate a list of addresses to verify on the map
Shows property ID, parcel ID, address, and coordinates for easy verification
"""
import sys
from pathlib import Path
from sqlalchemy import text
import csv
from datetime import datetime

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from models import Property
from database import SessionLocal

MUNICIPALITY = "Torrington"
OUTPUT_FILE = f"logs/torrington_address_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def generate_verification_list(limit: int = None):
    """Generate a CSV file with addresses to verify"""
    db = SessionLocal()
    
    try:
        print(f"\n{'='*60}")
        print("Generating Address Verification List")
        print(f"{'='*60}\n")
        
        # Query properties
        query = db.query(Property).filter(
            Property.municipality.ilike(f"%{MUNICIPALITY}%")
        ).filter(
            Property.address.isnot(None),
            Property.address != ''
        )
        
        if limit:
            query = query.limit(limit)
        
        properties = query.all()
        
        print(f"Found {len(properties):,} properties with addresses")
        
        # Prepare data
        verification_data = []
        
        for prop in properties:
            # Get coordinates
            coords = None
            if prop.geometry:
                try:
                    result = db.execute(text(
                        'SELECT ST_X(ST_Centroid(geometry)) as lon, '
                        'ST_Y(ST_Centroid(geometry)) as lat '
                        'FROM properties WHERE id = :id'
                    ), {'id': prop.id}).fetchone()
                    
                    if result and result[0] and result[1]:
                        coords = (float(result[0]), float(result[1]))
                except Exception:
                    pass
            
            verification_data.append({
                'property_id': prop.id,
                'parcel_id': prop.parcel_id or '',
                'address': prop.address or '',
                'latitude': coords[1] if coords else '',
                'longitude': coords[0] if coords else '',
                'owner_name': prop.owner_name or '',
                'assessed_value': prop.assessed_value or '',
            })
        
        # Write to CSV
        Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
            if verification_data:
                writer = csv.DictWriter(f, fieldnames=verification_data[0].keys())
                writer.writeheader()
                writer.writerows(verification_data)
        
        print(f"\n✅ Verification list saved to: {OUTPUT_FILE}")
        print(f"\n📋 Sample addresses to verify:")
        print(f"{'='*60}")
        
        # Show first 20 addresses
        for i, data in enumerate(verification_data[:20], 1):
            print(f"{i:2}. {data['address']}")
            if data['parcel_id']:
                print(f"    Parcel: {data['parcel_id']}")
            if data['latitude'] and data['longitude']:
                print(f"    Location: {data['latitude']:.6f}, {data['longitude']:.6f}")
            print()
        
        if len(verification_data) > 20:
            print(f"... and {len(verification_data) - 20} more addresses in the CSV file")
        
        print(f"\n💡 To verify on the map:")
        print(f"   1. Open http://localhost:3000/")
        print(f"   2. Search for each address")
        print(f"   3. Verify the property location matches the address")
        print(f"   4. Check that property details are correct")
        
        return OUTPUT_FILE
        
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate address verification list')
    parser.add_argument('--limit', type=int, help='Limit number of properties (default: all)')
    args = parser.parse_args()
    
    generate_verification_list(limit=args.limit)
