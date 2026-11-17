# Alphasuit website — step by step (no coding needed)

This is a normal website (HTML files). It is **free to host** on GitHub Pages. A free robot at GitHub runs the scanner **every night at 10 PM IST** and refreshes the results by itself.

You need: a computer or phone with a browser, and a free GitHub account. Nothing to install.

---

## PART 1 — Put the website online (about 15 minutes, one time)

**1. Make a GitHub account** at github.com (free). Verify your email.

**2. Make a new repository**
- Click the **+** (top right) → **New repository**.
- Name: `alphasuit`. Choose **Public**. Click **Create repository**.

**3. Upload the website files**
- Unzip `alphasuit-website.zip` on your computer.
- On your new repository page click **uploading an existing file**.
- Open the unzipped folder and **drag everything inside it** into the GitHub page (all the files AND the folders `assets`, `data`, `scanner`, `.github`).
  - Mac: press `Cmd + Shift + .` in the folder to show the hidden `.github` folder.
  - If GitHub will not take the `.github` folder, do step 3b below.
- Click **Commit changes**.

**3b. (only if the `.github` folder did not upload)**
- Repository → **Add file → Create new file**.
- In the name box type exactly: `.github/workflows/scan.yml`
- Open `.github/workflows/scan.yml` from the unzipped folder with Notepad, copy everything, paste it in, and click **Commit changes**.

**4. Allow the robot to publish**
- Repository → **Settings → Actions → General**.
- Scroll to **Workflow permissions**, choose **Read and write permissions**, click **Save**.

**5. Run the first scan now**
- Repository → **Actions** tab → click **Nightly scan and publish** on the left → **Run workflow** (green button) → **Run workflow**.
- Wait. The first run takes 20–60 minutes. A green tick means finished. (If you see a red cross, see "If something goes wrong" below.)

**6. Turn the website on**
- Repository → **Settings → Pages**.
- Under **Build and deployment → Source** choose **Deploy from a branch**.
- Branch: **gh-pages**, folder: **/ (root)**. Click **Save**.
- After 1–2 minutes your website is live at:
  **https://YOUR-GITHUB-NAME.github.io/alphasuit/**

That's it. From now on the robot updates the results every night by itself.

> Until your first real scan finishes, the site shows a yellow **"Sample data"** bar with made-up stocks. It disappears after the first successful scan.

---

## PART 2 — Post to the feed (market updates / trade plans)

1. Open your website's `feed-composer.html` page (your-site-address/feed-composer.html).
2. Fill the form → click **Make post text** → click **Copy**.
3. On GitHub open `data/feed.json` → click the **pencil (✏)** icon.
4. Put your cursor right after the first `[` , press Enter, **paste** the text.
5. Click **Commit changes**. Your post appears on the website in about a minute.

To delete a post: edit `data/feed.json` and remove its block. To pin it: the helper has a "Pin to top" box.

---

## PART 3 — Optional settings

- **Use your own domain** (like alphasuit.in): Settings → Pages → *Custom domain*. Buy the domain from GoDaddy/Namecheap and follow the instructions GitHub shows.
- **Use Google Sheets for stock prices** (more reliable than Yahoo from GitHub's servers): set up your sheet as described in the first Alphasuit project's README (`python manage.py sheet-setup`), publish each tab as CSV, then in GitHub: Settings → **Secrets and variables → Actions → New repository secret**, name `SHEETS_CSV_URLS`, value = your links separated by commas.
- **Show only stronger setups:** open `.github/workflows/scan.yml`, change `MIN_SCORE: "70"` to `"75"` or `"80"`.
- **Show entry / stop / target levels:** change `SHOW_LEVELS: "0"` to `"1"` (see the SEBI warning below).
- **Change the scan time:** the line `cron: "30 16 * * *"` is in UTC. 16:30 UTC = 22:00 IST.

---

## If something goes wrong

- **Red cross in Actions:** click the failed run → click **Run the scan** → read the last lines and send them to me. The website keeps showing yesterday's results, nothing breaks.
- **Common reason:** the stock-data websites sometimes block GitHub's servers. The scanner tries Google Sheet → NSE files → Yahoo. If all three block it, use the Google Sheet option above (Part 3).
- **Site shows "Sample data" for days:** the scan is failing — see the first point.
- **404 page:** Pages is not turned on (step 6) or the first run has not finished (step 5).
- **Nothing updates:** GitHub pauses scheduled robots in repositories with no activity for 60 days. Open the Actions tab and press **Run workflow** to wake it, or post to your feed now and then.

---

## What this website does NOT have (compared with the Python version)

A pure website has no server, so there are **no user accounts, no payments, no admin dashboard and no "track record" page.** Everything is free and open. The feed is edited through GitHub (Part 2). If you want accounts or paid plans later, use the first Alphasuit project (the Python one) on a server.

## Important

- This is for **education only**. Showing exact buy/sell prices (entry / stop / target) publicly may count as investment advice under SEBI rules — ask a professional before turning `SHOW_LEVELS` on or posting trade plans.
- Stock data comes from public/free sources and can be delayed or wrong. Charts use TradingView's free Lightweight Charts library.

## What is inside (for the curious)

- `index.html, stocks.html, crypto.html, setup.html, patterns.html, feed.html, legal.html` — the pages
- `assets/` — design and scripts
- `data/` — the scan results the pages read (`stocks.json`, `crypto.json`, `feed.json`, `charts/`)
- `scanner/` — the nightly scanner (Python); you never need to touch it
- `.github/workflows/scan.yml` — the free nightly robot
