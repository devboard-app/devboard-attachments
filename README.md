# devboard-attachments

**The file service.** It handles uploads and keeps the file info. The files themselves live in MinIO (S3-style storage). They never pass through this service.

It powers "images on comments". But it knows nothing about comments. Each file has a generic `context_type` and `context_id`, so it can also serve ticket files, avatars, or anything else later.

- **Port:** `8007`
- **Stack:** FastAPI, PostgreSQL (async SQLAlchemy), MinIO, Alembic

---

## Start here (about 5 minutes)

1. Open a terminal in `devboard-infra`.
2. Run `setup.bat`. It creates the database, starts MinIO and this service, and runs the migrations.
3. Open `http://localhost:8007/health`. You should see `{"status": "ok"}`.
4. MinIO console: `http://localhost:9001`. MinIO API: `http://localhost:9000`.

Only want this service? Postgres and MinIO must already be running. Then:

```bash
docker compose up --build -d
docker compose exec devboard-attachments alembic upgrade head
```

To rebuild after a code change: `redeploy.bat` in `devboard-infra`, option `7`.

---

## How an upload works

The client sends the file **straight to MinIO** with a temporary link (a *presigned URL*). Then it asks this service to confirm.

```
1. POST /attachments/request-upload/
   ├─ file type must be allowed
   ├─ size must be under MAX_FILE_SIZE_MB
   ├─ context must be under MAX_ATTACHMENTS_PER_CONTEXT
   ├─ saves a row with status "pending"
   └─ returns { attachment_id, upload_url }

2. Client PUTs the file to upload_url (MinIO). This service is not involved.

3. POST /attachments/{id}/confirm/
   ├─ already stored?        return it (safe to call twice)
   ├─ file missing in MinIO  409, row removed
   ├─ size is not as said    409, row removed
   ├─ size over the max      413, row and file removed
   ├─ content is not the declared type  415, row and file removed
   └─ status becomes "stored", size = the real size
```

The client's claims in step 1 are not trusted. Confirm checks the **real file**:

| Type | Check |
|---|---|
| `image/png`, `image/jpeg`, `image/webp`, `image/gif` | Opens with Pillow and verifies. |
| `application/pdf` | Starts with `%PDF-`. |
| `text/plain` | Decodes as UTF-8. |

A zip file named `cat.png` fails.

If confirm fails, both the row and the file are removed. Nothing is left half done.

---

## Two S3 clients (on purpose)

| Client | Address | Used for |
|---|---|---|
| Internal | `S3_ENDPOINT_URL` (`http://devboard-minio:9000`) | This service's own calls. |
| Public | `S3_PUBLIC_ENDPOINT_URL` (`http://localhost:9000`) | Signing links the browser will use. |

A presigned link is tied to its host name. A link signed for `devboard-minio` would fail in the browser. So links are signed with the public address.

Both clients start once, when the app starts.

---

## Who can do what

| Routes | How to log in |
|---|---|
| `/attachments/*` | `Authorization: Bearer <jwt>`. The token's `sub` is the owner. |
| `/internal/attachments/*` | `X-Service-Key: <INTERNAL_API_KEY>` |

- **Before a file is attached**, only the owner can touch it. That is all we know at upload time.
- **After it is attached**, the rules belong to whatever it is attached to (for example, a comment). Only devboard-work knows those rules. So work checks who may see the comment, then asks this service for links through the internal batch route.

---

## API

| Method | Path | Auth | What it does |
|---|---|---|---|
| `POST` | `/attachments/request-upload/` | JWT | Start an upload. Returns `attachment_id` and `upload_url`. |
| `POST` | `/attachments/{id}/confirm/` | JWT | Finish and check an upload. |
| `GET` | `/attachments/{id}/url/` | JWT (owner) | Get a download link. |
| `DELETE` | `/attachments/{id}/` | JWT (owner) | Delete the file and the row. Returns `204`. |
| `POST` | `/internal/attachments/batch/` | `X-Service-Key` | Up to 100 ids in, download links out. |
| `GET` | `/health` `/health/db` | none | Health checks. |

The batch route only returns links for files with status `stored`. Links expire after `PRESIGNED_URL_TTL_SECONDS`, so they are made when needed and never saved.

Errors: `403` not the owner. `404` not found. `409` file missing, size mismatch, too many files, or not stored. `413` too big. `415` wrong type.

---

## Settings

Copy `.env.example` to `.env`.

| Variable | What it is |
|---|---|
| `DATABASE_URL` | App database link (`postgresql+asyncpg://...`). |
| `DATABASE_URL_SYNC` | Alembic database link (`postgresql+psycopg2://...`). |
| `ATTACHMENTS_DB_PASSWORD` | Read by `devboard-infra\setup.bat` to create the database user. Must match the URLs. |
| `S3_ENDPOINT_URL` | MinIO address inside Docker. |
| `S3_PUBLIC_ENDPOINT_URL` | MinIO address the browser can reach. |
| `S3_ACCESS_KEY` `S3_SECRET_KEY` | MinIO login. |
| `S3_BUCKET` | Bucket name. Created at start if missing. |
| `MAX_FILE_SIZE_MB` | Default 5. Checked on the claimed size and on the real size. |
| `MAX_ATTACHMENTS_PER_CONTEXT` | Default 5. Counts only `stored` files. |
| `PRESIGNED_URL_TTL_SECONDS` | Default 900. Applies to upload and download links. |
| `JWT_SECRET` `INTERNAL_API_KEY` | Same values in every service. |

---

## Database

One table: `attachments`.

| Column | Notes |
|---|---|
| `id` | UUID. Also the first part of the storage key. |
| `owner_id` | The JWT `sub` of who asked for the upload. |
| `context_type` `context_id` | Empty while pending. |
| `filename` `content_type` | As the client declared. |
| `size` | Empty until confirmed, then the real size. |
| `storage_key` | `{id}/{filename}` |
| `status` | `pending` or `stored` |

```bash
alembic upgrade head
alembic revision --autogenerate -m "message"
```

---

## Cleanup

Uploads that were requested but never confirmed stay `pending`. This script removes `pending` rows older than 24 hours, and their files:

```bash
python -m app.cleanup
```

**Nothing runs it automatically yet.**

---

## Not done yet

1. **Nobody queries by context.** devboard-work keeps the file ids on the comment. The context columns are saved but not used to search.
2. **The batch route takes ids, not a context.** Someone could attach another user's file id to their own comment and get a link. Fix: take `(context_type, context_ids)` instead.
3. **The per-context limit can be skipped.** It counts only `stored` files, so several uploads requested before any confirm all pass.
4. **No list route.** A lost attachment id cannot be found again.
5. **Dev storage only.** MinIO uses root credentials. No bucket policy or lifecycle rules. Production needs a real bucket setup.

Also missing: a scheduler for the cleanup script.
