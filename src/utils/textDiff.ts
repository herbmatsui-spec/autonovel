import { InlineRevisionDiff, DiffOperation, DiffOperationType } from '../types/inlineRevision';

export function graphemeSplit(str: string): string[] {
  return [...str];
}

export function computeTextDiff(original: string, revised: string): InlineRevisionDiff {
  const originalChars = graphemeSplit(original);
  const revisedChars = graphemeSplit(revised);

  const dp: number[][] = Array.from({ length: originalChars.length + 1 }, () =>
    Array(revisedChars.length + 1).fill(0)
  );

  for (let i = 1; i <= originalChars.length; i++) {
    for (let j = 1; j <= revisedChars.length; j++) {
      if (originalChars[i - 1] === revisedChars[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  const operations: DiffOperation[] = [];
  let i = originalChars.length;
  let j = revisedChars.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && originalChars[i - 1] === revisedChars[j - 1]) {
      operations.unshift({
        type: 'equal',
        text: originalChars[i - 1],
        originalIndex: i - 1,
        revisedIndex: j - 1,
      });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      operations.unshift({
        type: 'insert',
        text: revisedChars[j - 1],
        revisedIndex: j - 1,
      });
      j--;
    } else {
      operations.unshift({
        type: 'delete',
        text: originalChars[i - 1],
        originalIndex: i - 1,
      });
      i--;
    }
  }

  return {
    operations,
    originalLength: originalChars.length,
    revisedLength: revisedChars.length,
  };
}

export function applyDiff(original: string, diff: InlineRevisionDiff): string {
  let result = '';
  for (const op of diff.operations) {
    if (op.type !== 'delete') {
      result += op.text;
    }
  }
  return result;
}

export function diffToString(diff: InlineRevisionDiff): string {
  return diff.operations
    .map((op) => {
      const prefix = op.type === 'insert' ? '+' : op.type === 'delete' ? '-' : ' ';
      return `${prefix}${op.text}`;
    })
    .join('');
}