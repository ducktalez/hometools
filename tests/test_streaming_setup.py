"""Tests for the streaming setup module."""

from pathlib import Path

from hometools.streaming.setup import (
    generate_pycharm_configs,
    streaming_config_table,
)


def test_streaming_config_table_contains_ports(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_AUDIO_PORT", "9000")
    monkeypatch.setenv("HOMETOOLS_VIDEO_PORT", "9001")
    table = streaming_config_table()
    assert "9000" in table
    assert "9001" in table


def test_streaming_config_table_contains_urls(monkeypatch):
    monkeypatch.setenv("HOMETOOLS_STREAM_HOST", "0.0.0.0")
    table = streaming_config_table()
    assert "0.0.0.0" in table
    assert "http://" in table


def test_generate_pycharm_configs_creates_files(tmp_path):
    created = generate_pycharm_configs(tmp_path)

    assert len(created) == 4
    for p in created:
        assert p.exists()

    names = {p.name for p in created}
    assert "serve_all.xml" in names
    assert "serve_audio.xml" in names
    assert "serve_video.xml" in names

    # Individual configs are Python run configurations
    audio_content = (tmp_path / ".idea" / "runConfigurations" / "serve_audio.xml").read_text(encoding="utf-8")
    assert "PythonConfigurationType" in audio_content
    assert "hometools" in audio_content

    # Serve All is a Compound config referencing both servers
    compound_content = (tmp_path / ".idea" / "runConfigurations" / "serve_all.xml").read_text(encoding="utf-8")
    assert "CompoundRunConfigurationType" in compound_content
    assert "Serve Audio" in compound_content
    assert "Serve Video" in compound_content


def test_generate_pycharm_configs_idempotent(tmp_path):
    generate_pycharm_configs(tmp_path)
    first_contents = {
        p.name: p.read_text(encoding="utf-8")
        for p in (tmp_path / ".idea" / "runConfigurations").iterdir()
    }
    generate_pycharm_configs(tmp_path)
    second_contents = {
        p.name: p.read_text(encoding="utf-8")
        for p in (tmp_path / ".idea" / "runConfigurations").iterdir()
    }
    assert first_contents == second_contents

