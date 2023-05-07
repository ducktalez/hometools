from pathlib import Path
import re
import subprocess
from pydub import AudioSegment


folder_grouped = Path('/home/simon/Schreibtisch/fragezeichen-merge/grouped/')  # use any mask suitable for you
for p in folder_grouped.glob('*'):
    # p = Path('/home/simon/Schreibtisch/test/002 - Die drei Fragezeichen und der Phantomsse/')  # use any mask suitable for you

    files = list(p.glob('*.mp3'))
    files.sort(key=lambda x: x.stem)
    filestems = "\n".join([i.stem for i in files])

    if Path(f"/home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}.mp3").is_file():
        print(f"Already done: /home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}.mp3")
    else:
        files.sort(key=lambda x: int(x.stem.split('Teil ')[-1]))
        print(f"Creating /home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}.mp3 from files:")
        filestems = "\n".join([i.stem for i in files])
        print(f'{filestems}')

        mp3files = [AudioSegment.from_file(i, format='mp3') for i in files]
        test = sum(mp3files)

        file_handle = test.export(f"/home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}.mp3", format="mp3", bitrate='128k')
        print('...done.')
        # file_handle = test.export(f"/home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}128k.mp3", format="mp3", bitrate='128k')
        # file_handle = test.export(f"/home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}192k.mp3", format="mp3", bitrate='192k')
        # file_handle = test.export(f"/home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}256k.mp3", format="mp3", bitrate='256k')
        # file_handle = test.export(f"/home/simon/Schreibtisch/fragezeichen-merge/DONE-pyversion/{p.stem}320k.mp3", format="mp3", bitrate='320k')

    # num = p.name.split(' - ')[0]
    # val = files[-1].stem.replace(num, '')
    # val = re.sub('\D', '', val)
    # if int(val) == len(files):
    #     pass
    # else:
    #     print(f'{val}\t{len(files)}\t{files[-1].stem}')

    # ##******************#
    # concat_files = '|'.join([f'{i.name}' for i in files])
    # concat_files_abs = '|'.join([f'{i}' for i in files])
    # output_file = f'"/home/simon/Schreibtisch/fragezeichen-merge/DONE/{p.stem}.mp3"'
    # anywhere_shell_ffmpeg_convert = f'ffmpeg -i "concat:{concat_files_abs}" -acodec copy {output_file}'
    # shell_ffmpeg_convert = f'ffmpeg -i "concat:{concat_files}" -acodec copy {output_file}'
    # print(anywhere_shell_ffmpeg_convert)

    # -c:a ac3 -b:a 160k output.m4a
    # -c:a ac3 -b:a 192k
    # ffmpeg -i "concat:/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 01.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 02.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 03.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 04.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 05.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 06.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 07.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 08.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 09.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 10.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 11.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 12.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 13.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 14.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 15.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 16.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 17.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 18.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 19.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 20.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 21.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 22.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 23.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 24.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 25.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 26.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 27.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 28.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 29.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 30.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 31.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 32.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 33.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 34.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 35.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 36.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 37.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 38.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 39.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 40.mp3" -c:a ac3 -b:a 192k "/home/simon/Schreibtisch/fragezeichen-merge/DONE/203 out 192.m4a"
    # ffmpeg -i "concat:/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/01 Die drei - Wertvolle Sammlerstücke.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/02 Die drei - Ein orginal Mobimec.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/03 Die drei - Drei fanatische Sammler.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/04 Die drei - Schlupfkrabbler.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/05 Die drei - Erdbebensicher.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/06 Die drei - Raus aus der Schusslinie.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/07 Die drei - Was ist in der Kiste.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/08 Die drei - Der kreative Kopf der Firma.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/09 Die drei - Roboter.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/10 Die drei - Rohrpost der besonderen Art.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/11 Die drei - Die Stadt der Engel.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/12 Die drei - Im Dämmerlicht der Kirche.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/13 Die drei - Zahlenrätsel.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/119 - Die drei Fragezeichen - Der geheime Schlüssel/14 Die drei - Kostenlose Werbung.mp3" -c:a ac3 -b:a 160k -acodec copy "/home/simon/Schreibtisch/fragezeichen-merge/DONE/output.m4a"
    # ffmpeg -i "concat:/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 01.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 02.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 03.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 04.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 05.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 06.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 07.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 08.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 09.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 10.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 11.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 12.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 13.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 14.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 15.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 16.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 17.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 18.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 19.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 20.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 21.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 22.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 23.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 24.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 25.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 26.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 27.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 28.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 29.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 30.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 31.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 32.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 33.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 34.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 35.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 36.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 37.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 38.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 39.mp3|/home/simon/Schreibtisch/fragezeichen-merge/grouped/203 - Tauchgang ins Ungewisse/Die drei ___ - 203 - Tauchgang ins Ungewisse - Teil 40.mp3" -acodec copy "/home/simon/Schreibtisch/fragezeichen-merge/DONE/203 - Tauchgang ins Ungewisse.mp3"

    # process = subprocess.run(shell_ffmpeg_convert, cwd=p)
    # print('\n'.join(i.stem for i in files))
    # print(f"{p.parent}/{p.stem}.mp3")

# file_handle2 = mp3files[0].export(f"{p.parent}/{p.stem}_192k.mp3", bitrate="192k")
# file_handle3 = mp3files[0].export(f"{p.parent}/{p.stem}_256k.mp3", bitrate="256k")
# file_handle4 = mp3files[0].export(f"{p.parent}/{p.stem}_320k.mp3", bitrate="320k")
# to234 = mp3files[0].export(f"{p.parent}/{p.stem}_nix.mp3")
# mp3files[0].export(f"{p.parent}/{p.stem}_raw.mp3", format='raw')  # parameters=["-ac", "2", "-ar", "8000"])


# p = Path('/media/simon/Volume/fragezeichen-merge')
# p = Path('/home/simon/Schreibtisch/fragezeichen-merge/#raw/')
# mp3files = list(p.rglob('*.mp3'))
# mp3names = [i.name for i in mp3files]
# for f in mp3files:
#     # 'Die drei ___ - 148 - und die feurige Flut - Teil 20.mp3'
#     die_drei, num, title, cnt = f.name.split(' - ')
#     p_new = (f.parent / f'{num} - {title}/{f.name}')
#     print(f'{f} ->\n{p_new}')
#     p_new.parent.mkdir(parents=True, exist_ok=True)
#     f.rename(p_new)


# for p in Path('/home/simon/Schreibtisch/fragezeichen-merge/grouped/').glob('*'):
#     split = p.name.split(' - ')
#     if p.is_dir():
#         print(f'{split[0]} --- {split[-1]}')
#     else:
#         print('asdafd')
