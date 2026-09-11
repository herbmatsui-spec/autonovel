/** ブランチ関連の共通定数とユーティリティ */
import { BranchType, BranchTreeNode, BranchTreeEdge } from '../types/branches';

/** ブランチのステースタイプ */
export const BRANCH_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  MERGED: 'merged',
  ARCHIVED: 'archived'
} as const;

export type BranchStatus = typeof BRANCH_STATUS[keyof typeof BRANCH_STATUS];

/** ブランチツリーのレイアウトオプション */
export const TREE_LAYOUT_OPTIONS = {
  direction: 'TB' as const, // Top to Bottom
  getNodeWidth: () => 180,
  getNodeHeight: () => 60,
  padding: 20
} as const;

/** 差分ビューアの表示モード */
export const DIFF_VIEW_MODE = {
  UNIFIED: 'unified',
  SIDE_BY_SIDE: 'side-by-side',
  INLINE: 'inline'
} as const;

export type DiffViewMode = typeof DIFF_VIEW_MODE[keyof typeof DIFF_VIEW_MODE];

/** マージコンフリクトの解決アクション */
export const CONFLICT_ACTION = {
  ACCEPT_BASE: 'accept-base',
  ACCEPT_SOURCE: 'accept-source',
  ACCEPT_TARGET: 'accept-target',
  ACCEPT_MANUAL: 'accept-manual'
} as const;

export type ConflictAction = typeof CONFLICT_ACTION[keyof typeof CONFLICT_ACTION];

/**
 * ISO日付文字列をDateオブジェクトに変換（無効な場合はnullを返す）
 */
export function parseISODate(dateString: string | null): Date | null {
  if (!dateString) return null;
  const date = new Date(dateString);
  return isNaN(date.getTime()) ? null : date;
}

/**
 * ブランチ名の表示用にトリム（長い名前は省略）
 */
export function formatBranchName(name: string, maxLength: number = 20): string {
  if (name.length <= maxLength) return name;
  return name.slice(0, maxLength - 3) + '...';
}

/**
 * ブランチツリーから特定のブランチを見つける
 */
export function findBranchById(nodes: BranchTreeNode[], branchId: number): BranchTreeNode | undefined {
  return nodes.find(node => node.id === branchId);
}

/**
 * ブランチツリーからルートブランチ（親がないブランチ）を見つける
 */
export function findRootBranches(nodes: BranchTreeNode[]): BranchTreeNode[] {
  return nodes.filter(node => node.data.parentId === null);
}

/**
 * 指定ブランチの子ブランチを取得
 * @note parent_idがnullの場合は空配列を返す（ルートブランチの子は取得しない）
 */
export function getChildBranches(nodes: BranchTreeNode[], parentId: number | null): BranchTreeNode[] {
  if (parentId === null) return [];
  return nodes.filter(node => node.data.parentId === parentId);
}

/**
 * ブランチのフルパス（ルートから現在まで）を取得
 */
export function getBranchPath(nodes: BranchTreeNode[], branchId: number): BranchTreeNode[] {
  const path: BranchTreeNode[] = [];
  let currentId: number | null = branchId;
  
  while (currentId !== null) {
    const node = findBranchById(nodes, currentId);
    if (!node) break;
    if (node.data.parentId !== null) { // 自分自身は除く
      path.unshift(node);
    }
    currentId = node.data.parentId;
  }
  
  return path;
}

/**
 * 指定ブランチの祖先ブランチを取得（ルートを含む、自分自身は含まない）
 */
export function getAncestorBranches(nodes: BranchTreeNode[], branchId: number): BranchTreeNode[] {
  const ancestors: BranchTreeNode[] = [];
  let currentId: number | null = branchId;
  
  while (currentId !== null) {
    const node = findBranchById(nodes, currentId);
    if (!node) break;
    if (node.data.parentId !== null) { // 自分自身は除く
      ancestors.unshift(node);
    }
    currentId = node.data.parentId;
  }
  
  return ancestors;
}

/** ブランチタイプのラベルマッピング（表示用） */
export const BRANCH_TYPE_LABELS: Record<BranchType, string> = {
  [BranchType.ROYAL]: '王道ルート',
  [BranchType.TWIST]: 'ツイストルート',
  [BranchType.PSYCHOLOGY]: '心理ルート'
};

/**
 * ブランチタイプの説明文を取得
 */
export function getBranchTypeDescription(type: BranchType): string {
  const descriptions: Record<BranchType, string> = {
    [BranchType.ROYAL]: '王道・カタルシス・主人公の活躍を重視したストーリー',
    [BranchType.TWIST]: 'サスペンス・急展開・どんでん返しを重視したストーリー',
    [BranchType.PSYCHOLOGY]: '日常・心情深化・キャラクターの掛け合いを重視したストーリー'
  };
  return descriptions[type] || '';
}

/**
 * トレイレイアウトアルゴリズム（簡易実装）
 * ノードに x, y 座標を計算して設定する
 */
export function computeTreeLayout(nodes: BranchTreeNode[], edges: BranchTreeEdge[]): BranchTreeNode[] {
  // ノードIDからノードオブジェクトへのマップを作成
  const nodeMap = new Map<number, BranchTreeNode>();
  nodes.forEach(node => {
    nodeMap.set(node.id, { ...node }); // コピーを作成
  });
  
  // 入次数（親の数）を計算
  const inDegree = new Map<number, number>();
  nodes.forEach(node => inDegree.set(node.id, 0));
  
  edges.forEach(edge => {
    inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
  });
  
  // ルートノード（入次数が0）を見つける
  const rootNodes = nodes.filter(node => node.data.parentId === null);
  
  // レベルごとのノードを格納
  const levels: BranchTreeNode[][] = [];
  
  // BFSでレベルごとにノードを処理
  const queue: { node: BranchTreeNode; level: number }[] = [];
  rootNodes.forEach(node => queue.push({ node, level: 0 }));
  
  while (queue.length > 0) {
    const { node, level } = queue.shift()!;
    
    // レベルが存在しない場合は追加
    if (!levels[level]) {
      levels[level] = [];
    }
    levels[level].push(node);
    
    // 子ノードをキューに追加
    const childrenIds = edges
      .filter(edge => edge.source === node.id)
      .map(edge => edge.target);
    
    childrenIds.forEach(childId => {
      const childNode = nodeMap.get(childId);
      if (childNode) {
        queue.push({ node: childNode, level: level + 1 });
      }
    });
  }
  
  // 各レベルのノードに座標を設定
  const levelWidth = 300; // レベル間の水平距離
  const nodeHeight = 100; // ノードの高さ
  
  levels.forEach((levelNodes, levelIndex) => {
    const y = levelIndex * (nodeHeight + 50) + 100; // 上からのオフセット
    
    // 同じレベル内のノードを水平に配置
    if (levelNodes.length === 1) {
      // 単一ノードの場合は中央に配置
      const singleNode = levelNodes[0];
      if (singleNode) {
        singleNode.position = { x: 400, y }; // 中央基準点
      }
    } else {
      // 複数ノードの場合は均等に配置
      const totalWidth = (levelNodes.length - 1) * levelWidth;
      const startX = 400 - totalWidth / 2; // 中央基準から左にオフセット
      
      levelNodes.forEach((node, index) => {
        node.position = { x: startX + index * levelWidth, y };
      });
    }
  });
  
  // マップから更新されたノードを取り出して返す
  return Array.from(nodeMap.values());
}
