def topo_sort(graph):
    graph = dict(graph)
    while graph:
        # Find all items without a parent
        leftmost = [l for l, s in graph.items() if not s]
        if not leftmost:
            raise ValueError('Dependency cycle detected! %s' % graph)
        for result in leftmost:
            yield result
            graph.pop(result)
            for bset in graph.values():
                bset.discard(result)

def get_filters(filters):
    unprocessed = list(filters)
    processed = set()
    graph = dict()

    while unprocessed:
        filter = unprocessed.pop(0)
        graph.setdefault(filter, set())
        for stream in reversed(filter.inputs):
            graph.setdefault(stream.source, set())
            graph[stream.source].add(filter)
            if stream.source not in processed:
                unprocessed.append(stream.source)
                processed.add(stream.source)

    return list(topo_sort(graph))

def draw_graph(streams):
    current_streams = list(streams)
    yield ''.join(s.symbol if s else ' ' for s in current_streams)
    want_filters = get_filters({s.source for s in current_streams})

    def gather_stream(stream, new_pos):
        if current_streams[new_pos] not in (stream, None):
            yield from gather_stream(current_streams[new_pos],
                                     current_streams.index(None))
        if stream is None:
            return
        parts = []
        for i, orig in enumerate(list(current_streams)):
            if orig is stream:
                if i == new_pos:
                    parts.append('├┼┤')
                else:
                    parts.append('└┴┘')
                    current_streams[i] = None
            elif i == new_pos:
                parts.append('┌┬┐')
                current_streams[i] = stream
            elif orig is None:
                parts.append(' ─')
            else:
                parts.append('│┼')
        first_fork = last_fork = None
        for i, part in enumerate(parts):
            if len(part) > 2:  # fork
                last_fork = i
                if first_fork is None:
                    first_fork = i
        if first_fork != last_fork:
            yield ''.join(
                p[0] if i <= first_fork else
                p[1] if i < last_fork else
                p[-1] if i <= last_fork else
                p[1] if len(p) > 2 else p[0]
                for i, p in enumerate(parts))

    def shuffle_streams(wanted, passthru_end):
        while len(current_streams) < len(wanted):
            current_streams.append(None)
        unconnected = set()
        for new_pos, stream in reversed(list(enumerate(wanted))[passthru_end+1:]):
            if stream not in current_streams:
                unconnected.add(stream)
            else:
                yield from gather_stream(stream, new_pos)
        current_streams[:] = wanted
        if unconnected:
            yield ''.join(
                '╻' if s in unconnected else
                '│' if s else ' '
                for s in current_streams)

    while want_filters:
        filter = want_filters.pop(0)
        wanted = [None if s in filter.outputs else s for s in current_streams]
        while wanted and wanted[-1] is None:
            wanted.pop()
        passthru = list(wanted)
        wanted.append(None)
        wanted.extend(filter.outputs)
        end = len(passthru)
        yield from shuffle_streams(wanted, end)
        filter_name = filter.name
        arg_tuples = filter.arg_tuples or (('', ''))
        param_name_size = max(len(n) for n, v in arg_tuples)
        param_value_size = max(len(v) for n, v in arg_tuples)
        port_size = max([len(filter.outputs), len(filter.inputs)])
        box_size = max([len(filter_name), param_name_size + 1 + param_value_size])
        param_value_size = box_size - 1 - param_name_size
        line_prefix = ''.join('│' if s else ' ' for s in current_streams[:end])
        yield ''.join([line_prefix, '╔',
                       ('╪' * len(filter.outputs)).ljust(port_size, '═'),
                       '╤═',
                       '═' * box_size,
                       '═╗'])
        yield ''.join([line_prefix, '║',
                       ''.join(s.type[0] for s in filter.outputs).ljust(port_size, ' '),
                       '│ ',
                       filter_name.ljust(box_size, ' '),
                       ' ║'])
        for param_name, param_value in filter.arg_tuples:
            yield ''.join([line_prefix, '║',
                       ' ' * port_size,
                        '│ ',
                       param_name.rjust(param_name_size, ' '),
                        ':',
                       param_value.ljust(param_value_size, ' '),
                        ' ║'])
        yield ''.join([line_prefix, '║',
                    ''.join(s.type[0] for s in filter.inputs).ljust(port_size, ' '),
                    '│',
                    filter.hash[:box_size+2].ljust(box_size+2),
                    '║'])
        yield ''.join([line_prefix, '╚',
                       ('╪' * len(filter.inputs)).ljust(port_size, '═'),
                       '╧═',
                       '═' * box_size,
                       '═╝'])
        current_streams = passthru + [None] + list(filter.inputs)
