import { computeTextDiff, applyDiff, graphemeSplit } from '../../src/utils/textDiff';
import { InlineRevisionDiff, DiffOperationType } from '../../src/types/inlineRevision';

describe('graphemeSplit', () => {
  it('should split ASCII string into characters', () => {
    expect(graphemeSplit('abc')).toEqual(['a', 'b', 'c']);
  });

  it('should split Japanese characters', () => {
    expect(graphemeSplit('あいう')).toEqual(['あ', 'い', 'う']);
  });

  it('should handle mixed ASCII and Japanese', () => {
    expect(graphemeSplit('aあb')).toEqual(['a', 'あ', 'b']);
  });

  it('should handle emoji', () => {
    expect(graphemeSplit('😀😃')).toEqual(['😀', '😃']);
  });

  it('should handle ruby annotations', () => {
    expect(graphemeSplit('漢|かん|字|じ|')).toEqual(['漢', '|', 'か', 'ん', '|', '字', '|', 'じ', '|']);
  });
});

describe('computeTextDiff', () => {
  it('should return empty operations for identical strings', () => {
    const diff = computeTextDiff('hello', 'hello');
    expect(diff.operations.every((op) => op.type === 'equal')).toBe(true);
    expect(diff.originalLength).toBe(5);
    expect(diff.revisedLength).toBe(5);
  });

  it('should detect insertions', () => {
    const diff = computeTextDiff('abc', 'axbc');
    const inserts = diff.operations.filter((op) => op.type === 'insert');
    expect(inserts.length).toBe(1);
    expect(inserts[0].text).toBe('x');
  });

  it('should detect deletions', () => {
    const diff = computeTextDiff('axbc', 'abc');
    const deletes = diff.operations.filter((op) => op.type === 'delete');
    expect(deletes.length).toBe(1);
    expect(deletes[0].text).toBe('x');
  });

  it('should detect replacements', () => {
    const diff = computeTextDiff('abc', 'axc');
    const inserts = diff.operations.filter((op) => op.type === 'insert');
    const deletes = diff.operations.filter((op) => op.type === 'delete');
    expect(inserts.length).toBe(1);
    expect(deletes.length).toBe(1);
  });

  it('should handle Japanese text insertions', () => {
    const diff = computeTextDiff('こんにちは', 'こんにちは世界');
    const inserts = diff.operations.filter((op) => op.type === 'insert');
    expect(inserts.length).toBe(2);
    expect(inserts.map((op) => op.text).join('')).toBe('世界');
  });

  it('should handle Japanese text deletions', () => {
    const diff = computeTextDiff('こんにちは世界', 'こんにちは');
    const deletes = diff.operations.filter((op) => op.type === 'delete');
    expect(deletes.length).toBe(2);
    expect(deletes.map((op) => op.text).join('')).toBe('世界');
  });

  it('should handle Japanese text replacements', () => {
    const diff = computeTextDiff('おはようございます', 'こんばんはございます');
    const inserts = diff.operations.filter((op) => op.type === 'insert');
    const deletes = diff.operations.filter((op) => op.type === 'delete');
    expect(inserts.length).toBeGreaterThan(0);
    expect(deletes.length).toBeGreaterThan(0);
  });

  it('should handle ruby-annotated text', () => {
    const original = '漢|かん|字|じ|';
    const revised = '漢|かん|字|じ|';
    const diff = computeTextDiff(original, revised);
    expect(diff.operations.every((op) => op.type === 'equal')).toBe(true);
  });

  it('should handle ruby annotation changes', () => {
    const original = '漢|かん|字|じ|';
    const revised = '漢|かん|字|し|';
    const diff = computeTextDiff(original, revised);
    const inserts = diff.operations.filter((op) => op.type === 'insert');
    const deletes = diff.operations.filter((op) => op.type === 'delete');
    expect(inserts.length).toBe(1);
    expect(deletes.length).toBe(1);
  });

  it('should handle empty strings', () => {
    const diff = computeTextDiff('', 'hello');
    expect(diff.operations.every((op) => op.type === 'insert')).toBe(true);
    expect(applyDiff('', diff)).toBe('hello');
  });

  it('should handle deletion to empty', () => {
    const diff = computeTextDiff('hello', '');
    expect(diff.operations.every((op) => op.type === 'delete')).toBe(true);
  });

  it('should maintain correct originalLength and revisedLength', () => {
    const diff = computeTextDiff('abc', 'abcd');
    expect(diff.originalLength).toBe(3);
    expect(diff.revisedLength).toBe(4);
  });
});

describe('applyDiff', () => {
  it('should reconstruct revised text from diff', () => {
    const original = 'hello world';
    const revised = 'hello beautiful world';
    const diff = computeTextDiff(original, revised);
    const result = applyDiff(original, diff);
    expect(result).toBe(revised);
  });

  it('should handle Japanese text', () => {
    const original = 'こんにちは';
    const revised = 'こんにちは世界';
    const diff = computeTextDiff(original, revised);
    const result = applyDiff(original, diff);
    expect(result).toBe(revised);
  });

  it('should handle deletions', () => {
    const original = 'hello beautiful world';
    const revised = 'hello world';
    const diff = computeTextDiff(original, revised);
    const result = applyDiff(original, diff);
    expect(result).toBe(revised);
  });

  it('should handle replacements', () => {
    const original = 'おはようございます';
    const revised = 'こんばんはございます';
    const diff = computeTextDiff(original, revised);
    const result = applyDiff(original, diff);
    expect(result).toBe(revised);
  });

  it('should handle empty original', () => {
    const diff = computeTextDiff('', 'hello');
    const result = applyDiff('', diff);
    expect(result).toBe('hello');
  });

  it('should handle deletion to empty', () => {
    const diff = computeTextDiff('hello', '');
    const result = applyDiff('hello', diff);
    expect(result).toBe('');
  });
});

describe('diffToString', () => {
  it('should format diff as string', () => {
    const diff = computeTextDiff('abc', 'axbc');
    const str = diffToString(diff);
    expect(str).toContain('+x');
  });

  it('should show deletions with -', () => {
    const diff = computeTextDiff('axbc', 'abc');
    const str = diffToString(diff);
    expect(str).toContain('-x');
  });

  it('should show equal with space', () => {
    const diff = computeTextDiff('abc', 'abc');
    const str = diffToString(diff);
    expect(str).toMatch(/^[ a]+$/);
  });
});