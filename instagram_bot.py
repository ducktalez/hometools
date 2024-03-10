""" Quickstart script for InstaPy usage """

# imports
from instapy import InstaPy
from instapy import smart_run
from instapy import set_workspace

post_url = 'https://www.instagram.com/p/CrtjROzrz0d/'
PATH = r"C:\download\chromedriver_win32\chromedriver.exe"


# set workspace folder at desired location (default is at your home folder)
set_workspace(path='wa_data')

# get an InstaPy session!
session = InstaPy(username="stylersimon@hotmail.de", password="melanin", headless_browser=True)

with smart_run(session):
    # general settings
    session.set_dont_include(["friend1", "friend2", "friend3"])

    # activity
    session.like_by_tags(["natgeo"], amount=10)

session = InstaPy(username="leberkas_simon", password="Logiton015@", headless_browser=True, )
session.login()
session.like_by_tags(["bmw", "mercedes"], amount=5)
