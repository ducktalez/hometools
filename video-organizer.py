"""
Borat should be named:
/Filme/Borat (2006) [tmdbid-496]/Borat (2006) [tmdbid-496].mp4
todo store metadata in file when the movie is absolutely clear
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
from tmdbv3api import TMDb, Movie

from cmp_files import remove_ugly_spacesDots
from config import tmdb_api_key
from utils import get_files_in_folder, VIDEO_SUFFIX

# TMDb-API einrichten
tmdb = TMDb()
tmdb.api_key = tmdb_api_key
tmdb.language = 'de'  # Setze die Sprache auf Deutsch (optional)

# Film suchen
movie = Movie()


def movie_sanitize_name_search(p: Path, remove_splits=0):
    return stem


def get_tmdb_from_name(search_str):
    tmdb_search = movie.search(search_str)

    # exit all, if tmdb does not find results
    if tmdb_search.total_results == 0:
        raise ValueError(f'No tmdb_search result for "{search_str}"')

    compare_search_dict = []

    for result in tmdb_search:
        title_split = split_for_search(result.title)
        try:
            release_year = int(result['release_date'][0:4])
        except ValueError as ex:
            # (f'If no release-date, film is to be released? {search_str}'
            continue
        original_title = result.original_title
        og_split = split_for_search(original_title)
        og_perc = sum([len(x) for x in og_split if x in search_str]) / len(''.join(og_split))
        release_match = str(release_year) in search_str

        title_perc = sum([len(x) for x in title_split if x in search_str]) / len(''.join(title_split))
        max_perc = max(title_perc, og_perc)

        compare_search_dict.append({'result.title': result.title, 'original_title': original_title,
                                    'max_perc': max_perc,
                                    'og_perc': og_perc,
                                    'title_perc': title_perc,
                                    'release_match': release_match,
                                    'release_year': release_year, 'result': result})

    compare_search_dict = sorted(compare_search_dict, key=lambda x: (-x['max_perc'],
                                                                     -x['og_perc'],
                                                                     -x['title_perc'],
                                                                     -x['result']['vote_count']))

    for x in compare_search_dict:
        print(f'Initial search results: {x["result.title"]} '
              f'{x["max_perc"]:4.2f}% match (og: {x["og_perc"]:4.2f}%, title: {x["title_perc"]:4.2f}%')

    # compare_search_dict2 = [x for x in compare_search_dict if x['max_perc'] > 0.85]
    #
    # for x in compare_search_dict2:
    #     print(f'Accepted searches: {x.values()}')
    #
    # if len(compare_search_dict2) > 1:
    #     inp = input(f'List has too many good results!')
    # elif len(compare_search_dict2) == 0:
    #     raise ValueError(f'List has too little good results!')

    return compare_search_dict


def split_for_search(s):
    """
    i<3: Allow early splits: "I, Robot"
    len(x)>3: remove empty ""-splits
    len(re.findall(r'\d{1,3}', x))>0): Exception for Numbers "Johnny English 2"
    """
    s = re.sub(r'\(engl\)', '', s)
    s = re.sub(r'(\d){1,4}p', '', s, flags=re.IGNORECASE)
    s = re.sub(r'uncut|extended|edition', '', s, flags=re.IGNORECASE)
    s = re.sub(r'x264|BluRay|DD51', '', s, flags=re.IGNORECASE)
    s = re.sub(r'tmdbid', '', s, flags=re.IGNORECASE)
    # s = re.sub('\(\d{4}\)', '', s)  # remove years (2005)
    splits = re.split(r'\W', s)
    splits = [remove_ugly_spacesDots(x) for x in splits]
    splits = [x for i, x in enumerate(splits) if (i<2 or len(x)>2 or len(re.findall(r'\d{1,3}', x))>0)]
    return splits


def get_tmbdid_from_path(p: Path):  # -> tmdbv3api.as_obj.AsObj

    search_split = p.stem
    search_split = split_for_search(search_split)

    while search_split:
        search_str = ' '.join(search_split)
        print(f'Searching for "{search_str}"')
        try:
            compare_search_dict = get_tmdb_from_name(search_str)
            compare_search_dict = sorted(compare_search_dict, key=lambda x: x['release_year'])
            tmdb_result = compare_search_dict[0]

            tmdb_id = tmdb_result['result']['id']
            title = tmdb_result['result']['title']
            original_title = tmdb_result['result']['original_title']
            release_year = tmdb_result['release_year']

            files_rename_dict = {p: {}}

            db_set = title.split(' ') + original_title.split(' ') + [f'\[tmdbid-{tmdb_id}\]'] + [f'\({release_year}\)']
            db_set = [re.sub('\W', '', e).lower() for e in db_set]
            db_set = set(db_set)
            file_split = p.stem
            file_split = [re.sub('\W', '', e).lower() for e in re.split('\W', file_split) if len(e)>0]
            file_set = set(file_split)

            left_set = file_set - db_set
            left_final = [x for x in file_split if any([re.search(x, l, flags=re.IGNORECASE) for l in left_set])]
            if len(left_final) > 0:
                left_final = ' '.join(x for x in left_final if len(x)>1)
                left_final = f' [{left_final}]'
            else:
                left_final = ''

            if len(left_final) > 1:
                print(f'Leftovers: {left_final}')

            # rename_as = f'{title} ({release_year}) [tmdbid-{tmdb_id}]{left_final}{p.suffix}'

            if not search_split[-1] in title and len(re.findall(r'\d', search_split[-1])) > 0:
                print(f'What is there? {search_split[-1]}')
                try_find = ' '.join(search_split[0:-1])
                try_replace = ' '.join(search_split)
                title_enhanced = re.sub(try_find, try_replace, title)
                if title_enhanced != title:
                    print(f'Renaming?\n{title_enhanced}\n{title}')
            else:
                title_enhanced = title
            rename_as = f'{title_enhanced} ({release_year}) [tmdbid-{tmdb_id}]{left_final}{p.suffix}'

            # both = re.sub(try_find, try_replace, title)
            # # rename_as3 = re.sub(' '.join(search_split[:-1]), '', b)
            # print(f'{rename_as}\n{rename_as2}\n{rename_as3}')
            files_rename_dict[p]['rename_as'] = rename_as
            return files_rename_dict
        except (ValueError, TypeError) as todo:
            _drop = search_split.pop()

    raise ValueError('No matches found in database')


files_list = get_files_in_folder(Path('//Syn723/Filme/#English (engl)'), suffix_accepted=VIDEO_SUFFIX)
tmdb.language = 'en'

files_list = get_files_in_folder(Path('//Syn723/Filme/irrelevant'), suffix_accepted=VIDEO_SUFFIX)
tmdb.language = 'de'

print(files_list)
# files_dict = dict.fromkeys(files_list, {})
files_rename_dict = {}
fails = []
for p in files_list:
    try:
        dct = get_tmbdid_from_path(p)
        files_rename_dict.update(dct)

    except (TypeError, ValueError) as ex:
        fails.append(p)
    print('--------------------------------------------------------------------')
# get_tmdbid_from_filename('Türkisch für Anfänger')

for p in fails:
    print(f'Failed Movie: {p.stem}\t{p.as_posix()}')

for p, v in files_rename_dict.items():
    print(f'{p.name} -> {v["rename_as"]}')

# file_name = "Borat"
# file_name = "Harry Potter und die Heiligtümer des Todes - Teil 1"
# file_name = 'Harry.Potter.(engl).1.Extended.and.the.Sorcerers.Stone.Extended.Edition.(2001).ENGLISCH DD51 720p BluRay x264-JJ.mp4'
# file_name = 'Zootopia.(engl).mp4'
# file_name = 'Johnny English 2.mp4'
# file_name = 'Türkisch Für Anfänger'
# asdf = get_tmbdid_from_path(Path(file_name))
# print(asdf)