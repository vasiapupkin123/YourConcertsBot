from concerts import ConcertsDefaultGrabber
from vkontakte import VkDefaultGrabber


class TotalDefaultGrabber(VkDefaultGrabber, ConcertsDefaultGrabber):
    def __init__(self):
        VkDefaultGrabber.__init__(self)
        ConcertsDefaultGrabber.__init__(self)
