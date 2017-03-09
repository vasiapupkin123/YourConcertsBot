import os
from multiprocessing import Pool


def remove_duplicates_from_seq_without_reordering(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def multithread_it(func, data, threads=None, max_threads=25, min_threads=1):
    if not threads:
        threads = max(min_threads, min(len(data), max_threads))
    with Pool(threads) as p:
        result = p.map(func, data)
    return result

def get_full_path(fname):
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(PROJECT_ROOT, fname)
