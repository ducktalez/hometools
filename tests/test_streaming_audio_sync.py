"""Tests for manual audio sync planning and execution."""

from hometools.streaming.audio.sync import plan_audio_sync, sync_audio_library


def test_plan_audio_sync_includes_missing_audio_files_only(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    (source / "Artist - Track.mp3").write_text("audio")
    (source / "ignore.txt").write_text("not-audio")

    operations = plan_audio_sync(source, target)

    assert len(operations) == 1
    assert operations[0].reason == "missing"
    assert operations[0].destination.name == "Artist - Track.mp3"


def test_plan_audio_sync_marks_changed_size(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    (source / "Artist - Track.mp3").write_text("audio-new")
    (target / "Artist - Track.mp3").write_text("old")

    operations = plan_audio_sync(source, target)

    assert len(operations) == 1
    assert operations[0].reason == "size-changed"


def test_sync_audio_library_copies_files(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()

    album_dir = source / "Album"
    album_dir.mkdir()
    source_file = album_dir / "Artist - Track.mp3"
    source_file.write_text("audio")

    operations = sync_audio_library(source, target)
    copied_file = target / "Album" / "Artist - Track.mp3"

    assert len(operations) == 1
    assert copied_file.exists()
    assert copied_file.read_text() == "audio"


def test_sync_audio_library_dry_run_does_not_copy(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()

    (source / "Artist - Track.mp3").write_text("audio")

    operations = sync_audio_library(source, target, dry_run=True)

    assert len(operations) == 1
    assert not (target / "Artist - Track.mp3").exists()

