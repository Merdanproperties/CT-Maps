"""
Test pagination approach for loading all Torrington properties
"""
import requests
import time

def test_pagination():
    bbox = '-73.198876,41.776364,-73.063057,41.881801'
    base_url = 'http://localhost:8000/api/search/'
    
    page_size = 2000
    page = 1
    all_properties = []
    total = None
    
    print(f"Loading Torrington properties with pagination (page_size={page_size})...")
    
    while True:
        params = {
            'bbox': bbox,
            'page_size': page_size,
            'page': page,
            'municipality': 'Torrington'
        }
        
        start = time.time()
        response = requests.get(base_url, params=params, timeout=30)
        elapsed = time.time() - start
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break
        
        data = response.json()
        if total is None:
            total = data.get('total', 0)
            print(f"Total properties: {total:,}")
        
        properties = data.get('properties', [])
        all_properties.extend(properties)
        
        print(f"Page {page}: Loaded {len(properties):,} properties ({elapsed:.2f}s) | Total so far: {len(all_properties):,}")
        
        if len(properties) < page_size or len(all_properties) >= total:
            break
        
        page += 1
    
    print(f"\n✅ Loaded all {len(all_properties):,} properties in {page} pages")
    return all_properties

if __name__ == "__main__":
    test_pagination()
