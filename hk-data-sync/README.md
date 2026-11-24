# hk-data-sync

Keeps the scrapers' data in a private storage bucket, apart from GitHub. GitHub holds the scripts; the bucket holds what they collect, 1,228 files and about 3.7 GB on 24 Nov 2026.

## sync.py

It needs Python 3.9 or newer and nothing else.

```bash
python3 sync.py status
```

```bash
python3 sync.py push
```

```bash
python3 sync.py pull
```

- `status` counts the files that differ between this machine and the bucket, and changes nothing.
- `push` sends every file the bucket lacks or holds an older copy of. Run it after a scrape.
- `pull` fetches every file this machine lacks or holds an older copy of. Run it on a new machine, after cloning the repo, to get all the data without scraping again.
- A folder after the command limits it, for example `python3 sync.py pull hk-rent-scraper` or `python3 sync.py push hk-catering-scraper/out`.

The files are each scraper's `data/` and `out/` folder and `hk-data-share/`, stored in the bucket under the same paths.

A file counts as the same when its size and contents match on both sides. Where the contents differ, the newer copy wins: `push` leaves a file alone if the bucket's copy is newer, and `pull` leaves one alone if the local copy is newer, and each says how many it left. `--force` overwrites them. Nothing is deleted on either side.

## Setting up the bucket

The script works with any S3-compatible bucket. With Cloudflare R2:

1. In the Cloudflare dashboard, open R2 and create a bucket named `hk-data`. Leave public access off.
2. Under R2's API tokens, create a token with Object Read & Write permission, limited to that bucket.
3. Cloudflare then shows an access key ID, a secret access key and an S3 endpoint of the form `https://<account id>.r2.cloudflarestorage.com`.
4. Copy `bucket.example.json` to `bucket.json` and fill in those three values.

`bucket.json` holds the key and is not committed. Anyone who should reach the data needs their own copy of it, or a token of their own.

For a bucket elsewhere, give its endpoint and add `"region"` if the provider needs one other than `auto`.

## Limits

- The bucket is private, so the OpenWhere site cannot read from it. It is storage for the people running the scripts.
- A file changed on two machines since the last sync keeps only the newer copy.
- Files are sent whole and one request each, which suits files up to a few hundred MB.
- A file uploaded to the bucket by another tool in several parts is seen as different and sent again.
