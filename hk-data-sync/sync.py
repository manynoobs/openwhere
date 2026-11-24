"""Keeps the scrapers' data in a private storage bucket, apart from GitHub.

    python sync.py status                   # what differs between this machine and the bucket
    python sync.py push                     # send new and changed files to the bucket
    python sync.py pull                     # fetch new and changed files from the bucket
    python sync.py pull hk-rent-scraper     # only that folder

The files are every scraper's data/ and out/ folder and hk-data-share/, stored in the bucket
under the same paths. A file is sent or fetched when the other side lacks it or holds
different contents. Where both sides changed a file the newer copy is kept, unless --force
is given. Nothing is ever deleted on either side.

The bucket is any S3-compatible one; Cloudflare R2 is what the settings assume. Copy
bucket.example.json to bucket.json and fill it in. bucket.json holds the key and is not
committed.

Standard library only; Python 3.9 or newer.
"""
import argparse
import hashlib
import hmac
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SETTINGS = ROOT / "bucket.json"
FOLDERS = ["hk-*-scraper/data", "hk-*-scraper/out", "hk-data-share"]
WORKERS = 4


def settings():
    if not SETTINGS.exists():
        raise SystemExit(f"no {SETTINGS.name}: copy bucket.example.json to bucket.json and fill it in")
    s = json.loads(SETTINGS.read_text(encoding="utf-8"))
    s["endpoint"] = s["endpoint"].rstrip("/")
    s.setdefault("region", "auto")
    return s


def signed_headers(s, method, path, query, now):
    """AWS Signature Version 4 headers for one request; the body is not signed."""
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    headers = {"host": urllib.parse.urlsplit(s["endpoint"]).netloc,
               "x-amz-content-sha256": "UNSIGNED-PAYLOAD", "x-amz-date": stamp}
    names = ";".join(sorted(headers))
    canonical = "\n".join([method, path, query,
                           "".join(f"{k}:{headers[k]}\n" for k in sorted(headers)),
                           names, "UNSIGNED-PAYLOAD"])
    scope = f"{stamp[:8]}/{s['region']}/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", stamp, scope,
                         hashlib.sha256(canonical.encode()).hexdigest()])
    key = ("AWS4" + s["secret_access_key"]).encode()
    for part in scope.split("/"):
        key = hmac.new(key, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["Authorization"] = (f"AWS4-HMAC-SHA256 Credential={s['access_key_id']}/{scope}, "
                                f"SignedHeaders={names}, Signature={signature}")
    del headers["host"]  # urllib sends it
    return headers


def call(s, method, key="", query=None, body=None, into=None):
    """One request to the bucket. Returns the answer, or writes it to the file `into`."""
    path = "/" + urllib.parse.quote(f"{s['bucket']}/{key}".rstrip("/"), safe="/")
    q = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(v, safe='')}"
                 for k, v in sorted((query or {}).items()))
    url = s["endpoint"] + path + ("?" + q if q else "")
    for attempt in range(5):
        headers = signed_headers(s, method, path, q, datetime.now(timezone.utc))
        if body is not None:
            headers["Content-Type"] = "application/octet-stream"
        try:
            req = urllib.request.Request(url, data=body, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                if into is None:
                    return r.read()
                part = into.with_name(into.name + ".part")
                with open(part, "wb") as f:
                    while chunk := r.read(1 << 20):
                        f.write(chunk)
                part.replace(into)
                return None
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                said = e.read().decode("utf-8", "replace")
                code = said.split("<Code>")[1].split("</Code>")[0] if "<Code>" in said else ""
                hint = " (check the key and bucket name in bucket.json)" if e.code in (401, 403, 404) else ""
                raise SystemExit(f"the bucket answered HTTP {e.code} {code}{hint}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2 ** attempt + random.random())
    raise SystemExit(f"no answer from the bucket after 5 tries: {method} {key}")


def chosen(key, only):
    return not only or any(key == o or key.startswith(o + "/") for o in only)


def here(only):
    files = {}
    for pattern in FOLDERS:
        for folder in REPO.glob(pattern):
            for p in folder.rglob("*"):
                if p.is_file() and p.name != ".DS_Store" and p.suffix != ".part":
                    files[p.relative_to(REPO).as_posix()] = p
    return {k: p for k, p in files.items() if chosen(k, only)}


def there(s, only):
    """Every file in the bucket: key -> (size, md5, time last written)."""
    files, token = {}, None
    while True:
        query = {"list-type": "2"}
        if token:
            query["continuation-token"] = token
        page = ET.fromstring(call(s, "GET", query=query))
        for c in page.findall("{*}Contents"):
            written = datetime.fromisoformat(c.findtext("{*}LastModified").replace("Z", "+00:00"))
            files[c.findtext("{*}Key")] = (int(c.findtext("{*}Size")),
                                           c.findtext("{*}ETag").strip('"'), written.timestamp())
        token = page.findtext("{*}NextContinuationToken")
        if not token:
            return {k: v for k, v in files.items() if chosen(k, only)}


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def compare(s, only):
    """Sort every file into: only here, only there, changed and newer here, changed and newer there."""
    local, remote = here(only), there(s, only)
    diff = {"only here": [], "only there": [], "newer here": [], "newer there": []}
    same = 0
    for key in sorted(local.keys() | remote.keys()):
        if key not in remote:
            diff["only here"].append(key)
        elif key not in local:
            diff["only there"].append(key)
        else:
            size, etag, written = remote[key]
            stat = local[key].stat()
            if stat.st_size == size and md5(local[key]) == etag:
                same += 1
            else:
                diff["newer here" if stat.st_mtime > written else "newer there"].append(key)
    sizes = {k: (local[k].stat().st_size if k in local else remote[k][0]) for k in local.keys() | remote.keys()}
    return diff, same, sizes


def amount(keys, sizes):
    n = sum(sizes[k] for k in keys)
    return f"{n / 1e9:.1f} GB" if n >= 1e9 else f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} kB"


def files(keys):
    return f"{len(keys)} file" + ("" if len(keys) == 1 else "s")


def move(keys, one, word):
    """Run `one` on every key, a few at a time, saying how far along at each quarter."""
    with ThreadPoolExecutor(WORKERS) as pool:
        for n, _ in enumerate(pool.map(one, keys), 1):
            if n * 4 // len(keys) > (n - 1) * 4 // len(keys):
                print(f"  {n}/{len(keys)} {word}", flush=True)


def cmd_status(s, args):
    diff, same, sizes = compare(s, args.folders)
    print(f"{same:6}  the same on both sides")
    for name, note in (("only here", "push sends them"), ("only there", "pull fetches them"),
                       ("newer here", "changed; push sends them"),
                       ("newer there", "changed; pull fetches them")):
        keys = diff[name]
        where = name.replace("there", "in the bucket")
        print(f"{len(keys):6}  {where}" + (f" ({amount(keys, sizes)}): {note}" if keys else ""))


def cmd_push(s, args):
    diff, _, sizes = compare(s, args.folders)
    keys = diff["only here"] + diff["newer here"] + (diff["newer there"] if args.force else [])
    if keys:
        move(keys, lambda k: call(s, "PUT", k, body=(REPO / k).read_bytes()), "sent")
    print(f"{files(keys)} sent" + (f" ({amount(keys, sizes)})" if keys else ""))
    if diff["newer there"] and not args.force:
        print(f"{files(diff['newer there'])} newer in the bucket left alone: "
              "pull, or push --force to overwrite")


def cmd_pull(s, args):
    diff, _, sizes = compare(s, args.folders)
    keys = diff["only there"] + diff["newer there"] + (diff["newer here"] if args.force else [])

    def fetch(key):
        (REPO / key).parent.mkdir(parents=True, exist_ok=True)
        call(s, "GET", key, into=REPO / key)

    if keys:
        move(keys, fetch, "fetched")
    print(f"{files(keys)} fetched" + (f" ({amount(keys, sizes)})" if keys else ""))
    if diff["newer here"] and not args.force:
        print(f"{files(diff['newer here'])} newer here left alone: "
              "push, or pull --force to overwrite")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "push", "pull"])
    ap.add_argument("folders", nargs="*", help="limit to these folders, e.g. hk-rent-scraper or hk-rent-scraper/out")
    ap.add_argument("--force", action="store_true", help="overwrite files that are newer on the other side")
    args = ap.parse_args()
    args.folders = [f.strip("/") for f in args.folders]
    {"status": cmd_status, "push": cmd_push, "pull": cmd_pull}[args.command](settings(), args)


if __name__ == "__main__":
    sys.exit(main())
