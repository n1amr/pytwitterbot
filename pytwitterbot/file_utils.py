import json
import os


def ensure_parent_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def touch_file(path):
    ensure_parent_dir(path)
    if not os.path.exists(path):
        with open(path, 'a'):
            pass


def load_json(path):
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def load_text(path):
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()


def write_json(data, path):
    ensure_parent_dir(path)
    with open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def write_bytes(data: bytearray, path: str):
    ensure_parent_dir(path)
    with open(path, 'wb') as f:
        f.write(data)


def write_text(text, path):
    ensure_parent_dir(path)
    with open(path, 'w', encoding='utf-8') as file:
        file.write(text)


def load_text_lines(path):
    with open(path, 'r') as file:
        return [line.rstrip('\r\n') for line in file]


def write_text_lines(lines, path):
    ensure_parent_dir(path)
    with open(path, 'w') as file:
        file.write('\n'.join(lines))


def load_commentable_file(path):
    lines = load_text_lines(path)
    lines = [_strip_inline_comment(line) for line in lines]
    lines = [line.strip() for line in lines]
    lines = [line for line in lines if line]
    return lines


def _strip_inline_comment(line: str):
    if '#' not in line:
        return line
    comment_start = line.index('#')
    return line[:comment_start]
