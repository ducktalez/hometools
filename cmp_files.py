import re
from pathlib import Path
from pydub import utils
import yaml


p_lut = Path.cwd() / 'wa_data/mp3files_lut.yaml'


def yaml_load(p: Path):
    try:
        with p.open('r') as file:
            loaded = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        loaded = {}
    return loaded


lut = yaml_load(p_lut)


def lut_yaml_dump(p: Path, lut):
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


def audiopaths_in_folder(p: Path):
    files_audio = []
    for suffix in ['mp3', 'm4a', 'ogg', 'opus', 'flac', 'aac', 'wav', 'aiff', 'wma']:
        files_audio.extend([f for f in p.rglob(f'*.{suffix}') if f.is_file()])
    files_audio = sorted(files_audio, key=lambda i: i.stem)
    # new_files = set([f for f in p.rglob(f'*') if f.is_file()])-set(files_audio)  # compare with all files
    return files_audio


def restr_space_fix(ss: str):
    tmp = re.sub(r' ( )+', ' ', ss)
    if tmp != ss:
        # print(f'--> cleaning double space\n{stem_normed}\n{tmp}')
        ss = tmp

    tmp = re.sub(r'^ +| +$', '', ss)
    if tmp != ss:
        # print(f'--> cleaning lead/trail space\n{stem_normed}\n{tmp}')
        ss = tmp
    return ss


def stem_normalize(stem):
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

    tmp = re.sub(r'\(Official Video\)', '', stem_normed, flags=re.IGNORECASE)
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
        meta = utils.mediainfo(f)
        for dt in delkeys:
            try:
                meta.pop(dt)
            except KeyError as ex:
                pass
        lut[f.as_posix()] = meta
    return meta


def audiofile_get_artist_title(p: Path):
    split = re.split(r"feat\.|prod\.|vs\.|\(|\[| - | & |\)|]", stem_normalize(p.stem), flags=re.IGNORECASE)
    split = [restr_space_fix(i) for i in split]
    # artist_options = [[]]
    # title_options = [[]]

    try:
        artist = lut['TAG']['artist']
        artist = re.sub('\| - Topic', '', artist)  # youtube-music artist
    except KeyError:
        artist = split[0]

    try:
        title = lut['TAG']['title']
    except KeyError:
        try:
            title = split[1]
        except Exception as ex:
            print(f'FUCKIN UGLY: {p}')
            title = 'MISSING'
    return artist, title


def find_mp3_dupes(p: Path, p_base):

    p_base = audiopaths_in_folder(p_base)
    p_new = audiopaths_in_folder(p)
    base_artist_dict = {}

    for pb in p_base:
        artist, title = audiofile_get_artist_title(pb)
        meta = audiofile_get_meta(pb)
        try:
            base_artist_dict[artist][pb]: [title, meta]
        except Exception as ex:
            base_artist_dict[artist] = {pb: [title, meta]}

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


def funnytest(p1, p2):

    base_paths = audiopaths_in_folder(p2)
    base_stems = [stem_normalize(p.stem) for p in base_paths]

    new_paths = audiopaths_in_folder(p1)
    new_stems = [stem_normalize(p.stem) for p in new_paths]
    dir_path = {stem_normalize(p.stem): p for p in new_paths}
    changepaths = []
    for p in new_paths:

        split = [stem_normalize(i) for i in re.split(' - ', p.stem)]
        if len(split) > 1:
            opt1 = [x for x in base_stems if split[0] in x]
            opt2 = [x for x in opt1 if split[1] in x]
            if opt2:
                print(f'{p.stem}\n{opt2}')
                changepaths.append(dir_path[p.stem])

    del_folder = Path('C:/Users/Simon/Music/DELETE_ME')
    for n in changepaths:
        print(f'Moving {n.name}? to \n{del_folder / n.name}')
    for n in changepaths:
        print(f'Moving {n.name} to {del_folder / n.name}...')
        n.rename(del_folder / n.name)


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


def doppelte(mp3names_smol):
    """Doppelte"""
    seen = set()
    dupes = [x for x in mp3names_smol if x in seen or seen.add(x)]
    print(dupes)
    print(len(dupes))


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


if __name__ == '__main__':
    p1 = Path('C:/Users/Simon/Music/Simons Musik')
    p2 = Path('C:/Users/Simon/Music/Audials/Audials Music')
    # find_mp3_dupes(p1, p2)
    funnytest(p1, p2)
