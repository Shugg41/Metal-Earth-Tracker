const SECRET = "";  // optional: set a password, then put the same value in GSHEET_SECRET

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (SECRET && body.secret !== SECRET) {
      return ContentService
        .createTextOutput(JSON.stringify({status: "error", message: "bad secret"}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const tabs = body.tabs || {};
    Object.keys(tabs).forEach(function (name) {
      let sheet = ss.getSheetByName(name);
      if (!sheet) sheet = ss.insertSheet(name);
      sheet.clearContents();
      const cols = tabs[name].columns || [];
      const rows = tabs[name].rows || [];
      const data = [cols].concat(rows);
      if (cols.length) {
        sheet.getRange(1, 1, data.length, cols.length).setValues(data);
      }
    });
    return ContentService
      .createTextOutput(JSON.stringify({status: "ok"}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({status: "error", message: String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
