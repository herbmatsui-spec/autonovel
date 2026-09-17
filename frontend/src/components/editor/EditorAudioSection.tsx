import React from "react";
import { AudioPlayer } from "../common/AudioPlayer";

interface EditorAudioSectionProps {
  /** 章に紐づく朗読音声トラック（存在する場合のみ表示） */
  audioTrack: {
    stream_url: string;
    duration_seconds?: number;
  } | null;
  /** 現在の話数（タイトル表示用） */
  currentEpNum?: number;
}

/**
 * エディタ下部のインライン音声プレイヤーセクション。
 *
 * Editor.tsx から分割（提案3: 巨大コンポーネント分割）。
 */
export const EditorAudioSection: React.FC<EditorAudioSectionProps> = ({
  audioTrack,
  currentEpNum,
}) => {
  if (!audioTrack) return null;

  return (
    <div style={{ marginTop: "12px" }}>
      <AudioPlayer
        src={audioTrack.stream_url}
        title={`第${currentEpNum || 1}話 朗読音声`}
        {...(audioTrack.duration_seconds !== undefined
          ? { duration: audioTrack.duration_seconds }
          : {})}
      />
    </div>
  );
};

export default EditorAudioSection;
