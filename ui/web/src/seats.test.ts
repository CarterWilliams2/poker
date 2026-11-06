import { expect, test } from 'vitest'
import { seatDirection } from './seats.ts'

// Which way each seat at a table of this size sits, rounded so that a straight line reads as one.
// Adding 0 turns the -0 that rounding can give into a plain 0.
function directions(count: number) {
  return Array.from({ length: count }, (_, index) => {
    const { across, down } = seatDirection(index, count)
    return [Math.round(across) + 0, Math.round(down) + 0]
  })
}

test('two players sit across from each other, the first at the bottom', () => {
  expect(directions(2)).toEqual([
    [0, 1],
    [0, -1],
  ])
})

test('seats go clockwise from the bottom', () => {
  expect(directions(4)).toEqual([
    [0, 1],
    [-1, 0],
    [0, -1],
    [1, 0],
  ])
})

test('seats are spaced evenly around the table at every size', () => {
  for (let count = 2; count <= 8; count++) {
    const gaps = Array.from({ length: count }, (_, index) => {
      const here = seatDirection(index, count)
      const next = seatDirection((index + 1) % count, count)
      return Math.hypot(next.across - here.across, next.down - here.down)
    })
    for (const gap of gaps) {
      expect(gap).toBeCloseTo(2 * Math.sin(Math.PI / count))
    }
  }
})
