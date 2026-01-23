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

      {/* Estimated Value (Top Right) - Safe rendering */}
      <div className="property-value-section">
        {getSafeValue('assessed_value') != null && (
          <>
            <div className="property-value">{formatShortCurrency(getSafeValue('assessed_value'))}</div>
            <div className="value-label">Est. Value</div>
          </>
        )}
      </div>

      {/* Details Row - Safe with null checks */}
      <div className="property-details">
        {getSafeValue('building_area_sqft') != null && (
          <div className="detail-row">
            <Home size={16} className="icon" />
            <span className="value">{formatNumber(getSafeValue('building_area_sqft'))} sqft</span>
          </div>
        )}

        {getSafeValue('lot_size_sqft') != null && (
          <div className="detail-row">
            <Home size={16} className="icon" />
            <span className="value">{formatNumber(getSafeValue('lot_size_sqft'))} lot</span>
          </div>
        )}

        {getPropertyTypeDisplay() && (
          <div className="detail-row">
            <Building2 size={16} className="icon" />
            <span className="value">{getPropertyTypeDisplay()}</span>
          </div>
        )}

        {/* Additional fields can be added here safely */}
        {getSafeValue('bedrooms') != null && (
          <div className="detail-row">
            <Home size={16} className="icon" />
            <span className="value">{getSafeValue('bedrooms')} Bedrooms</span>
          </div>
        )}

        {getSafeValue('bathrooms') != null && (
          <div className="detail-row">
            <Home size={16} className="icon" />
            <span className="value">{getSafeValue('bathrooms')} Bathrooms</span>
          </div>
        )}

        {Number(getSafeValue('is_absentee', 0)) === 1 && (
          <div className="detail-row">
            <Users size={16} className="icon" />
            <span className="value">Individual Owned</span>
          </div>
        )}
      </div>

      {/* Owner Name (Bottom Right) - Safe */}
      <div className="equity-section">
        <div className="equity-value">{getSafeValue('owner_name', 'N/A Owner')}</div>
        <div className="value-label">Owner</div>
      </div>

      {/* Contact Information - Always show with safe defaults */}
      <div className="property-contact">
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
