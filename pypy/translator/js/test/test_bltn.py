""" blttest - some tests of builtin stuff
"""

import py

from pypy.rpython.ootypesystem.bltregistry import BasicExternal, MethodDesc
from pypy.translator.js.test.runtest import compile_function

def check_source_contains(compiled_function, pattern):
    import re
    
    source = compiled_function.js.tmpfile.open().read()
    return re.search(pattern, source)

# check rendering _dom.get_document()
def test_simple_builtin():
    from pypy.translator.js.modules._dom import get_document
    def test_document_call():
        return get_document().getElementById("some_id")
    
    fn = compile_function(test_document_call, [])
    assert check_source_contains(fn, "= document")
    assert check_source_contains(fn, "\.getElementById")

# check rendering transparent proxy
class SomeProxy(BasicExternal):
    _render_xmlhttp = True
    
    _methods = {
        'some_method' : MethodDesc([], 3),
    }
    
    _fields = {
    }

SomeProxyInstance = SomeProxy()

def test_simple_proxy():
    def simple_proxy():
        retval = SomeProxyInstance.some_method()
    
    fn = compile_function(simple_proxy, [])
    assert check_source_contains(fn, "loadJSONDoc\('some_method'")

# next will try out the callback

