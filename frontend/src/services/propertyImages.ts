/**
 * Property Image Service
 * Fetches property images from various sources (Zillow, Google Street View, etc.)
 */

export interface PropertyImage {
  url: string
  source: 'zillow' | 'google_street_view' | 'placeholder' | 'custom'
  thumbnail?: string
  description?: string
}

class PropertyImageService {
  /**
   * Get property images from various sources
   */
  async getPropertyImages(
    address: string | null,
    city: string | null,
    state: string = 'CT',
    parcelId?: string
  ): Promise<PropertyImage[]> {
    const images: PropertyImage[] = []

    if (!address || !city) {
      // Return placeholder if no address
      return [this.getPlaceholderImage()]
    }

    // Try Google Street View first (free, no API key needed for basic usage)
    const streetViewImage = this.getGoogleStreetViewImage(address, city, state)
    if (streetViewImage) {
      images.push(streetViewImage)
    }

    // Try Zillow-style image URL (if we have parcel ID or can construct it)
    // Note: Zillow doesn't have a public API, but we can try to construct URLs
    // This is a placeholder - in production, you'd need to use a service that provides this
    if (parcelId) {
      const zillowImage = this.getZillowStyleImage(address, city, state, parcelId)
      if (zillowImage) {
        images.push(zillowImage)
      }
    }

      // If no images found, return placeholder
      if (images.length === 0) {
        images.push(this.getPlaceholderImage())
      }

    return images
  }

  /**
   * Get Google Street View image
   * Uses Google Street View Static API (free tier: $200/month = ~28,000 images)
   * Requires VITE_GOOGLE_STREET_VIEW_API_KEY environment variable
   */
  private getGoogleStreetViewImage(
    address: string,
    city: string,
    state: string
  ): PropertyImage | null {
    try {
      // Check if API key is configured
      const apiKey = import.meta.env.VITE_GOOGLE_STREET_VIEW_API_KEY
      if (!apiKey) {
        // API key not configured - return null to fall back to placeholder
        return null
      }

      // Construct address string
      const fullAddress = `${address}, ${city}, ${state}`
      const encodedAddress = encodeURIComponent(fullAddress)
      
      // Google Street View Static API URL
      // Documentation: https://developers.google.com/maps/documentation/streetview/get-api-key
      // Free tier: $200/month credit = ~28,000 images free
      const streetViewUrl = `https://maps.googleapis.com/maps/api/streetview?size=800x600&location=${encodedAddress}&key=${apiKey}`
      
      return {
        url: streetViewUrl,
        source: 'google_street_view',
        thumbnail: `https://maps.googleapis.com/maps/api/streetview?size=400x300&location=${encodedAddress}&key=${apiKey}`,
        description: `Street view of ${fullAddress}`,
      }
    } catch (error) {
      console.warn('Failed to generate street view image:', error)
      return null
    }
  }

  /**
   * Get Zillow-style image (placeholder - would need actual integration)
   */
  private getZillowStyleImage(
    address: string,
    city: string,
    state: string,
    parcelId: string
  ): PropertyImage | null {
    // This is a placeholder - Zillow doesn't have a public API
    // In production, you'd integrate with a service like:
    // - Rentals.com API
    // - RealtyMole API
    // - Or scrape (with proper permissions)
    
    // Return null - will fall back to placeholder
    // In production, integrate with actual property image service
    return null
  }

  /**
   * Get placeholder image using data URI (no external dependency)
   */
  getPlaceholderImage(): PropertyImage {
    // Use SVG data URI instead of external service
    const svgPlaceholder = (width: number, height: number, text: string) => {
      const svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#E0E0E0"/>
        <text x="50%" y="50%" font-family="Arial, sans-serif" font-size="16" fill="#999" text-anchor="middle" dominant-baseline="middle">${text}</text>
      </svg>`
      return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
    }
    
    return {
      url: svgPlaceholder(800, 600, 'No Image Available'),
      source: 'placeholder',
      thumbnail: svgPlaceholder(400, 300, 'No Image'),
      description: 'No image available for this property',
    }
  }

  /**
   * Get image from custom source (if stored in database)
   */
  getCustomImage(imageUrl: string): PropertyImage {
    return {
      url: imageUrl,
      source: 'custom',
      thumbnail: imageUrl,
      description: 'Property image',
    }
  }
}

export const propertyImageService = new PropertyImageService()
