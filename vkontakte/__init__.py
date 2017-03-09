from .grabber_api_methods import *
from .grabber_html_audio import *
from .grabber import *
from .utils import *

import os
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
def get_full_path(fname):
    return os.path.join(PROJECT_ROOT, fname)

VK_PRIVATE_CREDENTIALS = json.loads(open(get_full_path('workdata/credentials.json')).read())
ARCHIVE_FOLDERNAME = get_full_path('userdata/uid_artists_archive/')
COOKIES_FILENAME = get_full_path('workdata/cookies.json')
VK_FIRST = False

class VkDefaultGrabber(VKGrabber):
    def __init__(self, credentials=None, archive_foldername=None, vk_first=None, cookies_filename=None):
        VKGrabber.__init__(self,
                           credentials=credentials or VK_PRIVATE_CREDENTIALS,
                           archive_foldername=archive_foldername or ARCHIVE_FOLDERNAME,
                           vk_first=vk_first or VK_FIRST,
                           cookies_filename=cookies_filename or COOKIES_FILENAME)
