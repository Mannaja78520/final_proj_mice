// SAMPLE: a Google Form that fills the prize rules (A47-10, user 2026-10-22:
// "a sample of the data so a form can be made later").
//
// 1. In the rules sheet (tabs "items" and "people", docs/gacha/*.sample.csv):
//    Extensions > Apps Script, paste this file beside apps_script.gs, save.
// 2. Run makePeopleForm() once and allow it. It makes the form, links its
//    answers to this sheet and prints the form's link in the log.
// 3. Triggers (clock icon) > Add trigger: copyAnswer, From spreadsheet,
//    On form submit. Each answer is then added as one row of the "people" tab,
//    with the same column names the hub reads (Prize machines > Rules >
//    Take them from the sheet).
// The questions are the "people" columns; a new column is one more entry in COLS.
var COLS = [
  {col: 'event',   title: 'Event (empty = every event)', kind: 'text'},
  {col: 'person',  title: 'Name, as the face app knows it', kind: 'text', required: true},
  {col: 'item',    title: 'Kind of prize (* = any)', kind: 'text', required: true},
  {col: 'times',   title: 'How many times (0 = no limit)', kind: 'text'},
  {col: 'special', title: 'Special guest?', kind: 'choice', choices: ['yes', 'no']},
  {col: 'note',    title: 'Note', kind: 'text'}
];

function makePeopleForm() {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var form = FormApp.create('Prize rules: people');
  COLS.forEach(function (c) {
    var q = c.kind === 'choice' ? form.addMultipleChoiceItem().setChoiceValues(c.choices)
                                : form.addTextItem();
    q.setTitle(c.title).setRequired(!!c.required);
  });
  form.setDestination(FormApp.DestinationType.SPREADSHEET, book.getId());
  Logger.log('Form: ' + form.getPublishedUrl());
}

function copyAnswer(e) {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var sh = book.getSheetByName('people') || book.insertSheet('people');
  if (sh.getLastRow() === 0) sh.appendRow(COLS.map(function (c) { return c.col; }));
  var head = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  var got = {};
  COLS.forEach(function (c) { got[c.col] = ((e.namedValues[c.title] || [''])[0] || '').trim(); });
  sh.appendRow(head.map(function (h) { return got[h] === undefined ? '' : got[h]; }));
}
