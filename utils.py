import os
import re
from pathlib import Path

from print_tools import Colors

AUDIO_SUFFIX = ['.mp3', '.m4a', '.ogg', '.opus', '.aac', '.wma', '.rm', '.wav', '.flac', '.aif', '.aiff', '.aifc']
AUDIO_LOSS_SUFFIX = ['.mp3', '.m4a', '.ogg', '.opus', '.aac', '.wma', '.rm']
AUDIO_LOSSLESS_SUFFIX = ['.wav', '.flac', '.aif', '.aiff', '.aifc']
VIDEO_SUFFIX = ['.mp4', '.m4v', '.mvg', '.avi', '.mov', '.wmv', '.avchd', '.WebM', '.flv', '.mkv', '.vob', '.ogg', '.ogv']

DEL_FOLDER_DUMMY = Path('C:/Users/Simon/Music/DELETE_ME')


def get_files_in_folder(p: Path, suffix_accepted=None) -> [Path]:
    """Returns a path-list of all files with file-ending suffix
    e.g. audiofiles
    e.g. videofiles"""
    files = [f for f in p.rglob(f'*') if f.is_file()]

    if suffix_accepted:
        files = [f for f in files if f.suffix in suffix_accepted]

    files = sorted(files, key=lambda i: i.stem)
    return files


def get_audio_files_in_folder(p: Path, suffix=AUDIO_SUFFIX, print_non_audio=False):
    """Returns a path-list of all music files"""
    f_all = [f for f in p.rglob(f'*') if f.is_file()]

    files_audio = [f for f in f_all if f.suffix in suffix]

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


def get_file_size(p: Path):
    """C:/Users/Simon/Music/GETINHERE/Simons Musik/Rock -Punk, Ska/Talco - Bella Ciao.mp3"""
    file_stats = os.stat(p)
    f_size = file_stats.st_size
    return f_size


def path_make_dir(p: Path):
    """
    Creates the folder and files according to run specified through naming (E.g. MTC200_MSE_scratch)
    """
    folder = p if len(p.suffix) == 0 else p.parent  # if file -> parent-folder
    folder.mkdir(parents=True, exist_ok=True)
    return p


def rename_path(f: Path, new: Path):
    # i think it would be prettier, if this was not a separate function
    try:
        f.rename(new)
    except FileExistsError as ex:
        input(f'Alert! FileExistsError: {f} {new}\nIgnoring. Press Any to continue.')


def user_rename_file(f: Path, new: Path, ask_user_str=None):
    """"""
    x = input(ask_user_str or f'Renaming:\n\t{f}\n\t{new}\nEnter to continue. \'n\' to skip.')
    if x == '':
        rename_path(f, new)
    else:
        print(f'Skipped')


def user_rename_fromToDict(from_to_dict: dict, confirm_each=True):
    """{'asd/file.txt': 'asd/new.txt'}"""
    if len(from_to_dict) == 0:
        print(f'No files to rename!')
    else:
        if not confirm_each:
            for k, v in from_to_dict.items():
                print(f'{Colors.RED}{k}\n'
                      f'{Colors.GREEN}{v}'
                      f'{Colors.RESET}')
            x = input('Press Enter to rename all files above.')
            if x != '':
                print(f'Skipped!')
                return
        for k, v in from_to_dict.items():
            if confirm_each:
                user_rename_file(k, v)
            else:
                rename_path(k, v)


def attention_deleting_files(paths, delete_dir=Path('C:/Users/Simon/Music/DELETE_ME'), soft_delete=True):
    """Moving files to trash dir"""
    path_make_dir(delete_dir)
    for p in paths:
        if soft_delete:
            print(f'{p} ->{delete_dir / p.base_name}')
            p.rename_path(delete_dir / p.base_name)
        else:
            Path.unlink(p)


def deleting_file(p, delete_dir=Path('C:/Users/Simon/Music/DELETE_ME')):
    """Moving file to trash dir"""
    path_make_dir(delete_dir)
    user_rename_file(p, delete_dir / p.base_name, ask_user_str=f'{p} ->{delete_dir / p.base_name}')