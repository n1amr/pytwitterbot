import os
from json import loads, dumps

from pytwitterbot import data_files


def assert_file(path):
    if not os.path.exists(path):
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        file = open(path, 'w')
        file.close()


def assert_all_files():
    for file in data_files.get_all_files().values():
        assert_file(file)


def load_file_lines(filename):
    with open(data_files.get(filename), 'r') as file:
        lines = file.read().splitlines()
    return lines


def store_file_lines(filename, lines):
    with open(data_files.get(filename), 'w') as file:
        file.write('\n'.join(lines))


def load_json_file(filename):
    with open(data_files.get(filename), 'r') as file:
        j_obj = loads(file.read())
    return j_obj


def store_json_file(filename, j_obj):
    with open(data_files.get(filename), 'w') as file:
        file.write(dumps(j_obj))
