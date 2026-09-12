/**
 * マルチメディアマーカー関連のユーティリティ
 */

export const IMAGE_MARKER_REGEX = /\[\[img:([^\]]+)\]\]/g;

/**
 * テキスト内からすべての画像マーカーを抽出する
 * @param text 対象のテキスト
 * @returns 見つかったマーカーの配列 [{ marker: "[[img:xxx]]", sceneName: "xxx", index: 0 }, ...]
 */
export function extractImageMarkers(text: string) {
  const markers: Array<{ marker: string; sceneName: string; index: number }> = [];
  let match;
  
  // regexのlastIndexをリセット
  IMAGE_MARKER_REGEX.lastIndex = 0;
  
  while ((match = IMAGE_MARKER_REGEX.exec(text)) !== null) {
    markers.push({
      marker: match[0],
      sceneName: match[1] || '',
      index: match.index,
    });
  }
  
  return markers;
}

/**
 * 指定された位置（カーソル位置など）の直近にある画像マーカーを特定する
 * @param text 対象のテキスト
 * @param position カーソル位置（文字数）
 * @returns 最も近いマーカー、またはnull
 */
export function findNearestImageMarker(text: string, position: number) {
  const markers = extractImageMarkers(text);
  if (markers.length === 0) return null;

  let nearest = null;
  let minDistance = Infinity;

  markers.forEach(marker => {
    // マーカーの開始位置と終了位置のどちらが近いか
    const markerEnd = marker.index + marker.marker.length;
    const distance = Math.min(
      Math.abs(position - marker.index),
      Math.abs(position - markerEnd)
    );

    if (distance < minDistance) {
      minDistance = distance;
      nearest = marker;
    }
  });

  return nearest;
}
