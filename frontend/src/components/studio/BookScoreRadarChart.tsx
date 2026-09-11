import React, { useMemo } from 'react';

interface RadarData {
  structure: number;
  coherency: number;
  factual: number;
  visual: number;
  reader: number;
}

interface BookScoreRadarChartProps {
  scores: RadarData;
  previousScores?: RadarData | undefined;
  benchmark?: RadarData | undefined;
  size?: number | undefined;
  color?: string | undefined;
  previousColor?: string | undefined;
  benchmarkColor?: string | undefined;
}

const DIMENSIONS = [
  { key: 'structure', label: '構造' },
  { key: 'coherency', label: '一貫性' },
  { key: 'factual', label: '事実正確性' },
  { key: 'visual', label: '視覚的相乗効果' },
  { key: 'reader', label: '読者体験' },
] as const;

export const BookScoreRadarChart: React.FC<BookScoreRadarChartProps> = ({
  scores,
  previousScores,
  benchmark,
  size = 300,
  color = 'rgba(59, 130, 246, 0.5)', // blue-500
  previousColor = 'rgba(245, 158, 11, 0.4)', // amber-500
  benchmarkColor = 'rgba(156, 163, 175, 0.3)', // gray-400
}) => {
  const centerX = size / 2;
  const centerY = size / 2;
  const radius = size * 0.4;

  const getPoint = (index: number, value: number) => {
    const angle = (Math.PI * 2 * index) / DIMENSIONS.length - Math.PI / 2;
    const r = (value / 100) * radius;
    return {
      x: centerX + r * Math.cos(angle),
      y: centerY + r * Math.sin(angle),
    };
  };

  const points = useMemo(() => {
    return DIMENSIONS.map((dim, i) => getPoint(i, scores[dim.key as keyof RadarData]));
  }, [scores, size]);

  const previousPoints = useMemo(() => {
    if (!previousScores) return null;
    return DIMENSIONS.map((dim, i) => getPoint(i, previousScores[dim.key as keyof RadarData]));
  }, [previousScores, size]);

  const benchmarkPoints = useMemo(() => {
    if (!benchmark) return null;
    return DIMENSIONS.map((dim, i) => getPoint(i, benchmark[dim.key as keyof RadarData]));
  }, [benchmark, size]);

  const polygonPoints = points.map(p => `${p.x},${p.y}`).join(' ');
  const previousPolygonPoints = previousPoints ? previousPoints.map(p => `${p.x},${p.y}`).join(' ') : '';
  const benchmarkPolygonPoints = benchmarkPoints ? benchmarkPoints.map(p => `${p.x},${p.y}`).join(' ') : '';

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="overflow-visible">
        {/* Background Grids (Concentric Polygons) */}
        {[20, 40, 60, 80].map((level) => (
          <polygon
            key={level}
            points={DIMENSIONS.map((_, i) => {
              const p = getPoint(i, level);
              return `${p.x},${p.y}`;
            }).join(' ')}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="1"
          />
        ))}

        {/* Axis Lines */}
        {DIMENSIONS.map((_, i) => {
          const p = getPoint(i, 100);
          return (
            <line
              key={i}
              x1={centerX}
              y1={centerY}
              x2={p.x}
              y2={p.y}
              stroke="#d1d5db"
              strokeWidth="1"
            />
          );
        })}

        {/* Benchmark Area */}
        {benchmark && (
          <polygon
            points={benchmarkPolygonPoints}
            fill={benchmarkColor}
            stroke={benchmarkColor.replace('0.3', '0.6')}
            strokeWidth="2"
          />
        )}

        {/* Previous Score Area */}
        {previousScores && (
          <polygon
            points={previousPolygonPoints}
            fill={previousColor}
            stroke={previousColor.replace('0.4', '0.8')}
            strokeWidth="2"
          />
        )}

        {/* Current Score Area */}
        <polygon
          points={polygonPoints}
          fill={color}
          stroke={color.replace('0.5', '1')}
          strokeWidth="2"
        />

        {/* Dimension Labels */}
        {DIMENSIONS.map((dim, i) => {
          const p = getPoint(i, 110); // Slightly outside the 100% radius
          return (
            <text
              key={dim.key}
              x={p.x}
              y={p.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="text-[10px] fill-gray-500 font-medium"
            >
              {dim.label}
            </text>
          );
        })}
      </svg>
    </div>
  );
};
