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
import copy

from argparse_formatter import FlexiFormatter


class TriStateBooleanAction(argparse.Action):
    POSSIBLE_VALUES = ('true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', 'on', 'off', '1', '0')

    """!
    @brief A tri-state boolean action that can be `None` if not specified.

    This action is similar to `argparse.BooleanOptionalAction` (Python 3.9+), except that it adds two additional
    features:
    1. The user may specify an optional value string in addition to `--foo` and `--no-foo`. Supported values include:
       `true, false, t, f, yes, no, y, n, on, off, 1, 0`
    2. By default, the argument defaults to `None` if not specified, rather than `True` or `False`. This allows the
       application to explicitly detect if the argument was not specified and take an alternative action. `default` may
       be set to `True` or `False` to disable this behavior.

    Example usage:
    ```
                 # None (unless `default` is set)
    --foo        # True
    --foo=true   # True
    --foo=false  # False
    --no-foo     # False
    ```
    """
    def __init__(self,
                 option_strings,
                 dest,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        for option_string in option_strings:
            if not option_string.startswith('-'):
                raise ValueError('Positional arguments not supported for tri-state bool actions.')

        # Unfortunately Python argparse does not have a way to selectively capture an optional argument value only if it
        # meets some criteria. This means that we cannot support argument syntax with spaces:
        #   --foo true
        # If we tried to by setting nargs='?', if the user did not specify a truthiness value and just did --foo, any
        # positional arguments after --foo would be captured incorrectly. Python would not know that we don't want to
        # capture it. For example, if the user specified:
        #  --foo abc def
        # abc would be captured by --foo, and would not show up as a positional argument.
        #
        # To get around this, we only support = syntax, and we add all --foo=value variants as option names
        # (option_strings) rather than values. For ['--foo', '--bar'], we generate:
        #   --foo
        #   --no-foo
        #   --foo=true
        #   --foo=false
        #   ...
        #   --bar
        #   ...
        #
        # By default, when you run --help, the resulting output will be a bit of a mess:
        #   Optional arguments:
        #     --foo, --no-foo, --foo=true, --foo=false, --foo=t, ...
        #
        # We provide the TriStateBoolFormatter class below to instead print:
        #   Optional arguments:
        #     --foo[=<true, false, t, f, yes, no, y, n, on, off, 1, 0>], --no-foo
        _option_strings = copy.copy(option_strings)
        long_option_strings = [o for o in option_strings if o.startswith('--')]
        _option_strings.extend([f'--no-{o[2:]}' for o in long_option_strings])
        for v in self.POSSIBLE_VALUES:
            _option_strings.extend([f'{o}={v}' for o in long_option_strings])

        if help is not None and default is not None and default != argparse.SUPPRESS:
            help += " (default: %(default)s)"

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=1 if len(_option_strings) == 0 else 0,
            const=True,
            default=default,
            type=None,
            choices=None,
            required=required,
            help=help,
            metavar=None)

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string is None:
            if len(values) == 0:
                # Caught in constructor. Should not happen.
                raise ValueError('Value not specified.')
            else:
                parts = [self.dest, values[0]]
        else:
            parts = option_string.split('=')

        name = parts[0]
        if len(parts) > 1:
            # Taken from distutils.util.strtobool().
            value = parts[1].lower()
            if value in ('y', 'yes', 't', 'true', 'on', '1'):
                result = True
            elif value in ('n', 'no', 'f', 'false', 'off', '0'):
                result = False
            else:
                raise ValueError("Invalid boolean value %r." % value)
        elif name.startswith('--no-'):
            # There is a special case here. If the user named the argument `--no-foo`, they will have the options:
            #   1. --no-foo
            #   2. --no-no-foo
            # We strip out the leading `--no-` to check if (1) is present in the options strings. If so, this is case
            # (2) and they want us to return false. If not, this is case (1) and we should return true.
            #
            # For the more typical `--bar`, we'll only ever see `--no-` prefix for the false case, and this condition
            # will correctly identify case (2):
            #   1. --foo
            #   2. --no-bar
            if name.replace('--no-', '--') in self.option_strings:
                result = False
            else:
                result = True
        else:
            result = True

        setattr(namespace, self.dest, result)


class ExtendedBooleanAction(TriStateBooleanAction):
    """!
    @brief A boolean action accepting more values than a typical `store_true` or `store_false` action.

    This action is similar to `argparse.BooleanOptionalAction` (Python 3.9+), except that in addition to `--foo` and
    `-no-foo`, the user may also specify any of the following values (e.g., `--foo=off`):
    `true, false, t, f, yes, no, y, n, on, off, 1, 0`

    This makes it easier to specify boolean options via command line scripts by simply changing the value rather than
    having to include/omit the argument itself.

    Example usage:
    ```
                 # False (unless `default` is set to `True`)
    --foo        # True
    --foo=true   # True
    --foo=false  # False
    --no-foo     # False
    ```
    """
    POSSIBLE_VALUES = ('true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', 'on', 'off', '1', '0')

    def __init__(self, *args, **kwargs):
        if kwargs.get('default', None) is None:
            kwargs['default'] = False
        super().__init__(*args, **kwargs)


class CSVAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not isinstance(values, list):
            values = [values]

        flattened_values = [v.strip() for entry in values for v in entry.split(',')]
        result = getattr(namespace, self.dest)
        if result is None:
            result = []
        result.extend(flattened_values)
        setattr(namespace, self.dest, result)


class TriStateBoolFormatter(argparse.HelpFormatter):
    def _format_action_invocation(self, action):
        if isinstance(action, TriStateBooleanAction):
            options_printed = False
            def _format(option):
                # Note: Special case handling for --no-no-foo. See explanation in TriStateBooleanAction.
                if ((option.startswith('--no-') and option.replace('--no-', '--') in action.option_strings) or
                    not option.startswith('--')):
                    return option
                elif '=' in option:
                    return None
                else:
                    nonlocal options_printed
                    if options_printed:
                        return f"{option}[=...]"
                    else:
                        options_printed = True
                        return f"{option}[=<{', '.join(TriStateBooleanAction.POSSIBLE_VALUES)}>]"

            strings = [_format(o) for o in action.option_strings]
            return ', '.join([o for o in strings if o is not None])
        else:
            return super(TriStateBoolFormatter, self)._format_action_invocation(action)


# Alias for convenience.
class ExtendedBooleanFormatter(TriStateBoolFormatter):
    pass


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


class FlexiFormatterNoDescription(FlexiFormatter):
    def _format_text(self, text):
        if '%(prog)' in text:
            text = text % dict(prog=self._prog)
        return text + '\n\n'


class CapitalisedHelpFormatter(FlexiFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        return super(CapitalisedHelpFormatter, self).add_usage(usage, actions, groups, prefix)


class CapitalisedHelpFormatterNoDescription(FlexiFormatterNoDescription):
    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = 'Usage: '
        return super(CapitalisedHelpFormatterNoDescription, self).add_usage(usage, actions, groups, prefix)


def compose_formatter(*formatters) -> argparse.HelpFormatter:
    """!
    @brief Generate a new argparse `HelpFormatter` class that inherits from ome or more specified formatter classes
           in the order they are listed.

    @param formatters A list of names of one or more formatter classes to use. Each class must inherit from
           `HelpFormatter`.

    @return A new class that inherits from each of the listed classes.
    """
    if len(formatters) == 0:
        return argparse.HelpFormatter
    else:
        result = formatters[0]
        for formatter in formatters[1:]:
            class Formatter(result, formatter):
                pass
            result = Formatter
    return result


DefaultFormatter = compose_formatter(ArgumentDefaultsHelpFormatter,
                                     TriStateBoolFormatter,
                                     CapitalisedHelpFormatterNoDescription)


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        if 'formatter_class' not in kwargs:
            kwargs['formatter_class'] = DefaultFormatter
        if 'add_help' not in kwargs:
            overwrite_help = True
            kwargs['add_help'] = False
        else:
            overwrite_help = False

        super(ArgumentParser, self).__init__(*args, **kwargs)

        self._positionals.title = 'Positional Arguments'
        self._optionals.title = 'Optional Arguments'

        if overwrite_help:
            self.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                              help='Show this help message and exit.')

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
