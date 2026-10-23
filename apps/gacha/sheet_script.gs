// Mice hub <-> this Google Sheet (A47-15). Lets the Prize machines page READ and
// WRITE this sheet, private or not, with no Google key on the PC.
// Copy it from Prize machines > Google Sheet > "Copy the script": that copy has
// this hub's secret in place of __MICE_SECRET__ (this file in git never does).
//
// 1. In the sheet: Extensions > Apps Script, delete what is there, paste, save.
// 2. Deploy > New deployment > type Web app; Execute as: Me;
//    Who has access: Anyone. Allow it (Advanced > Go to ... (unsafe) on your own sheet).
// 3. Copy the Web app URL into Prize machines > Google Sheet > Script address.
//
// The hub POSTs {secret, op, tab, rows, head}; op is tabs | read | write | append.
// Without the secret nothing is read or written, so the address alone is harmless.
var SECRET = '__MICE_SECRET__';

function doPost(e) {
  var body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return out({ok: false, error: 'not JSON'}); }
  if (SECRET === '__MICE_' + 'SECRET__' || body.secret !== SECRET) return out({ok: false, error: 'wrong secret: copy the script again from the hub'});
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var tab = String(body.tab || '');
  var sh = tab ? book.getSheetByName(tab) : null;
  if (body.op === 'tabs') return out({ok: true, tabs: book.getSheets().map(function (s) { return s.getName(); })});
  if (!tab) return out({ok: false, error: 'which tab'});
  if (body.op === 'read') {
    if (!sh) return out({ok: true, rows: []});
    var v = sh.getDataRange().getDisplayValues();
    return out({ok: true, rows: (v.length === 1 && v[0].join('') === '') ? [] : v});
  }
  var rows = body.rows || [];
  if (!sh) sh = book.insertSheet(tab);
  if (body.op === 'write') {
    sh.clearContents();
    if (rows.length) sh.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
    return out({ok: true});
  }
  if (body.op === 'append') {
    if (sh.getLastRow() === 0 && body.head && body.head.length) sh.appendRow(body.head);
    rows.forEach(function (r) { sh.appendRow(r); });
    return out({ok: true});
  }
  return out({ok: false, error: 'unknown op ' + body.op});
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
