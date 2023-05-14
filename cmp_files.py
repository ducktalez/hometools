import copy
import re
from pathlib import Path
from pydub import utils
import yaml

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


def audiopaths_in_folder(p: Path):
    files_audio = []
    for suffix in ['mp3', 'm4a', 'ogg', 'opus', 'flac', 'aac', 'wav', 'aiff', 'wma']:
        files_audio.extend([f for f in p.rglob(f'*.{suffix}') if f.is_file()])
    files_audio = sorted(files_audio, key=lambda i: i.stem)
    # new_files = set([f for f in p.rglob(f'*') if f.is_file()])-set(files_audio)  # compare with all files
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


def split_stem(p: Path, min_length=3):
    split = re.split(r"feat\."
                     r"|prod\."
                     r"|vs\."
                     r"|\(|\["
                     r"| - "
                     r"|\, "
                     r"| & "
                     r"|\)|\]", stem_normalize(p.stem), flags=re.IGNORECASE)
    split = [repath_fix_spaces(i) for i in split]
    split = [i for i in split if len(i) > min_length]
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
                try:
                    changepaths.append(dir_path[p.stem])
                except Exception as ex:
                    pass
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

def funny2(a_folder: Path, b_folder: Path):

    # aaa = {p: {'split': split_extreme(p), 'matches': {}} for p in audiopaths_in_folder(a_folder)}

    bbb = [[p, ''.join(split_extreme(p)), audiofile_get_meta(p)] for p in audiopaths_in_folder(b_folder)]
    delete_files = {}
    maybe_files = {}

    for p in audiopaths_in_folder(a_folder):
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


    # changepaths = []
    # for p, v in aaa.items():
    #     split = a_val_sp['split']
    #     matches_dict = {}
    #     for b_merge, b_split_path in bbb.items():
    #         bsplit = b_split_path['split']
    #         matches = [s for s in split if s in b_merge]
    #         if len(matches) >= 2:
    #             matches_dict[a_merge] = {'matches': matches}  # 'matches_rev': matches_rev}
    #             matches_rev = [s for s in bsplit if s in a_merge]
    #             for b_merge2, v in sorted(matches_dict.items(), key=lambda item: -len(item[1]['matches'])):
    #                 matches = v['matches']
    #                 match_rate = len(matches) / len(split)
    #                 COLR = BColors.OKGREEN if match_rate >= 1.0 else BColors.OKBLUE if match_rate > 0.5 else BColors.RED
    #                 print(f'{COLR}{len(matches)}/{len(split)} ({match_rate:.02f}%)\033[39m:{split}')
    #
    #                 solve_len = len("".join(matches))
    #                 solve_rate = (len(b_merge)-solve_len)/len(b_merge)
    #                 COLR2 = [BColors.RED, BColors.WARNING, BColors.OKBLUE, BColors.OKGREEN][sum(int(solve_rate + 1 - i) for i in [.85, .55, .25])]
    #                 print(f'\t{COLR2}{len(b_merge)-solve_len}/{len(b_merge)} {solve_rate:0.2f}\033[39m: {matches} in {b_merge}')
    #
    #                 rev = v['matches_rev']
    #                 rev_len = len("".join(v['matches_rev']))
    #                 solve_rate_rev = (len(a_merge)-rev_len)/len(a_merge)
    #                 if 0.6 > solve_rate > 0.3:
    #                     COLR3 = [BColors.RED, BColors.WARNING, BColors.OKBLUE, BColors.OKGREEN][sum(int(solve_rate_rev + 1 - i) for i in [.85, .55, .25])]
    #                 else:
    #                     COLR3 = BColors.RESET
    #                 print(f'\t{COLR3}{len(a_merge)-rev_len}/{len(a_merge)} {solve_rate_rev:0.2f}\033[39m: {rev} in {a_merge}')
    #
    # # del_folder = Path('C:/Users/Simon/Music/DELETE_ME')
    # # for n in changepaths:
    # #     print(f'Moving {n.name}? to \n{del_folder / n.name}')
    # # for n in changepaths:
    # #     print(f'Moving {n.name} to {del_folder / n.name}...')
    # #     n.rename(del_folder / n.name)


# def doppelte(a, b):
#     """Doppelte"""
#     seen = set()
#     dupes = [x for x in mp3names_smol if x in seen or seen.add(x)]
#     print(dupes)
#     print(len(dupes))


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
    # funnytest(p1, p2)
    funny2(p1, p2)
