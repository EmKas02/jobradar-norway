"""Command-line entry point: `python -m jobradar <command>`."""
from __future__ import annotations

import argparse
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import finn, report, sources
from .filters import is_remote, is_rogaland, strip_html, title_is_relevant
from .matcher import Matcher
from .nav import NavFeed, latest_by_uuid
from .store import STATUSES, Store, now_iso

ROOT = Path.cwd()


def load_profile(path: Path) -> dict:
    if not path.exists():
        path = ROOT / "profile.example.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def nav_ad_to_row(ad: dict) -> dict:
    locations = ad.get("workLocations") or []
    text = strip_html(ad.get("description"))
    return {
        "uuid": ad["uuid"],
        "source": "nav",
        "title": ad.get("title") or "",
        "employer": (ad.get("employer") or {}).get("name", ""),
        "location": ", ".join(sorted({(l.get("municipal") or l.get("city") or "").title() for l in locations} - {""})),
        "remote": int(is_remote(text)),
        "url": ad.get("link") or "",
        "apply_url": ad.get("applicationUrl") or "",
        "due": ad.get("applicationDue") or "",
        "published": ad.get("published") or "",
        "expires": ad.get("expires") or "",
        "text": text,
    }


def cmd_sync(args, store: Store) -> None:
    if args.source in ("all", "nav"):
        sync_nav(args, store)
    if args.source in ("all", "companies", "remote"):
        config = yaml.safe_load(args.sources.read_text(encoding="utf-8"))
    if args.source in ("all", "companies"):
        sync_companies(config, store)
    if args.source in ("all", "remote"):
        sync_remote(config, store)


def sync_companies(config: dict, store: Store) -> None:
    print("Reading company career boards...")
    for company in config.get("companies", []):
        try:
            rows = sources.ADAPTERS[company["ats"]](company)
        except Exception as exc:  # one broken board should not stop the rest
            print(f"  {company['name']}: failed ({exc})")
            continue
        kept = [r for r in rows if sources.keep_company_job(r)]
        if rows:
            stored, removed = store.replace_source(rows[0]["source"], kept)
            print(f"  {company['name']}: {len(rows)} jobs, kept {stored}, removed {removed}")


def sync_remote(config: dict, store: Store) -> None:
    himalayas = config.get("remote", {}).get("himalayas")
    if not himalayas:
        return
    print("Reading Himalayas remote jobs (entry level, open to Norway)...")
    rows = sources.himalayas(himalayas["queries"])
    stored, removed = store.replace_source("himalayas", rows)
    print(f"  Himalayas: kept {stored}, removed {removed}")


def sync_nav(args, store: Store) -> None:
    last = store.get_meta("nav_last_sync")
    since = datetime.fromisoformat(last) if last and not args.days else datetime.now(timezone.utc) - timedelta(days=args.days or 14)
    started = now_iso()
    feed = NavFeed()
    print(f"Reading NAV feed since {since:%Y-%m-%d %H:%M}...")
    latest = latest_by_uuid(feed.iter_items(since))

    kept = removed = 0
    for uuid, item in latest.items():
        entry = item["_feed_entry"]
        if entry["status"] != "ACTIVE":
            if store.has_ad(uuid):
                store.delete_ad(uuid)
                removed += 1
            continue
        # Every Rogaland ad is fetched and left to the scorer; elsewhere only
        # data-sounding titles are fetched, then kept if the ad is remote.
        local = is_rogaland(entry.get("municipal"))
        if not local and not title_is_relevant(entry.get("title")):
            continue
        ad = feed.get_ad(item["url"])
        if not ad:
            continue
        row = nav_ad_to_row(ad)
        local = local or any(is_rogaland(l.get("municipal")) for l in ad.get("workLocations") or [])
        if local or row["remote"]:
            store.upsert_ad(row)
            kept += 1
    store.set_meta("nav_last_sync", started)
    print(f"Scanned {len(latest)} ads: kept {kept} (Rogaland or remote), removed {removed} inactive.")


def cmd_finn(args, store: Store) -> None:
    if args.paste:
        clipboard = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        path = finn.save_pasted_ad(clipboard, args.inbox)
        print(f"Saved {path.name}")
    if args.mail:
        alerts = {r["uuid"]: r for raw in finn.mail_alert_sources(args.days) for r in finn.parse_alert_email(raw)}
        for row in alerts.values():
            if not store.has_ad(row["uuid"]):
                store.upsert_ad(row)
        print(f"Read FINN alert emails from the last {args.days} days: {len(alerts)} jobs")
    ads = finn.load_inbox(args.inbox)
    for ad in ads:
        store.upsert_ad(ad)
    print(f"Imported {len(ads)} FINN ads from {args.inbox}/")


def cmd_report(args, store: Store) -> None:
    ads = [a for a in store.active_ads() if a.get("status") not in ("ignored", "rejected")]
    matcher = Matcher(load_profile(args.profile))
    scored = sorted(zip(ads, matcher.score_many(ads)), key=lambda p: p[1].score, reverse=True)
    scored = [(a, m) for a, m in scored if m.score >= args.min_score]
    out = args.out / f"jobs-{date.today().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report.render(scored, args.top), encoding="utf-8")
    for label, local in (("Rogaland", True), ("Remote", False)):
        print(f"\n{label}:")
        for ad, m in [p for p in scored if report.is_local(p[0]) == local][:8]:
            print(f"{m.score:>3}  {ad['uuid'][:8]}  {ad['title'][:60]}  ({ad['employer']})")
    print(f"\nFull report: {out}")


def cmd_mark(args, store: Store) -> None:
    uuid = store.resolve(args.id)
    ad = store.set_status(uuid, args.status, args.note)
    print(f"{ad['title']} ({ad['employer']}) -> {args.status}")


def cmd_tracker(args, store: Store) -> None:
    rows = store.applications()
    if not rows:
        print("No tracked applications yet. Use `mark <id> applied`.")
    for r in rows:
        print(f"{r['updated_at'][:10]}  {r['status']:<9}  {r['title']} ({r['employer']})  {r['note'] or ''}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="jobradar", description="Find and rank data jobs in Rogaland and remote.")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "jobradar.db")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sync", help="pull new ads from NAV, company boards and remote boards")
    p.add_argument("--source", choices=("all", "nav", "companies", "remote"), default="all")
    p.add_argument("--sources", type=Path, default=ROOT / "sources.yaml", help="company and remote board config")
    p.add_argument("--days", type=int, help="NAV: look back N days instead of since last sync")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("finn", help="import FINN ads saved in the inbox folder")
    p.add_argument("--inbox", type=Path, default=ROOT / "finn_inbox")
    p.add_argument("--paste", action="store_true", help="first save the ad copied with the bookmarklet (macOS clipboard)")
    p.add_argument("--mail", action="store_true", help="also add jobs from FINN alert emails in Mail.app (macOS)")
    p.add_argument("--days", type=int, default=14, help="with --mail: how far back to read alert emails")
    p.set_defaults(func=cmd_finn)

    p = sub.add_parser("report", help="score ads and write a Markdown report")
    p.add_argument("--profile", type=Path, default=ROOT / "profile.yaml")
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--min-score", type=int, default=25)
    p.add_argument("--out", type=Path, default=ROOT / "reports")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("mark", help="track an application")
    p.add_argument("id", help="ad id (the first 8 characters are enough)")
    p.add_argument("status", choices=STATUSES)
    p.add_argument("--note")
    p.set_defaults(func=cmd_mark)

    p = sub.add_parser("tracker", help="list tracked applications")
    p.set_defaults(func=cmd_tracker)

    args = parser.parse_args(argv)
    args.func(args, Store(args.db))


if __name__ == "__main__":
    main()
