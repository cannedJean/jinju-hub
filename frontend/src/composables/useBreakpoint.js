import { getCurrentScope, onScopeDispose, ref } from 'vue'

const DESKTOP_QUERY = '(min-width: 1280px)'
const TABLET_QUERY = '(min-width: 768px) and (max-width: 1279px)'
const MOBILE_QUERY = '(max-width: 767px)'

function track(query, target) {
  const mql = window.matchMedia(query)
  target.value = mql.matches
  const onChange = (event) => {
    target.value = event.matches
  }
  mql.addEventListener('change', onChange)
  return () => mql.removeEventListener('change', onChange)
}

export function useBreakpoint() {
  const isDesktop = ref(false)
  const isTablet = ref(false)
  const isMobile = ref(false)
  const stops = [
    track(DESKTOP_QUERY, isDesktop),
    track(TABLET_QUERY, isTablet),
    track(MOBILE_QUERY, isMobile),
  ]
  // Outside a component/effect scope (e.g. unit tests) there is nothing to dispose with.
  if (getCurrentScope()) onScopeDispose(() => stops.forEach((stop) => stop()))
  return { isDesktop, isTablet, isMobile }
}
