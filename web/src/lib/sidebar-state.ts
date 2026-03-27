/**
 * Read the sidebar state from localStorage
 * Returns true (expanded) by default if not set
 */
export function getSidebarState(): boolean {
  if (typeof window === 'undefined') return true

  const value = localStorage.getItem('cayuSidebarState')

  if (value === null) return true

  return value === 'true'
}
