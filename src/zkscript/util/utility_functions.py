from tx_engine import Script


def optimise_script(script: Script) -> Script:
    """Optimise a script by removing redundant operations."""
    patterns = [['OP_TOALTSTACK','OP_FROMALTSTACK'],['OP_FROMALTSTACK','OP_TOALTSTACK']]

    list_string_script = script.to_string().split()
    n = len(list_string_script)

    out = []
    head, following = 0,1 
    while head < n:
        current_element = list_string_script[head]
        if head == n-1:
            out.append(current_element)
        else:
            next_element = list_string_script[following]
            if [current_element,next_element] in patterns:
                head += 1
                following += 1
            else:
                out.append(current_element)
        head += 1
        following += 1

    return Script.parse_string(' '.join(out))
