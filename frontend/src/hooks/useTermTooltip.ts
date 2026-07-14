import terms from '../terms.json';

/**
 * ツールチップデータを取得するためのカスタムフック
 */
export const useTermTooltip = (termKey: keyof typeof terms) => {
  const termData = terms[termKey];
  
  return {
    term: termData?.term || '用語未定義',
    description: termData?.description || '解説がありません。',
    exists: !!termData
  };
};
