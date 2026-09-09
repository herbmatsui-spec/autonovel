import React, { useState } from "react";
import { GraphNodeDetail } from "../../types/graphInspector";
import { GraphEdge } from "../../types/graph";
import { upsertEdge } from "../../api/graph";
import { upsertNode } from "../../api/graph";
import { useToast } from "../../hooks/useToast";

const labelOptions = [
  { value: "Character", label: "Character", color: "#4fc3f7" }, // light blue
  { value: "Location", label: "Location", color: "#81c784" }, // light green
  { value: "Item", label: "Item", color: "#ffb74d" }, // orange
  { value: "Faction", label: "Faction", color: "#ba68c8" }, // purple
  { value: "Event", label: "Event", color: "#e57373" }, // red
  { value: "Concept", label: "Concept", color: "#90a4ae" }, // grey
];

const edgeTypeOptions = [
  { value: "FRIEND_OF", label: "Friend of" },
  { value: "ENEMY_OF", label: "Enemy of" },
  { value: "BELONGS_TO", label: "Belongs to" },
  { value: "OWNS", label: "Owns" },
  { value: "KNOWS", label: "Knows" },
  { value: "PART_OF", label: "Part of" },
];

interface NodeInspectorProps {
  node: GraphNodeDetail | null;
  edges: GraphEdge[];
  nodes: GraphNodeDetail[];
  onClose: () => void;
  onUpdate: (node: GraphNodeDetail) => void;
  onAddEdge: (edge: GraphEdge) => void;
}

export const NodeInspector: React.FC<NodeInspectorProps> = ({
  node,
  edges,
  nodes,
  onClose,
  onUpdate,
  onAddEdge,
}) => {
  if (!node) {
    return null;
  }

  const [localLabel, setLocalLabel] = useState(node.label);
  const [localProperties, setLocalProperties] = useState<{ key: string; value: string }[]>(
    Object.entries(node.properties).map(([key, value]) => ({ key, value }))
  );

  const [showAddEdgeDialog, setShowAddEdgeDialog] = useState(false);
  const [targetNodeId, setTargetNodeId] = useState("");
  const [edgeType, setEdgeType] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const { addToast } = useToast();

  const handleLabelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLabel = e.target.value;
    setLocalLabel(newLabel);
    const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
    onUpdate({ ...node, label: newLabel, properties: propertiesRecord });
  };

  const handlePropertyChange = (index: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLocalProperties((prev) =>
      prev.map((p, i) => (i === Number(index) ? { ...p, value } : p))
    );
    const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
    onUpdate({ ...node, label: localLabel, properties: propertiesRecord });
  };

  const handleDeleteProperty = (index: string) => {
    setLocalProperties((prev) => prev.filter((_, i) => i !== Number(index)));
    const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
    onUpdate({ ...node, label: localLabel, properties: propertiesRecord });
  };

  const handleAddProperty = () => {
    setLocalProperties((prev) => [...prev, { key: "", value: "" }]);
    const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
    onUpdate({ ...node, label: localLabel, properties: propertiesRecord });
  };

  const getLabelColor = (label: string) => {
    const option = labelOptions.find((opt) => opt.value === label);
    return option ? option.color : "#90a4ae"; // default to Concept color
  };

  const handleAddEdgeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetNodeId || !edgeType) {
      addToast("Please select a target node and edge type", "error");
      return;
    }
    try {
      const newEdge: GraphEdge = {
        source: node.id,
        target: targetNodeId,
        type: edgeType,
        properties: {},
      };
      await upsertEdge(newEdge);
      onAddEdge(newEdge);
      setShowAddEdgeDialog(false);
      setTargetNodeId("");
      setEdgeType("");
      addToast("Connection added successfully", "success");
    } catch (err) {
      addToast(`Failed to add edge: ${err}`, "error");
    }
  };

  const handleSaveNode = async () => {
    setIsSaving(true);
    try {
      const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
      const nodeToSave: GraphNodeDetail = {
        id: node.id,
        label: localLabel,
        properties: propertiesRecord,
      };
      await upsertNode(nodeToSave);
      addToast(`✨ ${localLabel} の設定を更新しました`, "success");
    } catch (err) {
      addToast(`Failed to save node: ${err}`, "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyToClipboard = async () => {
    const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
    const lines = [
      `【設定メモ: ${localLabel}】`,
      ...Object.entries(propertiesRecord).map(([key, value]) => `${key}: ${value}`),
    ];
    const text = lines.join("\n");
    try {
      await navigator.clipboard.writeText(text);
      addToast("設定をクリップボードにコピーしました", "success");
    } catch (err) {
      addToast("クリップボードへのコピーに失敗しました", "error");
    }
  };

  return (
    <div className="node-inspector">
      <div className="node-inspector-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h2>{node.label}</h2>
          <span
            style={{
              display: "inline-block",
              width: "10px",
              height: "10px",
              backgroundColor: getLabelColor(node.label),
              borderRadius: "50%",
            }}
          />
        </div>
        <select value={localLabel} onChange={handleLabelChange}>
          {labelOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleSaveNode}
          disabled={isSaving}
          style={{
            marginLeft: "12px",
            padding: "6px 12px",
            backgroundColor: isSaving ? "#cccccc" : "#4fc3f7",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: isSaving ? "not-allowed" : "pointer",
          }}
        >
          {isSaving ? "Saving..." : "💾 設定を保存"}
        </button>
        <button onClick={onClose} style={{ marginLeft: "8px" }}>
          Close
        </button>
      </div>
      <div className="node-inspector-body">
        <h3>Properties</h3>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "4px" }}>Key</th>
              <th style={{ textAlign: "left", padding: "4px" }}>Value</th>
              <th style={{ textAlign: "center", padding: "4px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {localProperties.map((prop, index) => (
              <tr key={index} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "4px" }}>
                  <input
                    type="text"
                    value={prop.key}
                    onChange={(e) => {
                      setLocalProperties((prev) =>
                        prev.map((p, i) =>
                          i === index ? { ...p, key: e.target.value } : p
                        )
                      );
                      const propertiesRecord = Object.fromEntries(localProperties.map(p => [p.key, p.value]));
                      onUpdate({ ...node, label: localLabel, properties: propertiesRecord });
                    }}
                    style={{ width: "100%", boxSizing: "border-box" }}
                  />
                </td>
                <td style={{ padding: "4px" }}>
                  <input
                    type="text"
                    value={prop.value}
                    onChange={(e) => handlePropertyChange(index.toString(), e)}
                    style={{ width: "100%", boxSizing: "border-box" }}
                  />
                </td>
                <td style={{ padding: "4px", textAlign: "center" }}>
                  <button onClick={() => handleDeleteProperty(index.toString())}>
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button onClick={handleAddProperty} style={{ marginTop: "8px" }}>
          + 属性を追加
        </button>
        
        <h3 style={{ marginTop: "24px" }}>Connections</h3>
        {edges.length === 0 ? (
          <p>No connections</p>
        ) : (
          <ul style={{ listStyle: "none", padding: 0 }}>
            {edges.map((edge, index) => {
              const isSource = edge.source === node.id;
              const targetId = isSource ? edge.target : edge.source;
              const direction = isSource ? "-->" : "<--";
              return (
                <li key={index} style={{ padding: "4px 0", borderBottom: "1px solid #eee" }}>
                  {targetId} {direction} [{edge.type}]
                </li>
              );
            })}
          </ul>
        )}
        
        <button
          onClick={handleCopyToClipboard}
          style={{ marginTop: "12px", padding: "8px 16px", backgroundColor: "#ffb74d", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
        >
          📝 本文へ設定を引用
        </button>
        
        <button
          onClick={() => setShowAddEdgeDialog(true)}
          style={{ marginTop: "16px", padding: "8px 16px", backgroundColor: "#4fc3f7", color: "white", border: "none", borderRadius: "4px", cursor: "pointer" }}
        >
          + 新しい関係を追加
        </button>
        
        {/* Add Edge Dialog */}
        {showAddEdgeDialog && (
          <div style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}>
            <div style={{
              backgroundColor: "white",
              padding: "24px",
              borderRadius: "8px",
              width: "300px",
              boxShadow: "0 4px 24px rgba(0,0,0,0.15)",
            }}>
              <h4>Add New Connection</h4>
              <form onSubmit={handleAddEdgeSubmit} style={{ marginTop: "16px" }}>
                <div style={{ marginBottom: "12px" }}>
                  <label>Target Node:</label>
                  <select
                    value={targetNodeId}
                    onChange={(e) => setTargetNodeId(e.target.value)}
                    style={{ width: "100%", padding: "8px", marginTop: "4px" }}
                  >
                    <option value="">Select a node</option>
                    {nodes
                      .filter((n) => n.id !== node.id)
                      .map((n) => (
                        <option key={n.id} value={n.id}>
                          {n.label || n.id}
                        </option>
                      ))}
                  </select>
                </div>
                <div style={{ marginBottom: "12px" }}>
                  <label>Relationship Type:</label>
                  <select
                    value={edgeType}
                    onChange={(e) => setEdgeType(e.target.value)}
                    style={{ width: "100%", padding: "8px", marginTop: "4px" }}
                  >
                    <option value="">Select a type</option>
                    {edgeTypeOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => setShowAddEdgeDialog(false)}
                    style={{ padding: "8px 16px", backgroundColor: "#f0f0f0", border: "none", borderRadius: "4px" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    style={{ padding: "8px 16px", backgroundColor: "#4fc3f7", color: "white", border: "none", borderRadius: "4px" }}
                  >
                    Add Connection
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};