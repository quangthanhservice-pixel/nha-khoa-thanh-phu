# Safe deployment checklist — Nha Khoa Thạnh Phú

> This branch is for deployment preparation only. Do not merge or deploy until the local feature changes are reviewed and recovery is tested.

## Confirmed from operator's terminal (2026-11-07)
- Production PostgreSQL version 18.6, SSL verify-full connection succeeded.
- Encrypted custom-format backup: `nktp-20261107-200953.dump.gpg` (7,024 bytes).
- SHA-256: `b3ebdf53151e753805d1d9b0e1d8b6729a51507996abb3ae2b06be83fef11f52`.
- GPG decryption and `pg_restore --list` succeeded (138 TOC entries, 16 TABLE DATA entries).
- Full archive was processed through `pg_restore --file=/dev/null` successfully.
- Operator downloaded the encrypted backup to Windows and reported a matching SHA-256.
- Production table `public.customer_reviews` did not exist when checked.

## Blocking checks before production
- [ ] Restore the encrypted backup into a disposable **local** PostgreSQL 18 instance and validate tables/row counts; never restore into Render production.
- [ ] Keep the backup passphrase separate from the encrypted archive; ensure an independent off-Codespaces copy remains accessible.
- [ ] Bring the uncommitted Codespaces feature changes into a review branch **without including** `.env`, database files, dumps, or `FETCH_HEAD`.
- [ ] Review the complete diff, permissions, CSRF protection, image upload validation, Cloudinary deletion behavior, and dependency compatibility.
- [ ] Verify `customer_reviews` schema against the feature model and migration strategy. SQLAlchemy `create_all` creates missing tables but does not alter existing ones.
- [ ] Confirm `CLOUDINARY_URL` is set privately in the Render service environment (never commit secrets).
- [ ] Run tests against an isolated database and confirm backup recovery before any deployment.
- [ ] Obtain explicit approval before merging to `main`, changing production database, or deploying.

## Important constraints
- Production contains patient records. Do not dump or log patient data into GitHub issues, pull requests, CI logs, or ChatGPT.
- GitHub connector cannot access uncommitted files in Codespaces or the private GPG passphrase.
- The Render Free PostgreSQL database was reported to have an expiration warning for 2026-12-06; verify and plan migration/upgrade before that date.
