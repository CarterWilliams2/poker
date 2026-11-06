import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import Pages from './Pages.tsx'

// These tests only check which page is picked. The real review page takes too long to draw to wait
// for here, and the real watch page would connect to a server. Each has tests of its own.
vi.mock('./Fixtures.tsx', () => ({ default: () => <h1>Sample states</h1> }))
vi.mock('./Watch.tsx', () => ({ default: () => <h1>Watch</h1> }))

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  history.pushState({}, '', '/')
})

test('the deal is the page at /', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
  render(<Pages />)
  expect(await screen.findByRole('button', { name: 'Deal again' })).toBeTruthy()
  expect(screen.queryByText('Sample states')).toBeNull()
})

test.each(['/watch', '/watch/'])('the watch page is at %s, and deals nothing', (address) => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  history.pushState({}, '', address)
  render(<Pages />)
  expect(screen.getByRole('heading', { name: 'Watch' })).toBeTruthy()
  expect(screen.queryByText('Deal again')).toBeNull()
  expect(fetch).not.toHaveBeenCalled()
})

test.each(['/dev/fixtures', '/dev/fixtures/'])(
  'the review page is at %s, and deals nothing',
  async (address) => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    history.pushState({}, '', address)
    render(<Pages />)
    expect(await screen.findByText('Sample states')).toBeTruthy()
    expect(screen.queryByText('Deal again')).toBeNull()
    expect(fetch).not.toHaveBeenCalled()
  },
)

test('the web app starts on the page for its address', async () => {
  history.pushState({}, '', '/dev/fixtures')
  document.body.innerHTML = '<div id="root"></div>'
  await import('./main.tsx')
  expect(await screen.findByText('Sample states')).toBeTruthy()
  document.body.innerHTML = ''
})
