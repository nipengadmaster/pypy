import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin


class SendTests:

    def test_green_send(self):
        myjitdriver = JitDriver(greens = ['i'], reds = ['counter'])
        lst = ["123", "45"]
        def f(i):
            counter = 20
            c = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i)
                myjitdriver.jit_merge_point(counter=counter, i=i)
                s = lst[i]
                c = len(s)
                counter -= 1
            return c
        res = self.meta_interp(f, [1])
        assert res == 2
        self.check_loops({'jump': 1,
                          'int_sub': 1, 'int_gt' : 1,
                          'guard_true': 1})    # all folded away

    def test_red_builtin_send(self):
        myjitdriver = JitDriver(greens = [], reds = ['i', 'counter'])
        lst = [{1:1, 2:2, 3:3}, {4:4, 5:5}]
        def externfn(i):
            return lst[i]
        def f(i):
            counter = 20
            res = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i)
                myjitdriver.jit_merge_point(counter=counter, i=i)
                dct = externfn(i)
                res = len(dct)
                counter -= 1
            return res
        res = self.meta_interp(f, [1], policy=StopAtXPolicy(externfn))
        assert res == 2
        if self.type_system == 'ootype':
            self.check_loops(call=1, builtin=1) # 'len' remains
        else:
            # 'len' becomes a getfield('num_items') for now in lltype,
            # which is itself encoded as a 'getfield_gc'
            self.check_loops(call=1, getfield_gc=1)

    def test_send_to_single_target_method(self):
        myjitdriver = JitDriver(greens = [], reds = ['i', 'counter'])
        class Foo:
            def meth(self, y):
                return self.x + y
        def externfn(i):
            foo = Foo()
            foo.x = i * 42
            return foo
        def f(i):
            counter = 20
            res = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i)
                myjitdriver.jit_merge_point(counter=counter, i=i)
                foo = externfn(i)
                res = foo.meth(i)
                counter -= 1
            return res
        res = self.meta_interp(f, [1], policy=StopAtXPolicy(externfn),
                               backendopt=True)
        assert res == 43
        self.check_loops({'call': 1, 'guard_no_exception': 1,
                          'getfield_gc': 1,
                          'int_add': 1,
                          'jump': 1, 'int_gt' : 1, 'guard_true' : 1,
                          'int_sub' : 1})

    def test_red_send_to_green_receiver(self):
        myjitdriver = JitDriver(greens = ['i'], reds = ['counter', 'j'])
        class Foo(object):
            def meth(self, i):
                return 42 + i
        class Foobar(Foo):
            def meth(self, i):
                return 146 + i
        lst = [Foo(), Foo(), Foobar(), Foo(), Foobar(), Foo()]
        def f(i, j):
            counter = 20
            res = 0
            while counter > 0:
                myjitdriver.can_enter_jit(counter=counter, i=i, j=j)
                myjitdriver.jit_merge_point(counter=counter, i=i, j=j)
                foo = lst[i]
                res = foo.meth(j)
                counter -= 1
            return res
        res = self.meta_interp(f, [4, -1])
        assert res == 145
        self.check_loops(int_add = 1)

    def test_oosend_base(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W1(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W2(self.y + 100)
            def getvalue(self):
                return self.y
        def f(x, y):
            if x & 1:
                w = W1(x)
            else:
                w = W2(x)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, w=w)
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 14])
        assert res == 17
        res = self.meta_interp(f, [4, 14])
        assert res == 1404
        self.check_loops(guard_class=0, new_with_vtable=0)

    def test_three_receivers(self):
        myjitdriver = JitDriver(greens = [], reds = ['y'])
        class Base:
            pass
        class W1(Base):
            def foo(self):
                return 1
        class W2(Base):
            def foo(self):
                return 2
        class W3(Base):
            def foo(self):
                return 3
        def externfn(y):
            if y % 4 == 0: return W1()
            elif y % 4 == 3: return W2()
            else: return W3()
        def f(y):
            while y > 0:
                myjitdriver.can_enter_jit(y=y)
                myjitdriver.jit_merge_point(y=y)                
                w = externfn(y)
                w.foo()
                y -= 1
            return 42
        policy = StopAtXPolicy(externfn)
        for j in range(69, 75):
            res = self.meta_interp(f, [j], policy=policy)
            assert res == 42
            self.check_loop_count(3)

    def test_oosend_guard_failure(self):
        py.test.skip("Unsupported yet")
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W2(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W1(self.y + 100)
            def getvalue(self):
                return self.y
        def f(x, y):
            if x & 1:
                w = W1(x)
            else:
                w = W2(x)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, w=w)
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 28])
        assert res == f(3, 28)
        res = self.meta_interp(f, [4, 28])
        assert res == f(4, 28)
        # The effect of the ClassGuard generated by the oosend to incr()
        # should be to unroll the loop, giving two copies of the body in
        # a single bigger loop with no failing guard except the final one.
        self.check_loop_count(1)
        self.check_loops(guard_class=0,
                                int_add=2, int_sub=2)
        self.check_jumps(14)

    def test_oosend_guard_failure_2(self):
        py.test.skip("Unsupported yet")
        # same as above, but using prebuilt objects 'w1' and 'w2'
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W2(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W1(self.y + 100)
            def getvalue(self):
                return self.y
        w1 = W1(10)
        w2 = W2(20)
        def f(x, y):
            if x & 1:
                w = w1
            else:
                w = w2
            while y > 0:
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 28])
        assert res == f(3, 28)
        res = self.meta_interp(f, [4, 28])
        assert res == f(4, 28)
        self.check_loop_count(1)
        self.check_loops(guard_class=0,
                                int_add=2, int_sub=2)
        self.check_jumps(14)

    def test_oosend_different_initial_class(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'w'])
        class Base:
            pass
        class W1(Base):
            def __init__(self, x):
                self.x = x
            def incr(self):
                return W2(self.x + 1)
            def getvalue(self):
                return self.x
        class W2(Base):
            def __init__(self, y):
                self.y = y
            def incr(self):
                return W2(self.y * 2)
            def getvalue(self):
                return self.y
        def f(x, y):
            w = W1(x)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, w=w)
                myjitdriver.jit_merge_point(x=x, y=y, w=w)
                w = w.incr()
                y -= 1
            return w.getvalue()
        res = self.meta_interp(f, [3, 28])
        assert res == f(3, 28)
        # The effect of the ClassGuard generated by the oosend to incr()
        # should be to unroll the first iteration of the loop.  Indeed,
        # looking only at the loop, we deduce that the class of 'w' is 'W2'.
        # However, this doesn't match the initial value of 'w'.
        # XXX This not completely easy to check...
        self.check_loop_count(1)
        self.check_loops(int_add=0, int_mul=1, guard_class=0)

    def test_indirect_call_unknown_object_1(self):
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y'])
        def getvalue2():
            return 2
        def getvalue25():
            return 25
        def getvalue1001():
            return -1001
        def externfn(n):
            if n % 5:
                return getvalue2
            elif n % 7:
                return getvalue25
            else:
                return getvalue1001
        def f(y):
            x = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y)
                myjitdriver.jit_merge_point(x=x, y=y)
                x += externfn(y)()
                y -= 1
            return x
        res = self.meta_interp(f, [198], policy=StopAtXPolicy(externfn))
        assert res == f(198)
        self.check_loop_count(3)

    def test_indirect_call_unknown_object_2(self):
        py.test.skip("XXX fix me!!!!!!! problem in optimize.py")
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y', 'state'])
        def getvalue2():
            return 2
        def getvalue25():
            return 25
        def getvalue1001():
            return -1001

        class State:
            count = 0
            def externfn(self, n):
                assert n == 198 - self.count
                self.count += 1
                if n % 5:
                    return getvalue2
                elif n % 7:
                    return getvalue25
                else:
                    return getvalue1001
        def f(y):
            state = State()
            x = 0
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y, state=state)
                myjitdriver.jit_merge_point(x=x, y=y, state=state)
                x += state.externfn(y)()
                y -= 1
            return x
        res = self.meta_interp(f, [198],
                               policy=StopAtXPolicy(State.externfn.im_func))
        assert res == f(198)
        self.check_loop_count(3)

    def test_two_behaviors(self):
        py.test.skip("XXX fix me!!!!!!! problem in optimize.py")
        myjitdriver = JitDriver(greens = [], reds = ['x', 'y'])
        class Int:
            def __init__(self, value):
                self.value = value
        cases = [True]*100 + [False, True]*10 + [False]*20
        def f(y):
            x = Int(0)
            while y > 0:
                myjitdriver.can_enter_jit(x=x, y=y)
                myjitdriver.jit_merge_point(x=x, y=y)
                y -= 1
                if cases[y]:
                    x = Int(x.value + 1)
            return x.value
        res = self.meta_interp(f, [len(cases)])
        assert res == 110
        self.check_loop_count(2)

    def test_three_cases(self):
        class Node:
            def __init__(self, x):
                self.x = x
        myjitdriver = JitDriver(greens = [], reds = ['node'])
        def f(n):
            node = Node(n)
            while node.x > 0:
                myjitdriver.can_enter_jit(node=node)
                myjitdriver.jit_merge_point(node=node)
                if node.x < 40:
                    if node.x < 20:
                        node = Node(node.x - 1)
                    node = Node(node.x - 1)
                node = Node(node.x - 1)
            return node.x
        res = self.meta_interp(f, [55])
        assert res == f(55)
        self.check_tree_loop_count(2)

    def test_three_classes(self):
        class Base:
            pass
        class A(Base):
            def f(self):
                return 1
        class B(Base):
            def f(self):
                return 2
        class C(Base):
            def f(self):
                return 3
        myjitdriver = JitDriver(greens = [], reds = ['n'])
        def extern(n):
            if n > 40:
                return A()
            elif n > 20:
                return B()
            else:
                return C()
        def f(n):
            while n > 0:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n -= extern(n).f()
            return n
        res = self.meta_interp(f, [55], policy=StopAtXPolicy(extern))
        assert res == f(55)
        self.check_tree_loop_count(2)

    def test_bug1(self):
        py.test.skip("BOOM")
        myjitdriver = JitDriver(greens = [], reds = ['node', 'n'])
        def extern(n):
            if n <= 21:
                return B(n)
            else:
                return A()
        def f(n):
            node = A()
            while n >= 0:
                myjitdriver.can_enter_jit(node=node, n=n)
                myjitdriver.jit_merge_point(node=node, n=n)
                n = node.decr(n)
                node = extern(n)
            return n
        res = self.meta_interp(f, [40], policy=StopAtXPolicy(extern))
        assert res == f(40)

    def test_recursive_call_to_portal_from_blackhole(self):
        from pypy.rpython.annlowlevel import hlstr
        
        myjitdriver = JitDriver(greens = ['k'], reds = ['n'])
        def f(n, k):
            while n >= 0:
                myjitdriver.can_enter_jit(n=n, k=k)
                myjitdriver.jit_merge_point(n=n, k=k)
                if n == 3 and k == 0:
                    return f(10, 1)
                n -= 1
            if k == 1:
                return "string"
            return "xyz"

        res = self.meta_interp(f, [20, 0])
        assert hlstr(res) == "string"

class TestOOtype(SendTests, OOJitMixin):
    def skip(self):
        py.test.skip('in-progress')

    test_red_builtin_send = skip
    test_send_to_single_target_method = skip
    test_red_send_to_green_receiver = skip
    test_oosend_base = skip
    test_oosend_different_initial_class = skip
    test_indirect_call_unknown_object_1 = skip
    test_three_cases = skip
    test_three_classes = skip
    test_recursive_call_to_portal_from_blackhole = skip


class TestLLtype(SendTests, LLJitMixin):
    pass
