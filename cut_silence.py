from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from pathlib import Path
import logging
import subprocess
import numpy as np
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, POPM
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3
import matplotlib.pyplot as plt
import librosa
import librosa.beat
from mutagen import File

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def plot_waveform(p: Path, trimmed_p: Path):
    """Zeigt die Waveform des Original- und des bearbeiteten Audios an, fokussiert auf die Schnittstellen."""
    original = AudioSegment.from_file(p)
    trimmed = AudioSegment.from_file(trimmed_p)

    original_samples = np.array(original.get_array_of_samples())
    trimmed_samples = np.array(trimmed.get_array_of_samples())

    zoom_range = 5000  # Anzahl der Samples um den Schnittbereich herum

    plt.figure(figsize=(12, 6))

    # Zoom auf den Anfang der Bearbeitung
    plt.subplot(2, 1, 1)
    plt.plot(original_samples[:zoom_range], color='blue', label='Original')
    plt.plot(trimmed_samples[:zoom_range], color='red', label='Bearbeitet', alpha=0.7)
    plt.title("Waveform (Zoom auf Anfang)")
    plt.legend()

    # Zoom auf das Ende der Bearbeitung
    plt.subplot(2, 1, 2)
    plt.plot(original_samples[-zoom_range:], color='blue', label='Original')
    plt.plot(trimmed_samples[-zoom_range:], color='red', label='Bearbeitet', alpha=0.7)
    plt.title("Waveform (Zoom auf Ende)")
    plt.legend()

    plt.tight_layout()
    plt.show()


def analyze_bpm(p: Path):
    """Analysiert die BPM eines Tracks und speichert den Wert in den Metadaten."""
    y, sr = librosa.load(p, sr=None)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = round(tempo[0])  # BPM auf ganze Zahl runden

    ext = p.suffix.lower()
    if ext == ".mp3":
        audio = MP3(p, ID3=EasyID3)
    elif ext == ".flac":
        audio = FLAC(p)
    elif ext in [".m4a", ".mp4"]:
        audio = MP4(p)
    else:
        logging.warning(f"Nicht unterstütztes Format für BPM-Speicherung: {p}")
        return

    audio["bpm"] = str(bpm)
    audio.save()
    logging.info(f"BPM ({bpm}) in Metadaten für {p.name} gespeichert.")


def get_audio_length(p: Path):
    """Hilfsfunktion, um die Länge der Audiodatei in Sekunden mit ffprobe zu ermitteln."""
    cmd = ["ffprobe", "-i", str(p), "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        logging.error(f"Konnte die Länge der Datei {p.name} nicht bestimmen.")
        return 0


def trim_audio_fixed_duration(p: Path, start_trim_ms: int = 0, end_trim_ms: int = 0, overwrite=False):
    """Schneidet eine feste Anzahl Millisekunden vom Anfang & Ende mit FFmpeg, ohne Qualitätsverlust.

    Args:
        p (Path): Die zu bearbeitende Audiodatei.
        start_trim_ms (int): Anzahl der zu entfernenden Millisekunden am Anfang.
        end_trim_ms (int): Anzahl der zu entfernenden Millisekunden am Ende.
        overwrite (bool): Falls True, wird die Originaldatei überschrieben, sonst wird "-ffmpeg" angehängt.
        output_folder (str, optional): Falls angegeben, wird die Datei in diesem Unterordner gespeichert.
    """

    # Berechnungen in Sekunden für FFmpeg
    start_trim_sec = start_trim_ms / 1000
    audio_length_sec = get_audio_length(p)  # Hilfsfunktion, um die Länge der Datei zu bestimmen
    end_trim_sec = max(0.0, audio_length_sec - (end_trim_ms / 1000))  # Sicherstellen, dass die Endzeit nicht negativ ist

    if start_trim_sec >= end_trim_sec:
        logging.warning(f"Fehler: Die gewählten Start-/Endzeiten sind zu lang für {p.name}. Datei bleibt unverändert.")
        return
    else:
        new_path = p if overwrite else p.with_stem(p.stem + "-ffmpeg")

        cmd = [
            "ffmpeg", "-i", str(p),
            "-c:a", "copy", "-ss", str(start_trim_sec), "-to", str(end_trim_sec),
            str(new_path), "-y" if overwrite else "-n"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Prüfen, ob FFmpeg tatsächlich geschnitten hat
        if "Output file is empty" in result.stderr:
            logging.warning(f"Keine Änderungen für {p.name}, Datei wird nicht gespeichert.")
            return

        logging.info(f"Fixe Stille entfernt mit FFmpeg und gespeichert als: {new_path}")

def read_all_tags(p: Path):
    """Liest alle Tags als Dictionary."""
    audio = File(p)
    if audio is None or not hasattr(audio, "tags") or audio.tags is None:
        return {}
    return dict(audio.tags)

def write_all_tags(p: Path, tags: dict):
    """Schreibt alle Tags aus einem Dictionary zurück."""
    audio = File(p)
    if audio is None:
        logging.error(f"Datei {p.name} konnte nicht gelesen werden.")
        return False
    if audio.tags is None:
        audio.add_tags()
    for key, value in tags.items():
        audio.tags[key] = value
    audio.save()
    logging.info(f"Metadaten in {p.name} wiederhergestellt.")
    return True

def get_popm_rating(p: Path):
    """
    Liest das `POPM`-Tag aus einer MP3-Datei.
    Gibt eine Bewertung als (0–255, 0–5 Sterne) zurück.
    """
    try:
        audio = MP3(p, ID3=ID3)
        popm_tags = audio.tags.getall("POPM")
        if not popm_tags:
            logging.warning(f"Keine Bewertung (POPM) für {p.name} gefunden.")
            return 0, 0

        rating_raw = popm_tags[0].rating  # Wert 0–255
        return rating_raw

    except Exception as e:
        logging.error(f"Fehler beim Lesen von {p.name}: {e}")
        return 0

def set_popm_rating(p: Path, rating: int, email: str = "default", playcount: int = 0):
    """
    Setzt das `POPM`-Rating einer MP3-Datei.

    Parameter:
    - p: Pfad zur MP3-Datei
    - rating: Bewertung (je nach Modus 0–5 oder 0–255)
    - mode: "stars" (Standard) oder "raw"
    - email: Identifikator im POPM-Frame (Standard: "default")
    - playcount: Optionaler Zähler für Abspielhäufigkeit
    """
    try:
        if not (0 <= rating <= 255):
            raise ValueError("Raw-Rating muss zwischen 0 und 255 liegen.")
        rating_raw = rating

        audio = MP3(p, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        popm = POPM(email=email, rating=rating_raw, count=playcount)
        audio.tags.setall("POPM", [popm])
        audio.save()

        logging.info(f"{p.name}: Bewertung gesetzt auf {rating_raw}")
        return True

    except Exception as e:
        logging.error(f"Fehler beim Schreiben von {p.name}: {e}")
        return False

import subprocess
from pathlib import Path
import logging

def split_mp3_lossless(p: Path, start_sec: float, end_sec: float, overwrite=False):
    """
    todo dieses verwenden
    Verwendet mp3splt, um verlustfrei ein MP3 zu schneiden (nur auf Framegrenzen möglich).

    Args:
        p (Path): Eingabedatei (muss .mp3 sein)
        start_sec (float): Startzeit in Sekunden
        end_sec (float): Endzeit in Sekunden
        overwrite (bool): Ob Originaldatei überschrieben wird (standard: False)
    """
    if p.suffix.lower() != ".mp3":
        logging.error(f"Nur MP3-Dateien werden unterstützt, nicht {p.suffix}")
        return

    output = p if overwrite else p.with_stem(p.stem + "-split")

    # mp3splt erwartet Zeitangaben im Format MM.SS oder HH.MM.SS
    def format_time(sec):
        minutes = int(sec // 60)
        seconds = sec % 60
        return f"{minutes}.{seconds:06.3f}"

    start_formatted = format_time(start_sec)
    end_formatted = format_time(end_sec)

    cmd = [
        "mp3splt", "-f", "-o", output.stem, "-d", str(output.parent),
        str(p), start_formatted, end_formatted
    ]

    logging.info(f"Schneide {p.name} verlustfrei: {start_formatted} bis {end_formatted}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        logging.error(f"Fehler beim Schneiden: {result.stderr}")
    else:
        logging.info(f"Erfolg: Datei gespeichert unter {output.with_suffix('.mp3')}")



def remove_silence_with_ffmpeg(p: Path, overwrite=False, save_difference_flag=False, silence_thresh=-75):
    """Verwendet pydub zur Analyse und FFmpeg zum Schneiden ohne Rekodierung, speichert optional die entfernte Stille."""
    if "-ffmpeg" in p.stem or "-removed" in p.stem:
        logging.info(f"Überspringe Datei {p.name}, da sie bereits verarbeitet wurde.")
        return

    audio = AudioSegment.from_file(p)
    nonsilent_parts = detect_nonsilent(audio, silence_thresh=silence_thresh, seek_step=10)
    start_trim = max(0, nonsilent_parts[0][0] - 200)  # Leichten Puffer einfügen
    end_trim = min(len(audio), nonsilent_parts[-1][1] + 1500)

    # Prüfen, ob FFmpeg wirklich etwas geschnitten hat
    if (not nonsilent_parts) or (start_trim == 0 and end_trim == len(audio)):
        logging.info(f"Keine Änderungen für {p.name}, Datei wird nicht gespeichert.")
        return

    # popm_value = get_popm_rating(p)  # TODO # todo wird nicht korrekt befüllt, metadaten rating geht verloren...
    # tags = read_all_tags(p)

    if overwrite:
        p_source = p.rename(p.with_stem(p.stem + "-ffmpeg-original"))  # safety-copy
        p_new = p
    else:
        p_source = p
        p_new = p.with_stem(p.stem + "-ffmpeg")
    # todo tutorial with mp3splthttps://sourceforge.net/projects/mp3splt/files/latest/download
    #     sudo apt install mp3splt
    #     # oder
    #     brew install mp3splt
    cmd = [
        "ffmpeg", "-i", str(p_source),
        "-c:a", "copy",
        "-map_metadata", "0",
        # "-metadata", f"rating={popm_value}",
        "-ss", str(start_trim / 1000),
        "-to", str(end_trim / 1000 + 0.5),
        str(p_new)
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Prüfen, ob FFmpeg wirklich etwas geschnitten hat
    if "Output file is empty" in result.stderr:
        logging.info(f"Keine Änderungen für {p.name}, Datei wird nicht gespeichert.")
        return
    logging.info(f"Stille entfernt mit FFmpeg und gespeichert als: {p_new}")
    # write_all_tags(p_new, tags)

    if save_difference_flag:
        removed_audio = audio[:start_trim] + audio[end_trim:]
        removed_path = p.with_stem(p.stem + "-ffmpeg-removed")
        if p.suffix.lower() == ".m4a":
            removed_audio.export(removed_path, format="mp4", parameters=["-c:a", "aac"])
        else:
            removed_audio.export(removed_path, format=p.suffix[1:])
        logging.info(f"Entfernte Stille gespeichert als: {removed_path}")


def process_audio_folder(folder: Path, overwrite=False, save_difference_wav=False, silence_thresh=-75):
    """Durchläuft alle Audiodateien in einem Ordner und entfernt Stille."""
    for file in folder.glob("*.*"):
        if file.suffix.lower() in [".mp3", ".flac", ".m4a",
                                   ".wav"] and "-ffmpeg" not in file.stem and "-removed" not in file.stem:
            remove_silence_with_ffmpeg(file, overwrite=overwrite, save_difference_flag=save_difference_wav,
                                       silence_thresh=silence_thresh)
            # analyze_bpm(file)  # todo


audio_folder = Path("C:/Users/Simon/Music/Audials/Audials Music/test")
process_audio_folder(audio_folder, overwrite=False, save_difference_wav=False)

