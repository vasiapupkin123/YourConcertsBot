from .base import *
from .provider_seatscan import *
from .provider import *

import os
MODULE_PATH = os.path.dirname(os.path.abspath(__file__))
def get_full_path(fname):
    return os.path.join(MODULE_PATH, fname)


folder = 'workdata/'
seatscan_artist_2_url_json_filename = get_full_path(folder + 'seatscan_artist_2_url_2.json')
seatscan_artist_2_artist_filename = get_full_path(folder + 'seatscan_artist_2_artist.json')
seatscan_artists_failed_filename = get_full_path(folder + 'seatscan_artists_that_failed.txt')
all_concerts_filename = get_full_path(folder + 'all_concerts.json')

class ConcertsDefaultGrabber(ConcertsProvider):
    def __init__(self):
        ConcertsProvider.__init__(self,
                                  seatscan_artist_2_url_json_filename=seatscan_artist_2_url_json_filename,
                                  seatscan_artist_2_artist_json_filename=seatscan_artist_2_artist_filename,
                                  seatscan_artists_that_failed_on_seatscan_filename=seatscan_artists_failed_filename,
                                  all_concerts_filename=all_concerts_filename)