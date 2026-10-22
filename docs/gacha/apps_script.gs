// Google Apps Script for the "Send them to the sheet" button (Prize machines page).
// Optional: pulling rules from the sheet needs no script, only Publish to web.
//
// 1. In the sheet: Extensions > Apps Script, paste this, save.
// 2. Deploy > New deployment > Web app; Execute as: Me; Who has access: Anyone.
// 3. Copy the web app link into Prize machines > Rules > Write-back link.
// The hub POSTs {"kind": "rules", "rules": {"items": [...], "people": [...]}}.
// Each list replaces the tab of the same name (items, people). Anyone with the
// link can overwrite those two tabs: keep the link private.
function doPost(e) {
  var body = JSON.parse(e.postData.contents);
  if (body.kind !== 'rules') return out({ok: false, error: 'unknown kind'});
  var cols = {items: ['event', 'item', 'total', 'per_person', 'note'],
              people: ['event', 'person', 'item', 'times', 'special', 'note']};
  var book = SpreadsheetApp.getActiveSpreadsheet();
  Object.keys(cols).forEach(function (tab) {
    var sh = book.getSheetByName(tab) || book.insertSheet(tab);
    var rows = [cols[tab]].concat((body.rules[tab] || []).map(function (r) {
      return cols[tab].map(function (c) { return r[c] === undefined ? '' : r[c]; });
    }));
    sh.clearContents();
    sh.getRange(1, 1, rows.length, cols[tab].length).setValues(rows);
  });
  return out({ok: true});
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
