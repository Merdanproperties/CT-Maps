import { useState, useEffect } from 'react'
import { propertyImageService, PropertyImage } from '../services/propertyImages'
import { ChevronLeft, ChevronRight, X, Image as ImageIcon } from 'lucide-react'
import './PropertyImageGallery.css'

interface PropertyImageGalleryProps {
  address: string | null
  city: string | null
  parcelId?: string
  images?: PropertyImage[] // Optional: if images are already provided
}

export default function PropertyImageGallery({
  address,
  city,
  parcelId,
  images: providedImages,
}: PropertyImageGalleryProps) {
  const [images, setImages] = useState<PropertyImage[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    const loadImages = async () => {
      setIsLoading(true)
      try {
        if (providedImages && providedImages.length > 0) {
          setImages(providedImages)
        } else {
          const fetchedImages = await propertyImageService.getPropertyImages(
            address,
            city,
            'CT',
            parcelId
          )
          setImages(fetchedImages)
        }
      } catch (error) {
        console.error('Failed to load property images:', error)
        setImages([propertyImageService.getPlaceholderImage()])
      } finally {
        setIsLoading(false)
      }
    }

    loadImages()
  }, [address, city, parcelId, providedImages])

  const nextImage = () => {
    setCurrentIndex((prev) => (prev + 1) % images.length)
  }

  const prevImage = () => {
    setCurrentIndex((prev) => (prev - 1 + images.length) % images.length)
  }

  const goToImage = (index: number) => {
    setCurrentIndex(index)
  }

  if (isLoading) {
    return (
      <div className="property-image-gallery loading">
        <div className="image-placeholder">
          <ImageIcon size={48} />
          <p>Loading images...</p>
        </div>
      </div>
    )
  }

  if (images.length === 0) {
    return (
      <div className="property-image-gallery empty">
        <div className="image-placeholder">
          <ImageIcon size={48} />
          <p>No images available</p>
        </div>
      </div>
    )
  }

  const currentImage = images[currentIndex]

  return (
    <>
      <div className="property-image-gallery">
        {/* Main Image */}
        <div className="gallery-main">
          <div
            className="main-image-container"
            onClick={() => setIsFullscreen(true)}
          >
            <img
              src={currentImage.url}
              alt={currentImage.description || `Property image ${currentIndex + 1}`}
              className="main-image"
              onError={(e) => {
                // Hide broken image and show placeholder
                const target = e.currentTarget
                target.style.display = 'none'
                const placeholder = target.parentElement?.querySelector('.image-error-placeholder')
                if (placeholder) {
                  (placeholder as HTMLElement).style.display = 'flex'
                }
              }}
            />
            <div className="image-error-placeholder" style={{ display: 'none' }}>
              <ImageIcon size={48} />
              <p>Image not available</p>
            </div>
            {images.length > 1 && (
              <>
                <button
                  className="gallery-nav prev"
                  onClick={(e) => {
                    e.stopPropagation()
                    prevImage()
                  }}
                  aria-label="Previous image"
                >
                  <ChevronLeft size={24} />
                </button>
                <button
                  className="gallery-nav next"
                  onClick={(e) => {
                    e.stopPropagation()
                    nextImage()
                  }}
                  aria-label="Next image"
                >
                  <ChevronRight size={24} />
                </button>
              </>
            )}
            <div className="image-counter">
              {currentIndex + 1} / {images.length}
            </div>
          </div>
        </div>

        {/* Thumbnail Strip */}
        {images.length > 1 && (
          <div className="gallery-thumbnails">
            {images.map((image, index) => (
              <button
                key={index}
                className={`thumbnail ${index === currentIndex ? 'active' : ''}`}
                onClick={() => goToImage(index)}
                aria-label={`View image ${index + 1}`}
              >
                <img
                  src={image.thumbnail || image.url}
                  alt={image.description || `Thumbnail ${index + 1}`}
                  onError={(e) => {
                    // Hide broken thumbnail
                    e.currentTarget.style.display = 'none'
                  }}
                />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div className="gallery-fullscreen" onClick={() => setIsFullscreen(false)}>
          <button
            className="fullscreen-close"
            onClick={() => setIsFullscreen(false)}
            aria-label="Close fullscreen"
          >
            <X size={24} />
          </button>
          <div className="fullscreen-content" onClick={(e) => e.stopPropagation()}>
            <img
              src={currentImage.url}
              alt={currentImage.description || `Property image ${currentIndex + 1}`}
              className="fullscreen-image"
            />
            {images.length > 1 && (
              <>
                <button
                  className="fullscreen-nav prev"
                  onClick={prevImage}
                  aria-label="Previous image"
                >
                  <ChevronLeft size={32} />
                </button>
                <button
                  className="fullscreen-nav next"
                  onClick={nextImage}
                  aria-label="Next image"
                >
                  <ChevronRight size={32} />
                </button>
                <div className="fullscreen-counter">
                  {currentIndex + 1} / {images.length}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}
