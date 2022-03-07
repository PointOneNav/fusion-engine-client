########################################################################################################################
# @brief Argument parser helper classes.
#
# @author Adam Shapiro <adam@pointonenav.com>
#
# @date Created 9/4/2018
########################################################################################################################

# Needed to allow importing of system argparse package below since this module has the same name.
from __future__ import absolute_import

import argparse

from argparse_formatter import FlexiFormatter


# Modified from argparse.ArgumentDefaultsHelpFormatter to omit when default is None.
class ArgumentDefaultsHelpFormatter(argparse.HelpFormatter):
    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not argparse.SUPPRESS and action.default is not None:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


class CapitalisedHelpFormatter(FlexiFormatter, ArgumentDefaultsHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        return super(CapitalisedHelpFormatter, self).add_usage(usage, actions, groups, prefix)


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        if 'formatter_class' not in kwargs:
            kwargs['formatter_class'] = CapitalisedHelpFormatter
        if 'add_help' not in kwargs:
            overwrite_help = True
            kwargs['add_help'] = False
        else:
            overwrite_help = False

        super(ArgumentParser, self).__init__(*args, **kwargs)

        self._positionals.title = 'Positional arguments'
        self._optionals.title = 'Optional arguments'

        if overwrite_help:
            self.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                              help = 'Show this help message and exit.')

    def find_argument(self, option_string):
        return self._option_string_actions.get(option_string, None)

    def remove_argument(self, option_string):
        action = self.find_argument(option_string)
        if action is None:
            return

        for option_string in action.option_strings:
            del self._option_string_actions[option_string]

        for i, entry in enumerate(self._actions):
            if entry is action:
                del self._actions[i]
                break

        for group in self._action_groups:
            for i, entry in enumerate(group._actions):
                if entry is action:
                    del group._actions[i]
                    break
            for i, entry in enumerate(group._group_actions):
                if entry is action:
                    del group._group_actions[i]
                    break


def _find_option(parser, name):
    # If the user specified an option string (-f, --foo), find a matching action and its destination variable name.
    if name.startswith('-'):
        action = None
        action_index = None
        for i, entry in enumerate(parser._actions):
            if name in entry.option_strings:
                action = entry
                action_index = i
                break
    # Otherwise, assume the specified name is a destination name (or positional argument).
    else:
        action = None
        action_index = None
        for i, entry in enumerate(parser._actions):
            if entry.dest == name:
                action = entry
                action_index = i
                break

    if action is None:
        raise ValueError("Option '%s' not found." % name)
    else:
        return action, action_index


def remove_option(parser, name):
    # Find the option.
    action, action_index = _find_option(parser, name)

    # Remove the option.
    parser._actions.pop(action_index)

    for string in action.option_strings:
        if string in parser._option_string_actions:
            del parser._option_string_actions[string]

    # Loop over each action group and remove the option from it if present.
    for group in parser._action_groups:
        for i, entry in enumerate(group._group_actions):
            if entry is action:
                group._group_actions.pop(i)


def rename_option(parser, input, dest=None, *args):
    # Find the option.
    action, action_index = _find_option(parser, input)

    # If the user only wants to change the destination, do that now.
    if len(args) == 0:
        if dest is None:
            raise ValueError("No new name or destination specified.")
        else:
            action.dest = dest.lstrip('-').replace('-', '_')
            return

    # Remove the existing option strings.
    had_option_strings = len(action.option_strings) != 0
    used_optional_as_dest = False
    for string in action.option_strings:
        if string.lstrip('-').replace('-', '_') == action.dest:
            used_optional_as_dest = True

        if string in parser._option_string_actions:
            del parser._option_string_actions[string]

    # Now check if the user specified a new destination (name without leading --).
    new_option_strings = list(args)
    found_positional = False
    for option in new_option_strings:
        if not option.startswith('-'):
            if dest is None:
                dest = option
                found_positional = True
            else:
                raise ValueError("Destination already specified.")

    if found_positional:
        new_option_strings.remove(dest)

    # If all option strings were removed and this was previously optional, move it to the positionals group.
    action.option_strings = new_option_strings
    if len(action.option_strings) == 0:
        if had_option_strings:
            for i, entry in enumerate(parser._optionals._group_actions):
                if entry is action:
                    parser._optionals._group_actions.pop(i)

            parser._positionals._group_actions.append(action)
    # Otherwise, move it to the optionals group (if needed) add the new option strings.
    else:
        if not had_option_strings:
            for i, entry in enumerate(parser._positionals._group_actions):
                if entry is action:
                    parser._positionals._group_actions.pop(i)

            parser._optionals._group_actions.append(action)

        candidate_dest = None
        for string in action.option_strings:
            if candidate_dest is None and string.startswith('--'):
                candidate_dest = string

            parser._option_string_actions[string] = action

        if candidate_dest is None:
            candidate_dest = action.option_strings[0]

        if (used_optional_as_dest or not had_option_strings) and dest is None:
            dest = candidate_dest

    # Update the destination if requested.
    if dest is not None:
        action.dest = dest.lstrip('-').replace('-', '_')
