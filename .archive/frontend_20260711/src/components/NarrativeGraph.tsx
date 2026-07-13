import React, { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { NarrativeMetricTrend } from '../api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface NarrativeGraphProps {
  data: NarrativeMetricTrend[];
  onSceneClick: (epNum: number, sceneNum: number) => void;
}

export const NarrativeGraph: React.FC<NarrativeGraphProps> = ({ data, onSceneClick }) => {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['Tension', 'Emotional Satisfaction', 'Mystery Density']);
  const [periodFilter, setPeriodFilter] = useState<{ startEp: number; endEp: number }>({ startEp: 1, endEp: 999 });

  if (!data || data.length === 0) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        color: 'var(--text-muted)',
        background: 'rgba(255,255,255,0.02)',
        borderRadius: '12px',
        border: '1px dashed var(--border)'
      }}>
        データがありません。スコアリングを実行してください。
      </div>
    );
  }

  // Determine min and max episode numbers from data
  const epNumbers = data.map(d => d.ep_num);
  const minEp = Math.min(...epNumbers);
  const maxEp = Math.max(...epNumbers);

  // Initialize period filter on first load
  useEffect(() => {
    setPeriodFilter({ startEp: minEp, endEp: maxEp });
  }, [minEp, maxEp]);

  // Filter data based on period filter
  const filteredData = useMemo(() => {
    return data.filter(d => d.ep_num >= periodFilter.startEp && d.ep_num <= periodFilter.endEp);
  }, [data, periodFilter]);

  // 全データから利用可能な指標の一覧を抽出 (filtered data)
  const allMetricNames = Array.from(new Set(filteredData.flatMap(d => Object.keys(d.scores))));

  const labels = filteredData.map(d => `Ep${d.ep_num}-S${d.scene_num}`);
   
  // Target curves (ideal lines) - example: ideal tension arc (rise then fall)
  const targetDatasets: any[] = [];
  // Example ideal tension: start at 30, peak at 70 at middle, end at 50
  if (allMetricNames.includes('Tension')) {
    const tensionIdeal = filteredData.map((d, idx) => {
      const progress = idx / Math.max(filteredData.length - 1, 1);
      // Simple arc: sin curve scaled
      return 30 + 40 * Math.sin(progress * Math.PI);
    });
    targetDatasets.push({
      label: '理想テンションカーブ',
      data: tensionIdeal,
      borderColor: 'rgba(255,255,255,0.6)',
      backgroundColor: 'rgba(255,255,255,0)',
      borderDash: [5, 5],
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 0,
    });
  }
  // Example ideal emotional satisfaction: steady increase to 80
  if (allMetricNames.includes('Emotional Satisfaction')) {
    const emoIdeal = filteredData.map((d, idx) => {
      const progress = idx / Math.max(filteredData.length - 1, 1);
      return 20 + 60 * progress;
    });
    targetDatasets.push({
      label: '理想感情的充足度',
      data: emoIdeal,
      borderColor: 'rgba(255,255,255,0.6)',
      backgroundColor: 'rgba(255,255,255,0)',
      borderDash: [5, 5],
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 0,
    });
  }
  // Example ideal mystery density: steady 50
  if (allMetricNames.includes('Mystery Density')) {
    const mysteryIdeal = filteredData.map(() => 50);
    targetDatasets.push({
      label: '理想謎密度',
      data: mysteryIdeal,
      borderColor: 'rgba(255,255,255,0.6)',
      backgroundColor: 'rgba(255,255,255,0)',
      borderDash: [5, 5],
      tension: 0.3,
      pointRadius: 0,
      pointHoverRadius: 0,
    });
  }

  const datasets = selectedMetrics.map((metric, idx) => {
    const colors = [
      'rgba(99, 102, 241, 1)',   // Indigo
      'rgba(16, 185, 129, 1)',  // Emerald
      'rgba(244, 63, 94, 1)',   // Rose
      'rgba(234, 179, 8, 1)',   // Yellow
      'rgba(6, 182, 212, 1)',   // Cyan
    ];
    return {
      label: metric,
      data: filteredData.map(d => d.scores[metric] || 0),
      borderColor: colors[idx % colors.length],
      backgroundColor: colors[idx % colors.length].replace('1)', '0.2)'),
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: { color: 'var(--text-secondary)' },
        title: { display: true, text: 'Score (0-100)', color: 'var(--text-secondary)' }
      },
      x: {
        grid: { display: false },
        ticks: { color: 'var(--text-secondary)' },
      }
    },
    plugins: {
      legend: {
        labels: { color: '#fff' }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context: any) => `${context.dataset.label}: ${context.parsed.y}`,
        }
      }
    },
    onClick: (_event: any, elements: any[]) => {
      if (elements.length > 0) {
        const index = elements[0].index;
        const scene = filteredData[index];
        onSceneClick(scene.ep_num, scene.scene_num);
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {allMetricNames.map(metric => (
          <Button
            key={metric}
            variant={selectedMetrics.includes(metric) ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedMetrics(prev =>
              prev.includes(metric) ? prev.filter(m => m !== metric) : [...prev, metric]
            )}
            className="rounded-full"
          >
            {metric}
          </Button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem' }}>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>期間フィルタ: </span>
        <select
          value={periodFilter.startEp}
          onChange={(e) => setPeriodFilter(prev => ({ ...prev, startEp: parseInt(e.target.value) }))}
          style={{ padding: '0.3rem 0.5rem', fontSize: '0.8rem', borderRadius: '4px', border: '1px solid var(--border)', background: 'rgba(255,255,255,0.05)', color: '#fff' }}
        >
          {[...Array(maxEp - minEp + 1)].map((_, i) => minEp + i).map(ep => (
            <option key={ep} value={ep}>第{ep}話から</option>
          ))}
        </select>
        <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0 0.5rem' }}>〜</span>
        <select
          value={periodFilter.endEp}
          onChange={(e) => setPeriodFilter(prev => ({ ...prev, endEp: parseInt(e.target.value) }))}
          style={{ padding: '0.3rem 0.5rem', fontSize: '0.8rem', borderRadius: '4px', border: '1px solid var(--border)', background: 'rgba(255,255,255,0.05)', color: '#fff' }}
        >
          {[...Array(maxEp - minEp + 1)].map((_, i) => minEp + i).map(ep => (
            <option key={ep} value={ep}>第{ep}話まで</option>
          ))}
        </select>
      </div>
      <div style={{ flex: 1, minHeight: '400px', position: 'relative' }}>
        <Line data={{ labels, datasets: [...datasets, ...targetDatasets] }} options={options} />
      </div>
    </div>
  );
};
