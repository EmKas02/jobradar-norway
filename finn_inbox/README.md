# FINN inbox

FINN.no does not allow automated crawling, so jobradar never fetches finn.no.

1. On finn.no/job, search for e.g. `data` in Rogaland, then **Lagre søk** and turn on email alerts.
   Also follow the big local employers that post mainly on FINN: Equinor, Aker BP, Lyse, SpareBank 1 Sør-Norge, Vår Energi.
2. When an alert shows an interesting ad, open it and click the **Copy for jobradar** bookmarklet ([bookmarklet.md](bookmarklet.md)), then run `jobradar finn --paste`. Or create a `.txt` file here by hand:

```
https://www.finn.no/job/ad/123456789
Data Analyst - Example AS - Stavanger
<paste the ad text here>
```

3. Run `jobradar finn` and then `jobradar report`.

`.txt` files in this folder are git-ignored.

## From FINN's alert emails (macOS Mail)

`jobradar finn --mail` reads only FINN's job alert emails (sender `inspirasjon.finn.no`) from the last 14 days (`--days N` to change) and adds each job with its employer, title and teaser. The links are FINN's tracking redirects; jobradar stores them but never opens them. Open the promising ones yourself and use the bookmarklet to add the full ad text.
