import { useState, useEffect } from 'react'

/**
 * Returns a debounced version of value that updates after delayMs of no changes.
 * Used to throttle API calls (e.g. search) while keeping the input responsive.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debouncedValue
}
