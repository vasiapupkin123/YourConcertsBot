# coding=utf-8
"""
class extracts info about concerts from local database
"""
from .base import Concert

class LocalConcertsProvider:
    def __init__(self, all_concerts_filename):
        pass

# по идее seatscan не должен писать, а должен лишь возвращать всегда новые концерты при любом внешнем вызове
