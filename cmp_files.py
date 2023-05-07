import re
from pathlib import Path
from pydub import utils
import yaml

p = Path('C:/Users/Simon/Desktop/mp3work/')  # 001 - Die drei Fragezeichen und der Super-Papagei/
p = Path('C:/Users/Simon/Music/Audials/Audials Music/')
p = Path('C:/Users/Simon/Desktop/fragezeichen-merge/#raw')
p = Path('C:/Users/Simon/Music/')
p = Path('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/')
p = Path('C:/Users/Simon/Music/Simons Musik/')

audiofile_suffixes = ['mp3', 'm4a', 'ogg', 'opus', 'flac', 'aac']  # 'wav', 'aiff', 'wma',

# *********************************************************************** #
files_audio = []
for suffix in ['mp3', 'm4a', 'ogg', 'opus', 'flac', 'aac']:
    files_audio.extend([f for f in p.rglob(f'*.{suffix}') if f.is_file()])
files_audio = sorted(files_audio, key=lambda i: i.stem)

# *********************************************************************** #

# x = "\n".join([f"{pt.name}" for pt in files_audio])
# print(x)

# print(f'{names}')


# *************************************************************************** #

def stem_guess_parentheses_info(stem):
    parentheses_infos = re.findall('\(\w*\)|\[\w*\]|\{\w*\}', stem_normed)
    if parentheses_infos:
        parentheses_infos = [i for i in parentheses_infos]
        print(f'{parentheses_infos}, at \t{stem_normed}')
        for klinfo in parentheses_infos:
            klinfo = klinfo[1:-1]
            if re.match('^feat\. ', klinfo):
                klinfo.replace('feat. ', '')
                print(f'feature info: {klinfo}')
            if re.match(' (mix|remix|edit|cover)$', klinfo):
                klinfo = re.sub(' (mix|remix|edit|cover)$', '', klinfo)
                print(f'MIX                  dsfg: {klinfo}')
            # '"by" ___'
            # extended

            # ['[DnB]'], at [DnB] - Feint - We Wo
            # n't Be Alone feat. Laura Brehm) [Monstercat edit

            # -> leading '.feat'
            # -> trailing 'remix', 'mix', 'edit'
    # *************************************************************************** #


p_lut = Path.cwd() / 'wa_data/mp3files_lut.yaml'
try:
    with p_lut.open('r') as file:
        lut = yaml.load(file, Loader=yaml.FullLoader)
except FileNotFoundError:
    lut = {}


def lut_yaml_dump(lut):
    with p_lut.open('w') as f:
        yaml.dump(lut, f)


# www.sdfgertg.com
for c, f in enumerate(files_audio):
    stem = f.stem
    try:
        meta = lut[f.as_posix()]
    except KeyError:
        meta = utils.mediainfo(f)
        lut[f.as_posix()] = meta

    try:
        # meta_title = meta['TAG'].get('title')  # 'Die deutsche Selbstüberschätzung, Teil 2'
        # meta_artist = meta['TAG'].get('artist')
        # meta_sample_rate = meta.get('sample_rate')  # 44100
        # meta_size = meta.get('size')  # 9629390
        # meta_bit_rate = meta.get('bit_rate')  # 320992
        # meta_duration = meta.get('duration')  # 239.990125
        # print(f'{f.name}')
        # print(f'{f.name}\t{meta}')
        pass
    except KeyError as ke:
        print(f'---> Keyerror in file {f}')
        meta = {}

    # *************************************************************************** #
    # ==> if no " ", make '-', '_' -> ' '
    if not ' ' in stem:
        print(f'Oh no {stem}')  # todo
        print(f'{re.sub("-", " ", stem)}')

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

    # tmp = re.sub(r'[\w]*\.(?:com|net|org|co.uk|de|vu|ru)', '', stem_normed, flags=re.IGNORECASE)
    # if tmp != stem_normed:
    #     print(f'--> website replace\n{stem_normed}\n{tmp}')  # check [a-zA-Z]{2,5}\W, frei.wild Mollono.Bass
    #     stem_normed = tmp

    tmp = re.sub(r'\(\w*\.[a-zA-Z]{2,5}\)', '', stem_normed, flags=re.IGNORECASE)
    tmp = re.sub(r'[\w]*\.(?:com|net|org|co.uk|de|vu|ru)', '', tmp, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> website replace\n{stem_normed}\n{tmp}')  # check [a-zA-Z]{2,5}\W, frei.wild Mollono.Bass
        stem_normed = tmp

    tmp = re.sub(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U00002702-\U000027B0\U000024C2-\U0001F251"
                 u"\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55"
                 u"\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+", '', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> unicode replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    # === semantic replaces

    # (feat. mo feat. mo
    tmp = re.sub(r'(?<=\W)(featuring|feat\.|feat|ft\.|ft)\W', 'feat. ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> "feat." replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'(?<=\W)((produced by|produced|prod\. by|prod by|prod\.|prod))\W', 'prod. ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> ".prod" replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'(?<=\W)(^ )', ' ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> use spacing\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    tmp = re.sub(r'(?<=(\W|\(|\[))(vs\.|vs|versus)', 'vs. ', stem_normed, flags=re.IGNORECASE)
    if tmp != stem_normed:
        print(f'--> .vs replace\n{stem_normed}\n{tmp}')
        stem_normed = tmp

    # stem_normed = re.sub(r'(\W&|",")\W', ', ', stem_normed)
    # potential "and" divide
    # stem_normed = re.sub('_', ' ', stem_normed)
    tmp = re.sub(r' {2,}', ' ', stem_normed)
    if tmp != stem_normed:
        # print(f'--> cleaning double space\n{stem_normed}\n{tmp}')
        stem_normed = tmp
    tmp = re.sub(r'^ +| +$', '', stem_normed)
    if tmp != stem_normed:
        # print(f'--> cleaning lead/trail space\n{stem_normed}\n{tmp}')
        stem_normed = tmp
    # if stem != stem_normed:
    #     print(f'{stem}\n{stem_normed}')
    # *************************************************************************** #

    # split_feat = re.split(' feat.', stem_normed)
    # findall_feats = re.findall(r'feat\.*(\)|\,)', stem_normed)
    # if len(split_feat) > 1:
    #     print(split_feat)
    #     print(findall_feats)
    #     print()

    #####
    # artist replaces
    # '| - Topic'

    # *************************************************************************** #
    # removing features
    ### open \W(feat\.| ft\.| featuring | ft)\W
    # *************************************************************************** #

    # print(f'{test[:-1]} \t{test[-1]}')

    # def stem_guess_artist(stem_normed):
    # split1 = re.split(r' feat. |\, ', stem_normed, flags=re.IGNORECASE)  # both side relevant
    # split2 = re.split(r'\(feat. ', stem_normed, flags=re.IGNORECASE)  # right side relevant
    # split3 = re.split(r' - ', stem_normed, flags=re.IGNORECASE)  # left side artist, right side titlle, middle is problem
    # split4 = re.split(r'\W-\W', stem_normed, flags=re.IGNORECASE)  # left side artist, right side titlle, middle is problem
    # split5 = re.split(r'mix|edit|remix', stem_normed, flags=re.IGNORECASE)  # left side artist, right side title, middle is problem
    split6 = re.split(r'feat\.|prod\.|vs\.|\(|\[| - |\)|\]', stem_normed, flags=re.IGNORECASE)
    print(f'{split6}')

    # *************************************************************************** #
    # URLS
    # urls = re.findall('[\w]*\.(?:com|net|org|co.uk|de|vu|ru)', stem_normed)  # check [a-zA-Z]{2,5}\W, frei.wild Mollono.Bass
    # if urls:
    #     print(urls, stem)
    # *************************************************************************** #
    # if not (c % 200):
    #     lut_yaml_dump(lut)


# lut_yaml_dump(lut)


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
    mp3names_interpret = [s.replace('') for s in mp3names_interpret]
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
    fragezeichen_main()
