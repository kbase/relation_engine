import os


def get_view_names():
    current_dir = os.path.dirname(__file__)
    view_names = []
    for file_name in os.listdir(current_dir):
        (basename, ext) = os.path.splitext(file_name)
        if ext == '.aql':
            view_names.append(basename)
    return view_names


def get_view_content(view_name):
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, view_name + '.aql')
    if not os.path.isfile(file_path):
        raise ViewNonexistent()
    with open(file_path, 'r') as fd:
        return fd.read()


class ViewNonexistent(Exception):

    def __init__(self):
        pass

    def __str__(self):
        return 'View does not exist. Available views are: ' + str(get_view_names())
