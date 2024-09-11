import copy
import re
from pathlib import Path
import yaml
# from mutagen.id3 import ID3
import music_tag

from print_tools import BColors

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


# # *************************************************************************** #
# # def stem_guess_parentheses_info(stem):
# parentheses_infos = re.findall(r'\([^\)]*\)|\[[^\]]*\]', stem_normed)
# if parentheses_infos:
#     # print(f'{parentheses_infos}, at \t{stem_normed}')
#     for klinfo in parentheses_infos:
#         klinfo = klinfo[1:-1]
#         if re.match(r'^feat\. ', klinfo):
#             klinfo.replace('feat. ', '')
#             print(f'feature info: {klinfo}')
#         if re.match(' (radio|original|edit|cover|version)$', klinfo):
#             klinfo = re.sub(' (mix|remix|edit|cover)$', '', klinfo)
#             print(f'MIX                  dsfg: {klinfo}')
#         if re.match(' (remix|mix|edit|cover|version)$', klinfo):
#             klinfo = re.sub(' (mix|remix|edit|cover)$', '', klinfo)
#             print(f'MIX                  dsfg: {klinfo}')
#         # '"by" ___'
#         # extended
#
#         # ['[DnB]'], at [DnB] - Feint - We Wo
#         # n't Be Alone feat. Laura Brehm) [Monstercat edit
#
#         # -> leading '.feat'
#         # -> trailing 'remix', 'mix', 'edit'
#
# # print(f'{test[:-1]} \t{test[-1]}')
#
# v1 = re.findall(r'(?:\(|\[)\w+ (?:radio|original|edit|cover|version).{0,14}(?:\)|\])', stem_normed, flags=re.IGNORECASE)


def get_audiopaths_in_folder(p: Path, print_non_audio=False):
    """Returns a path-list of all music files"""
    f_all = [f for f in p.rglob(f'*') if f.is_file()]

    audio_suffix = ['.mp3', '.m4a', '.ogg', '.opus', '.flac', '.aac', '.wav', '.aif', '.aiff', '.aifc', '.wma', '.rm']
    files_audio = [f for f in f_all if f.suffix in audio_suffix]

    files_audio = sorted(files_audio, key=lambda i: i.stem)
    if print_non_audio:
        print(f'Ignoring:')
        for x in list(set(f_all) - set(files_audio)):
            print(f'--{x}')
    return files_audio


def repath_fix_spaces(ss: str):
    tmp = re.sub(r' ( )+', ' ', ss)
    if tmp != ss:
        # print(f'--> cleaning double space\n{stem_normed}\n{tmp}')
        ss = tmp

    tmp = re.sub(r'^ +| +$', '', ss)
    if tmp != ss:
        # print(f'--> cleaning lead/trail space\n{stem_normed}\n{tmp}')
        ss = tmp
    return ss


def stem_sanitized(stem):
    # *************************************************************************** #
    # NORMALIZATION
    stem_normed = stem
    # === save replaces ===
    tmp = re.sub('&amp;', '&', stem_normed)
    if tmp != stem_normed:
        # print(f'--> &amp; replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    # === meta replaces Wildfire (128kbit_AAC)
    tmp = re.sub(r'\(152kbit_Opus\)|\(\d{1,3}kbit\_[A-Za-z]+\)', '', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> 152kbit_Opus-group replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp
    tmp = re.sub(r'\(Official.{0,8}Video\)', '', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> useless replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'\(\w*\.[a-zA-Z]{2,5}\)', '', stem_normed, flags=re.IGNORECASE)
    tmp = re.sub(r'\w*\.(?:com|net|org|co.uk|de|vu|ru|pl)', '', tmp, flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> website url replace\n{stem_normed}\n{tmp}')  # check [a-zA-Z]{2,5}\W,
        # frei.wild Mollono.Bass, no_4mat
        stem_normed = tmp

    tmp = re.sub(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U00002702-\U000027B0\U000024C2-\U0001F251"
                 u"\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
                 u"\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+", '', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> unicode replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    # === semantic replaces
    # (feat. mo feat. mo
    tmp = re.sub(r'(?<=\W)(featuring|feat\.|feat|ft\.|ft)\W', 'feat. ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> "feat." replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp
        # todo 'introducing', „present(s)“ bzw. „introducing“, „duet with“

    tmp = re.sub(r'(?<=\W)(produced by|produced|prod\. by|prod by|prod\.|prod)\W', 'prod. ', stem_normed,
                 flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> ".prod" replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'(?<=(\W|\(|\[))(vs\.|vs|versus)', 'vs. ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        # print(f'--> .vs replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'(?<=\W)(^ )', ' ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> use spacing\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    re.sub(r'\([^\)]*\)|\[[^\]]*\]', '', stem_normed)
    if tmp != stem_normed:
        print(f'--> remove all inside parentheses \n{stem_normed}\n{tmp}')
        stem_normed = tmp

    # stem_normed = re.sub(r'(\W&|",")\W', ', ', stem_normed)
    # potential "and" divide
    # stem_normed = re.sub('_', ' ', stem_normed)
    tmp = re.sub(r' ( )+', ' ', stem_normed)
    if tmp != stem_normed:
        # print(f'--> cleaning double space\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'^ +| +$', '', stem_normed)
    if tmp != stem_normed:
        # print(f'--> cleaning lead/trail space\n{stem_normed}\n{tmp}')
        stem_normed = tmp
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
                     r"|\, "
                     r"| & "
                     r"|\)|\]", stem_sanitized(p.stem), flags=re.IGNORECASE)
    split = [repath_fix_spaces(i) for i in split]

    # shortest artists: 'JJ - Still', shortest filename 'ss.mp3'
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


def audiofile_get_artist_title(p: Path):
    split = split_stem(p)
    # artist_options = [[]]
    # title_options = [[]]

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


def assume_artist_title_from_pathname(p: Path):
    split = split_stem(p)
    try:
        artist = split[0]
        title = split[1]
    except IndexError as ex:
        print(f'WARNING: Could not get Artist and Title from path: {p}')  # debug
        artist = ''
        title = split[0]

    return artist, title


def find_mp3_dupes(p: Path, p_base=None):
    p_base = get_audiopaths_in_folder(p_base)
    p_new = get_audiopaths_in_folder(p)

    base_artist_dict = {}

    for pb in p_base:
        print(pb)
        artist, title = audiofile_get_artist_title(pb)
        meta = audiofile_get_meta(pb)
        try:
            base_artist_dict[artist][pb]: [title, meta]
        except Exception as ex:
            base_artist_dict[artist] = {pb: [title, meta]}

    print(f'Songs in dict 1:')
    print(base_artist_dict)

    for f in p_new:
        f = Path(f)
        stem = f.stem
        # *************************************************************************** #
        # ==> if no " ", make '-', '_' -> ' '
        if not ' ' in stem:
            print(f'Oh no {stem}')  # todo
            print(f'{re.sub("-", " ", stem)}')
        # *************************************************************************** #

        artist, title = audiofile_get_artist_title(f)
        if base_artist_dict.get(artist):
            candidates = base_artist_dict[artist].items()
            for p_b, base_t_m in candidates:
                if title in base_t_m or base_t_m in title:
                    print(f'Success: {base_t_m} {title}\np1: {f}\np2: {p_b}')

    # new_stem_list.append(stem_normed)
    # if not (c % 200):
    #     lut_yaml_dump(p_lut, lut)
    # print(new_stem_list.sort())

    # lut_yaml_dump(p_lut, lut)


def funny2(new_p, base_p):
    """

    """
    base_paths = get_audiopaths_in_folder(base_p)
    base_stems = [stem_sanitized(p.stem) for p in base_paths]

    new_paths = get_audiopaths_in_folder(new_p)
    new_stems = [stem_sanitized(p.stem) for p in new_paths]

    dir_path = {stem_sanitized(p.stem): p for p in new_paths}
    changepaths = []
    for p in new_paths:

        split = [stem_sanitized(i) for i in re.split(' - ', p.stem)]
        if len(split) > 1:
            opt1 = [x for x in base_stems if split[0] in x]
            opt2 = [x for x in opt1 if split[1] in x]
            if opt2:
                print(f'{p.stem}\n{opt2}')
                try:
                    changepaths.append(dir_path[p.stem])
                except Exception as ex:
                    pass
                changepaths.append(dir_path[p.stem])

    del_folder = Path('C:/Users/Simon/Music/DELETE_ME')
    for n in changepaths:
        print(f'Moving {n.name}? to \n{del_folder / n.name}')
    input('Press enter to continue')
    # for n in changepaths:
    #     print(f'Moving {n.name} to {del_folder / n.name}...')
    #     n.rename(del_folder / n.name)


def path_make_dir(p: Path):
    """
    Creates the folder and files according to run specified through naming (E.g. MTC200_MSE_scratch)
    """
    folder = p if len(p.suffix) == 0 else p.parent  # if file -> parent-folder
    folder.mkdir(parents=True, exist_ok=True)
    return p


def attention_deleting_files(paths, delete_dir=Path('C:/Users/Simon/Music/DELETE_ME')):
    """Moving files to trash dir"""
    path_make_dir(delete_dir)
    for p in paths:
        print(f'{p} ->{delete_dir / p.name}')
        p.rename(delete_dir / p.name)


def hey_delete_song_dupes(base_dir, new_dir):
    """

    """
    base_paths = get_audiopaths_in_folder(base_dir)
    base_names = [stem_sanitized(x.name) for x in base_paths]

    new_paths = get_audiopaths_in_folder(new_dir)
    new_names = [stem_sanitized(x.name) for x in new_paths]

    dupe_names = set(base_names) & set(new_names)

    print(f'Found these dupes:')
    for d in dupe_names:
        print(d)

    new_path_lut = {stem_sanitized(p.name): p for p in new_paths}

    del_folder = Path('C:/Users/Simon/Music/DELETE_ME')
    del_paths = [new_path_lut[n] for n in dupe_names]

    for p in del_paths:
        print(f'Moving {p.name}: {p} to {del_folder / p.name}')
    input('Press Enter to move those files to delete.')
    attention_deleting_files(del_paths, del_folder)


# check parentesis

# *************************************************************************** #

# *************************************************************************** #

# if len(splits) == 2:
#     pass
# elif len(splits) == 1:
#     print(f'No split?:\t{stem}')
# else:
#     print(f'Too many splits:\t{stem}')

# _2.mp3
# excluding audio
# ??? inhaltsangabe, intro, missing files,
# mp3-checks
#   - length = metadata-length?

# s = "Die drei ___ - 168 - GPS-Gangster - Teil 10"
# s = "Die drei ___ - 167 - und das blaue Biest - Teil 40"
# s = s.replace('Die drei ___ - ', '')
# nr, titel, teil = s.split(' - ')
# print(f'{nr}\t{titel} {teil}')
# intro raus

# group
#   - interprets + title
#   - title (only str characters)

def funny2(a_folder: Path, b_folder: Path):

    # aaa = {p: {'split': split_extreme(p), 'matches': {}} for p in audiopaths_in_folder(a_folder)}

    bbb = [[p, ''.join(split_extreme(p)), audiofile_get_meta(p)] for p in get_audiopaths_in_folder(b_folder)]
    delete_files = {}
    maybe_files = {}

    for p in get_audiopaths_in_folder(a_folder):
        split = split_extreme(p)
        for p_main, merge, meta in bbb:
            matches = [s for s in split if s in merge]
            b_artist, b_title = audiofile_get_artist_title(p_main)
            merge_cpy = copy.deepcopy(merge)
            for s in matches:
                merge_cpy = merge_cpy.replace(s, '')

            if b_artist in split and b_title in split:
                print(f'==={b_artist}\t{b_title}\t{matches}')
                print(f'==={p.stem}\t{p_main.stem}')

            if len(matches) >= 3:
                if b_title in split:
                    print('asd')
                else:
                    print('xftgh')
                print(f'{p.stem}, {BColors.OKBLUE}{matches} \t{BColors.OKGREEN} Can be deleted {BColors.RESET}. {p_main.stem}')
                delete_files[p] = p_main

            elif len(matches) >= 2:
                merge_cpy = copy.deepcopy(merge)
                for s in matches:
                    merge_cpy = merge_cpy.replace(s, '')

                if len(merge_cpy)/len(merge) < 0.25:
                    print(f'{p.stem}, {BColors.OKBLUE}{matches} \t{BColors.OKGREEN} Overall match sufficient: '
                          f'{len(merge_cpy) / len(merge):.2f}{BColors.RESET}. {p_main.stem}')
                    delete_files[p] = p_main
                else:
                    # print(f'{p.stem}, {BColors.OKBLUE}{matches} \t{BColors.WARNING} Overall match not sufficient: {len(merge_cpy) / len(merge):.2f}{BColors.RESET}')
                    maybe_files[p] = p_main
            # else:
            #     print(f'{p.stem}, {BColors.OKBLUE}{matches} \t{BColors.RED} no match.{BColors.RESET}')

    print(delete_files)


def group_interprets(mp3names):
    mp3names_interpret = [s.split(' - ')[0] for s in mp3names]
    sorted(mp3names_interpret)
    mp3names_interpret = [re.sub('[a-zA-Z]', '', s) for s in mp3names_interpret]
    print(f'{len(set(mp3names_interpret))} different interprets: {set(mp3names_interpret)}')
    mp3names_interpret = sum([s.split(', ') for s in mp3names_interpret], [])
    print(f'{len(set(mp3names_interpret))} different interprets: {set(mp3names_interpret)}')
    mp3names_interpret = sum([s.split(' feat. ') for s in mp3names_interpret], [])
    mp3names_interpret = sum([s.split(' ft. ') for s in mp3names_interpret], [])
    print(f'{len(set(mp3names_interpret))} different interprets: {set(mp3names_interpret)}')
    mp3names_interpret = sum([s.split(' & ') for s in mp3names_interpret], [])
    print(f'{len(set(mp3names_interpret))} different interprets: {set(mp3names_interpret)}')
    mp3names_interpret = sum([s.split(' vs. ') for s in mp3names_interpret], [])
    mp3names_interpret = sum([s.split(' vs ') for s in mp3names_interpret], [])
    print(f'{len(set(mp3names_interpret))} different interprets: {set(mp3names_interpret)}')
    mp3names_interpret = sum([s.split(' vs ') for s in mp3names_interpret], [])
    print(f'{len(set(mp3names_interpret))} different interprets: {set(mp3names_interpret)}')


def fragezeichen_main():
    # def fragezeichen_raw():
    p = Path('C:/Users/Simon/Desktop/fragezeichen-merge/#raw')
    fpaths = list(p.glob('*'))
    names = [s.name for s in fpaths]
    nrs = [s.split(' - ')[1] for s in names]
    titles = [s.split(' - ')[2] for s in names]
    titles_unique = list(set(titles))
    print('\n'.join(titles_unique))
    print(len(titles_unique))
    nrs_unique = sorted(set([int(re.sub('[ a-zA-Z]', '', s)) for s in nrs]))
    print(nrs_unique, len(nrs_unique))


def hey_get_all_tracks(p: Path):
    songs_list = get_audiopaths_in_folder(p)
    return songs_list


def get_expected_name_from_metainfo(p: Path):
    pass


def hey_get_all_track_sanitations(p: Path, apply=False):
    """returns all tracks in a folder, that have obvious flaws like double space, trailing spaces, ..."""
    songs_list = hey_get_all_tracks(p)

    name_changes = {}
    for track in songs_list:
        stem0 = track.stem
        stem1 = stem_sanitized(stem0)
        if stem0 != stem1:
            print(stem0)
            print(stem1)
        else:
            pass


def hey_sanitize_all_track_names(dir: Path):
    """
    Sanitizing music file names
    replacing doublespaces, leading spaces, strailing spaces, "&amp"
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
            k.rename(v)
        except FileExistsError as ex:
            print(f'Alert! FileExistsError: {k} {v}')
            input('Ignoring. Press Enter to continue.')


def rename(f: Path, new: Path):
    # i think it would be prettier, if this was not a separate function
    try:
        f.rename(new)
    except FileExistsError as ex:
        input(f'Alert! FileExistsError: {f} {new}\nIgnoring. Press Enter to continue.')


def user_rename_file(f: Path, new: Path):
    x = input(f'Renaming:\n{f}\n{new}\nEnter to continue. \'n\' to skip.')
    if x == '':
        rename(f, new)
    else:
        print(f'Skipped')


def user_rename_files_in_dict(change_filenames: dict, confirm_each=False):
    if len(change_filenames) == 0:
        print(f'No files to rename!')
    else:
        for k, v in change_filenames.items():
            print(f'{k}\n{v}')
        if not confirm_each:
            input('Press Enter to rename all files above.')
        for k, v in change_filenames.items():
            if confirm_each:
                user_rename_file(k, v)
            else:
                rename(k, v)


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
    s = stem_sanitized(s)  # removing spaces
    if s0 != s:
        pass  # now you know why
    return s


def hey_find_all_dupes(dir: Path):
    """Finds dupes, if the song file names are equal, but in different folders.
    Sanitize Names first!"""
    # load all track-paths in list
    tracks_list = hey_get_all_tracks(dir)
    dupes = []
    p_a = Path('path/stem.mp3')

    # track-list is sorted by stem (aka track filename), so dupes are following each other
    for p in tracks_list:
        if p.stem == p_a.stem:
            dupes.append(p_a)
            dupes.append(p)
        p_a = p

    for d in dupes:
        print(f'{d}')
    # todo do this


def hey_remove_album_in_pathname(dir: Path):
    """
    C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao - Combat Circus.mp3
    C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao.mp3
    """
    tracks_list = hey_get_all_tracks(dir)
    # rename_dict = {}
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
    # hey_delete_song_dupes(Path('C:/Users/Simon/Music/GETINHERE'), Path('C:/Users/Simon/Music/Audials/Audials Music FUK'))
    # hey_get_all_track_sanitations(Path('C:/Users/Simon/Music/GETINHERE'))
    # hey_sanitize_all_track_names(Path('C:/Users/Simon/Music/GETINHERE/Simons Musik'))
    # hey_remove_album_in_pathname(Path("C:/Users/Simon/Music/GETINHERE/Simons Musik/"))
    hey_find_all_dupes(Path("C:/Users/Simon/Music/GETINHERE/Simons Musik/"))
    # todo: search .wav/.flac/... and search for matchi9ng .mp3; otherwise convert each song
