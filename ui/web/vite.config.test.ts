// @vitest-environment node
import { createHash } from 'node:crypto'
import { createServer as createHttpServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import { fileURLToPath } from 'node:url'
import { createServer, type ViteDevServer } from 'vite'
import { afterAll, beforeAll, expect, test, vi } from 'vitest'

const addressOf = (server: Server) => server.address() as AddressInfo

// The address of every WebSocket that reached the stand-in for the Python server.
const sockets: string[] = []
let pythonServer: Server
let devServer: ViteDevServer
let host: string

beforeAll(async () => {
  pythonServer = createHttpServer((request, response) => {
    response.end(`Python answered ${request.url}`)
  })
  // Completes the WebSocket handshake, as RFC 6455 sets it out. A browser only opens the socket if
  // this answer comes back to it, because the answer is worked out from the key it sent.
  pythonServer.on('upgrade', (request, socket) => {
    sockets.push(request.url!)
    const accept = createHash('sha1')
      .update(`${request.headers['sec-websocket-key']}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
      .digest('base64')
    socket.end(
      'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n' +
        `Sec-WebSocket-Accept: ${accept}\r\n\r\n`,
    )
  })
  await new Promise<void>((listening) => pythonServer.listen(0, '127.0.0.1', listening))

  vi.stubEnv('POKER_SERVER_PORT', String(addressOf(pythonServer).port))
  devServer = await createServer({
    configFile: fileURLToPath(new URL('vite.config.ts', import.meta.url)),
    logLevel: 'silent',
    // Any free port, and no need to watch files or look for packages to prepare: these tests only
    // make requests.
    server: { port: 0, watch: null },
    optimizeDeps: { noDiscovery: true },
  })
  await devServer.listen()
  const { address, port } = addressOf(devServer.httpServer as Server)
  host = `${address}:${port}`
})

afterAll(async () => {
  vi.unstubAllEnvs()
  await devServer.close()
  pythonServer.close()
})

test('only listens on this computer', () => {
  expect(host).toMatch(/^127\.0\.0\.1:/)
})

test('passes API requests to the Python server', async () => {
  const response = await fetch(`http://${host}/api/deal?seed=7`)
  expect(await response.text()).toBe('Python answered /api/deal?seed=7')
})

test('passes WebSockets to the Python server', async () => {
  await new Promise((opened, failed) => {
    const socket = new WebSocket(`ws://${host}/ws/watch`)
    socket.onopen = opened
    socket.onerror = failed
  })
  expect(sockets).toEqual(['/ws/watch'])
})

test('serves the web app itself, with hot reload', async () => {
  const page = await (await fetch(`http://${host}/`)).text()
  expect(page).toContain('/src/main.tsx')
  expect(page).toContain('/@vite/client')
})

test('serves the web app at its other pages too', async () => {
  const page = await (await fetch(`http://${host}/dev/fixtures`)).text()
  expect(page).toContain('/src/main.tsx')
})

test('can load the samples, which sit outside the web folder', async () => {
  const code = await (await fetch(`http://${host}/src/Fixtures.tsx`)).text()
  const [, address] = code.match(/"([^"]*heads-up\.json[^"]*)"/)!
  const sample = await fetch(`http://${host}${address}`)
  expect(sample.status).toBe(200)
  expect(await sample.text()).toContain('match_start')
})
