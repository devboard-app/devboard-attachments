# devboard-attachments

File attachment service for DevBoard. Handles the upload lifecycle and the metadata; the
bytes live in object storage and never pass through this service on the way in.

It backs the "images on comments" feature but knows nothing about comments — attachments
are tagged with a generic `context_type` / `context_id` pair, so the same service works for
ticket attachments, avatars, or anything else added later.

FastAPI + async SQLAlchemy + Postgres + MinIO (S3-compatible). Port **8007**.

## The upload flow

The service never receives the file on upload. The client uploads directly to storage with
a presigned URL, then asks the service to confirm it.

```
1. POST /attachments/request-upload            (JWT)
   ├─ content_type must be in the allow list
   ├─ declared size must be under MAX_FILE_SIZE_MB
   ├─ context must be under MAX_ATTACHMENTS_PER_CONTEXT
   ├─ insert row, status=pending, storage_key = "{attachment_id}/{filename}"
   └─ 200 { attachment_id, upload_url }

2. Client PUTs the bytes straight to MinIO using upload_url.
   The service is not involved.

3. POST /attachments/{id}/confirm              (JWT)
   ├─ already stored?              return as-is (idempotent)
   ├─ HEAD the object              missing        -> 409, row and object removed
   ├─ real size vs declared size   mismatch       -> 409, removed
   ├─ real size vs max             too large      -> 413, removed
   ├─ download and sniff content   wrong type     -> 415, removed
   └─ status=stored, size = the real size
```

Everything the client says in step 1 is a claim. The presigned PUT does not constrain what
actually gets uploaded, so confirm re-derives the size from the object and validates the
*content*, not the filename: Pillow `open()` + `verify()` for images, a `%PDF-` prefix
check for PDFs, a UTF-8 decode for text. A zip named `cat.png` fails here.

A failed confirm rolls back both sides — the object is deleted and the row is removed —
so nothing is left half-created.

## Two S3 clients, on purpose

```python
_s3        = _client(settings.S3_ENDPOINT_URL)         # http://devboard-minio:9000
_public_s3 = _client(settings.S3_PUBLIC_ENDPOINT_URL)  # http://localhost:9000
```

An S3v4 signature covers the host header, so a URL signed for `devboard-minio:9000` is
invalid when a browser sends it to `localhost:9000`. Presigned URLs have to be signed with
the hostname the *client* will use, while the service's own calls (`head_object`,
`get_object`, `delete_object`, `create_bucket`) go over the docker network.

Both clients are created once in the FastAPI lifespan via an `AsyncExitStack` — creating a
client per operation was measurably wasteful and is why `init_storage()` exists. Calling a
storage function before the lifespan has run raises rather than silently building a new
client.

In production with a real S3 and a CDN in front, the two endpoints likely collapse into one.

## Auth

Two models, deliberately different:

| routes | auth |
|---|---|
| `/attachments/*` | `Authorization: Bearer <jwt>`, `sub` is the owner UUID |
| `/internal/attachments/*` | `X-Service-Key` |

Every user-facing operation checks `attachment.owner_id` against the caller. That's the
right rule for the window *before* a file is attached to anything — at request-upload time
the comment doesn't exist yet, so ownership is the only identity available.

Once a file is attached, access follows the rules of whatever it's attached to, and only
devboard-work knows those. That's what the internal batch endpoint is for: work decides
whether the caller can see a comment, then asks for presigned URLs for its attachments.

## API

```
POST   /attachments/request-upload        JWT    -> { attachment_id, upload_url }
POST   /attachments/{id}/confirm          JWT    -> AttachmentResponse
GET    /attachments/{id}/url              JWT    -> { url }   (owner only)
DELETE /attachments/{id}                  JWT    -> 204

POST   /internal/attachments/batch        X-Service-Key   -> [ResolvedAttachment]

GET    /health
GET    /health/db
```

`POST /internal/attachments/batch` takes up to 100 `attachment_ids` and returns a
presigned GET for each one that is `stored`. Presigned URLs expire after
`PRESIGNED_URL_TTL_SECONDS`, so they're generated at render time rather than stored.

## Configuration

Copy `.env.example` to `.env`.

| var | notes |
|---|---|
| `DATABASE_URL` | async driver — `postgresql+asyncpg://...` |
| `DATABASE_URL_SYNC` | sync driver, used by alembic only. **Missing from `.env.example`** |
| `S3_ENDPOINT_URL` | internal, for the service's own calls |
| `S3_PUBLIC_ENDPOINT_URL` | what the client will hit; presigned URLs are signed for this |
| `S3_ACCESS_KEY` `S3_SECRET_KEY` `S3_BUCKET` | MinIO credentials; the bucket is created on startup if absent |
| `MAX_FILE_SIZE_MB` | enforced on the declared size and again on the real one |
| `MAX_ATTACHMENTS_PER_CONTEXT` | counts `stored` rows only |
| `PRESIGNED_URL_TTL_SECONDS` | applies to both PUT and GET URLs |
| `JWT_SECRET` `INTERNAL_API_KEY` | shared across the stack |

`setup.bat` in devboard-infra reads `ATTACHMENTS_DB_PASSWORD` from this `.env` to create
the database user, so that needs to be present too.

## Running it

```
cd ..\devboard-infra
setup.bat        # creates attachments_user + attachments_db, brings up devboard-minio
migrate.bat      # option 5 for this service alone
redeploy.bat
```

MinIO's console is on `localhost:9001`, the API on `localhost:9000`.

Migrations are alembic and run against `DATABASE_URL_SYNC`:

```
alembic upgrade head
alembic revision --autogenerate -m "..."
```

## Schema

One table, `attachments`:

| column | notes |
|---|---|
| `id` | uuid, also the first segment of the storage key |
| `owner_id` | indexed; the JWT `sub` of whoever requested the upload |
| `context_type` `context_id` | nullable while pending; indexed together |
| `filename` `content_type` | as declared by the client |
| `size` | null until confirmed, then the real object size |
| `storage_key` | `{id}/{filename}` |
| `status` | `pending` or `stored` |

Postgres rather than Mongo here, unlike devboard-analytics: attachment metadata is uniform,
the pending→stored lifecycle wants transactions, and the identity is relational. If
per-file attributes ever vary, that's a `properties JSONB` column, not another database.

## Housekeeping

`app/cleanup.py` removes `pending` rows older than 24 hours along with their objects — the
debris from uploads that were requested and never confirmed. It's a standalone script:

```
python -m app.cleanup
```

Nothing schedules it yet.

## Known gaps

- **The context columns are write-only.** devboard-work stores `attachment_ids` on the
  comment and resolves by id, so nothing ever queries by `(context_type, context_id)` and
  the index is unused. The link is effectively stored in two places, with work as the
  authoritative one.
- **The batch endpoint takes ids, not a context.** It returns a presigned URL for any
  `stored` attachment whose id you pass, and work stores attachment ids without checking
  ownership — so a user can attach someone else's file id to their own comment and have it
  resolve. Taking `(context_type, context_ids[])` instead would close this, because the id
  would stop being the capability.
- **`MAX_ATTACHMENTS_PER_CONTEXT` is checked against `stored` rows only**, at
  request-upload time. Requesting several uploads before confirming any of them gets past it.
- **No listing endpoint.** There's no way to enumerate your own attachments, so an
  attachment id that gets lost is unreachable.
- **The cleanup script has no scheduler.**
- **Dev-only storage config.** MinIO with root credentials, bucket auto-created at startup,
  no bucket policy or lifecycle rules. Production is a config swap plus a real bucket setup.
