// ============================================================
// 御請求明細書 自動生成システム — Code.gs（メイン）
// ============================================================
// 【構成】
//   Code.gs          … メインロジック・メニュー・トリガー
//   InvoiceBuilder.gs … 請求書シート生成ロジック
//   PdfExporter.gs   … PDF出力・Driveフォルダ管理
//
// 【スプレッドシート構成】
//   「フォーム回答_事業所」… Googleフォーム（事業所用）の回答シート
//   「総務入力」          … 総務が利用料・日付を入力するシート
//   「請求書_XXXX_氏名」  … 利用者ごとに自動生成されるシート
// ============================================================

// ===== シート名定数 =====
const SH_FORM   = 'フォーム回答_事業所';
const SH_OFFICE = '総務入力';

// ===== メニュー =====
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📄 請求書管理')
    .addItem('① 事業所データを請求書に反映', 'applyFormDataToInvoices')
    .addSeparator()
    .addItem('② 全員分PDF一括生成', 'exportAllPDF')
    .addSeparator()
    .addItem('【初期設定】総務入力シートを作成', 'setupOfficeSheet')
    .addToUi();
}

// ===== フォーム送信トリガー（自動実行） =====
// フォーム送信時に自動で請求書シートを作成・更新する
function onFormSubmit(e) {
  try {
    const row  = e.range.getRow();
    const ss   = SpreadsheetApp.getActiveSpreadsheet();
    const formSh = ss.getSheetByName(SH_FORM);
    processOneRow(ss, formSh, row);
  } catch(err) {
    Logger.log('onFormSubmit error: ' + err);
  }
}

// ===== ① 事業所データを全行反映（手動実行） =====
function applyFormDataToInvoices() {
  const ss     = SpreadsheetApp.getActiveSpreadsheet();
  const formSh = ss.getSheetByName(SH_FORM);
  if (!formSh) { ui('エラー', SH_FORM + ' シートが見つかりません'); return; }

  const lastRow = formSh.getLastRow();
  if (lastRow < 2) { ui('情報', 'フォーム回答がまだありません'); return; }

  let count = 0;
  for (let r = 2; r <= lastRow; r++) {
    processOneRow(ss, formSh, r);
    count++;
  }
  ui('完了', count + '名分の請求書シートを作成・更新しました');
}

// ===== 1行処理：フォーム回答→請求書シート作成 =====
function processOneRow(ss, formSh, row) {
  const headers = getHeaders(formSh);
  const vals    = formSh.getRange(row, 1, 1, formSh.getLastColumn()).getValues()[0];
  const get     = (label) => vals[headers[label]] !== undefined ? vals[headers[label]] : '';

  // 基本情報
  const facility = String(get('事業所'));
  const room     = String(get('部屋番号'));
  const name     = String(get('利用者氏名')).trim();
  const month    = String(get('対象月（YYYY-MM）')).trim(); // 例: "2026-02"

  if (!room || !name) return;

  // サービス料（最大10件）
  const services = [];
  for (let i = 1; i <= 10; i++) {
    const n = get(`サービス${i}_内容`);
    const q = get(`サービス${i}_数量`);
    const u = get(`サービス${i}_単位`);
    const p = get(`サービス${i}_単価`);
    if (n) services.push({ name: String(n), qty: Number(q)||0, unit: String(u), price: Number(p)||0 });
  }

  // 消耗品（最大15件）
  const supplies = [];
  for (let i = 1; i <= 15; i++) {
    const n = get(`消耗品${i}_品名`);
    const q = get(`消耗品${i}_数量`);
    const u = get(`消耗品${i}_単位`);
    const p = get(`消耗品${i}_単価`);
    if (n) supplies.push({ name: String(n), qty: Number(q)||0, unit: String(u), price: Number(p)||0 });
  }

  // 総務入力シートから利用料などを取得
  const officeData = getOfficeData(ss, room, name);

  // 請求書シートを構築
  buildInvoiceSheet(ss, {
    facility, room, name, month,
    services, supplies,
    ...officeData
  });
}

// ===== 総務入力シートから該当利用者の行を取得 =====
function getOfficeData(ss, room, name) {
  const sh = ss.getSheetByName(SH_OFFICE);
  if (!sh) return defaultOfficeData();

  const lastRow = sh.getLastRow();
  for (let r = 2; r <= lastRow; r++) {
    const r_room = String(sh.getRange(r, COL_OFF.ROOM).getValue()).trim();
    const r_name = String(sh.getRange(r, COL_OFF.NAME).getValue()).trim();
    if (r_room === room && r_name === name) {
      return {
        year          : sh.getRange(r, COL_OFF.YEAR).getValue()         || new Date().getFullYear(),
        billingMonth  : sh.getRange(r, COL_OFF.BILL_MON).getValue()     || '',
        billingDay    : sh.getRange(r, COL_OFF.BILL_DAY).getValue()     || 10,
        riyoryoTanka  : Number(sh.getRange(r, COL_OFF.RIYO_TANKA).getValue())  || 49500,
        riyoryoSu     : Number(sh.getRange(r, COL_OFF.RIYO_SU).getValue())     || 1,
        kanriryoTanka : Number(sh.getRange(r, COL_OFF.KANRI_TANKA).getValue()) || 10000,
        kanriryoSu    : Number(sh.getRange(r, COL_OFF.KANRI_SU).getValue())    || 1,
        kyoyakuTanka  : Number(sh.getRange(r, COL_OFF.KYOEKI_TANKA).getValue())|| 20000,
        kyoyakuSu     : Number(sh.getRange(r, COL_OFF.KYOEKI_SU).getValue())   || 1,
      };
    }
  }
  return defaultOfficeData();
}

function defaultOfficeData() {
  return {
    year:new Date().getFullYear(), billingMonth:'', billingDay:10,
    riyoryoTanka:49500, riyoryoSu:1,
    kanriryoTanka:10000, kanriryoSu:1,
    kyoyakuTanka:20000, kyoyakuSu:1,
  };
}

// ===== 総務入力シートの列定数 =====
const COL_OFF = {
  ROOM:1, NAME:2, YEAR:3, BILL_MON:4, BILL_DAY:5,
  RIYO_TANKA:6, RIYO_SU:7,
  KANRI_TANKA:8, KANRI_SU:9,
  KYOEKI_TANKA:10, KYOEKI_SU:11,
  STATUS:12
};

// ===== 【初期設定】総務入力シートを作成 =====
function setupOfficeSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SH_OFFICE);
  if (sh) { ui('情報', SH_OFFICE + ' はすでに存在します'); return; }

  sh = ss.insertSheet(SH_OFFICE);
  const headers = [
    '部屋番号','利用者氏名','請求年','請求月','請求日',
    '利用料_単価','利用料_数量',
    '管理料_単価','管理料_数量',
    '共益費_単価','共益費_数量',
    '状態'
  ];
  sh.getRange(1, 1, 1, headers.length).setValues([headers])
    .setFontWeight('bold')
    .setBackground('#d0e4f7');
  sh.setFrozenRows(1);

  // 列幅調整
  sh.setColumnWidth(1, 80);
  sh.setColumnWidth(2, 140);
  [3,4,5].forEach(c => sh.setColumnWidth(c, 80));
  [6,7,8,9,10,11].forEach(c => sh.setColumnWidth(c, 100));
  sh.setColumnWidth(12, 90);

  ui('完了', SH_OFFICE + ' シートを作成しました。\n\n'
    + '利用者の部屋番号・氏名を入力し、利用料などを設定してください。\n'
    + '（フォームからデータが届くと自動的に紐付けされます）');
}

// ===== ② 全員分PDF一括生成 =====
function exportAllPDF() {
  const ss       = SpreadsheetApp.getActiveSpreadsheet();
  const sheets   = ss.getSheets();
  const invSheets = sheets.filter(s => s.getName().startsWith('請求書_'));

  if (invSheets.length === 0) {
    ui('情報', '請求書シートがありません。\n先に「① 事業所データを請求書に反映」を実行してください');
    return;
  }

  const folder = getOrCreateFolder('請求書PDF_' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMM'));
  let count = 0;

  invSheets.forEach(sh => {
    exportSheetAsPdf(ss, sh, folder);
    count++;
    // 状態を「PDF生成済」に更新
    markAsDone(ss, sh.getName());
  });

  ui('完了', count + '件のPDFを生成しました。\nGoogleドライブの「' + folder.getName() + '」フォルダをご確認ください。\n\n'
    + 'フォルダURL:\n' + folder.getUrl());
}

// ===== Driveフォルダ取得 or 作成 =====
function getOrCreateFolder(name) {
  const it = DriveApp.getFoldersByName(name);
  return it.hasNext() ? it.next() : DriveApp.createFolder(name);
}

// ===== 総務シートの状態を更新 =====
function markAsDone(ss, sheetName) {
  const offSh = ss.getSheetByName(SH_OFFICE);
  if (!offSh) return;
  // シート名は「請求書_ROOM_NAME」形式
  const parts = sheetName.replace('請求書_','').split('_');
  if (parts.length < 2) return;
  const room = parts[0];
  const name = parts.slice(1).join('_');
  const lastRow = offSh.getLastRow();
  for (let r = 2; r <= lastRow; r++) {
    const rRoom = String(offSh.getRange(r, COL_OFF.ROOM).getValue()).trim();
    const rName = String(offSh.getRange(r, COL_OFF.NAME).getValue()).trim();
    if (rRoom === room && rName === name) {
      offSh.getRange(r, COL_OFF.STATUS).setValue('PDF生成済');
      break;
    }
  }
}

// ===== ユーティリティ =====
function getHeaders(sheet) {
  const vals = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const map  = {};
  vals.forEach((h, i) => { map[String(h).trim()] = i; });
  return map;
}

function ui(title, msg) {
  SpreadsheetApp.getUi().alert(title, msg, SpreadsheetApp.getUi().ButtonSet.OK);
}
