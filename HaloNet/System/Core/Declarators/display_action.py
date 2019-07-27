import sys


def display_action(func):
    outer_frame_locals = sys._getframe(1).f_locals

    if 'display_actions' not in outer_frame_locals:
        outer_frame_locals['display_actions'] = list()
    outer_frame_locals['display_actions'].append(func)
    return func
