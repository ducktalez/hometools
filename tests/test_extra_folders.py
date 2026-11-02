"""Extra library folders (video): storage, catalog merge, streaming, API."""

from __future__ import annotations

from pathlib import Path

import pytest

from hometools.streaming.core.extra_folders import (
    add_extra_folder,
    extra_roots,
    list_extra_folders,
    remove_extra_folder,
    split_extra_path,
)
from hometools.streaming.video.catalog import build_video_index, collect_thumbnail_work


@pytest.fixture()
def dirs(tmp_path: Path):
    lib = tmp_path / "lib"
    (lib / "Main Series").mkdir(parents=True)
    (lib / "Main Series" / "S01E01.mp4").write_bytes(b"\0" * 32)
    extra = tmp_path / "elsewhere" / "Filme"
    (extra / "Doku").mkdir(parents=True)
    (extra / "Doku" / "a.mp4").write_bytes(b"\0" * 32)
    (extra / "loose.mp4").write_bytes(b"\0" * 32)
    cache = tmp_path / "cache"
    cache.mkdir()
    return lib, extra, cache


def test_add_list_remove(dirs):
    lib, extra, cache = dirs
    entry = add_extra_folder(cache, "video", str(extra), library_dir=lib)
    assert entry is not None and entry["alias"] == "Filme"
    assert list_extra_folders(cache, "video") == [entry]
    assert add_extra_folder(cache, "video", str(extra), library_dir=lib) is None  # duplicate
    assert remove_extra_folder(cache, "video", "Filme") is True
    assert list_extra_folders(cache, "video") == []
    assert remove_extra_folder(cache, "video", "Filme") is False


def test_add_rejects_invalid(dirs):
    lib, extra, cache = dirs
    assert add_extra_folder(cache, "video", str(extra / "nope"), library_dir=lib) is None
    assert add_extra_folder(cache, "video", "", library_dir=lib) is None
    assert add_extra_folder(cache, "video", str(lib), library_dir=lib) is None
    assert add_extra_folder(cache, "video", str(lib / "Main Series"), library_dir=lib) is None


def test_alias_unique(dirs, tmp_path):
    lib, extra, cache = dirs
    other = tmp_path / "x" / "Filme"
    other.mkdir(parents=True)
    a = add_extra_folder(cache, "video", str(extra), library_dir=lib)
    b = add_extra_folder(cache, "video", str(other), library_dir=lib)
    assert a and b and a["alias"] != b["alias"]


def test_split_extra_path(dirs):
    lib, extra, cache = dirs
    add_extra_folder(cache, "video", str(extra), library_dir=lib)
    roots = extra_roots(cache, "video")
    assert split_extra_path("Filme/Doku/a.mp4", roots) == (roots["Filme"], "Doku/a.mp4")
    assert split_extra_path("Main Series/S01E01.mp4", roots) is None


def test_index_includes_extra(dirs):
    lib, extra, cache = dirs
    add_extra_folder(cache, "video", str(extra), library_dir=lib)
    items = {i.relative_path: i for i in build_video_index(lib, cache_dir=cache)}
    assert set(items) == {"Main Series/S01E01.mp4", "Filme/Doku/a.mp4", "Filme/loose.mp4"}
    assert items["Filme/Doku/a.mp4"].artist == "Doku"
    assert items["Filme/loose.mp4"].artist == "Filme"
    assert "path=Filme" in items["Filme/Doku/a.mp4"].stream_url
    work = collect_thumbnail_work(lib, cache)
    assert {w[3] for w in work} == set(items)


def test_api_roundtrip_and_stream(dirs):
    from fastapi.testclient import TestClient

    from hometools.streaming.video.server import create_app

    lib, extra, cache = dirs
    client = TestClient(create_app(lib, cache_dir=cache, audit_dir=cache / "audit", safe_mode=True))
    assert client.get("/api/video/folders").json() == {"items": []}
    assert client.post("/api/video/folders", json={"path": str(extra / "nope")}).status_code == 422
    r = client.post("/api/video/folders", json={"path": str(extra)})
    assert r.status_code == 200 and r.json()["folder"]["alias"] == "Filme"
    assert client.get("/video/stream", params={"path": "Filme/Doku/a.mp4"}).status_code != 404
    assert client.get("/video/stream", params={"path": "Filme/../../lib/Main Series/S01E01.mp4"}).status_code in (400, 404)
    assert client.delete("/api/video/folders", params={"alias": "Filme"}).status_code == 200
    assert client.delete("/api/video/folders", params={"alias": "Filme"}).status_code == 404
    assert client.get("/video/stream", params={"path": "Filme/Doku/a.mp4"}).status_code == 404
