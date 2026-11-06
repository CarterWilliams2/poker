import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import Pages from './Pages.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Pages />
  </StrictMode>,
)
