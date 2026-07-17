# The Novel Forge

The Novel Forge is a private, local Streamlit writing studio. Its first working vertical slice takes an author from a novel seed through an interview and editable story bible to versioned, approval-gated chapter drafting. It keeps every revision, protects locked chapters, validates model output with Pydantic, backs up its SQLite database, and never stores an API key in source code or the database.

This is deliberately not a one-click novel generator. The author reviews, edits, approves, and locks the work.

## Windows setup (no programming experience required)

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/). During installation, select **Add Python to PATH**.
2. Open PowerShell in this folder. In File Explorer, open the project folder, click the address bar, type `powershell`, and press Enter.
3. Create the private Python environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Put your OpenAI API key in the current PowerShell session (replace the sample value):

   ```powershell
   $env:OPENAI_API_KEY="your-api-key-here"
   ```

   To store it for your Windows user account instead, run the following once, then close and reopen PowerShell:

   ```powershell
   [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-api-key-here", "User")
   ```

   The key is read only from the environment. Do not put it in the database, source files, or screenshots.

5. Launch the studio:

   ```powershell
   streamlit run app.py
   ```

   Your browser should open to `http://localhost:8501`. The app is local; stop it with Ctrl+C in PowerShell.

## Produce the first manuscript chapter

1. On **Projects**, create a project and enter a seed, title, author or pen name, and optional dedication.
2. Complete **Seed Interview**, including boundaries, style habits to avoid, requested front matter (such as a preface), and requested back matter (such as an epilogue).
3. On **Story Bible**, generate a proposal, edit its entries, and refine the Voice Charter.
4. On **Outline**, create chapter cards, or go directly to **Manuscript** and open **Drop in partial chapter drafts**. Paste one or more samples headed `Chapter 1: Optional title`, `Chapter 2: Optional title`, and so on.
5. Each pasted sample is saved verbatim as an author-originated version. Select it, review the exact expansion scope and word target, then ask the machine to expand it into a separate version.
6. Compare versions, approve the chosen one, and lock the chapter. Unlocking requires explicit confirmation and never deletes the approved version.

Generation uses the Voice Charter, relevant bible and character facts, chapter outline, preceding approved chapter summary, unresolved continuity facts, writing controls, and author decisions. It does not send the entire manuscript when that concise bundle is sufficient.

## Backups

Use **Create local database backup** on the Projects page. Backups are timestamped in `data\backups`. To make a manual backup while the app is stopped:

```powershell
Copy-Item .\data\novel_forge.db .\data\backups\manual-backup.db
```

To restore, stop the app, preserve the current database under another name, then copy the chosen backup to `data\novel_forge.db`.

## Tests

```powershell
pytest
```

Tests cover schema creation, append-only chapter versions, locked-content protection, Pydantic structured-output validation, print DOCX creation, EPUB navigation/TOC creation, and export preflight findings.

## Current scope and roadmap

The working slice includes all requested data tables and UI destinations, but advanced outline generation, separate editorial pass engines, full KDP front matter and running-header controls, PDF rendering, production-grade image/font handling, and the complete KDP Studio export UI remain subsequent milestones. Basic print DOCX, ebook DOCX, EPUB, and preflight foundations live in `novel_forge/exports.py` for that next phase.

Before publication, always recheck current Amazon KDP specifications. Trim, margin, gutter, font, image, TOC, and file-validation requirements can change.

## Deploy with Streamlit Community Cloud

Netlify cannot run this application because it is a long-running Python/Streamlit server, not a static HTML site. To host it from GitHub:

1. Go to [share.streamlit.io](https://share.streamlit.io), sign in, and choose **Create app**.
2. Select repository `Richardatf/Novel-Forge`, branch `main`, and entry point `app.py`.
3. Open **Advanced settings** and add these secrets, choosing your own strong values:

   ```toml
   OPENAI_API_KEY = "your-api-key"
   NOVEL_FORGE_HOSTED = "true"
   APP_PASSWORD = "a-long-unique-studio-password"
   ```

4. Deploy. Hosted mode fails closed if `APP_PASSWORD` is missing. The password is compared securely and is never stored in SQLite or source control.

Streamlit Community Cloud's local filesystem is not durable project storage. A restart or redeploy can remove the SQLite database. Use the application's backup button frequently and download the backup, or keep real manuscripts in the local Windows installation. Do not treat the hosted copy as the only copy of a manuscript.
