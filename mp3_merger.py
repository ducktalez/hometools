from pydub import AudioSegment, utils
import re
from pathlib import Path


def print_path_stems(p_list):
    return '\n'.join([i.stem for i in p_list])


# def check_parts_enum(sorted_paths, key=lambda x: int(re.sub(r'\D', '', x.stem))):
#     check_enum = [key(x) for x in sorted_paths]
#     for a, b in enumerate(check_enum, check_enum[0]):
#         if a != b:
#             raise ValueError(f'FAILED {a}, {b}\t: {sorted_paths}')


def mp3merge_list(path_list, p_merged: Path, meta_TAG=None):
    merged = sum([AudioSegment.from_file(p) for p in path_list])
    if meta_TAG is None:
        meta_TAG = utils.mediainfo(path_list[0])
        meta_TAG_last = utils.mediainfo(path_list[-1])
        meta_TAG['TAG']['track'] = str(len(path_list) + 1)

    merged.export(p_merged, format='mp3', bitrate='128k', tags=meta_TAG)


def merge_mp3files_infolder_pydub(path_list):
    mp3dict = {i: {'track': utils.mediainfo(i)['TAG']['track'], 'stem-dlist': re.findall(r'\d+', i.stem)} for i in path_list}

    try:
        mp3sorted = [i[0] for i in sorted(mp3dict.items(), key=lambda x: int(x[1]['track']))]
    except Exception as ex:

        try:
            mp3sorted = [i[0] for i in sorted(mp3dict.items(), key=lambda x: int(x[1]['stem-dlist'][-1]))]
        except Exception as ex:

            try:
                mp3sorted = [i[0] for i in sorted(mp3dict.items(), key=lambda x: int(x[1]['stem-dlist'][1]))]
            except Exception as ex:
                raise Exception(f'Could not determine ranking in: {path_list[1]}')

    # print(print_path_stems(mp3files))
    # mp3files.sort(key=lambda x: int(re.findall(r'\d+', x.stem)[-1]))
    print(print_path_stems(mp3sorted))
    # check_parts_enum(mp3sorted)


# nuhrpath = Path('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/Nuhr weiter so/')
# test = Path('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/')
test = Path('C:/Users/Simon/Music/Simons Musik')
test = Path('C:/Users/Simon/Desktop/mp3work/grouped/001 - Die drei Fragezeichen und der Super-Papagei')

for t in test.rglob('*'):
    if t.is_dir():
        mp3files = [i for i in p_input.rglob('*.mp3')]
        merge_mp3files_infolder_pydub(mp3files)
