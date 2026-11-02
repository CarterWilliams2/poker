import { expect, test } from 'vitest'
import { cardName, parseCard, SUITS } from './cards.ts'

test('splits a card into its rank and suit', () => {
  expect(parseCard('10H')).toEqual({ rank: '10', suit: 'H' })
  expect(parseCard('AS')).toEqual({ rank: 'A', suit: 'S' })
})

test('names cards the way you would say them', () => {
  expect(cardName('AS')).toBe('Ace of spades')
  expect(cardName('QH')).toBe('Queen of hearts')
  expect(cardName('7C')).toBe('7 of clubs')
})

test('only hearts and diamonds are red', () => {
  const red = Object.entries(SUITS).filter(([, suit]) => suit.red).map(([letter]) => letter)
  expect(red).toEqual(['H', 'D'])
})

test('rejects anything that is not a card', () => {
  for (const text of ['1H', '10X', 'AH ', '']) {
    expect(() => parseCard(text)).toThrow('Not a card')
  }
})
