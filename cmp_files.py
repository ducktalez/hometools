import re
from pathlib import Path

p = Path('C:/Users/Simon/Desktop/mp3work/')  # 001 - Die drei Fragezeichen und der Super-Papagei/
p = Path('C:/Users/Simon/Music/Audials/Audials Music/')
p = Path('C:/Users/Simon/Desktop/fragezeichen-merge/#raw')
p = Path('C:/Users/Simon/Music/')
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


# www.sdfgertg.com
for f in files_audio:
    stem = f.stem

    removes = ['mp3']

    splits = stem.split(' - ')
    # test = re.split(' feat. | ft. | featuring | ft | & | &amp; | vs. |"," ', splits[0])  # ' and ' too many hits?

    # ==> if no " ", make '-', '_' -> ' '
    if not ' ' in stem:
        print(f'Oh no {stem}')
        print(f'{re.sub("-", " ", stem)}')

    # *************************************************************************** #
    # NORMALIZATION
    stem_normed = stem
    # === save replaces ===
    stem_normed = re.sub('&amp;', '&', stem_normed)
    # === meta replaces Wildfire (128kbit_AAC)
    stem_normed = re.sub('\(152kbit_Opus\)|\(Official Video\)|\(\d{1,3}kbit\_[A-Z]{2,4}\)', '', stem_normed)
    stem_normed = re.sub('', '', stem_normed)
    # === semantic replaces
    stem_normed = re.sub('\W(feat\.|ft\.|featuring|ft)\W', ' feat. ', stem_normed)
    stem_normed = re.sub('(\W&|",")\W', ', ', stem_normed)
    # potential "and" divide
    # stem_normed = re.sub('_', ' ', stem_normed)
    stem_normed = re.sub('  ', ' ', stem_normed)
    # if stem != stem_normed:
    #     print(f'{stem}\n{stem_normed}')
    # *************************************************************************** #
    split_feat = re.split(' feat. ', stem_normed)
    findall_feats = re.findall('feat.\.*(\)|\,)', stem_normed)
    if len(split_feat) > 1:
        print(split_feat)
        print(findall_feats)
        print()

    # *************************************************************************** #
    # removing features
    ### open \W(feat\.| ft\.| featuring | ft)\W
    # *************************************************************************** #

    # asfds ft sdfg
    test = re.split('\W(feat.| ft.|featuring|ft|&|&amp;|vs.)\W|","\W|', stem)

    # print(f'{test[:-1]} \t{test[-1]}')

    # *************************************************************************** #
    # URLS
    # urls = re.findall('[\w]*\.(?:com|net|org|co.uk|de|vu|ru)', stem_normed)  # check [a-zA-Z]{2,5}\W, frei.wild Mollono.Bass
    # if urls:
    #     print(urls, stem)
    # *************************************************************************** #

    # *************************************************************************** #
    # parentheses_infos = re.findall('\(\w*\)|\[\w*\]|\{\w*\}', stem_normed)
    # if parentheses_infos:
    #     parentheses_infos = [i for i in parentheses_infos]
    #     print(f'{parentheses_infos}, at \t{stem_normed}')
    #     for klinfo in parentheses_infos:
    #         klinfo = klinfo[1:-1]
    #         if re.match('^feat\. ', klinfo):
    #             klinfo.replace('feat. ', '')
    #             print(f'feature info: {klinfo}')
    #         if re.match(' (mix|remix|edit)$', klinfo):
    #             klinfo = re.sub(' (mix|remix|edit)$', '', klinfo)
    #             print(f'MIX                  dsfg: {klinfo}')
    #         # '"by" ___'
    #         # extended
    #
    #         # ['[DnB]'], at [DnB] - Feint - We Wo
    #         # n't Be Alone feat. Laura Brehm) [Monstercat edit
    #
    #         # -> leading '.feat'
    #         # -> trailing 'remix', 'mix', 'edit'
    # *************************************************************************** #

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


def doppelte():
    """Doppelte"""
    seen = set()
    dupes = [x for x in mp3names_smol if x in seen or seen.add(x)]
    print(dupes)
    print(len(dupes))


def group_interprets():
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
