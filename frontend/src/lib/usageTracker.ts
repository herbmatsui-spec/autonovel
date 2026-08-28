import { useState, useEffect } from 'react';

// Define the types of nodes in our graph
export type NodeId = 
  | `step-${string}` 
  | `tab-${string}`
  | `node-${string}`;

interface Transition {
  from: NodeId;
  to: NodeId;
  timestamp: number;
}

interface UsageStats {
  transitions: Transition[];
  nodeCounts: Record<NodeId, number>;
  transitionCounts: Record<string, number>; // from-to as key
}

// In-memory storage for usage data
// In a real app, this might be persisted to localStorage or synced with backend
let usageStats: UsageStats = {
  transitions: [],
  nodeCounts: {},
  transitionCounts: {}
};

// Load from localStorage if available
try {
  const stored = localStorage.getItem('novel-usage-stats');
  if (stored) {
    usageStats = JSON.parse(stored);
  }
} catch (e) {
  console.warn('Failed to load usage stats from localStorage', e);
}

// Save to localStorage periodically
const saveToLocalStorage = () => {
  try {
    localStorage.setItem('novel-usage-stats', JSON.stringify(usageStats));
  } catch (e) {
    console.warn('Failed to save usage stats to localStorage', e);
  }
};

// Auto-save every 30 seconds
setInterval(saveToLocalStorage, 30000);

// Also save before page unload
window.addEventListener('beforeunload', saveToLocalStorage);

/**
 * Records a transition from one node to another
 */
export function recordTransition(from: NodeId, to: NodeId) {
  const transition: Transition = {
    from,
    to,
    timestamp: Date.now()
  };
  
  usageStats.transitions.push(transition);
  
  // Update node counts
  usageStats.nodeCounts[from] = (usageStats.nodeCounts[from] || 0) + 1;
  usageStats.nodeCounts[to] = (usageStats.nodeCounts[to] || 0) + 1;
  
  // Update transition counts
  const key = `${from}-${to}`;
  usageStats.transitionCounts[key] = (usageStats.transitionCounts[key] || 0) + 1;
  
  // Keep only recent transitions (last 1000) to prevent memory growth
  if (usageStats.transitions.length > 1000) {
    usageStats.transitions = usageStats.transitions.slice(-1000);
    // Recalculate counts
    usageStats.nodeCounts = {};
    usageStats.transitionCounts = {};
    
    for (const t of usageStats.transitions) {
      usageStats.nodeCounts[t.from] = (usageStats.nodeCounts[t.from] || 0) + 1;
      usageStats.nodeCounts[t.to] = (usageStats.nodeCounts[t.to] || 0) + 1;
      const key = `${t.from}-${t.to}`;
      usageStats.transitionCounts[key] = (usageStats.transitionCounts[key] || 0) + 1;
    }
  }
}

/**
 * Gets related nodes for a given node based on usage statistics
 * @param nodeId The node to find related nodes for
 * @param limit Maximum number of related nodes to return
 * @returns Array of related nodes with scores
 */
export function getRelatedNodes(nodeId: NodeId, limit: number = 5): Array<{
  nodeId: NodeId;
  score: number;
  transitionCount: number;
}> {
  // Find all transitions where this node is the 'from'
  const outgoingTransitions = usageStats.transitions.filter(t => t.from === nodeId);
  
  // Count transitions to each 'to' node
  const toCounts: Record<NodeId, number> = {};
  for (const t of outgoingTransitions) {
    toCounts[t.to] = (toCounts[t.to] || 0) + 1;
  }
  
  // Convert to array and sort by count descending
  const related: Array<{
    nodeId: NodeId;
    score: number;
    transitionCount: number;
  }> = Object.entries(toCounts).map(([nodeIdStr, count]) => ({
    nodeId: nodeIdStr as NodeId,
    transitionCount: count,
    // Normalize score to 0-1 range based on max count
    score: 0 // Will calculate below
  }));
  
  // Calculate normalized scores
  if (related.length > 0) {
    const maxCount = Math.max(...related.map(r => r.transitionCount));
    for (const r of related) {
      r.score = r.transitionCount / maxCount;
    }
  }
  
  // Sort by score descending and limit
  return related
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/**
 * Gets the strength of association between two nodes
 * @param from Source node
 * @param to Target node
 * @returns Association strength (0-1)
 */
export function getAssociationStrength(from: NodeId, to: NodeId): number {
  const key = `${from}-${to}`;
  const totalOutgoing = usageStats.nodeCounts[from] || 1; // Avoid division by zero
  
  if (totalOutgoing === 0) return 0;
  
  // Normalize by the maximum possible transitions from this node
  const fromOutgoingCount = usageStats.transitionCounts[key] || 0;

  
  // Find max outgoing from this node
  let maxFromOutgoing = 0;
  for (const [key, count] of Object.entries(usageStats.transitionCounts)) {
    if (key.startsWith(`${from}-`)) {
      maxFromOutgoing = Math.max(maxFromOutgoing, count);
    }
  }
  
  if (maxFromOutgoing === 0) return 0;
  
  return fromOutgoingCount / maxFromOutgoing;
}

/**
 * Hook to use usage stats in components
 */
export function useUsageStats() {
  const [stats, setStats] = useState(() => usageStats);
  
  // Update stats when they change (in a real app, we'd use pub/sub or similar)
  useEffect(() => {
    const checkForUpdates = () => {
      setStats(usageStats);
    };
    
    // Poll for updates every second (in a real app, we'd use events)
    const interval = setInterval(checkForUpdates, 1000);
    return () => clearInterval(interval);
  }, []);
  
  return stats;
}

/**
 * Reset usage stats (for development/testing)
 */
export function resetUsageStats() {
  usageStats = {
    transitions: [],
    nodeCounts: {},
    transitionCounts: {}
  };
  saveToLocalStorage();
}

export type { Transition, UsageStats };