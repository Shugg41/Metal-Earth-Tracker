# Live Google Sheets sync

Mirror your collection into a Google Sheet you own. On every save, the app
pushes a full snapshot to your sheet — **Models**, **Build Logs**, and
**Photos** each land on their own tab.

This uses a Google Apps Script "web app" as the receiver, so there is **no
Google Cloud project, no API to enable, and no JSON key file** — just a URL you
paste into your app secrets.

## One-time setup (~5 minutes)

1. Create (or open) the Google Sheet you want to mirror into.
2. In that sheet: **Extensions → Apps Script**. Delete the placeholder code and
   paste in [`apps_script.gs`](./apps_script.gs).
   *(Optional: set `SECRET` to any password to lock down your webhook.)*
3. **Deploy → New deployment** → gear icon → **Web app**.
   Set **Execute as: Me** and **Who has access: Anyone**, then **Deploy**.
   Approve the prompt (click *Advanced → Go to … (unsafe)* — it's your own script).
4. Copy the **Web app URL** (`https://script.google.com/macros/s/…/exec`).
5. Add it to your app secrets — `.streamlit/secrets.toml` locally, or
   *Manage app → Secrets* on Streamlit Cloud:

   ```toml
   GSHEET_WEBHOOK_URL = "https://script.google.com/macros/s/XXXX/exec"
   # GSHEET_SECRET = "the-same-password-as-SECRET"   # only if you set one
   ```

6. Reload the app, open the **📤 Export** page, and click **Sync now**. Every
   save after that updates the sheet automatically.

## Notes

- Sync is **best-effort**: if the webhook is unreachable, your save still
  succeeds (and is still backed up to GitHub) — you just get a warning toast.
- The script **replaces** each tab's contents on every sync, so the sheet is
  always a clean mirror with no duplicate rows. Treat the sheet as read-only;
  edits there are overwritten on the next sync (this is a one-way mirror).
- The webhook URL is effectively a write password. Setting `SECRET` adds a
  second check so a leaked URL alone can't write to your sheet.
