import React, { useMemo } from 'react';
import { InlineRevisionDiff, DiffOperation } from '../../types/inlineRevision';

interface DiffViewerProps {
  original: string;
  revised: string;
  showLineNumbers?: boolean;
  granularity?: 'line' | 'char';
  onOperationClick?: (operation: DiffOperation) => void;
}

interface DiffLine {
  type: 'equal' | 'insert' | 'delete';
  content: string;
  originalIndex?: number;
  revisedIndex?: number;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  original,
  revised,
  showLineNumbers = true,
  granularity = 'char',
  onOperationClick,
}) => {
  const diffLines = useMemo(() => {
    if (granularity === 'char') {
      return computeCharDiff(original, revised);
    }
    return computeLineDiff(original, revised);
  }, [original, revised, granularity]);

  return (
    <div className="diff-viewer">
      <div className="diff-header">
        <span className="diff-legend">
          <span className="legend-item"><span className="diff-delete"></span>削除</span>
          <span className="legend-item"><span className="diff-insert"></span>追加</span>
          <span className="legend-item"><span className="diff-equal"></span>同一</span>
        </span>
        <span className="granularity-toggle">
          粒度: <strong>{granularity === 'char' ? '文字' : '行'}</strong>
        </span>
      </div>

      <div className="diff-content">
        <div className="diff-pane original">
          <div className="pane-header">原文</div>
          <div className="diff-lines">
            {diffLines.map((line, index) => (
              <DiffLineComponent
                key={index}
                line={line}
                showLineNumbers={showLineNumbers}
                lineNumber={index + 1}
                pane="original"
                onClick={onOperationClick}
              />
            ))}
          </div>
        </div>

        <div className="diff-pane revised">
          <div className="pane-header">修正後</div>
          <div className="diff-lines">
            {diffLines.map((line, index) => (
              <DiffLineComponent
                key={index}
                line={line}
                showLineNumbers={showLineNumbers}
                lineNumber={index + 1}
                pane="revised"
                onClick={onOperationClick}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

interface DiffLineComponentProps {
  line: DiffLine;
  showLineNumbers: boolean;
  lineNumber: number;
  pane: 'original' | 'revised';
  onClick?: (operation: any) => void;
}

const DiffLineComponent: React.FC<DiffLineComponentProps> = ({
  line,
  showLineNumbers,
  lineNumber,
  pane,
  onClick,
}) => {
  const shouldShow = (pane === 'original' && line.type !== 'insert') ||
    (pane === 'revised' && line.type !== 'delete');

  if (!shouldShow) {
    return (
      <div className={`diff-line placeholder ${line.type}`}>
        {showLineNumbers && <span className="line-number">{lineNumber}</span>}
        <span className="line-content">&nbsp;</span>
      </div>
    );
  }

  return (
    <div
      className={`diff-line ${line.type}`}
      onClick={() => onClick?.({ type: line.type, content: line.content })}
    >
      {showLineNumbers && <span className="line-number">{lineNumber}</span>}
      <span className="line-content">
        {escapeHtml(line.content)}
      </span>
    </div>
  );
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
    .replace(/"/g, '"')
    .replace(/'/g, '&#039;');
}

function computeLineDiff(original: string, revised: string): DiffLine[] {
  const originalLines = original.split('\n');
  const revisedLines = revised.split('\n');

  const dp: number[][] = Array.from({ length: originalLines.length + 1 }, () =>
    Array(revisedLines.length + 1).fill(0)
  );

  for (let i = 1; i <= originalLines.length; i++) {
    for (let j = 1; j <= revisedLines.length; j++) {
      if (originalLines[i - 1] === revisedLines[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  const lines: DiffLine[] = [];
  let i = originalLines.length;
  let j = revisedLines.length;

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && originalLines[i - 1] === revisedLines[j - 1]) {
      lines.unshift({
        type: 'equal',
        content: originalLines[i - 1],
        originalIndex: i - 1,
        revisedIndex: j - 1,
      });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      lines.unshift({
        type: 'insert',
        content: revisedLines[j - 1],
        revisedIndex: j - 1,
      });
      j--;
    } else {
      lines.unshift({
        type: 'delete',
        content: originalLines[i - 1],
        originalIndex: i - 1,
      });
      i--;
    }
  }

  return lines;
}

function computeCharDiff(original: string, revised: string): DiffLine[] {
  const originalChars = [...original];
  const revisedChars = [...revised];

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

  const lines: DiffLine[] = [];
  let i = originalChars.length;
  let j = revisedChars.length;
  let currentLine = '';
  let lineType: 'equal' | 'insert' | 'delete' | null = null;
  let originalIndex = 0;
  let revisedIndex = 0;

  const flushLine = () => {
    if (currentLine) {
      lines.push({
        type: lineType!,
        content: currentLine,
        originalIndex: lineType === 'delete' ? originalIndex : lineType === 'insert' ? undefined : originalIndex - currentLine.length,
        revisedIndex: lineType === 'insert' ? revisedIndex : lineType === 'delete' ? undefined : revisedIndex - currentLine.length,
      });
      currentLine = '';
      lineType = null;
    }
  };

  let currentLine = '';

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && originalChars[i - 1] === revisedChars[j - 1]) {
      if (lineType !== 'equal') {
        flushLine();
        lineType = 'equal';
      }
      currentLine = originalChars[i - 1] + currentLine;
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      if (lineType !== 'insert') {
        flushLine();
        lineType = 'insert';
      }
      currentLine = revisedChars[j - 1] + currentLine;
      j--;
    } else {
      if (lineType !== 'delete') {
        flushLine();
        lineType = 'delete';
      }
      currentLine = originalChars[i - 1] + currentLine;
      i--;
    }
  }

  flushLine();

  return lines.reverse();
}

export { computeLineDiff, computeCharDiff };