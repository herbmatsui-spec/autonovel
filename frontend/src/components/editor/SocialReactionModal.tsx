import React, { useState, useEffect, useRef } from "react";

export interface StreamComment {
  user: string;
  text: string;
  timestamp: string;
}

export interface ForumPost {
  res_num: number;
  name: string;
  body: string;
}

interface SocialReactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInsert: (text: string) => void;
  initialStreamComments?: StreamComment[];
  initialForumPosts?: ForumPost[];
  highlightText?: string;
}

export const SocialReactionModal: React.FC<SocialReactionModalProps> = ({
  isOpen,
  onClose,
  onInsert,
  initialStreamComments = [],
  initialForumPosts = [],
  highlightText = "",
}) => {
  const [activeTab, setActiveTab] = useState<"stream" | "forum">("stream");
  const [streamComments, setStreamComments] = useState<StreamComment[]>(initialStreamComments);
  const [forumPosts, setForumPosts] = useState<ForumPost[]>(initialForumPosts);
  const [editedStreamComments, setEditedStreamComments] = useState<StreamComment[]>([]);
  const [editedForumPosts, setEditedForumPosts] = useState<ForumPost[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen) {
      setStreamComments(initialStreamComments);
      setForumPosts(initialForumPosts);
      setEditedStreamComments(initialStreamComments.map(c => ({ ...c })));
      setEditedForumPosts(initialForumPosts.map(p => ({ ...p })));
    }
  }, [isOpen, initialStreamComments, initialForumPosts]);

  const formatStreamComment = (comment: StreamComment): string => {
    return `${comment.user}: ${comment.text}`;
  };

  const formatForumPost = (post: ForumPost): string => {
    return `${post.res_num}：${post.name}：${post.body}`;
  };

  const buildStreamBlock = (): string => {
    const header = "【配信コメント】";
    const body = streamComments.map(formatStreamComment).join("\n");
    return `${header}\n${body}`;
  };

  const buildForumBlock = (): string => {
    const header = "【掲示板スレッド】";
    const body = forumPosts.map(formatForumPost).join("\n");
    return `${header}\n${body}`;
  };

  const handleStreamCommentEdit = (index: number, field: "user" | "text", value: string) => {
    setEditedStreamComments(prev => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleForumPostEdit = (index: number, field: "name" | "body", value: string) => {
    setEditedForumPosts(prev => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const applyEdits = () => {
    setStreamComments(editedStreamComments);
    setForumPosts(editedForumPosts);
  };

  const insertSelected = () => {
    let text = "";
    if (activeTab === "stream") {
      text = buildStreamBlock();
    } else {
      text = buildForumBlock();
    }
    onInsert(text);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box social-reaction-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>💬 配信・掲示板演出 挿入</h3>
          <button className="modal-close-btn" onClick={onClose} aria-label="閉じる">×</button>
        </div>

        {highlightText && (
          <div className="modal-highlight" style={{ marginBottom: "16px", padding: "12px", background: "rgba(255,255,0,0.1)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
            <strong>対象ハイライト:</strong>
            <p style={{ fontSize: "0.85rem", marginTop: "4px", whiteSpace: "pre-wrap", maxHeight: "100px", overflow: "auto" }}>
              {highlightText}
            </p>
          </div>
        )}

        <div className="modal-tabs" style={{ display: "flex", borderBottom: "1px solid var(--border-color)", marginBottom: "16px" }}>
          <button
            className={`modal-tab ${activeTab === "stream" ? "active" : ""}`}
            onClick={() => setActiveTab("stream")}
          >
            📺 配信コメント ({streamComments.length})
          </button>
          <button
            className={`modal-tab ${activeTab === "forum" ? "active" : ""}`}
            onClick={() => setActiveTab("forum")}
          >
            📋 掲示板スレッド ({forumPosts.length})
          </button>
        </div>

        {activeTab === "stream" && (
          <div className="stream-comments-section">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {streamComments.length} 件のコメント
              </span>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => setEditedStreamComments([...editedStreamComments, { user: "新規ユーザー", text: "", timestamp: new Date().toISOString() }])}
              >
                + 追加
              </button>
            </div>
            <div style={{ maxHeight: "350px", overflowY: "auto" }}>
              {editedStreamComments.map((comment, index) => (
                <div key={index} className="stream-comment-row" style={{ display: "flex", gap: "8px", marginBottom: "8px", padding: "8px", background: "rgba(0,0,0,0.03)", borderRadius: "6px" }}>
                  <input
                    type="text"
                    value={comment.user}
                    onChange={(e) => handleStreamCommentEdit(index, "user", e.target.value)}
                    placeholder="ユーザー名"
                    style={{ width: "120px", fontSize: "0.85rem" }}
                  />
                  <textarea
                    value={comment.text}
                    onChange={(e) => handleStreamCommentEdit(index, "text", e.target.value)}
                    placeholder="コメント内容"
                    style={{ flex: 1, minHeight: "44px", fontSize: "0.85rem", fontFamily: "inherit" }}
                    rows={2}
                  />
                  <button
                    type="button"
                    className="btn-icon btn-danger"
                    onClick={() => setEditedStreamComments(prev => prev.filter((_, i) => i !== index))}
                    title="削除"
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "forum" && (
          <div className="forum-posts-section">
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {forumPosts.length} レス
              </span>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => setEditedForumPosts([...editedForumPosts, { res_num: editedForumPosts.length + 1, name: "名無しさん", body: "" }])}
              >
                + 追加
              </button>
            </div>
            <div style={{ maxHeight: "350px", overflowY: "auto" }}>
              {editedForumPosts.map((post, index) => (
                <div key={index} className="forum-post-row" style={{ display: "flex", flexDirection: "column", gap: "4px", marginBottom: "12px", padding: "8px", background: "rgba(0,0,0,0.03)", borderRadius: "6px" }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span style={{ fontWeight: "bold", fontSize: "0.8rem", color: "var(--text-muted)", minWidth: "40px" }}>
                      {post.res_num}
                    </span>
                    <input
                      type="text"
                      value={post.name}
                      onChange={(e) => handleForumPostEdit(index, "name", e.target.value)}
                      placeholder="名前"
                      style={{ width: "140px", fontSize: "0.85rem" }}
                    />
                    <button
                      type="button"
                      className="btn-icon btn-danger"
                      onClick={() => setEditedForumPosts(prev => prev.filter((_, i) => i !== index))}
                      title="削除"
                    >
                      🗑
                    </button>
                  </div>
                  <textarea
                    value={post.body}
                    onChange={(e) => handleForumPostEdit(index, "body", e.target.value)}
                    placeholder="レス内容"
                    style={{ fontSize: "0.85rem", fontFamily: "inherit", minHeight: "44px" }}
                    rows={2}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="modal-preview" style={{ marginTop: "16px", padding: "12px", background: "rgba(0,0,0,0.02)", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
          <strong style={{ fontSize: "0.85rem" }}>プレビュー:</strong>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem", marginTop: "8px", fontFamily: "monospace", maxHeight: "150px", overflow: "auto" }}>
            {activeTab === "stream" ? buildStreamBlock() : buildForumBlock()}
          </pre>
        </div>

        <div className="modal-footer" style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "16px" }}>
          <button type="button" className="btn-secondary" onClick={onClose}>
            キャンセル
          </button>
          <button type="button" className="btn-secondary" onClick={applyEdits}>
            編集を反映
          </button>
          <button type="button" className="btn-primary" onClick={insertSelected} disabled={(activeTab === "stream" ? streamComments.length : forumPosts.length) === 0}>
            {activeTab === "stream" ? "📺 配信コメントを挿入" : "📋 掲示板スレッドを挿入"}
          </button>
        </div>
      </div>
    </div>
  );
};