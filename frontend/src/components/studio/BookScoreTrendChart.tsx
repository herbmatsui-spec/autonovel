import React, { useMemo } from 'react';

interface TrendPoint {
  chapter: number;
  score: number;
}

interface BookScoreTrendChartProps {
  data: TrendPoint[];
  width?: number;
  height?: number;
  color?: string;
}

export const BookScoreTrendChart: React.FC<BookScoreTrendChartProps> = ({
  data,
  width = 400,
  height = 200,
  color = 'rgba(59, 130, 246, 1)', // blue-500
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center w-full h-full text-gray-400 text-sm">
        データがありません
      </div>
    );
  }

  const padding = { top: 20, right: 30, bottom: 30, left: 40 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const minChapter = Math.min(...data.map(d => d.chapter));
  const maxChapter = Math.max(...data.map(d => d.chapter));
  const chapterRange = maxChapter - minChapter || 1;

  const getX = (chapter: number) => 
    padding.left + ((chapter - minChapter) / chapterRange) * chartWidth;
  
  const getY = (score: number) => 
    padding.top + chartHeight - (score / 100) * chartHeight;

  const linePoints = useMemo(() => {
    return data
      .sort((a, b) => a.chapter - b.chapter)
      .map(d => `${getX(d.chapter)},${getY(d.score)}`)
      .join(' ');
  }, [data, width, height]);

  return (
    <div className="relative" style={{ width, height }}>
      <svg width={width} height={height} className="overflow-visible">
        {/* Y-Axis Grid Lines */}
        {[0, 25, 50, 75, 100].map(level => (
          <g key={level}>
            <line 
              x1={padding.left} 
              y1={getY(level)} 
              x2={padding.left + chartWidth} 
              y2={getY(level)} 
              stroke="#e5e7eb" 
              strokeWidth="1" 
            />
            <text 
              x={padding.left - 10} 
              y={getY(level)} 
              textAnchor="end" 
              dominantBaseline="middle" 
              className="text-[10px] fill-gray-400"
            >
              {level}
            </text>
          </g>
        ))}

        {/* X-Axis Labels */}
        {data.length <= 10 || data[0]?.chapter === minChapter ? (
          data.map((d, i) => (
            <text 
              key={i} 
              x={getX(d.chapter)} 
              y={padding.top + chartHeight + 20} 
              textAnchor="middle" 
              className="text-[10px] fill-gray-500"
            >
              {`第${d.chapter}章`}
            </text>
          ))
        ) : (
          // For many chapters, just show start and end
          <>
            <text x={getX(minChapter)} y={padding.top + chartHeight + 20} textAnchor="middle" className="text-[10px] fill-gray-500">
              {`第${minChapter}章`}
            </text>
            <text x={getX(maxChapter)} y={padding.top + chartHeight + 20} textAnchor="middle" className="text-[10px] fill-gray-500">
              {`第${maxChapter}章`}
            </text>
          </>
        )}

        {/* Trend Line */}
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          points={linePoints}
        />

        {/* Data Points */}
        {data.map((d, i) => (
          <circle
            key={i}
            cx={getX(d.chapter)}
            cy={getY(d.score)}
            r="3"
            fill={color}
            stroke="white"
            strokeWidth="1"
          />
        ))}
      </svg>
    </div>
  );
};
