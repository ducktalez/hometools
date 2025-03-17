import copy
import inspect

import yaml
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3

import utils
from utils import *
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("hometools.log"),
        logging.StreamHandler()
    ]
)

p_lut = Path.cwd() / 'wa_data/mp3files_lut.yaml'


def yaml_load(p: Path):
    try:
        with p.open('r', encoding='utf-8') as file:
            return yaml.load(file, Loader=yaml.FullLoader) or {}
    except FileNotFoundError:
        logging.warning(f"YAML file not found: {p}")
        return {}


lut = yaml_load(p_lut)


def get_audio_metadata(file_path: Path):
    try:
        audio = EasyID3(file_path)
        metadata = {
            "title": audio.get("title", ["Unknown"])[0],
            "artist": audio.get("artist", ["Unknown"])[0],
            "album": audio.get("album", ["Unknown"])[0],
            "genre": audio.get("genre", ["Unknown"])[0]
        }
        return metadata
    except Exception as e:
        print(f"Error reading metadata from {file_path}: {e}")
        return None


def audiofiles_meta_yaml_dump(p: Path, lut):
    delkeys = ['DISPOSITION',
               'codec_name', 'avg_frame_rate', 'bits_per_raw_sample', 'bits_per_sample', 'channel_layout', 'channels',
               'chroma_location', 'closed_captions', 'codec_long_name', 'codec_tag', 'codec_tag_string', 'codec_type',
               'coded_height', 'coded_width', 'color_primaries', 'color_range', 'color_space', 'color_transfer',
               'display_aspect_ratio', 'duration_ts', 'field_order', 'filename', 'film_grain', 'format_long_name',
               'format_name', 'has_b_frames', 'height', 'id', 'index', 'initial_padding', 'level', 'max_bit_rate',
               'nb_frames', 'nb_programs', 'nb_read_frames', 'nb_read_packets', 'nb_streams', 'pix_fmt', 'probe_score',
               'profile', 'r_frame_rate', 'refs', 'sample_aspect_ratio', 'sample_fmt', 'start_pts', 'time_base',
               'width']
    for k, v in lut.items():
        for dt in delkeys:
            v.pop(dt, None)  # Verhindert KeyError

    with p.open('w', encoding='utf-8') as f:
        yaml.dump(lut, f, allow_unicode=True)


def stem_identifier(stem):
    """

    Ignored Ideas:
     - Check for 'introducing', „present(s)“, „introducing“, „duet with“
    Special cases:
     - shortest artists: 'JJ - Still', shortest filename 'ss.mp3'
     - Interprets: frei.wild Mollono.Bass, no_4mat
    """
    # *************************************************************************** #
    # NORMALIZATION
    stem_normed = stem
    # === save replaces ===
    stem_normed = re.sub('&amp;', '&', stem_normed)
    stem_normed = re.sub(r'\(152kbit_Opus\)|\(\d{1,3}kbit\_[A-Za-z]+\)', '', stem_normed, flags=re.IGNORECASE)
    stem_normed = re.sub(r'\(Official.{0,8}Video\)', '', stem_normed, flags=re.IGNORECASE)
    # removing links from file
    stem_normed = re.sub(r'\(\w*\.[a-zA-Z]{2,5}\)', '', stem_normed, flags=re.IGNORECASE)
    stem_normed = re.sub(r'\w*\.(?:com|net|org|co.uk|de|vu|ru|pl)', '', stem_normed, flags=re.IGNORECASE)
    stem_normed = re.sub(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U00002702-\U000027B0\U000024C2-\U0001F251"
                 u"\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
                 u"\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+", '', stem_normed, flags=re.IGNORECASE)
    # Unifying artist combinations
    stem_normed = re.sub(r'(?<=\W)(featuring|feat\.|feat|ft\.|ft)\W', 'feat. ', stem_normed, flags=re.IGNORECASE)
    stem_normed = re.sub(r'(?<=\W)(produced by|produced|prod\. by|prod by|prod\.|prod)\W', 'prod. ', stem_normed,
                 flags=re.IGNORECASE)
    stem_normed = re.sub(r'(?<=(\W|\(|\[))(vs\.|vs|versus)', 'vs. ', stem_normed, flags=re.IGNORECASE)
    stem_normed = re.sub(r'(?<=\W)(^ )', ' ', stem_normed, flags=re.IGNORECASE)
    re.sub(r'\([^\)]*\)|\[[^\]]*\]', '', stem_normed)
    stem_normed = re.sub(r' ( )+', ' ', stem_normed)
    stem_normed = re.sub(r'^ +| +$', '', stem_normed)
    return stem_normed


def audiofile_get_meta(p: Path):
    delkeys = ['DISPOSITION',
               'codec_name', 'avg_frame_rate', 'bits_per_raw_sample', 'bits_per_sample', 'channel_layout', 'channels',
               'chroma_location', 'closed_captions', 'codec_long_name', 'codec_tag', 'codec_tag_string', 'codec_type',
               'coded_height', 'coded_width', 'color_primaries', 'color_range', 'color_space', 'color_transfer',
               'display_aspect_ratio', 'duration_ts', 'field_order', 'filename', 'film_grain', 'format_long_name',
               'format_name', 'has_b_frames', 'height', 'id', 'index', 'initial_padding', 'level', 'max_bit_rate',
               'nb_frames', 'nb_programs', 'nb_read_frames', 'nb_read_packets', 'nb_streams', 'pix_fmt', 'probe_score',
               'profile', 'r_frame_rate', 'refs', 'sample_aspect_ratio', 'sample_fmt', 'start_pts', 'time_base',
               'width']
    if p.as_posix() in lut:
        meta = {k: v for k, v in lut[p.as_posix()].items() if k not in delkeys}
    else:
        meta = utils.mediainfo(p)
        meta = {k: v for k, v in meta.items() if k not in delkeys}
        lut[p.as_posix()] = meta

    return meta


def split_stem(p: Path, min_length=2):
    split = re.split(r"feat\."
                     r"|prod\."
                     r"|vs\."
                     r"|\(|\["
                     r"| - "
                     r"|, "
                     r"| & "
                     r"|\)|\]", stem_identifier(p.stem), flags=re.IGNORECASE)
    split = [repath_fix_spaces(i) for i in split]

    split = [i for i in split if len(i) >= min_length]
    # print(f'{split}\t{p.name}')
    return split


def split_extreme(p: Path, min_length=3):
    split = split_stem(p, min_length=min_length)
    splitSSS = [re.sub(r'original'
                       r'|Official'
                       r'|Extended'
                       r'|Radio'
                       r'|vocal'
                       r'|edit'
                       r'|remix'
                       r'|mix'
                       r'|version'
                       r'|release', '', i, flags=re.IGNORECASE) for i in split]
    splitSSS = [re.sub(r'\W|_', '', i) for i in splitSSS]
    # print(f'{splitSSS}\n{p}')
    splitSSS = [i for i in set(splitSSS) if len(i) > min_length]
    return splitSSS


def audiofile_assume_artist_title(p: Path):
    """
    Assuming artist and title only given the file-name.
    Music files should usually be named 'Artist - Title.mp3'
    """
    split = split_stem(p)

    try:
        artist = lut[p.as_posix()]['TAG']['artist']
        artist = re.sub('\| - Topic', '', artist)  # youtube-music artist
    except KeyError:
        artist = split[0]

    try:
        title = lut[p.as_posix()]['TAG']['title']
    except KeyError:
        try:
            title = split[1]
        except Exception as ex:
            print(f'FUCKIN UGLY: {p}')
            # still open: sanitize C:\Users\Simon\Music\GETINHERE\Partycrew\Sean Paul -Temperature.mp3
            title = 'MISSING'
    return artist, title


def hey_get_all_tracks(p: Path):
    """returns paths"""
    songs_list = get_audio_files_in_folder(p)
    return songs_list


def get_expected_name_from_metainfo(p: Path):
    pass


def hey_get_all_track_sanitations(p: Path, apply=False):
    """returns all tracks in a folder, that have obvious flaws like double space, trailing spaces, ...

    TODO 05.02.2025
        XV - Pictures On My Wall [Prod. By Seven]
        XV - Pictures On My Wall [prod. Seven]
    """
    songs_list = hey_get_all_tracks(p)

    name_changes = {}
    for track in songs_list:
        stem0 = track.stem
        stem1 = stem_identifier(stem0)
        if stem0 != stem1:
            print(stem0)
            print(stem1)
        else:
            pass


def remove_ugly_spaces(s):
    s = re.sub(r' ( )+', ' ', s)
    s = re.sub(r'^ +| +$', '', s)
    return s


def remove_ugly_dots(s):
    return s


def hey_sanitize_all_track_names(dir: Path):
    """Sanitizing music file names, replacing...
    - doublespaces
    - leading spaces
    - trailing spaces
    - "&amp"
    """
    logging.info(f"Starting function: {inspect.currentframe().f_code.co_name}")
    tracks_list = hey_get_all_tracks(dir)
    change_options = {}
    for p in tracks_list:
        stem = p.stem
        stem = re.sub(r' ( )+', ' ', stem)
        stem = re.sub(r'^ +| +$', '', stem)
        stem = re.sub('&amp;', '&', stem)
        if stem != p.stem:
            print(f'{p.name}\n{stem}{p.suffix}')
            change_options[p] = p.parent / f'{stem}{p.suffix}'
    for k, v in change_options.items():
        print(f'{k}\n{v}')
    x = input('Sanitizing track names? Press Enter to apply all changes.')
    if x == '':
        for k, v in change_options.items():
            try:
                rename_path(k, v)  # k.rename(v)  <- direct approach
            except FileExistsError as ex:
                print(f'Alert! FileExistsError: {k} {v}')
                input('Ignoring. Press Any to continue.')
    else:
        print(f'Skipped!')


def sanitize_track_to_path(s):
    """
    'Queen - Fat Bottomed Girls - Single Version \ Remastered 2011.mp3'
    'Queen - Fat Bottomed Girls - Single Version _ Remastered 2011.mp3'
    """
    s0 = copy.deepcopy(s)
    s = re.sub(r'AC/DC', 'ACDC', s)  # <.<
    s = re.sub(r'"', '', s)  # e.g. (from "Star Wars")
    s = re.sub(r'/', '_', s)
    s = re.sub(r'\\', '_', s)
    s = re.sub(r'<', '_', s)
    s = re.sub(r'>', '_', s)
    s = re.sub(r':', '_', s)
    s = re.sub(r'\|', '_', s)
    s = re.sub(r'\?', '_', s)
    s = re.sub(r'\*', '_', s)
    s = stem_identifier(s)  # removing spaces
    if s0 != s:
        pass  # now you know why
    return s


def get_audio_dict(p: Path, suffix=None, key='path'):
    d = {}
    for pp in get_files_in_folder(p, suffix_accepted=suffix):
        artist_f, title_f = audiofile_assume_artist_title(pp)

        ext = pp.suffix.lower()
        try:
            if ext == ".mp3":
                audio = MP3(pp, ID3=EasyID3)
            elif ext == ".flac":
                audio = FLAC(pp)
            elif ext in [".m4a", ".mp4"]:
                audio = MP4(pp)
            else:
                logging.warning(f"Nicht unterstütztes Format: {ext}")
                continue

            title = audio.tags.get("title", ["Unknown"])[0]
            artist = audio.tags.get("artist", ["Unknown"])[0]
            album = audio.tags.get("album", ["Unknown"])[0]

            stem = stem_identifier(pp.name)

            values = {
                'path': pp,
                'stem': stem,
                'suffix': pp.suffix,
                'size': get_file_size(pp),
                'title': title,
                'artist': artist,
                'album': album,
                'artist-path': artist_f,
                'title-path': title_f
            }

            d[values[key]] = values
        except Exception as e:
            logging.error(f"Fehler beim Lesen von {pp}: {e}")

    return d


def hey_check_audioformat_duplicates(p: Path):
    logging.info(f"Starting function: {inspect.currentframe().f_code.co_name}")
    wav_d = get_audio_dict(p, suffix=AUDIO_LOSSLESS_SUFFIX, key='stem')
    mp3_d = get_audio_dict(p, suffix=AUDIO_LOSS_SUFFIX, key='stem')

    # wav_d = {k: v | {'mp3-match': k in mp3_d} for k, v in wav_d.items()}
    missing_converts = []
    for k, v in wav_d.items():
        if k in mp3_d:
            pass
        else:
            missing_converts.append(v['path'])

    pass


def hey_delete_song_dupes(main_dir: Path, new_dir: Path, check_file_size=False, dry_run=True):
    logging.info(f"Starting function: {inspect.currentframe().f_code.co_name}")
    main_tracks = {stem_identifier(p.name): p for p in get_audio_files_in_folder(main_dir)}
    new_tracks = {stem_identifier(p.name): p for p in get_audio_files_in_folder(new_dir)}

    duplicates = set(main_tracks.keys()) & set(new_tracks.keys())

    if check_file_size:
        size_mismatch = {t for t in duplicates if get_file_size(main_tracks[t]) != get_file_size(new_tracks[t])}
        duplicates -= size_mismatch
        if size_mismatch:
            logging.warning(f"Ignoring {len(size_mismatch)} duplicates with different sizes.")

    print("Found duplicates:")
    for d in duplicates:
        print(f" - {new_tracks[d]}")

    if dry_run:
        pass
    else:
        for d in duplicates:
            try:
                new_tracks[d].unlink()  # Datei löschen
                logging.info(f"Deleted duplicate: {new_tracks[d]}")
            except Exception as e:
                logging.error(f"Failed to delete {new_tracks[d]}: {e}")


def hey_find_all_dupes(dir: Path, delete_dupes=False):
    """Finds dupes, if the song file names are equal, but in different folders.
    Sanitize Names first!"""
    logging.info(f"Starting function: {inspect.currentframe().f_code.co_name}")

    # load all track-paths in list
    tracks_list = hey_get_all_tracks(dir)
    dupes_dict = {x.stem: [] for x in tracks_list}

    for p in tracks_list:
        dupes_dict[p.stem].append({'path': p, 'size': get_file_size(p)})

    dupes_dict = {k: v for k, v in dupes_dict.items() if len(v) > 1}

    if delete_dupes:
        for k, v in dupes_dict.items():
            v = sorted(v, key=lambda key: key['size'], reverse=True)
            if v[0] == v[-1]:
                print(f'Found {len(v)} duplicates with same size for {k}.')
            else:
                print(f'Found {len(v)} duplicates with different size {k}: {[x["size"] for x in v]} {[x["path"].as_posix() for x in v]}')
            del_list = v[1:]
            s = '\n'.join([f'{x["path"].as_posix()} ({x["size"]})' for x in del_list])
            print(f'Keeping only: \n'
                  f'{v[0]["path"].as_posix()} (size {v[0]["size"]})\n'
                  f'Removing:\n'
                  f'{s}')
            for x in del_list:
                deleting_file(x['path'])
    else:
        print(delete_dupes)


def hey_remove_album_in_pathname(dir: Path):
    """
    Entfernt das Album aus dem Dateinamen, falls es redundant ist.
    Beispiel:
    C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao - Combat Circus.mp3
    wird zu:
    C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao.mp3
    """
    logging.info(f"Starting function: {inspect.currentframe().f_code.co_name}")
    tracks_list = hey_get_all_tracks(dir)

    for p in tracks_list:
        ext = p.suffix.lower()
        try:
            if ext == ".mp3":
                audio = MP3(p, ID3=EasyID3)
            elif ext == ".flac":
                audio = FLAC(p)
            elif ext in [".m4a", ".mp4"]:
                audio = MP4(p)
            else:
                logging.warning(f"Nicht unterstütztes Format: {ext}")
                continue

            title = audio.tags.get("title", [None])[0] or "Unknown"
            artist = audio.tags.get("artist", [None])[0] or "Unknown"
            album = audio.tags.get("album", [None])[0] or "Unknown"

            bad_stem = sanitize_track_to_path(f"{artist} - {title} - {album}")
            correct_stem = sanitize_track_to_path(f"{artist} - {title}")

            if p.stem == bad_stem:
                p_change = p.with_name(f"{correct_stem}{p.suffix}")
                user_rename_file(p, p_change)
                logging.info(f"Datei umbenannt: {p.name} -> {p_change.name}")
        except Exception as e:
            logging.error(f"Fehler beim Verarbeiten von {p}: {e}")



if __name__ == '__main__':
    p = Path("C:/Users/Simon/Music/GETINHERE/")
    # hey_sanitize_all_track_names(Path('C:/Users/Simon/Music/GETINHERE'))
    hey_delete_song_dupes(Path('C:/Users/Simon/Music/GETINHERE'), Path('C:/Users/Simon/Music/Audials'), dry_run=False)
    # todo debug check, if folder2 is inside folder1. remove those files from the list.
    # hey_get_all_track_sanitations(Path('C:/Users/Simon/Music/GETINHERE'))
    hey_remove_album_in_pathname(Path("C:/Users/Simon/Music/GETINHERE"))
    hey_find_all_dupes(p, delete_dupes=True)
    hey_check_audioformat_duplicates(p)
