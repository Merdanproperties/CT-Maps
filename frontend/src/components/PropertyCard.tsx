import { Property, PropertyNormalizer, PropertyCardData } from '../types/property'
import { DevelopmentSafety } from '../utils/developmentSafety'
import { Home, Building2, Users, Phone, Mail } from 'lucide-react'
import './PropertyCard.css'

interface PropertyCardProps {
  property: Property | any // Accept any to handle API responses, will be normalized
  onClick?: () => void
}

export default function PropertyCard({ property, onClick }: PropertyCardProps) {
  // Development safety check - validates data structure in dev mode
  DevelopmentSafety.validatePropertyBeforeRender(property, 'PropertyCard')
  
  // Normalize and validate property data - ensures type safety and backward compatibility
  const normalizedProperty = PropertyNormalizer.normalize(property)
  const cardData = PropertyNormalizer.toCardData(normalizedProperty)
  
  // Validate property is displayable
  const validation = PropertyNormalizer.validate(normalizedProperty)
  if (!validation.isValid) {
    console.warn('Property validation failed:', validation.errors, property)
    // Still render, but with safe defaults
  }
  // Safe getter functions with defaults
  const getSafeValue = (field: string, defaultValue: any = null) => {
    return PropertyNormalizer.getSafeValue(normalizedProperty, field, defaultValue)
  }

  const formatCurrency = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatShortCurrency = (value: number | null | undefined) => {
    if (value == null || isNaN(value)) return null
    const numValue = Number(value)
    if (numValue >= 1000000) {
      return `$${(numValue / 1000000).toFixed(1)}M`
    } else if (numValue >= 1000) {
      return `$${(numValue / 1000).toFixed(0)}K`
    }
    return formatCurrency(numValue)
  }

  const formatNumber = (value: number | null | undefined, decimals: number = 0) => {
    if (value == null || isNaN(value)) return 'N/A'
    return Number(value).toLocaleString(undefined, { maximumFractionDigits: decimals })
  }

  // Determine property type display with safe fallback
  const getPropertyTypeDisplay = () => {
    const propType = getSafeValue('property_type')
    if (!propType) return null
    const type = String(propType).toLowerCase()
    if (type.includes('single') || type.includes('one')) return 'Single Family'
    if (type.includes('two') || type.includes('2')) return 'Two Family'
    if (type.includes('multi') || type.includes('5+')) return 'Multi family (5+)'
    return String(propType)
  }

  return (
    <div className="property-card" onClick={onClick} style={{ cursor: onClick ? 'pointer' : 'default' }}>
      {/* Checkbox */}
      <input type="checkbox" className="property-card-checkbox" />

      {/* Address and Location - Safe with defaults */}
      <div className="property-header">
        <h3>{getSafeValue('address', 'No Address')}</h3>
        {getSafeValue('municipality') && (
          <span className="municipality">
            {getSafeValue('municipality')}, CT {getSafeValue('zip_code', '')}
          </span>
        )}
      </div>

      {/* Owner Section */}
      <div className="property-owner">
        <span className="owner-label">Owner:</span>
        <span className="owner-value">{getSafeValue('owner_name', 'N/A')}</span>
      </div>

      {/* Details - Compact pairs */}
      <div className="property-details-compact">
        {/* Building Area / Lot Size */}
        {(() => {
          const buildingArea = getSafeValue('building_area_sqft')
          const lotSize = getSafeValue('lot_size_sqft')
          if (buildingArea != null || lotSize != null) {
            const parts = []
            if (buildingArea != null) {
              parts.push(`${formatNumber(buildingArea)} sqft`)
            }
            if (lotSize != null) {
              parts.push(`${formatNumber(lotSize)} sqft lot`)
            }
            return (
              <div className="detail-pair">
                <span className="detail-value">{parts.join(' / ')}</span>
              </div>
            )
          }
          return null
        })()}

        {/* Land Use / Property Type */}
        {(() => {
          const landUse = getSafeValue('land_use')
          const propertyType = getPropertyTypeDisplay()
          if (landUse || propertyType) {
            const parts = []
            if (landUse) parts.push(landUse)
            if (propertyType) parts.push(propertyType)
            return (
              <div className="detail-pair">
                <span className="detail-value">{parts.join(' / ')}</span>
              </div>
            )
          }
          return null
        })()}

        {/* Zoning */}
        {(() => {
          const zoning = getSafeValue('zoning')
          if (zoning) {
            return (
              <div className="detail-pair">
                <span className="detail-value">Zoning: {zoning}</span>
              </div>
            )
          }
          return null
        })()}

        {/* Year Sold / Last Sale Price */}
        {(() => {
          const lastSaleDate = getSafeValue('last_sale_date')
          const lastSalePrice = getSafeValue('last_sale_price')
          // Extract year from sale date if it's a date string
          let yearSold = null
          if (lastSaleDate) {
            try {
              const date = new Date(lastSaleDate)
              if (!isNaN(date.getTime())) {
                yearSold = date.getFullYear()
              }
            } catch (e) {
              // If parsing fails, try to extract year from string
              const yearMatch = String(lastSaleDate).match(/\d{4}/)
              if (yearMatch) {
                yearSold = parseInt(yearMatch[0])
              }
            }
          }
          if (yearSold != null || lastSalePrice != null) {
            const parts = []
            if (yearSold != null) {
              parts.push(String(yearSold))
            }
            if (lastSalePrice != null) {
              parts.push(formatShortCurrency(lastSalePrice) || 'N/A')
            }
            return (
              <div className="detail-pair">
                <span className="detail-value">{parts.join(' / ')}</span>
              </div>
            )
          }
          return null
        })()}
      </div>

      {/* Contact Information - Bottom */}
      <div className="property-contact-bottom">
        <div className="contact-item">
          <Phone size={14} className="contact-icon" />
          {getSafeValue('owner_phone') ? (
            <a 
              href={`tel:${getSafeValue('owner_phone')}`} 
              className="contact-link" 
              onClick={(e) => e.stopPropagation()}
            >
              {getSafeValue('owner_phone')}
            </a>
          ) : (
            <span className="contact-na">N/A</span>
          )}
        </div>
        <div className="contact-item">
          <Mail size={14} className="contact-icon" />
          {getSafeValue('owner_email') ? (
            <a 
              href={`mailto:${getSafeValue('owner_email')}`} 
              className="contact-link" 
              onClick={(e) => e.stopPropagation()}
            >
              {getSafeValue('owner_email')}
            </a>
          ) : (
            <span className="contact-na">N/A</span>
          )}
        </div>
      </div>

      {/* Tags - Safe with number conversion */}
      <div className="property-tags">
        {Number(getSafeValue('is_absentee', 0)) === 1 && (
          <span className="tag tag-absentee">Absentee Owners</span>
        )}
        {Number(getSafeValue('is_vacant', 0)) === 1 && (
          <span className="tag tag-vacant">Vacant</span>
        )}
        {/* Additional tags can be added here safely */}
      </div>
    </div>
  )
}
