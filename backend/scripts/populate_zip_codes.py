"""
Script to populate zip codes for properties using reverse geocoding
Uses OpenStreetMap Nominatim API (free, but has rate limits)
"""
import os
import sys
import time
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal
import requests

load_dotenv()

# Rate limiting: Nominatim allows 1 request per second
NOMINATIM_DELAY = 1.1  # Slightly more than 1 second to be safe

def get_zip_from_nominatim(lat: float, lng: float, retries: int = 3) -> str | None:
    """
    Get zip code from OpenStreetMap Nominatim reverse geocoding API
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'lat': lat,
        'lon': lng,
        'format': 'json',
        'addressdetails': 1
    }
    headers = {
        'User-Agent': 'CT Property Search App'  # Required by Nominatim
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract zip code from address
            address = data.get('address', {})
            zip_code = (
                address.get('postcode') or 
                address.get('postal_code') or
                None
            )
            
            if zip_code:
                # Clean zip code (sometimes includes +4 extension)
                zip_code = zip_code.split('-')[0].strip()
                if len(zip_code) == 5 and zip_code.isdigit():
                    return zip_code
            
            return None
            
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            print(f"  ⚠️  Error geocoding ({lat}, {lng}): {e}")
            return None
    
    return None

def populate_zip_codes(batch_size: int = 100, limit: int = None, use_municipality_fallback: bool = True):
    """
    Populate zip codes for properties that don't have them
    
    Args:
        batch_size: Number of properties to process per batch
        limit: Maximum number of properties to process (None = all missing zip codes)
        use_municipality_fallback: If True, use municipality-based lookup for properties that fail geocoding
    """
    db = SessionLocal()
    
    try:
        # Get properties without zip codes
        query = db.query(Property).filter(
            (Property.zip_code.is_(None)) | (Property.zip_code == '')
        )
        
        total_missing = query.count()
        print(f"Found {total_missing:,} properties without zip codes")
        
        if limit:
            query = query.limit(limit)
            print(f"Processing first {limit:,} properties...")
        
        properties = query.all()
        print(f"Processing {len(properties):,} properties...")
        print(f"Estimated time: ~{len(properties) * NOMINATIM_DELAY / 60:.1f} minutes")
        print()
        
        # CT Municipality to primary zip code mapping (common zip codes)
        # This is a fallback for when geocoding fails
        municipality_zips = {
            'Bridgeport': '06604',
            'Hartford': '06103',
            'New Haven': '06510',
            'Stamford': '06901',
            'Waterbury': '06702',
            'Norwalk': '06850',
            'Danbury': '06810',
            'New Britain': '06051',
            'West Hartford': '06107',
            'Greenwich': '06830',
            'Hamden': '06514',
            'Meriden': '06450',
            'Bristol': '06010',
            'Middletown': '06457',
            'Stratford': '06615',
            'Norwich': '06360',
            'Torrington': '06790',
            'New London': '06320',
            'Ansonia': '06401',
            'Derby': '06418',
            'Shelton': '06484',
            'Fairfield': '06824',
            'Milford': '06460',
            'West Haven': '06516',
            'East Haven': '06512',
            'North Haven': '06473',
            'Orange': '06477',
            'Westport': '06880',
            'Trumbull': '06611',
            'Monroe': '06468',
            'Bethel': '06801',
            'Danbury': '06810',
            'Ridgefield': '06877',
            'Newtown': '06470',
            'Brookfield': '06804',
            'New Milford': '06776',
            'Litchfield': '06759',
            'Winsted': '06098',
            'Canaan': '06018',
            'Salisbury': '06068',
            'Sharon': '06069',
            'Cornwall': '06753',
            'Kent': '06757',
            'Warren': '06754',
            'Washington': '06793',
            'Roxbury': '06783',
            'Woodbury': '06798',
            'Southbury': '06488',
            'Oxford': '06478',
            'Seymour': '06483',
            'Beacon Falls': '06403',
            'Naugatuck': '06770',
            'Prospect': '06712',
            'Bethany': '06524',
            'Woodbridge': '06525',
            'Hamden': '06514',
            'North Haven': '06473',
            'Wallingford': '06492',
            'Cheshire': '06410',
            'Southington': '06489',
            'Plainville': '06062',
            'Farmington': '06032',
            'Avon': '06001',
            'Simsbury': '06070',
            'Granby': '06035',
            'East Granby': '06026',
            'Suffield': '06078',
            'Windsor': '06095',
            'Windsor Locks': '06096',
            'Enfield': '06082',
            'Somers': '06071',
            'Ellington': '06029',
            'Tolland': '06084',
            'Vernon': '06066',
            'Manchester': '06040',
            'Bolton': '06043',
            'Coventry': '06238',
            'Mansfield': '06250',
            'Storrs': '06268',
            'Willimantic': '06226',
            'Windham': '06280',
            'Canterbury': '06331',
            'Plainfield': '06374',
            'Sterling': '06377',
            'Voluntown': '06384',
            'Griswold': '06351',
            'Preston': '06365',
            'Ledyard': '06339',
            'Groton': '06340',
            'Stonington': '06378',
            'North Stonington': '06359',
            'Mystic': '06355',
            'Old Saybrook': '06475',
            'Westbrook': '06498',
            'Clinton': '06413',
            'Killingworth': '06419',
            'Durham': '06422',
            'Madison': '06443',
            'Guilford': '06437',
            'Branford': '06405',
            'East Haven': '06512',
            'New Haven': '06510',
            'West Haven': '06516',
            'Orange': '06477',
            'Milford': '06460',
            'Stratford': '06615',
            'Bridgeport': '06604',
            'Fairfield': '06824',
            'Westport': '06880',
            'Norwalk': '06850',
            'Darien': '06820',
            'Stamford': '06901',
            'Greenwich': '06830',
            'New Canaan': '06840',
            'Wilton': '06897',
            'Ridgefield': '06877',
            'Redding': '06896',
            'Bethel': '06801',
            'Danbury': '06810',
            'New Fairfield': '06812',
            'Sherman': '06784',
            'New Milford': '06776',
            'Bridgewater': '06752',
            'Roxbury': '06783',
            'Washington': '06793',
            'Warren': '06754',
            'Kent': '06757',
            'Cornwall': '06753',
            'Sharon': '06069',
            'Salisbury': '06068',
            'Canaan': '06018',
            'Norfolk': '06058',
            'Colebrook': '06021',
            'Winsted': '06098',
            'Barkhamsted': '06063',
            'Hartland': '06091',
            'Granby': '06035',
            'East Granby': '06026',
            'Suffield': '06078',
            'Windsor': '06095',
            'Windsor Locks': '06096',
            'Enfield': '06082',
            'Somers': '06071',
            'Ellington': '06029',
            'Tolland': '06084',
            'Vernon': '06066',
            'Manchester': '06040',
            'Bolton': '06043',
            'Coventry': '06238',
            'Mansfield': '06250',
            'Storrs': '06268',
            'Willimantic': '06226',
            'Windham': '06280',
            'Canterbury': '06331',
            'Plainfield': '06374',
            'Sterling': '06377',
            'Voluntown': '06384',
            'Griswold': '06351',
            'Preston': '06365',
            'Ledyard': '06339',
            'Groton': '06340',
            'Stonington': '06378',
            'North Stonington': '06359',
            'Mystic': '06355',
            'Old Saybrook': '06475',
            'Westbrook': '06498',
            'Clinton': '06413',
            'Killingworth': '06419',
            'Durham': '06422',
            'Madison': '06443',
            'Guilford': '06437',
            'Branford': '06405',
            'East Haven': '06512',
            'New Haven': '06510',
            'West Haven': '06516',
            'Orange': '06477',
            'Milford': '06460',
            'Stratford': '06615',
            'Bridgeport': '06604',
            'Fairfield': '06824',
            'Westport': '06880',
            'Norwalk': '06850',
            'Darien': '06820',
            'Stamford': '06901',
            'Greenwich': '06830',
            'New Canaan': '06840',
            'Wilton': '06897',
            'Ridgefield': '06877',
            'Redding': '06896',
            'Bethel': '06801',
            'Danbury': '06810',
            'New Fairfield': '06812',
            'Sherman': '06784',
            'New Milford': '06776',
            'Bridgewater': '06752',
            'Roxbury': '06783',
            'Washington': '06793',
            'Warren': '06754',
            'Kent': '06757',
            'Cornwall': '06753',
            'Sharon': '06069',
            'Salisbury': '06068',
            'Canaan': '06018',
            'Norfolk': '06058',
            'Colebrook': '06021',
            'Winsted': '06098',
            'Barkhamsted': '06063',
            'Hartland': '06091',
            'Granby': '06035',
            'East Granby': '06026',
            'Suffield': '06078',
            'Windsor': '06095',
            'Windsor Locks': '06096',
            'Enfield': '06082',
            'Somers': '06071',
            'Ellington': '06029',
            'Tolland': '06084',
            'Vernon': '06066',
            'Manchester': '06040',
            'Bolton': '06043',
            'Coventry': '06238',
            'Mansfield': '06250',
            'Storrs': '06268',
            'Willimantic': '06226',
            'Windham': '06280',
            'Canterbury': '06331',
            'Plainfield': '06374',
            'Sterling': '06377',
            'Voluntown': '06384',
            'Griswold': '06351',
            'Preston': '06365',
            'Ledyard': '06339',
            'Groton': '06340',
            'Stonington': '06378',
            'North Stonington': '06359',
            'Mystic': '06355',
            'Old Saybrook': '06475',
            'Westbrook': '06498',
            'Clinton': '06413',
            'Killingworth': '06419',
            'Durham': '06422',
            'Madison': '06443',
            'Guilford': '06437',
            'Branford': '06405',
        }
        
        updated = 0
        failed = 0
        used_fallback = 0
        
        for i, property in enumerate(properties, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(properties)} ({i/len(properties)*100:.1f}%) - Updated: {updated}, Failed: {failed}, Fallback: {used_fallback}")
            
            # Get centroid of property geometry using PostGIS
            result = db.execute(
                text("""
                    SELECT 
                        ST_Y(ST_Centroid(geometry)) as lat,
                        ST_X(ST_Centroid(geometry)) as lng
                    FROM properties
                    WHERE id = :prop_id
                """),
                {"prop_id": property.id}
            ).first()
            
            if not result:
                failed += 1
                continue
            
            lat, lng = result.lat, result.lng
            
            if not lat or not lng:
                failed += 1
                continue
            
            # Try to get zip code from geocoding
            zip_code = get_zip_from_nominatim(lat, lng)
            
            # If geocoding failed and fallback is enabled, use municipality lookup
            if not zip_code and use_municipality_fallback and property.municipality:
                zip_code = municipality_zips.get(property.municipality)
                if zip_code:
                    used_fallback += 1
            
            if zip_code:
                property.zip_code = zip_code
                updated += 1
            else:
                failed += 1
            
            # Rate limiting
            if i < len(properties):
                time.sleep(NOMINATIM_DELAY)
            
            # Commit every batch
            if i % batch_size == 0:
                db.commit()
                print(f"  ✅ Committed batch of {batch_size} properties")
        
        # Final commit
        db.commit()
        
        print()
        print("=" * 60)
        print("Summary:")
        print(f"  ✅ Updated: {updated:,} properties")
        print(f"  ⚠️  Failed: {failed:,} properties")
        print(f"  📍 Used municipality fallback: {used_fallback:,} properties")
        print(f"  📊 Success rate: {updated/len(properties)*100:.1f}%")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate zip codes for properties")
    parser.add_argument("--limit", type=int, help="Limit number of properties to process")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for commits")
    parser.add_argument("--no-fallback", action="store_true", help="Don't use municipality fallback")
    
    args = parser.parse_args()
    
    populate_zip_codes(
        batch_size=args.batch_size,
        limit=args.limit,
        use_municipality_fallback=not args.no_fallback
    )
