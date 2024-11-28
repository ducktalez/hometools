"""
Borat should be named:
/Filme/Borat (2006) [tmdbid-496]/Borat (2006) [tmdbid-496].mp4
"""
import re
from pathlib import Path
from sys import flags

from tmdbv3api import TMDb, Movie, TV, Season

from cmp_files import remove_ugly_spaces, remove_ugly_dots
from config import tmdb_api_key
from utils import get_files_in_folder, attention_deleting_files, VIDEO_SUFFIX, user_rename_fromToDict, user_rename_file


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
        print(f'Initial search results: "{x["result.title"]}" '
              f'{x["max_perc"]:4.2f}% match (og: {x["og_perc"]:4.2f}%, title: {x["title_perc"]:4.2f}% '
              f'original_title: {x["original_title"]}')

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
    splits = [remove_ugly_spaces(x) for x in splits]
    splits = [x for i, x in enumerate(splits) if (i<2 or len(x)>2 or len(re.findall(r'\d{1,3}', x))>0)]
    return splits


def film_title_add_counter(search_split, title):
    """
    Keeping the order of Films in the file name
    If file:    "Harry Potter and the Philosopher Stone.mp4"
            ->  "Harry Potter 1 and the Philosopher Stone.mp4 "
    Not required for Series, as they usually have S02E12
    """
    if not search_split[-1] in title and len(re.findall(r'\d', search_split[-1])) > 0:
        print(f'What is there? {search_split[-1]}')
        try_find = ' '.join(search_split[0:-1])
        try_replace = ' '.join(search_split)
        title_enhanced = re.sub(try_find, try_replace, title)
        if title_enhanced != title:
            print(f'Renaming?\n{title_enhanced}\n{title}')
    else:
        title_enhanced = title
    return title_enhanced

def get_leftovers(p, tmdb_result):
    """
    Keeping infos in the original filename (e.g. codec tags)
    """
    tmdb_id = tmdb_result['result']['id']
    title = tmdb_result['result']['title']
    original_title = tmdb_result['result']['original_title']
    release_year = tmdb_result['release_year']
    db_set = title.split(' ') + original_title.split(' ') + [f'\[tmdbid-{tmdb_id}\]'] + [f'\({release_year}\)']
    db_set = [re.sub('\W', '', e).lower() for e in db_set]
    db_set = set(db_set)
    file_split = p.stem
    file_split = [re.sub('\W', '', e).lower() for e in re.split('\W', file_split) if len(e) > 0]
    file_set = set(file_split)

    left_set = file_set - db_set
    left_final = [x for x in file_split if any([re.search(x, l, flags=re.IGNORECASE) for l in left_set])]
    if len(left_final) > 0:
        left_final = ' '.join(x for x in left_final if len(x) > 1)
        left_final = f' [{left_final}]'
    else:
        left_final = ''

    if len(left_final) > 1:
        print(f'Leftovers: {left_final}')
    return left_final

def get_tmbdid_from_path(p: Path):  # -> tmdbv3api.as_obj.AsObj

    search_split = p.stem
    search_split = split_for_search(search_split)

    while search_split:
        search_str = ' '.join(search_split)
        print(f'Searching for "{search_str}"')
        try:
            compare_search_dict = get_tmdb_from_name(search_str)
            tmdb_result = compare_search_dict[0]

            tmdb_id = tmdb_result['result']['id']
            title = tmdb_result['result']['title']
            year = tmdb_result['release_year']
            leftovers = get_leftovers(p, tmdb_result)
            title_v2 = film_title_add_counter(search_split, title)

            rename_as = f'{title_v2} ({year}){leftovers} [tmdbid-{tmdb_id}]{p.suffix}'

            dct = {p: {'rename_as': rename_as}}
            return dct
        except (ValueError, TypeError) as ex:
            _drop = search_split.pop()

    raise ValueError('No matches found in database')


def tmdb_serie_infos(serie_id):
    """getting all episodes in a series"""
    tv_show = tv.details(serie_id)

    season_dict = {n: season_api.details(tv_show.id, n) for n in range(0, tv_show.number_of_seasons + 1)}
    e_dict = dict.fromkeys(season_dict, {})
    for n, s_details in season_dict.items():
        e_dict[n] = {e.episode_number: {'tmdb': e} for e in s_details.episodes}

    return e_dict


def delete_meta_files(p: Path):
    """
    Delete all files that e.g. Jellyfin creates
    """
    suffix = '.nfo .jpg .png .svg'.split(' ')
    p_list = get_files_in_folder(p, suffix_accepted=suffix)
    for pp in p_list:
        print(f'Delete: {pp}')
    attention_deleting_files(p_list, soft_delete=False)

    # reversed=True, so that subfolders are deleted first
    dir_list = sorted(Path(p).glob('**/*/'), reverse=True)
    for dir in dir_list:
        try:
            Path.rmdir(dir)
            print(f'Deleted: {dir}')
        except OSError:
            print(f'Skipped {dir}')


def serie_path_to_numberss(p: Path):
    p_stem = p.stem
    print('Trying' + p_stem)

    pattern = r"S(\d{1,2})E(\d{1,4})"
    match = re.search(pattern, p_stem, flags=re.IGNORECASE)

    if match:
        season = int(match.group(1))  # Staffelnummer
        episode = int(match.group(2))  # Episodennummer
        print(f"Staffel: {season}, Episode: {episode}")
    else:
        print("Kein Staffel-/Episodenmuster gefunden.")
    return {'season': season, 'episode': episode}


def re_umlaute_replace(s: str, reverse=False):
    umlaute = {'ä': 'ae', 'ö': 'oe', 'ü': 'ue',
               'ß': 'ss'}
    for k, v in umlaute.items():
        if reverse:
            _k, _v = k, v
            k, v = _v, _k

        s = re.sub(k, v, s)
        s = re.sub(k.upper(), v.upper(), s)
    return s


def series_rename_episodes(dir_p: Path):
    """
    dir_p = //Syn723/Serien/Breaking Bad/
        |-- Breaking.Bad.S02E03.Gedaechnisschwund.GERMAN.BluRay.720p.x264-TSCC.mp4
    """
    series_name = dir_p.name
    series_name = re.sub('#|\(engl\)', '', series_name, flags=re.IGNORECASE)
    tmdb_search = tv.search(series_name)
    # todo some episodes are much longer, E1034. Also, some have so S01
    #   - check amount of episodes in movie-db OR maximum number in files
    e_dict = tmdb_serie_infos(tmdb_search['results'][0].id)
    from_to = {}
    for p in get_files_in_folder(dir_p, suffix_accepted=VIDEO_SUFFIX):
        print(f'Starting with: {p}')
        se = serie_path_to_numberss(p)
        s = se['season']
        e = se['episode']
        p_stem = p.stem
        p_stem = re.sub(r'\.', ' ', p_stem)
        p_stem = re.sub(r'\(engl\)', '', p_stem)
        p_stem = re.sub(series_name, '', p_stem, flags=re.IGNORECASE)
        p_stem = re.sub('S\d{1,2}E\d{1,4}', '', p_stem, flags=re.IGNORECASE)
        db_name = e_dict[s][e]['tmdb'].name
        rmv_splits = set(re.split(r'\W', db_name) + re.split(r'\W', re_umlaute_replace(db_name)))
        for n in [x for x in rmv_splits if len(x) > 0]:
            p_stem = re.sub(n, '', p_stem, flags=re.IGNORECASE)
            # Levenshtein.distance("foo", "foobar")
        # p_stem = p_stem.replace(db_name, '')
        p_stem = re.sub(db_name, '', p_stem, flags=re.IGNORECASE)
        p_leftovers = re.split('\W', p_stem)
        p_leftovers = [x for x in p_leftovers if len(x)>0]
        p_leftovers = ' '.join(p_leftovers)
        p_leftovers = f' [{p_leftovers}]' if len(p_leftovers) > 0 else p_leftovers
        tmdb_p = p.parent / remove_ugly_spaces(f'{series_name} S{s:02d}E{e:02d} {db_name}{p_leftovers}{p.suffix}')
        if p == tmdb_p:
            print(f'No changes at {p}')
        else:
            print(f'\t{p}\nto\t{tmdb_p}')
            from_to[p] = tmdb_p
            # user_rename_file(p, tmdb_p)

    for k, v in from_to.items():
        user_rename_fromToDict(from_to, confirm_each=False)
    return


if __name__ == '__main__':
    """
    
    """
    # TMDb-API einrichten
    tmdb = TMDb()
    tmdb.api_key = tmdb_api_key

    # Country-specific, Results which the database shows
    tmdb.language = 'de'  # 'en', 'de'

    # Search Film
    movie = Movie()

    # Search Series
    tv = TV()

    # Search Episodes
    season_api = Season()

    for dir_p in Path('//Syn723/Serien/').glob('**/*/'):
        series_rename_episodes(dir_p)


    # files_list = get_files_in_folder(Path('//Syn723/Filme/#English (engl)'), suffix_accepted=VIDEO_SUFFIX)
    # tmdb.language = 'en'
    #
    # files_list = get_files_in_folder(Path('//Syn723/Filme/irrelevant'), suffix_accepted=VIDEO_SUFFIX)
    # # files_list = get_files_in_folder(Path('//Syn723/Filme/#Ski_Surf'), suffix_accepted=VIDEO_SUFFIX)
    # files_list = get_files_in_folder(Path('//Syn723/Filme/ungesehen'), suffix_accepted=VIDEO_SUFFIX)
    # files_list = get_files_in_folder(Path('//Syn723/Serien/Doktor Who'), suffix_accepted=VIDEO_SUFFIX)
    #
    # tmdb.language = 'de'
    #
    # print(files_list)
    #
    # files_rename_dict = {}
    # fails = []
    # for p in files_list:
    #     try:
    #         dct = get_tmbdid_from_path(p)
    #         files_rename_dict.update(dct)
    #
    #     except (TypeError, ValueError) as ex:
    #         fails.append(p)
    #     print('--------------------------------------------------------------------')
    #
    # for p in fails:
    #     print(f'Failed Movie: {p.stem}\t{p.as_posix()}')
    #
    # for p, v in files_rename_dict.items():
    #     print(f'\t{p.name} -> \nTo\t{v["rename_as"]}')
    #
    # # file_name = "Borat"
    # # file_name = "Harry Potter und die Heiligtümer des Todes - Teil 1"
    # # file_name = 'Harry.Potter.(engl).1.Extended.and.the.Sorcerers.Stone.Extended.Edition.(2001).ENGLISCH DD51 720p BluRay x264-JJ.mp4'
    # # file_name = 'Zootopia.(engl).mp4'
    # # file_name = 'Johnny English 2.mp4'
    # # file_name = 'Türkisch Für Anfänger'
    # # asdf = get_tmbdid_from_path(Path(file_name))
    # # print(asdf)