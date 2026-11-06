import { lazy, Suspense } from 'react'
import App from './App.tsx'

// Loaded only when asked for, so the other pages don't have to carry every sample match.
const Fixtures = lazy(() => import('./Fixtures.tsx'))

// The page for this address. A new page also needs its address in PAGES in ui/server/app.py.
export default function Pages() {
  if (location.pathname.replace(/\/$/, '') === '/dev/fixtures') {
    return (
      <Suspense>
        <Fixtures />
      </Suspense>
    )
  }
  return <App />
}
