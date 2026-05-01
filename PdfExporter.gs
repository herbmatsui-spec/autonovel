// ============================================================
// PdfExporter.gs — PDF出力（シート単体をA4 PDFに変換）
// ============================================================

// ===== 指定シートをPDFとしてDriveフォルダに保存 =====
function exportSheetAsPdf(ss, sheet, folder) {
  const ssId    = ss.getId();
  const sheetId = sheet.getSheetId();

  // Google Sheets の PDF エクスポートURL
  // 参考: https://developers.google.com/sheets/api/guides/export
  const url = [
    `https://docs.google.com/spreadsheets/d/${ssId}/export`,
    `?format=pdf`,
    `&size=A4`,          // A4サイズ
    `&portrait=true`,    // 縦向き
    `&fitw=true`,        // 幅に合わせて縮小
    `&top_margin=0.50`,  // 上余白（インチ）
    `&bottom_margin=0.50`,
    `&left_margin=0.50`,
    `&right_margin=0.50`,
    `&sheetnames=false`, // シート名を印刷しない
    `&printtitle=false`, // スプレッドシート名を印刷しない
    `&pagenumbers=false`,// ページ番号なし
    `&gridlines=false`,  // グリッド線なし
    `&fzr=false`,        // 固定行なし
    `&gid=${sheetId}`,   // 対象シートのみ
  ].join('');

  const token   = ScriptApp.getOAuthToken();
  const options = {
    headers: { 'Authorization': 'Bearer ' + token },
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  if (response.getResponseCode() !== 200) {
    Logger.log('PDF出力失敗: ' + sheet.getName() + ' / ' + response.getResponseCode());
    return null;
  }

  // ファイル名: 部屋番号_氏名_YYYY年M月.pdf
  const shName  = sheet.getName(); // 例: 請求書_207_中川ツヤ子
  const parts   = shName.replace('請求書_', '').split('_');
  const room    = parts[0] || '';
  const name    = parts.slice(1).join('_') || '';
  const now     = new Date();
  const yyyymm  = Utilities.formatDate(now, 'Asia/Tokyo', 'yyyy年M月');
  const fileName = `${room}_${name}_${yyyymm}.pdf`;

  const blob = response.getBlob().setName(fileName);
  const file = folder.createFile(blob);
  Logger.log('PDF生成: ' + fileName + ' → ' + file.getUrl());
  return file;
}

// ===== 単体PDF生成（メニューから選択行のみ実行） =====
function exportActivePDF() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sh    = ss.getActiveSheet();
  if (!sh.getName().startsWith('請求書_')) {
    ui('エラー', '請求書シートを選択してから実行してください');
    return;
  }
  const folder = getOrCreateFolder('請求書PDF_' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMM'));
  const file   = exportSheetAsPdf(ss, sh, folder);
  if (file) {
    ui('完了', 'PDFを生成しました。\n\nURL: ' + file.getUrl());
  } else {
    ui('エラー', 'PDF生成に失敗しました。ログを確認してください。');
  }
}
