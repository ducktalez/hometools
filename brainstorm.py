from pathlib import Path
from pydub import AudioSegment, utils


p = Path('/home/simon/Schreibtisch/fragezeichen-merge/fragezeichen-merge/#raw/')
p = Path('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/')

for f in p.rglob('*.mp3'):
    # m = mutagen.File('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/Nuhr - Kein Scherz/Dieter Nuhr - Die deutsche Selbstüberschätzung, Teil 2.mp3')
    # m = mutagen.File('/home/simon/Schreibtisch/fragezeichen-merge/fragezeichen-merge/002 - Die drei Fragezeichen und der Phantomsse/03 Die drei - Angriff.mp3')

    pd = utils.mediainfo(f)
    print(pd['TAG'])
