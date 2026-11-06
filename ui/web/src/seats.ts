// Which way a seat sits from the middle of the table, with `down` pointing down the screen. The
// first seat is at the bottom and the rest go clockwise from it, the way play goes round a table.
export function seatDirection(index: number, count: number) {
  const angle = Math.PI / 2 + (2 * Math.PI * index) / count
  return { across: Math.cos(angle), down: Math.sin(angle) }
}
