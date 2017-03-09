def replace_html_symbols(text):
    d = {'&#39;': "'", '&#33;': '!'}
    for b, s in d.items():
        text = text.replace(b, s)
    return text


def count_list_values(l):
    # ['a','a','b','b','a','c'] -> [['a':3],['b':2],['c':1]]
    d = {x: l.count(x) for x in l}
    dl = sorted(d, key=lambda k: -d[k])
    d = [[k, d[k]] for k in dl]
    return d
