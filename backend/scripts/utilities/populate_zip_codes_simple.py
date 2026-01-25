"""
Quick script to populate zip codes using municipality lookup
This is much faster than geocoding and works for most CT properties
"""
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models import Property
from database import SessionLocal

load_dotenv()

# CT Municipality to primary zip code mapping
MUNICIPALITY_ZIPS = {
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
    'Darien': '06820',
    'New Canaan': '06840',
    'Wilton': '06897',
    'Redding': '06896',
    'New Fairfield': '06812',
    'Sherman': '06784',
    'Bridgewater': '06752',
    'Norfolk': '06058',
    'Colebrook': '06021',
    'Barkhamsted': '06063',
    'Hartland': '06091',
    'Andover': '06232',
    'Ashford': '06278',
    'Berlin': '06037',
    'Bloomfield': '06002',
    'Bolton': '06043',
    'Bozrah': '06334',
    'Brooklyn': '06234',
    'Burlington': '06013',
    'Canton': '06019',
    'Chaplin': '06235',
    'Colchester': '06415',
    'Columbia': '06237',
    'Cromwell': '06416',
    'Deep River': '06417',
    'Eastford': '06242',
    'East Haddam': '06423',
    'East Hampton': '06424',
    'East Lyme': '06333',
    'Easton': '06612',
    'Essex': '06426',
    'Franklin': '06254',
    'Glastonbury': '06033',
    'Goshen': '06756',
    'Haddam': '06438',
    'Hampton': '06247',
    'Hartford': '06103',
    'Hebron': '06248',
    'Killingly': '06239',
    'Lebanon': '06249',
    'Ledyard': '06339',
    'Lisbon': '06351',
    'Lyme': '06371',
    'Marlborough': '06447',
    'Montville': '06353',
    'Morris': '06763',
    'Newington': '06111',
    'North Branford': '06471',
    'North Canaan': '06018',
    'North Stonington': '06359',
    'Old Lyme': '06371',
    'Pomfret': '06258',
    'Portland': '06480',
    'Putnam': '06260',
    'Redding': '06896',
    'Salem': '06420',
    'Scotland': '06264',
    'Sprague': '06330',
    'Stafford': '06075',
    'Thompson': '06277',
    'Union': '06076',
    'Willington': '06279',
    'Wolcott': '06716',
    'Woodstock': '06281',
}

def populate_zip_codes_from_municipality():
    """
    Quickly populate zip codes using municipality lookup
    This is much faster than geocoding and works for most properties
    """
    db = SessionLocal()
    
    try:
        # Get properties without zip codes
        properties = db.query(Property).filter(
            (Property.zip_code.is_(None)) | (Property.zip_code == '')
        ).all()
        
        print(f"Found {len(properties):,} properties without zip codes")
        print("Populating zip codes from municipality mapping...")
        print()
        
        updated = 0
        not_found = 0
        
        for i, property in enumerate(properties, 1):
            if i % 1000 == 0:
                print(f"Progress: {i}/{len(properties)} ({i/len(properties)*100:.1f}%) - Updated: {updated}, Not found: {not_found}")
            
            if property.municipality:
                zip_code = MUNICIPALITY_ZIPS.get(property.municipality)
                if zip_code:
                    property.zip_code = zip_code
                    updated += 1
                else:
                    not_found += 1
            else:
                not_found += 1
        
        # Commit all changes
        db.commit()
        
        print()
        print("=" * 60)
        print("Summary:")
        print(f"  ✅ Updated: {updated:,} properties")
        print(f"  ⚠️  Not found in mapping: {not_found:,} properties")
        print(f"  📊 Success rate: {updated/len(properties)*100:.1f}%")
        print("=" * 60)
        
        if not_found > 0:
            print()
            print("Municipalities not found in mapping:")
            missing = db.query(Property.municipality).filter(
                (Property.zip_code.is_(None)) | (Property.zip_code == ''),
                Property.municipality.isnot(None)
            ).distinct().all()
            for muni in missing:
                print(f"  - {muni[0]}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    populate_zip_codes_from_municipality()
