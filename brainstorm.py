from pathlib import Path
from pydub import AudioSegment, utils
import re


p = Path('/home/simon/Schreibtisch/fragezeichen-merge/fragezeichen-merge/#raw/')
p = Path('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/')

# m = mutagen.File('/home/simon/Schreibtisch/fragezeichen-merge/Hörspiele/Nuhr - Kein Scherz/Dieter Nuhr - Die deutsche Selbstüberschätzung, Teil 2.mp3']
# m = mutagen.File('/home/simon/Schreibtisch/fragezeichen-merge/fragezeichen-merge/002 - Die drei Fragezeichen und der Phantomsse/03 Die drei - Angriff.mp3']


# def stem_normalize(stem):
    # *************************************************************************** #
    # NORMALIZATIONstem
    # === save replaces ===re.sub('&amp;', '&', tmp]

    # print(f'--> &amp; replace\n{tmp}\n{tmp}']
        
    # === meta replaces Wildfire (128kbit_AAC)re.sub(r'\(152kbit_Opus\)|\(\d{1,3}kbit\_[A-Za-z]+\)', '', x, flags=re.IGNORECASE]

    # print(f'--> 152kbit_Opus-group replace\n{tmp}\n{tmp}']

tmp = ["mOat, Rodriguez Jr. - Buggin' Out - Rodriguez Jr. Remix.mp3"]

tmp += [re.sub(u"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642\u2600-\u2B55\u200d\u23cf\u23e9\u231a\ufe0f\u3030]", '', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'\(Official Video\)', '', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'\(\w*\.[a-zA-Z]{2,5}\)', '', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'\w*\.(?:com|net|org|co.uk|de|vu|ru|pl)', '', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'(?<=\W)(produced by|produced|prod\. by|prod by|prod\.|prod)\W', 'prod. ', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'(?<=(\W|\(|\[))(vs\.|vs|versus)', 'vs. ', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'(?<=\W)(^ )', ' ', tmp[-1], flags=re.IGNORECASE)]
tmp += [re.sub(r'\([^\)]*\)|\[[^\]]*\]', '', tmp[-1])]
tmp += [re.sub(r'^ +| +$|(?<= ) ', '', tmp[-1])]
tmp = '\n'.join(tmp)
print(tmp)



# ah = [0.85, 0.6, 0.3]
# ha = [0.3, 0.6, 0.85]
# test = [0.15, 0.4, 0.7]
# x = 0.4
# sum(int(x+i) for i in [.15, .4, .7])
# a = [sum(int(x+i) for i in [.15, .4, .7]) for x in [0.1, 0.4, 0.7, 1]]
# b = [sum(int(x+1-i) for i in [.85, .6, .3]) for x in [0.1, 0.4, 0.7, 1]]
# c = [int(x+.15)+int(x+.4)+int(x+.7) for x in [0.1, 0.4, 0.7, 1]]