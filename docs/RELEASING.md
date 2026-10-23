# Release builds and recovery

The `Build, Test and Release` workflow builds assets for an **existing published
release and tag**. It never creates or moves tags, creates another release, or
rewrites release notes. Versions come from `vMAJOR.MINOR.PATCH`, never the Actions
run number. Both build jobs check out the same resolved commit SHA.

Publishing a release triggers the workflow (`release: published`). GitHub does
not trigger another workflow when a release is created with `GITHUB_TOKEN`;
in that case, or for a release published before this workflow was installed,
use the explicit manual recovery below.

## Recover v2.2.232

After the fix is merged and central approval is given, run the corrected
workflow from **main**, not from the old tag (which still has the old workflow):

```sh
gh workflow run build-and-release.yml --repo TimUx/Dienstplan --ref main \
  -f release_tag=v2.2.232 \
  -f source_sha=a3b1bc7059d4e4fccd79339fd7b1fbdfcf038c6d
```

The workflow definition/tools come from the selected workflow ref. The actual
Windows/Linux application, tests, PyInstaller spec and installer/package scripts
come from the selected tag's commit. This allows rebuilding the old source with
the repaired orchestration, without moving its tag or inventing a new version.
The full source SHA is mandatory for manual runs and must match the remote tag,
including when the tag is annotated. Missing tags/releases, draft/immutable
releases and SHA mismatches fail before any build. The publication job checks the
remote target again immediately before upload.

Windows non-slow tests, PyInstaller One-Dir, ZIP, Inno Setup, optional signing
with `WINDOWS_SIGN_CERT_BASE64`/`WINDOWS_SIGN_CERT_PASSWORD` and timestamp retries
are retained. Missing signing secrets still yield unsigned artifacts; configured
signing failures still fail the build. Linux remains on Ubuntu 22.04 and produces
tar.gz, deb and rpm.

## Verify completion

Find the dispatched run and wait for **both builds and asset verification**:

```sh
gh run list --repo TimUx/Dienstplan --workflow build-and-release.yml --limit 5
gh run watch RUN_ID --repo TimUx/Dienstplan --exit-status
gh release view v2.2.232 --repo TimUx/Dienstplan --json tagName,assets,url
```

Expected non-empty download assets:

- `Dienstplan-Windows-v2.2.232.zip`
- `Dienstplan-Windows-Setup-v2.2.232.exe`
- `Dienstplan-Linux-v2.2.232.tar.gz`
- `dienstplan_2.2.232_amd64.deb`
- `dienstplan-2.2.232-1.x86_64.rpm`

Uploads begin only after both builds pass and all five files exist and are
non-empty. Every uploaded asset is downloaded again through the GitHub asset API
and compared to the local SHA-256; a release record alone is not success.
Same-tag runs are serialized. Re-running an approved recovery replaces same-named
assets (`--clobber`), allowing a partially failed upload to recover; it does not
change the release's other metadata. Do not start recovery without approval.

Release guard tests (no application dependencies required):

```sh
python3 -m unittest discover -s scripts -p test_release_target.py -v
```
