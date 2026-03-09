'use strict';

const { _normalize, _countDuplicates } = require('./index');

describe('normalize', () => {
  test('lowercases and trims', () => {
    expect(_normalize('  Chiavi  ')).toBe('chiavi');
  });

  test('removes definite articles', () => {
    expect(_normalize('il telefono')).toBe('telefono');
    expect(_normalize('la borsa')).toBe('borsa');
    expect(_normalize('lo zaino')).toBe('zaino');
    expect(_normalize('le chiavi')).toBe('chiavi');
    expect(_normalize('gli occhiali')).toBe('occhiali');
    expect(_normalize("l'ombrello")).toBe('ombrello');
  });

  test('removes indefinite articles', () => {
    expect(_normalize('un passaporto')).toBe('passaporto');
    expect(_normalize('una borsa')).toBe('borsa');
    expect(_normalize('uno zaino')).toBe('zaino');
  });

  test('removes apostrophe prepositions', () => {
    expect(_normalize("nell'armadio")).toBe('armadio');
    expect(_normalize("sull'armadio")).toBe('armadio');
    expect(_normalize("dall'armadio")).toBe('armadio');
    expect(_normalize("dell'armadio")).toBe('armadio');
    expect(_normalize("all'armadio")).toBe('armadio');
  });

  test('handles empty / null input', () => {
    expect(_normalize('')).toBe('');
    expect(_normalize(null)).toBe('');
    expect(_normalize(undefined)).toBe('');
  });
});

describe('countDuplicates', () => {
  const items = [
    { name: 'chiavi' },
    { name: 'chiavi 2' },
    { name: 'telefono' },
  ];

  test('counts base name and numbered variants', () => {
    expect(_countDuplicates('chiavi', items)).toBe(2);
  });

  test('counts single item', () => {
    expect(_countDuplicates('telefono', items)).toBe(1);
  });

  test('returns 0 when no match', () => {
    expect(_countDuplicates('passaporto', items)).toBe(0);
  });

  test('does not match partial names', () => {
    expect(_countDuplicates('chia', items)).toBe(0);
  });
});
