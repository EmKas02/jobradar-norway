# "Copy for jobradar" bookmarklet

You open the FINN ad yourself; the bookmarklet only copies what is on your screen to the
clipboard, in the inbox format. Nothing is fetched automatically.

## Install (once)

1. Show the bookmarks bar (Safari: View → Show Favorites Bar; Chrome: Cmd+Shift+B).
2. Add any page as a bookmark, then edit it: name it **Copy for jobradar** and replace the URL with:

```
javascript:(()=>{if(!/(^|\.)finn\.no$/.test(location.hostname)){alert('Open a FINN job ad first');return}const g=s=>{const e=document.querySelector(s);return e?e.innerText.trim():''};const title=g('h1')||document.title;const body=(document.querySelector('main')||document.body).innerText.trim();const txt=location.href.split('?')[0]+'\n'+title+'\n'+body;navigator.clipboard.writeText(txt).then(()=>alert('Copied for jobradar. Now run: jobradar finn --paste'),()=>prompt('Copy this text:',txt))})()
```

## Use

1. Open an interesting FINN job ad (from your saved-search email or a search).
2. Click **Copy for jobradar**.
3. In the terminal:

```bash
cd ~/JobSearch/jobradar-norway && .venv/bin/jobradar finn --paste && .venv/bin/jobradar report
```

The ad is saved to `finn_inbox/<finnkode>.txt` and scored with everything else.
Edit line 2 of that file to `Title - Employer - Location` if you want those columns filled in the report.
