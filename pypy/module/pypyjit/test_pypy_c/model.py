import py
import re
import os.path
from pypy.tool.jitlogparser.parser import parse, Function
from pypy.tool.jitlogparser.storage import LoopStorage


def find_ids_range(code):
    """
    Parse the given function and return a dictionary mapping "ids" to
    "line ranges".  Ids are identified by comments with a special syntax::

        # "myid" corresponds to the whole line
        print 'foo' # ID: myid
    """
    result = {}
    start_lineno = code.co.co_firstlineno
    for i, line in enumerate(py.code.Source(code.source)):
        m = re.search('# ID: (\w+)', line)
        if m:
            name = m.group(1)
            lineno = start_lineno+i
            result[name] = xrange(lineno, lineno+1)
    return result

def find_ids(code):
    """
    Parse the given function and return a dictionary mapping "ids" to
    "opcodes".
    """
    ids = {}
    ranges = find_ids_range(code)
    for name, linerange in ranges.iteritems():
        opcodes = [opcode for opcode in code.opcodes
                   if opcode.lineno in linerange]
        ids[name] = opcodes
    return ids


class Log(object):
    def __init__(self, func, rawtraces):
        storage = LoopStorage()
        traces = [parse(rawtrace) for rawtrace in rawtraces]
        traces = storage.reconnect_loops(traces)
        self.loops = [LoopWithIds.from_trace(trace, storage) for trace in traces]

    def _filter(self, loop, is_entry_bridge=False):
        return is_entry_bridge == '*' or loop.is_entry_bridge == is_entry_bridge

    def loops_by_filename(self, filename, **kwds):
        """
        Return all loops which start in the file ``filename``
        """
        return [loop for loop in self.loops
                if loop.filename == filename and self._filter(loop, **kwds)]

    def loops_by_id(self, id, **kwds):
        """
        Return all loops which contain the ID ``id``
        """
        return [loop for loop in self.loops
                if loop.has_id(id) and self._filter(loop, **kwds)]


class LoopWithIds(Function):

    is_entry_bridge = False

    def __init__(self, *args, **kwds):
        Function.__init__(self, *args, **kwds)
        self.compute_ids()

    @classmethod
    def from_trace(cls, trace, storage):
        res = cls.from_operations(trace.operations, storage)
        res.is_entry_bridge = 'entry bridge' in trace.comment
        return res

    def compute_ids(self):
        self.ids = {}
        self.code = None
        if not self.filename:
            return
        self.code = self.chunks[0].getcode()
        ids = find_ids(self.code)
        all_my_opcodes = self.get_set_of_opcodes()
        # XXX: for now, we just look for the first opcode in the id range
        for id, opcodes in ids.iteritems():
            targetop = opcodes[0]
            if targetop in all_my_opcodes:
                self.ids[id] = opcodes

    def get_set_of_opcodes(self):
        res = set()
        for chunk in self.chunks:
            opcode = self.code.map[chunk.bytecode_no]
            res.add(opcode)
        return res

    def has_id(self, id):
        return id in self.ids

    def _ops_for_chunk(self, chunk, include_debug_merge_points):
        for op in chunk.operations:
            if op.name != 'debug_merge_point' or include_debug_merge_points:
                yield op

    def allops(self, include_debug_merge_points=False):
        for chunk in self.chunks:
            for op in self._ops_for_chunk(chunk, include_debug_merge_points):
                yield op

    def ops_by_id(self, id, include_debug_merge_points=False):
        target_opcodes = self.ids[id]
        for chunk in self.chunks:
            opcode = self.code.map[chunk.bytecode_no]
            if opcode in target_opcodes:
                for op in self._ops_for_chunk(chunk, include_debug_merge_points):
                    yield op


    @classmethod
    def parse_ops(cls, src):
        ops = [cls.parse_op(line) for line in src.splitlines()]
        return [op for op in ops if op is not None]

    @classmethod
    def parse_op(cls, line):
        # strip comment
        if '#' in line:
            line = line[:line.index('#')]
        # find the resvar, if any
        if '=' in line:
            resvar, _, line = line.partition('=')
            resvar = resvar.strip()
        else:
            resvar = None
        line = line.strip()
        if not line:
            return None
        opname, _, args = line.partition('(')
        opname = opname.strip()
        assert args.endswith(')')
        args = args[:-1]
        args = args.split(',')
        args = map(str.strip, args)
        return opname, resvar, args

    def match(self, expected_src):
        alpha_map = {}
        def match_var(v1, v2):
            if v1 not in alpha_map:
                alpha_map[v1] = v2
            assert alpha_map[v1] == v2, "variable mismatch"
        #
        expected_ops = self.parse_ops(expected_src)
        ops = list(self.allops())
        assert len(ops) == len(expected_ops), "wrong number of operations"
        for op, (exp_opname, exp_res, exp_args) in zip(ops, expected_ops):
            assert op.name == exp_opname
            match_var(op.res, exp_res)
            assert len(op.args) == len(exp_args), "wrong number of arguments"
            for arg, exp_arg in zip(op.args, exp_args):
                match_var(arg, exp_arg)
        return True
