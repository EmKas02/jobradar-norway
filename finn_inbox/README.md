# FINN inbox

FINN.no does not allow automated crawling, so jobradar never fetches finn.no.

1. On finn.no/job, search for e.g. `data` in Rogaland, then **Lagre søk** and turn on email alerts.
   Also follow the big local employers that post mainly on FINN: Equinor, Aker BP, Lyse, SpareBank 1 Sør-Norge, Vår Energi.
2. When an alert shows an interesting ad, create a `.txt` file here:

```
https://www.finn.no/job/ad/123456789
Data Analyst - Example AS - Stavanger
<paste the ad text here>
```

3. Run `jobradar finn` and then `jobradar report`.

`.txt` files in this folder are git-ignored.
