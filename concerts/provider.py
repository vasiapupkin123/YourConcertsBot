# coding=utf-8
from concerts import SeatscanGrabber


class ConcertsProvider():
    """
    class extracts info about concerts from several sources: sites and local database
    it decides whether it's better to check on web for new concerts or use only local
    """

    def __init__(self,
                 seatscan_artist_2_url_json_filename,
                 seatscan_artist_2_artist_json_filename,
                 seatscan_artists_that_failed_on_seatscan_filename,
                 all_concerts_filename):
        self.seatscan = SeatscanGrabber(
            artist_2_url_json_filename=seatscan_artist_2_url_json_filename,
            artist_2_artist_json_filename=seatscan_artist_2_artist_json_filename,
            artists_that_failed_on_seatscan_filename=seatscan_artists_that_failed_on_seatscan_filename,
            all_concerts_filename=all_concerts_filename
        )

    def get_concerts(self, artists, save_to_json_filename=None, log_print_freq=None):
        return self.seatscan.get_concerts(artists, save_to_json_filename, log_print_freq)

    def get_text_from_concerts_list(self, concerts=None, cities=None, delim='\n---\n'):
        return self.seatscan.get_text_from_concerts_list(concerts, cities, delim)

    def get_concerts_in_text(self, artists, cities=None, delim='\n---\n', log_print_freq=None):
        return self.seatscan.get_concerts_in_text(artists, cities, delim, log_print_freq)
