import textwrap


def bytes_to_hex(buffer, bytes_per_row=32, bytes_per_col=1):
    if bytes_per_col == 1:
        if bytes_per_row > 0:
            return '\n'.join(textwrap.wrap(' '.join(['%02X' % b for b in buffer]), (3 * bytes_per_row - 1)))
        else:
            return ' '.join(['%02X' % b for b in buffer])
    else:
        byte_string = ''
        for i, b in enumerate(buffer):
            if i > 0:
                if bytes_per_row > 0 and (i % bytes_per_row) == 0:
                    byte_string += '\n'
                elif (i % bytes_per_col) == 0:
                    byte_string += ' '

            byte_string += '%02x' % b
        return byte_string
