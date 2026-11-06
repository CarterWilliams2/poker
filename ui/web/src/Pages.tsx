import { lazy, Suspense } from 'react'
import App from './App.tsx'
import Watch from './Watch.tsx'

// Loaded only when asked for, so the other pages don't have to carry every sample match.
const Fixtures = lazy(() => import('./Fixtures.tsx'))

// The page for this address. A new page also needs its address in PAGES in ui/server/app.py.
export default function Pages() {
  switch (location.pathname.replace(/\/$/, '')) {
    case '/watch':
      return <Watch />
    case '/dev/fixtures':
      return (
        <Suspense>
          <Fixtures />
        </Suspense>
      )
    default:
      return <App />
  }
}
