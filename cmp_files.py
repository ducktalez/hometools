import copy
import yaml
import music_tag

import utils
from print_tools import BColors
from utils import *

p_lut = Path.cwd() / 'wa_data/mp3files_lut.yaml'


def yaml_load(p: Path):
    try:
        with p.open('r') as file:
            loaded = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        loaded = {}
    return loaded


lut = yaml_load(p_lut)


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
            try:
                v.pop(dt)
            except KeyError as ex:
                pass
    with p.open('w') as f:
        yaml.dump(lut, f)


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
    try:
        meta = lut[p.as_posix()]
    except KeyError:
        meta = utils.mediainfo(p)
        for dt in delkeys:
            try:
                meta.pop(dt)
            except KeyError as ex:
                pass
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
            title = 'MISSING'
    return artist, title


def hey_get_all_tracks(p: Path):
    """returns paths"""
    songs_list = get_audio_files_in_folder(p)
    return songs_list


def get_expected_name_from_metainfo(p: Path):
    pass


def hey_get_all_track_sanitations(p: Path, apply=False):
    """returns all tracks in a folder, that have obvious flaws like double space, trailing spaces, ..."""
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
    input('Press Enter to apply all changes.')
    for k, v in change_options.items():
        try:
            k.rename_path(v)
        except FileExistsError as ex:
            print(f'Alert! FileExistsError: {k} {v}')
            input('Ignoring. Press Enter to continue.')


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

        tags = music_tag.load_file(p)
        title = tags['tracktitle']
        artist = tags['artist']
        album = tags['album']
        stem = stem_identifier(pp.name)

        values = {'path': pp,
                 'stem': stem,
                 'suffix': pp.suffix,
                 'size': get_file_size(p),
                 'title': title,
                 'artist': artist,
                 'album': album,
                 'artist-path': artist_f,
                 'title-path': title_f}

        d[values[key]] = values

    return d


def hey_check_audioformat_duplicates(p: Path):
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


def hey_delete_song_dupes(base_dir, new_dir, check_file_size=False):
    """
    Deletes song-dupes in new_dir, if already exists in base_dir
    """

    new_d = dict.fromkeys(get_audio_files_in_folder(new_dir))
    new_d = {stem_identifier(k.name): {'path': k} for k in new_d}

    base_d = dict.fromkeys(get_audio_files_in_folder(base_dir))
    base_d = {stem_identifier(k.name): {'path': k} for k in base_d}
    # Ignore 'new'-entries in 'base' (...if new_dir is inside base_dir)
    base_d = {k: v for k, v in base_d if not k in new_d}

    dupe_names = set(base_d.keys()) & set(new_d.keys())

    if check_file_size:
        for k, v in base_d.items():
            base_d[k]['size'] = get_file_size(v['path'])
        for k, v in new_d.items():
            new_d[k]['size'] = get_file_size(v['path'])
        ignoring_dupes = {x for x in dupe_names if (base_d[x]["size"] != new_d[x]["size"])}
        for x in ignoring_dupes:
            print(f'Ignoring Duplicate with different size: {base_d[x]["size"]} {new_d[x]["size"]} in {x}')
            dupe_names.remove(x)

    print(f'Found these dupes:')
    for d in dupe_names:
        print(d)

    del_paths = [new_d[n]['path'] for n in dupe_names]

    for p in del_paths:
        print(f'Moving {p.name}: {p} to {DEL_FOLDER_DUMMY / p.name}')
    input(f'Press Enter to move those files to {DEL_FOLDER_DUMMY}.')
    attention_deleting_files(del_paths, DEL_FOLDER_DUMMY)


def hey_find_all_dupes(dir: Path, delete_dupes=False):
    """Finds dupes, if the song file names are equal, but in different folders.
    Sanitize Names first!"""

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
    C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao - Combat Circus.mp3
    C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao.mp3
    """
    tracks_list = hey_get_all_tracks(dir)
    for p in tracks_list:
        tags = music_tag.load_file(p)
        title = tags['tracktitle']
        artist = tags['artist']
        album = tags['album']
        bad_stem = f'{artist} - {title} - {album}'
        bad_stem = sanitize_track_to_path(bad_stem)
        if p.stem == bad_stem:
            p_change = p.parent / f'{artist} - {title}{p.suffix}'
            # rename_dict[p] = p_change
            user_rename_file(p, p_change)


if __name__ == '__main__':
    p = Path("C:/Users/Simon/Music/GETINHERE/")
    # hey_delete_song_dupes(Path('C:/Users/Simon/Music/Audials'), Path('C:/Users/Simon/Desktop/DELETE'), check_file_size=True)
    # todo debug check, if folder2 is inside folder1. remove those files from the list.
    # hey_get_all_track_sanitations(Path('C:/Users/Simon/Music/GETINHERE'))
    # hey_sanitize_all_track_names(Path('C:/Users/Simon/Music/GETINHERE/Simons Musik'))
    # hey_remove_album_in_pathname(Path("C:/Users/Simon/Music/GETINHERE/Simons Musik/"))
    # hey_find_all_dupes(Path("C:/Users/Simon/Music/GETINHERE/Simons Musik/"))
    hey_check_audioformat_duplicates(p)
