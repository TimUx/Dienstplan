"""Release guard regression tests; run without application dependencies."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import release_target


TAG = "v2.2.232"
SHA = "a3b1bc7059d4e4fccd79339fd7b1fbdfcf038c6d"
REPO = "TimUx/Dienstplan"


def release(**changes):
    result = {
        "tag_name": TAG, "draft": False, "published_at": "2026-10-23T10:01:21Z",
        "immutable": False,
    }
    result.update(changes)
    return result


class TargetTests(unittest.TestCase):
    def resolve(self, source=SHA, required=True, metadata=None, sha=SHA):
        with patch.object(release_target, "command", side_effect=[
            "", sha, json.dumps(metadata or release()),
        ]) as run:
            result = release_target.resolve_target(TAG, source, required, REPO)
            self.assertEqual(run.call_args_list[0].args, (
                "git", "fetch", "--no-tags", "origin", f"refs/tags/{TAG}",
            ))
            return result

    def test_dispatch_resolves_selected_version_and_sha(self):
        self.assertEqual(self.resolve(), ("2.2.232", SHA))

    def test_published_event_resolves_tag_without_dispatch_sha(self):
        self.assertEqual(self.resolve(source="", required=False), ("2.2.232", SHA))

    def test_uppercase_sha(self):
        self.assertEqual(self.resolve(source=SHA.upper()), ("2.2.232", SHA))

    def test_mismatched_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "not requested source"):
            self.resolve(sha="b" * 40)

    def test_missing_or_invalid_explicit_sha_rejected_before_fetch(self):
        for source in ("", "main", SHA[:7], "x" * 40, SHA + "\n"):
            with self.subTest(source=source), patch.object(release_target, "command") as run:
                with self.assertRaisesRegex(ValueError, "full 40-character"):
                    release_target.resolve_target(TAG, source, True, REPO)
                run.assert_not_called()

    def test_invalid_tags_rejected_before_fetch(self):
        for tag in ("", "main", "v2.2.0232", "v2.2.232;echo bad", "v2.2.232\n"):
            with self.subTest(tag=tag), patch.object(release_target, "command") as run:
                with self.assertRaises(ValueError):
                    release_target.resolve_target(tag, SHA, True, REPO)
                run.assert_not_called()

    def test_unpublished_or_different_release_rejected(self):
        for changes in ({"draft": True}, {"published_at": None}, {"tag_name": "v2.2.231"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "published"):
                self.resolve(metadata=release(**changes))

    def test_immutable_release_rejected(self):
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.resolve(metadata=release(immutable=True))

    def test_missing_remote_tag_or_release_is_not_created(self):
        with patch.object(release_target, "command", side_effect=subprocess.CalledProcessError(1, "fetch")):
            with self.assertRaises(subprocess.CalledProcessError):
                release_target.resolve_target(TAG, SHA, True, REPO)

    def test_missing_release_is_not_created(self):
        with patch.object(release_target, "command", side_effect=[
            "", SHA, subprocess.CalledProcessError(1, "gh api"),
        ]) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                release_target.resolve_target(TAG, SHA, True, REPO)
            self.assertEqual(run.call_count, 3)
            self.assertEqual(run.call_args.args, ("gh", "api", f"repos/{REPO}/releases/tags/{TAG}"))

    def test_lightweight_and_annotated_tags_resolve_to_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            origin = Path(directory) / "origin"
            checkout = Path(directory) / "checkout"
            def git(*args):
                return subprocess.check_output(
                    ["git", *args], text=True, stderr=subprocess.DEVNULL,
                ).strip()
            git("init", str(origin))
            git("-C", str(origin), "-c", "user.name=Test", "-c", "user.email=test@example.com",
                "commit", "--allow-empty", "-m", "Source")
            sha = git("-C", str(origin), "rev-parse", "HEAD")
            git("-C", str(origin), "tag", TAG)
            git("-C", str(origin), "-c", "user.name=Test", "-c", "user.email=test@example.com",
                "tag", "-a", "v2.2.233", "-m", "Annotated release")
            git("clone", "--no-tags", str(origin), str(checkout))
            original = release_target.command
            def command(*args):
                if args[0] == "gh":
                    return json.dumps(release(tag_name=args[-1].split("/")[-1]))
                return original("git", "-C", str(checkout), *args[1:])
            with patch.object(release_target, "command", side_effect=command):
                for tag in (TAG, "v2.2.233"):
                    self.assertEqual(
                        release_target.resolve_target(tag, sha, True, REPO), (tag[1:], sha),
                    )
            self.assertEqual(git("-C", str(origin), "rev-parse", f"{TAG}^{{commit}}"), sha)


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_cwd = Path.cwd()
        os.chdir(self.directory.name)
        self.names = release_target.asset_names("2.2.232")
        self.content = b"binary build output"
        self.assets = []
        for index, name in enumerate(self.names):
            Path(name).write_bytes(self.content)
            self.assets.append({
                "name": name, "id": index, "state": "uploaded", "size": len(self.content),
            })

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.directory.cleanup()

    def publish(self, assets=None, downloaded=None):
        with patch.object(release_target, "command", side_effect=[
            "", json.dumps({"assets": self.assets if assets is None else assets}),
        ]) as command, patch.object(
            release_target.subprocess, "check_output",
            return_value=self.content if downloaded is None else downloaded,
        ):
            release_target.publish_assets(TAG, "2.2.232", REPO)
            self.assertEqual(command.call_args_list[0].args, (
                "gh", "release", "upload", TAG, *self.names, "--clobber", "--repo", REPO,
            ))

    def test_all_five_downloads_verified(self):
        self.assertEqual(len(self.names), 5)
        self.publish()

    def test_missing_or_empty_file_prevents_any_upload(self):
        for empty in (True, False):
            with self.subTest(empty=empty), patch.object(release_target, "command") as run:
                Path(self.names[0]).write_bytes(b"")
                if not empty:
                    Path(self.names[0]).unlink()
                with self.assertRaisesRegex(ValueError, "Missing or empty"):
                    release_target.publish_assets(TAG, "2.2.232", REPO)
                run.assert_not_called()

    def test_missing_remote_asset_rejected(self):
        with self.assertRaisesRegex(ValueError, "not uploaded correctly"):
            self.publish(assets=self.assets[:-1])

    def test_wrong_remote_size_or_state_rejected(self):
        for changes in ({"size": 0}, {"state": "starter"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "not uploaded correctly"):
                self.publish(assets=[dict(self.assets[0], **changes), *self.assets[1:]])

    def test_corrupted_download_rejected(self):
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.publish(downloaded=b"wrong bytes")

    def test_main_rechecks_sha_before_publication(self):
        with patch.dict(os.environ, {
            "RELEASE_TAG": TAG, "GITHUB_REPOSITORY": REPO,
            "SOURCE_SHA": SHA, "REQUIRE_SOURCE_SHA": "true",
        }), patch("sys.argv", ["release_target.py", "publish"]), patch.object(
            release_target, "resolve_target", side_effect=ValueError("Tag changed"),
        ), patch.object(release_target, "publish_assets") as publish:
            with self.assertRaisesRegex(ValueError, "Tag changed"):
                release_target.main()
            publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
