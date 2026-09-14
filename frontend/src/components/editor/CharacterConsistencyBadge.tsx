import React from 'react';

interface Props {
  consistency: number;
  issueCount: number;
  onClick: () => void;
}

export const CharacterConsistencyBadge: React.FC<Props> = ({ consistency, issueCount, onClick }) => {
  const color = consistency > 95 ? 'bg-green-500' : 'bg-yellow-500';

  return (
    <div 
      onClick={onClick}
      className={`cursor-pointer px-3 py-1 rounded text-white ${color} flex items-center gap-2`}
    >
      <span>🗣️</span>
      <span>キャラ口調一致度: {consistency}%</span>
      {issueCount > 0 && <span className="text-xs bg-white text-black px-1 rounded">{issueCount}件の修正候補</span>}
    </div>
  );
};
