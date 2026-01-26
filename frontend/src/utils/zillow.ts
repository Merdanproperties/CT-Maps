/**
 * Zillow URL Utility
 * Generates Zillow property search URLs from property address information
 */

/**
 * Normalize address for Zillow URL
 * - Remove special characters
 * - Replace spaces with hyphens
 * - Handle common address abbreviations
 */
function normalizeAddressForZillow(address: string): string {
  if (!address) return ''
  
  return address
    .toLowerCase()
    .trim()
    // Replace common abbreviations
    .replace(/\bstreet\b/gi, 'st')
    .replace(/\bavenue\b/gi, 'ave')
    .replace(/\broad\b/gi, 'rd')
    .replace(/\bdrive\b/gi, 'dr')
    .replace(/\blane\b/gi, 'ln')
    .replace(/\bcourt\b/gi, 'ct')
    .replace(/\bplace\b/gi, 'pl')
    .replace(/\bboulevard\b/gi, 'blvd')
    .replace(/\bparkway\b/gi, 'pkwy')
    // Remove special characters except spaces and hyphens
    .replace(/[^a-z0-9\s-]/g, '')
    // Replace multiple spaces with single space
    .replace(/\s+/g, ' ')
    // Replace spaces with hyphens
    .replace(/\s/g, '-')
    // Remove multiple consecutive hyphens
    .replace(/-+/g, '-')
    // Remove leading/trailing hyphens
    .replace(/^-+|-+$/g, '')
}

/**
 * Generate Zillow property search URL
 * Uses Zillow's search format which is more reliable than path-based URLs
 * Format: https://www.zillow.com/homes/[encoded-query]_rb/
 */
export function generateZillowUrl(
  address: string | null,
  city: string | null,
  zipCode: string | null
): string | null {
  if (!address) return null

  // Build search query parts
  const queryParts: string[] = [address]
  
  if (city) {
    queryParts.push(city)
  }
  
  if (zipCode) {
    queryParts.push(zipCode)
  }
  
  queryParts.push('CT')
  
  // Join and encode the query
  const query = queryParts.join(' ')
  const encodedQuery = encodeURIComponent(query)
  
  // Use Zillow's search format (more reliable than path-based)
  const url = `https://www.zillow.com/homes/${encodedQuery}_rb/`
  
  return url
}

/**
 * Generate Zillow search URL (alternative format using query parameters)
 * This is a fallback if the direct URL format doesn't work
 */
export function generateZillowSearchUrl(
  address: string | null,
  city: string | null,
  zipCode: string | null
): string | null {
  if (!address) return null

  const searchQuery = [address]
  if (city) searchQuery.push(city)
  if (zipCode) searchQuery.push(zipCode)
  searchQuery.push('CT')

  const query = searchQuery.join(' ')
  return `https://www.zillow.com/homes/${encodeURIComponent(query)}_rb/`
}
