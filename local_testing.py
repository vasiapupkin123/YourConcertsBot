from grabber import TotalDefaultGrabber

grabber = TotalDefaultGrabber()
print(grabber.get_concerts_in_text(['Сплин']))
print(grabber.get_audios(7235317))
print(grabber.get_friends_id_list(7235317))
