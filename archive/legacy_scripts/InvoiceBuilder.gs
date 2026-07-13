// ============================================================
// InvoiceBuilder.gs — 請求書シート生成（既存Excel書式を完全再現）
// ============================================================

// ===== 請求書シートを構築（既存Excelの書式を完全再現） =====
function buildInvoiceSheet(ss, data) {
  const shName = `請求書_${data.room}_${data.name}`;

  // 既存シートは削除して再作成（データ更新対応）
  const existing = ss.getSheetByName(shName);
  if (existing) ss.deleteSheet(existing);

  const sh = ss.insertSheet(shName);
  ss.setActiveSheet(sh);

  // ===== 列幅設定（既存Excelに合わせる）=====
  setColumnWidths(sh);

  // ===== 行高さ設定 =====
  setRowHeights(sh);

  // ===== セル値・書式を書き込む =====
  writeInvoice(sh, data);

  // 印刷範囲設定
  sh.setHiddenGridlines(false);
  const range = sh.getRange('A1:N31');
  sh.setColumnGroupControlPosition(SpreadsheetApp.GroupControlTogglePosition.AFTER);

  // 印刷設定
  sh.getRange('A1:N31').activate();
}

// ===== 列幅（ポイント→ピクセル換算、Sheetsは幅をピクセルで指定） =====
function setColumnWidths(sh) {
  // Excel列幅（文字数単位）をピクセルに変換（×7.2 ≒ 概算）
  const widths = {
    1:32,  // A: 4.39
    2:30,  // B: 4.14
    3:145, // C: 19.63
    4:33,  // D: 4.54
    5:35,  // E: 4.82
    6:105, // F: 14.23
    7:104, // G: 14.11
    8:77,  // H: 10.39
    9:60,  // I (結合用)
    10:60, // J: 11.0
    11:42, // K: 5.66
    12:44, // L: 5.92
    13:106,// M: 14.39
    14:117,// N: 15.8
  };
  Object.entries(widths).forEach(([col, px]) => sh.setColumnWidth(Number(col), px));
}

// ===== 行高さ =====
function setRowHeights(sh) {
  const heights = {
    1:35, 2:21, 3:28, 4:32, 5:24,
    6:27, 7:26, 8:26, 9:26, 10:26,
    11:26, 12:26, 13:26, 14:26, 15:24,
    16:24, 17:24, 18:24, 19:24, 20:24,
    21:24, 22:24, 23:24, 24:24, 25:24,
    26:24, 27:24, 28:43, 29:29, 30:15,
    31:24
  };
  Object.entries(heights).forEach(([r, h]) => sh.setRowHeight(Number(r), h));
}

// ===== 請求書本体の書き込み =====
function writeInvoice(sh, d) {
  const thin   = SpreadsheetApp.BorderStyle.SOLID;
  const medium = SpreadsheetApp.BorderStyle.SOLID_MEDIUM;
  const BLACK  = '#000000';

  // ---- 行1：タイトル ----
  sh.getRange('A1:N1').merge()
    .setValue('御請求明細書兼領収書')
    .setFontSize(20).setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle');

  // ---- 行2：発行日 ----
  const yr  = d.year  || new Date().getFullYear();
  const mon = d.billingMonth || (d.month ? d.month.split('-')[1] : new Date().getMonth()+1);
  const day = d.billingDay  || 10;
  sh.getRange('J2').setValue(yr + '年').setFontSize(10);
  sh.getRange('K2').setValue(Number(mon)).setFontSize(10);
  sh.getRange('L2').setValue('月').setFontSize(10);
  sh.getRange('M2').setValue(day + '日').setFontSize(10);

  // ---- 行3：件名 ----
  const targetMon = d.month ? Number(d.month.split('-')[1]) : Number(mon);
  sh.getRange('C3').setValue('件名').setFontSize(12).setFontWeight('bold');
  sh.getRange('D3').setValue('：').setFontSize(12).setFontWeight('bold');
  sh.getRange('F3').setValue(targetMon).setFontSize(11);
  sh.getRange('G3').setValue('月分').setFontSize(10);
  sh.getRange('H3').setValue(Number(d.room)).setFontSize(10);
  sh.getRange('I3').setValue('号室').setFontSize(10);
  sh.getRange('J3:L3').merge().setValue(d.name).setFontSize(10);
  sh.getRange('M3').setValue('様分').setFontSize(10);

  // 行3 下線
  sh.getRange('C3:M3').setBorder(null, null, true, null, null, null, BLACK, thin);

  // ---- 行4：セクションヘッダー ----
  sh.getRange('A4:G4').merge()
    .setValue('利用料(税別）').setFontSize(14).setFontWeight('bold')
    .setVerticalAlignment('bottom');
  sh.getRange('I4:N4').merge()
    .setValue('消耗品代（税別）').setFontSize(14).setFontWeight('bold')
    .setVerticalAlignment('bottom');

  // ---- 行5：利用料テーブルヘッダー ----
  const hStyle = (range) => range
    .setFontSize(12).setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setBorder(true, true, true, true, null, null, BLACK, thin);

  sh.getRange('A5:C5').merge(); hStyle(sh.getRange('A5:C5')).setValue('内容');
  hStyle(sh.getRange('D5')).setValue('数量');
  hStyle(sh.getRange('E5')).setValue('単位');
  hStyle(sh.getRange('F5')).setValue('単価');
  hStyle(sh.getRange('G5')).setValue('金額');

  // 消耗品ヘッダー
  sh.getRange('I5:J5').merge(); hStyle(sh.getRange('I5:J5')).setValue('内容');
  hStyle(sh.getRange('K5')).setValue('数量');
  hStyle(sh.getRange('L5')).setValue('単位');
  hStyle(sh.getRange('M5')).setValue('単価');
  hStyle(sh.getRange('N5')).setValue('金額');

  // ---- 行6〜8：利用料（非課税固定費）----
  const feeRows = [
    { row:6, label:`${targetMon}月分の利用料（非課税）`, qty:d.riyoryoSu||1,  tanka:d.riyoryoTanka||49500 },
    { row:7, label:`${targetMon}月分の管理料`,           qty:d.kanriryoSu||1, tanka:d.kanriryoTanka||10000 },
    { row:8, label:`${targetMon}月分の共益費（非課税）`, qty:d.kyoyakuSu||1,  tanka:d.kyoyakuTanka||20000 },
  ];
  feeRows.forEach(({row, label, qty, tanka}) => {
    const r = row;
    sh.getRange(r, 1, 1, 2).merge()
      .setValue(targetMon).setFontSize(11)
      .setHorizontalAlignment('center')
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 3).setValue(label).setFontSize(8)
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 4).setValue(qty).setFontSize(11)
      .setHorizontalAlignment('right')
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 5).setValue('月').setFontSize(11)
      .setBorder(true,true,true,false,null,null,BLACK,thin);
    sh.getRange(r, 6).setValue(tanka).setFontSize(11)
      .setNumberFormat('#,##0')
      .setHorizontalAlignment('right')
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 7).setFormula(`=D${r}*F${r}`).setFontSize(11)
      .setNumberFormat('#,##0')
      .setHorizontalAlignment('right')
      .setBorder(true,true,true,true,null,null,BLACK,thin);
  });

  // 行9：小計
  sh.getRange('F9').setValue('小計').setFontSize(11)
    .setHorizontalAlignment('center')
    .setBorder(true,true,true,true,null,null,BLACK,thin);
  sh.getRange('G9').setFormula('=SUM(G6:G8)').setFontSize(11)
    .setNumberFormat('#,##0')
    .setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,thin);

  // ---- 消耗品データ（行6〜25）----
  const MAX_SUPPLY = 20;
  const supplies = d.supplies || [];
  for (let i = 0; i < MAX_SUPPLY; i++) {
    const r = 6 + i;
    const s = supplies[i];
    const iRange  = sh.getRange(r, 9, 1, 2);  // I:J結合
    iRange.merge().setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 11).setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 12).setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 13).setBorder(true,true,true,true,null,null,BLACK,thin).setNumberFormat('#,##0');
    sh.getRange(r, 14).setFormula(`=K${r}*M${r}`).setNumberFormat('#,##0')
      .setHorizontalAlignment('right')
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    if (s) {
      iRange.setValue(s.name).setFontSize(11);
      sh.getRange(r, 11).setValue(s.qty).setFontSize(11).setHorizontalAlignment('right');
      sh.getRange(r, 12).setValue(s.unit).setFontSize(11);
      sh.getRange(r, 13).setValue(s.price).setFontSize(11).setHorizontalAlignment('right');
    }
  }

  // 消耗品 小計（行26）
  sh.getRange('M26').setValue('小計').setFontSize(12)
    .setHorizontalAlignment('center')
    .setBorder(true,true,true,true,null,null,BLACK,thin);
  sh.getRange('N26').setFormula('=SUM(N6:N25)').setFontSize(11)
    .setNumberFormat('#,##0')
    .setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,thin);

  // ---- 行11：サービス料ヘッダー ----
  sh.getRange('A11:G11').merge()
    .setValue('サービス料（税別）').setFontSize(14).setFontWeight('bold')
    .setVerticalAlignment('bottom');
  // 下線
  sh.getRange('A11:G11').setBorder(null,null,true,null,null,null,BLACK,thin);

  // ---- 行12：サービス料テーブルヘッダー ----
  sh.getRange('A12:C12').merge(); hStyle(sh.getRange('A12:C12')).setValue('内容');
  hStyle(sh.getRange('D12')).setValue('数量');
  hStyle(sh.getRange('E12')).setValue('単位');
  hStyle(sh.getRange('F12')).setValue('単価');
  hStyle(sh.getRange('G12')).setValue('金額');

  // ---- サービス料データ（行13〜26）----
  const MAX_SVC = 14;
  const services = d.services || [];
  for (let i = 0; i < MAX_SVC; i++) {
    const r = 13 + i;
    const s = services[i];
    sh.getRange(r, 1, 1, 2).merge()
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 3).setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 4).setBorder(true,true,true,true,null,null,BLACK,thin).setHorizontalAlignment('right');
    sh.getRange(r, 5).setBorder(true,true,true,true,null,null,BLACK,thin);
    sh.getRange(r, 6).setBorder(true,true,true,true,null,null,BLACK,thin)
      .setNumberFormat('#,##0').setHorizontalAlignment('right');
    sh.getRange(r, 7).setFormula(`=D${r}*F${r}`).setFontSize(11)
      .setNumberFormat('#,##0').setHorizontalAlignment('right')
      .setBorder(true,true,true,true,null,null,BLACK,thin);
    if (s) {
      sh.getRange(r, 1).setValue(targetMon).setFontSize(11);
      sh.getRange(r, 3).setValue(s.name).setFontSize(11);
      sh.getRange(r, 4).setValue(s.qty).setFontSize(11);
      sh.getRange(r, 5).setValue(s.unit).setFontSize(11);
      sh.getRange(r, 6).setValue(s.price).setFontSize(11);
    }
  }

  // サービス料 小計（行27）
  sh.getRange('F27').setValue('小計').setFontSize(11)
    .setHorizontalAlignment('center')
    .setBorder(true,true,true,true,null,null,BLACK,thin);
  sh.getRange('G27').setFormula('=SUM(G13:G26)').setFontSize(11)
    .setNumberFormat('#,##0').setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,thin);

  // ---- 行28：合計ラベル ----
  sh.getRange('C28').setValue('非課税分合計').setFontSize(12).setHorizontalAlignment('center');
  sh.getRange('E28:F28').merge().setValue('課税分合計').setFontSize(12).setHorizontalAlignment('center');
  sh.getRange('H28:I28').merge().setValue('消費税合計').setFontSize(10.5).setHorizontalAlignment('center');
  sh.getRange('J28:K28').merge().setValue('総合計').setFontSize(12).setHorizontalAlignment('center');

  // ---- 行29：合計値 ----
  // 非課税：利用料(G6)+共益費(G8)
  sh.getRange('C29').setFormula('=G6+G8').setFontSize(12)
    .setNumberFormat('#,##0').setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,thin);
  sh.getRange('D29').setValue('+').setFontSize(12).setHorizontalAlignment('center');
  // 課税分：管理料(G7)+サービス小計(G27)+消耗品小計(N26)
  sh.getRange('E29:F29').merge().setFormula('=G7+G27+N26').setFontSize(12)
    .setNumberFormat('#,##0').setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,thin);
  sh.getRange('G29').setValue('+').setFontSize(12).setHorizontalAlignment('center');
  sh.getRange('H29').setFormula('=E29*0.1').setFontSize(12)
    .setNumberFormat('#,##0').setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,thin);
  sh.getRange('I29').setValue('=').setFontSize(12).setHorizontalAlignment('center');
  // 総合計（太枠）
  sh.getRange('J29:K29').merge().setFormula('=C29+E29+H29').setFontSize(12)
    .setNumberFormat('#,##0').setHorizontalAlignment('right')
    .setBorder(true,true,true,true,null,null,BLACK,medium);

  // ---- 行30：説明書き ----
  sh.getRange('C30').setValue('利用料、共益費、その他').setFontSize(10);
  sh.getRange('E30:F30').merge().setValue('サービス料など').setFontSize(10);

  // ---- 行31：注釈 ----
  sh.getRange('C31').setValue('有効期限　：　提出から１カ月').setFontSize(10);
  sh.getRange('G31').setValue('支払い条件 ： お振込み又は引き落とし').setFontSize(10);

  // ---- 印刷範囲・余白設定 ----
  sh.setHiddenGridlines(true);
}
