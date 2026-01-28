"""
Validate Zillow URL generation for properties
Tests URL format generation (does not require network access)
"""
import sys
from pathlib import Path
from sqlalchemy.orm import Session
from typing import List, Dict, Tuple
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from models import Property
from database import SessionLocal

# Try to load .env, but don't fail if it doesn't exist or has permission issues
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # Continue without .env file

def normalize_address_for_zillow(address: str) -> str:
    """Normalize address for Zillow URL (matches frontend logic)"""
    if not address:
        return ''
    
    normalized = address.lower().strip()
    
    # Replace common abbreviations
    replacements = {
        'street': 'st',
        'avenue': 'ave',
        'road': 'rd',
        'drive': 'dr',
        'lane': 'ln',
        'court': 'ct',
        'place': 'pl',
        'boulevard': 'blvd',
        'parkway': 'pkwy'
    }
    
    for full, abbrev in replacements.items():
        normalized = normalized.replace(f' {full} ', f' {abbrev} ')
        normalized = normalized.replace(f' {full},', f' {abbrev},')
        if normalized.endswith(f' {full}'):
            normalized = normalized[:-len(f' {full}')] + f' {abbrev}'
    
    # Remove special characters except spaces and hyphens
    normalized = ''.join(c if c.isalnum() or c in ' -' else ' ' for c in normalized)
    
    # Clean up spaces
    normalized = ' '.join(normalized.split())
    
    # Replace spaces with hyphens
    normalized = normalized.replace(' ', '-')
    
    # Remove multiple consecutive hyphens
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    
    # Remove leading/trailing hyphens
    normalized = normalized.strip('-')
    
    return normalized

def generate_zillow_url(address: str, city: str = None, zip_code: str = None) -> str:
    """Generate Zillow URL (matches frontend logic exactly)"""
    if not address:
        return None
    
    # Build search query parts (matches frontend exactly)
    query_parts = [address]
    if city:
        query_parts.append(city)
    if zip_code:
        query_parts.append(zip_code)
    query_parts.append('CT')
    
    # Join and encode the query (matches frontend encodeURIComponent)
    query = ' '.join(query_parts)
    # Use quote (not quote_plus) to match JavaScript encodeURIComponent
    # encodeURIComponent uses %20 for spaces, not +
    from urllib.parse import quote
    encoded_query = quote(query, safe='')
    
    # Use Zillow's search format (matches frontend)
    url = f"https://www.zillow.com/homes/{encoded_query}_rb/"
    
    return url

def test_url_format(address: str, city: str = None, zip_code: str = None) -> Tuple[str, bool]:
    """Test URL format generation (format validation only, no network check)"""
    url = generate_zillow_url(address, city, zip_code)
    if not url:
        return None, False
    
    # Validate URL format
    is_valid_format = (
        url.startswith('https://www.zillow.com/homes/') and
        url.endswith('_rb/') and
        'zillow.com' in url
    )
    
    return url, is_valid_format

def validate_properties(db: Session, limit: int = None) -> Dict:
    """Validate Zillow URLs for properties"""
    query = db.query(Property).filter(
        Property.address.isnot(None),
        Property.address != ''
    )
    if limit:
        query = query.limit(limit)
    properties = query.all()
    
    results = {
        'total': len(properties),
        'valid_urls': 0,
        'invalid_urls': 0,
        'missing_address': 0,
        'sample_urls': [],
        'issues': []
    }
    
    for prop in properties:
        if not prop.address:
            results['missing_address'] += 1
            continue
        
        url, is_valid = test_url_format(
            prop.address,
            prop.municipality,
            prop.zip_code
        )
        
        if url:
            results['valid_urls'] += 1
            if len(results['sample_urls']) < 10:
                results['sample_urls'].append({
                    'id': prop.id,
                    'address': prop.address,
                    'city': prop.municipality,
                    'zip': prop.zip_code,
                    'url': url,
                    'valid': is_valid
                })
        else:
            results['invalid_urls'] += 1
            results['issues'].append({
                'id': prop.id,
                'address': prop.address,
                'reason': 'Could not generate URL'
            })
    
    return results

def main():
    """Main validation function"""
    print("🔍 Validating Zillow URL generation...")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # Test with ALL properties
        print("\n📊 Testing ALL properties with addresses...")
        total_count = db.query(Property).filter(
            Property.address.isnot(None),
            Property.address != ''
        ).count()
        print(f"   Found {total_count} properties with addresses")
        
        # Test all properties (no limit)
        results = validate_properties(db, limit=None)
        
        print(f"\n✅ Results:")
        print(f"   Total properties tested: {results['total']}")
        print(f"   Valid URLs generated: {results['valid_urls']}")
        print(f"   Invalid URLs: {results['invalid_urls']}")
        print(f"   Missing addresses: {results['missing_address']}")
        
        if results['sample_urls']:
            print(f"\n📋 Sample URLs (first {len(results['sample_urls'])}):")
            for sample in results['sample_urls']:
                print(f"\n   Property ID: {sample['id']}")
                print(f"   Address: {sample['address']}")
                print(f"   City: {sample['city'] or 'N/A'}")
                print(f"   Zip: {sample['zip'] or 'N/A'}")
                print(f"   URL: {sample['url']}")
                print(f"   Format Valid: {'✅' if sample['valid'] else '❌'}")
        
        if results['issues']:
            print(f"\n⚠️  Issues found: {len(results['issues'])}")
            for issue in results['issues'][:5]:  # Show first 5
                print(f"   - Property {issue['id']}: {issue['address']} - {issue['reason']}")
        
        print("\n" + "=" * 60)
        print("✅ Validation complete!")
        print("\n💡 Note: URL format validation only. Actual Zillow page availability")
        print("   depends on whether the property exists in Zillow's database.")
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    main()
