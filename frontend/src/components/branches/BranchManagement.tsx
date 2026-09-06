import React from 'react';
import { BranchTree } from './BranchTree';
import { BranchSelector } from './BranchSelector';
import { ChapterDiffViewer } from './ChapterDiffViewer';
import { MergeConflictPreview } from './MergeConflictPreview';
import { useBranchTree } from '@/hooks/useBranchTree';
import { useChapterDiff } from '@/hooks/useChapterDiff';
import { useMergePreview } from '@/hooks/useMergePreview';
import { BranchMergeRequest, MergePreviewResponse, ChapterDiffResponse } from '@/types/branches';

export const BranchManagement: React.FC<{ bookId: number }> = ({ bookId }) => {
  const { data: treeData, isLoading: treeLoading, isError: treeError } = useBranchTree(bookId);
  const [selectedBranchId, setSelectedBranchId] = React.useState<number | null>(null);
  const [compareBranchId, setCompareBranchId] = React.useState<number | null>(null);
  const [currentChapter, setCurrentChapter] = React.useState<number>(1);
  const [showDiffViewer, setShowDiffViewer] = React.useState(false);
  const [showMergePreview, setShowMergePreview] = React.useState(false);
  const [diffData, setDiffData] = React.useState<ChapterDiffResponse | null>(null);
  const [mergePreviewData, setMergePreviewData] = React.useState<MergePreviewResponse | null>(null);
  
  const { data: chapterDiffData, isLoading: diffLoading, isError: diffError } = useChapterDiff(
    bookId, 
    selectedBranchId || 1, 
    compareBranchId || 2, 
    currentChapter
  );
  
  const mergePreviewMutation = useMergePreview();
  
  const handleSelectBranch = (branchId: number) => {
    setSelectedBranchId(branchId);
  };
  
  const handleCompareBranch = (branchId: number) => {
    setCompareBranchId(branchId);
  };
  
  const handleChapterChange = (chapter: number) => {
    setCurrentChapter(chapter);
  };
  
  const handleShowDiff = () => {
    setShowDiffViewer(true);
  };
  
  const handleHideDiff = () => {
    setShowDiffViewer(false);
    setDiffData(null);
  };
  
  const handleShowMergePreview = () => {
    if (selectedBranchId && compareBranchId) {
      setShowMergePreview(true);
      const mergeRequest: BranchMergeRequest = {
        source_branch_id: selectedBranchId,
        target_branch_id: compareBranchId,
        merge_ep_num: currentChapter
      };
      mergePreviewMutation.mutate(mergeRequest);
    }
  };
  
  const handleHideMergePreview = () => {
    setShowMergePreview(false);
    setMergePreviewData(null);
  };
  
  const handleExecuteMerge = () => {
    // In a real implementation, this would call the actual merge endpoint
    alert('マージが実行されました！（実際の実装ではAPIを呼び出します）');
    setShowMergePreview(false);
    // Optionally refresh the tree data
  };
  
  React.useEffect(() => {
    if (chapterDiffData) {
      setDiffData(chapterDiffData);
    }
  }, [chapterDiffData]);
  
  React.useEffect(() => {
    if (mergePreviewMutation.data) {
      setMergePreviewData(mergePreviewMutation.data);
    }
  }, [mergePreviewMutation.data]);
  
  if (treeLoading) return <div>Loading branch management...</div>;
  if (treeError) return <div>Error loading branch management</div>;
  
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>ブランチ管理</h1>
      
      {/* Branch Selector */}
      <BranchSelector bookId={bookId} />
      
      {/* Main Content */}
      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Branch Tree Visualization */}
        <div style={{ flex: 2, minWidth: '300px' }}>
          <h2>ブランチツリー</h2>
          <BranchTree bookId={bookId} />
          <div style={{ marginTop: '16px', padding: '12px', backgroundColor: '#f8f9fa', borderRadius: '4px' }}>
            <button
              onClick={() => {
                if (selectedBranchId !== null) {
                  setCompareBranchId(selectedBranchId);
                } else if (treeData?.nodes?.[0]) {
                  setCompareBranchId(treeData.nodes[0].id);
                }
              }}
              style={{
                padding: '8px 16px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              比較対象として選択
            </button>
          </div>
        </div>
        
        {/* Controls and Preview */}
        <div style={{ flex: 1, minWidth: '250px' }}>
          <h2>操作パネル</h2>
          
          {/* Branch Selection Controls */}
          <div style={{ marginBottom: '16px' }}>
            <h3>ブランチ選択</h3>
            <div style={{ marginBottom: '8px' }}>
              <label>基準ブランチ: </label>
              <select
                value={selectedBranchId ?? ''}
                onChange={(e) => {
                  const id = parseInt(e.target.value);
                  if (!isNaN(id)) setSelectedBranchId(id);
                }}
                style={{ padding: '4px', borderRadius: '4px' }}
              >
                <option value="">-- 選択してください --</option>
                {treeData?.nodes?.map(node => (
                  <option key={node.id} value={node.id}>
                    {node.data.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>比較ブランチ: </label>
              <select
                value={compareBranchId ?? ''}
                onChange={(e) => {
                  const id = parseInt(e.target.value);
                  if (!isNaN(id)) setCompareBranchId(id);
                }}
                style={{ padding: '4px', borderRadius: '4px' }}
              >
                <option value="">-- 選択してください --</option>
                {treeData?.nodes?.map(node => (
                  <option key={node.id} value={node.id}>
                    {node.data.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          {/* Chapter Selection */}
          <div style={{ marginBottom: '16px' }}>
            <h3>章選択</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label>章番号: </label>
              <input
                type="number"
                value={currentChapter}
                onChange={(e) => {
                  const num = parseInt(e.target.value);
                  if (!isNaN(num) && num > 0) setCurrentChapter(num);
                }}
                style={{ width: '80px', padding: '4px' }}
                min="1"
              />
              <button
                onClick={handleShowDiff}
                style={{
                  padding: '6px 12px',
                  backgroundColor: '#28a745',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                差分表示
              </button>
              <button
                onClick={handleShowMergePreview}
                disabled={!(selectedBranchId && compareBranchId)}
                style={{
                  padding: '6px 12px',
                  backgroundColor: selectedBranchId && compareBranchId ? '#ffc107' : '#6c757d',
                  color: selectedBranchId && compareBranchId ? '#212529' : 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: selectedBranchId && compareBranchId ? 'pointer' : 'not-allowed'
                }}
              >
                マージプレビュー
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Diff Viewer Modal */}
      {showDiffViewer && (
        <ChapterDiffViewer
          chapterNumber={currentChapter}
          branchAId={selectedBranchId || 1}
          branchBId={compareBranchId || 2}
          onClose={handleHideDiff}
        />
      )}
      
      {/* Merge Preview Modal */}
      {showMergePreview && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 4px 20px rgba(0,0,0,0.2)', maxWidth: '90vw', maxHeight: '90vh', overflow: 'auto' }}>
            <MergeConflictPreview
              previewData={mergePreviewData}
              onResolveConflict={(chunkId, action, manualContent) => {
                // In a real implementation, this would update local state
                console.log(`Resolving conflict ${chunkId} with action ${action}`, manualContent);
              }}
              onExecuteMerge={handleExecuteMerge}
            />
          </div>
        </div>
      )}
    </div>
  );
};
