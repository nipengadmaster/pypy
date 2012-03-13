import py

from pypy.rlib import rerased_raw
from pypy.rpython.annlowlevel import hlstr
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin


def test_direct_int():
    storage = rerased_raw.UntypedStorage("ii")

    storage.setint(0, 2)
    assert storage.getint(0) == 2

    storage.setint(1, 5)
    assert storage.getint(1) == 5

def test_direct_float():
    storage = rerased_raw.UntypedStorage("f")
    storage.setfloat(0, 5.5)

    assert storage.getfloat(0) == 5.5

def test_direct_instance():
    class A(object):
        def __init__(self, value):
            self.value = value

    storage = rerased_raw.UntypedStorage("o")
    storage.setinstance(0, A(4))

    assert storage.getinstance(0, A).value == 4

def test_direct_getlength():
    storage = rerased_raw.UntypedStorage("ooi")
    assert storage.getlength() == 3

def test_direct_getshape():
    storage = rerased_raw.UntypedStorage("ooi")
    assert storage.getshape() == "ooi"


class TestRerasedRawLLType(LLRtypeMixin, BaseRtypingTest):
    def test_int(self):
        def f(x):
            storage = rerased_raw.UntypedStorage("i")
            storage.setint(0, x)
            return storage.getint(0)

        res = self.interpret(f, [4])
        assert res == 4

    def test_instance(self):
        class A(object):
            def __init__(self, v):
                self.v = v

        def f(x):
            storage = rerased_raw.UntypedStorage("o")
            storage.setinstance(0, A(x))
            return storage.getinstance(0, A).v

        res = self.interpret(f, [27])
        assert res == 27

    # def test_float(self):
    #     def f(x):
    #         storage = rerased_raw.UntypedStorage("f")
    #         storage.setfloat(0, x)
    #         return storage.getfloat(0)

    #     res = self.interpret(f, [12.3])
    #     assert res == 12.3

    def test_exception_catching(self):
        class A(object):
            def __init__(self, v):
                self.v = v

        def f(x):
            try:
                storage = rerased_raw.UntypedStorage("io")
                storage.setint(0, x)
                value1 = storage.getint(0)
                storage.setinstance(1, A(x))
                value2 = storage.getinstance(1, A)
                return value1 + value2.v
            except Exception:
                return 50000

        res = self.interpret(f, [4])
        assert res == 8

    def test_union(self):
        def f(x, v):
            if x:
                storage = rerased_raw.UntypedStorage("i")
            else:
                storage = rerased_raw.UntypedStorage("ii")
            storage.setint(0, v)
            return storage.getint(0)

        res = self.interpret(f, [True, 15])
        assert res == 15

    def test_getlength(self):
        def f():
            storage = rerased_raw.UntypedStorage("ooi")
            return storage.getlength()

        res = self.interpret(f, [])
        assert res == 3

    def test_getshape(self):
        def f():
            storage = rerased_raw.UntypedStorage("ooi")
            return storage.getshape()

        llres = self.interpret(f, [])
        assert hlstr(llres) == "ooi"