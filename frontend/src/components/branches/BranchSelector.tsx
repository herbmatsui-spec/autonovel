import React from 'react';
import { useBranchTree } from '@/hooks/useBranchTree';
import { useSearchParams } from 'react-router-dom';
import { BranchTreeNode } from '@/types/branches';

export const BranchSelector: React.FC<{ bookId: number }> = ({ bookId }) => {
  const { data, isLoading, isError } = useBranchTree(bookId);
  const [searchParams, setSearchParams] = useSearchParams();
  const currentBranchId = searchParams.get('branch') ? parseInt(searchParams.get('branch')!) : null;

  if (isLoading) return <div>Loading branches...</div>;
  if (isError) return <div>Error loading branches</div>;

  if (!data || !data.nodes) return <div>No branches available</div>;

  const handleBranchChange = (branchId: number) => {
    setSearchParams({ branch: branchId.toString() }, { replace: true });
  };

  return (
    <div style={{ padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px', marginBottom: '16px' }}>
      <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
        現在の分岐:
      </div>
      <select
        onChange={(e) => handleBranchChange(parseInt(e.target.value))}
        value={currentBranchId ?? ''}
        style={{
          padding: '8px',
          borderRadius: '4px',
          border: '1px solid #ddd',
          minWidth: '200px'
        }}
      >
        <option value="">-- 分岐を選択 --</option>
        {data.nodes.map(node => (
          <option key={node.id} value={node.id}>
            {node.data.label} 
            {node.id === currentBranchId && ' (現在)'} 
          </option>
        ))}
      </select>
    </div>
  );
};
