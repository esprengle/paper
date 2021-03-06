#: vim set encoding=utf-8 :
##
 # Paper
 # Develop apps for Pythonista using HTML, CSS and JavaScript
 #
 # author 0x77
 # version 0.4
##


# Imports
import sys
#import ui
# Are we being run from Pythonista?
if not sys.platform == 'ios':
    print('Paper only runs on Pythonista.')
    sys.exit()
else:
    import os
    import json
    import traceback
    import threading
    import ui

    from types import ModuleType
    from bottle import run, route, get, post, static_file, request


__all__ = ['app']

# Is this Python 2 or 3?
py_three = (sys.version_info > (3, 0))


# Helper functions for the JS API
class JSUtils(object):
    def __init(self):
        pass

    # Module
    def asImport(self, module):
        return __import__(module)

    # Expressions
    def cmp(self, a, b):
        return a == b

    def tcmp(self, a, b):
        return a is b

    def enum(self, obj):
        result = []

        for index, item in enumerate(obj):
            result.append((index, item))

        return result

    # Math
    def add(self, a, b):
        return a + b

    def sub(self, a, b):
        return a - b

    def div(self, a, b):
        return a / b

    def mul(self, a, b):
        return a * b


# Type utilsChange the class to:

class JSFunction(object):
    def __init__(self, app, code):
        self.app = app
        self.code = code

    def __call__(self, *args):
        if len(args) == 0:
            args = ''
        else:
            args = ','.join(args)
        
        call = '({})({})'.format(self.code, args)
        print('call evaljs')
        print(call)
        returnval= self.app._js.eval_js(call)
        print('done evaljs',returnval)
        return returnval


# Library code
class PaperApp(object):
    '''
    Where all the magic happens
    '''

    # Application root directory
    _root = None
    # JavaScript WebView
    _js = None
    # Functions exposed to the JS API
    _exposed = {}
    # Names ignored on imports
    _ignored_imports = [
        '__name__', '__doc__', '__file__', '__package__', '__builtins__'
    ]
    # Built-in names that should be available at the JS API
    _allowed_builtins = [
        'abs', 'all', 'any', 'bin', 'bytearray', 'bytes', 'callable', 'chr',
        'cmp', 'coerce', 'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod',
        'enumerate', 'execfile', 'filter', 'float', 'format', 'getattr', 'hasattr',
        'hash', 'hex', 'id', 'input', 'intern', 'int', 'isinstance', 'issubclass',
        'iter', 'len', 'list', 'locals', 'long', 'print', 'range', 'str', 'sum',
        'tuple', 'type'
    ]
    # Objects created by JavaScript
    _py_objs = {
        '__anon__': {}
    }
    # Holder for extended types
    _extended = {}

    def __init__(self, root, all_builtins=False):
        self._root = root
        self._all_builtins = all_builtins
        self.initserver()

    def _extend_types(self, data):
        '''
        Extend the type-converter
        '''

        pass

    def _js_obj(self, owner, obj=None, index=None, it=False):
        '''
        Convert a Python object to a JavaScript reference
        '''

        if index is not None:
            value = owner[index]
        elif it is not None:
            value = owner
        else:
            value = getattr(owner, obj)

        if type(value) in [str, int, float, dict, tuple, bool, complex]:
            result = {
                'type': type(value).__name__
            }
        elif isinstance(value, ModuleType):
            result = {
                'type': 'dict'
            }
        elif callable(value):
            result = {
                'type': 'function'
            }
        elif value is None:
            result = {
                'type': 'none'
            }
        else:
            if index is not None or it is not None:
                print(type(value).__name__)

                obj_id = id(value)
                self._py_objs[obj_id] = value

                result = {
                    'type': 'reference',
                    '__id__': obj_id
                }

            if type(value) in self._extended:
                result = {
                    'type': type(value).__name__
                }
            else:
                result = {
                    'type': 'unknown'
                }

        return result

    def _js_obj_loop(self, obj):
        if type(obj) == list:
            for i in range(len(obj)):
                obj[i] = self._js_obj(obj, index=i)
        # elif type(obj) == dict:
        #     obj = self._js_obj()

            print(obj)
        return obj

    def expose(self, function, alias=None):
        '''
        Expose a Python function to the JS API
        '''

        if py_three:
            f_alias = alias or function.__name__
        else:
            f_alias = alias or function.func_name

        self._exposed[f_alias] = {'name': function}

        return function

    def run(self):
        '''
        Serves as a bridge from Python to JavaScript (and vice-versa)
        '''

        # Serve static files (actually, just the API and jQuery)
        @get('/js/<filename:re:.*\.(js)>')
        def includes(filename):
            print(filename)
            return static_file(filename, root='./include')

        # Serve the app
        @get('/')
        def index():
            print('serving')
            return static_file('index.html', root=self._root)

        # Handle API calls
        @post('/api')
        def api():
            print(request.json)
            is_builtin = ('builtin' in request.json)
            is_call = ('call' in request.json)

            data = {
                'null': True
            }

            if is_builtin:
                builtin = request.json['builtin']

                if builtin == 'init':
                    if py_three:
                        module = 'builtins'
                    else:
                        module = '__builtin__'

                    builtin_import = __import__(module)
                    builtins = dir(builtin_import)
                    builtin_id = id(builtin_import)

                    self._py_objs[builtin_id] = builtin_import

                    data = {
                        '__id__': builtin_id
                    }

                    for name in builtins:
                        if name in self._ignored_imports:
                            continue

                        if not self._all_builtins:
                            if name not in self._allowed_builtins:
                                continue

                        data[name] = self._js_obj(builtin_import, name)
                elif builtin == 'utils':
                    util_import = JSUtils()
                    utils = dir(util_import)
                    util_id = id(util_import)

                    self._py_objs[util_id] = util_import

                    data = {
                        '__id__': util_id
                    }

                    for name in utils:
                        if name.startswith('_'):
                            continue

                        data[name] = self._js_obj(util_import, name)
                elif builtin == 'extend':
                    fields = request.json['fields']
                    ext_type = fields['type']
                    ext_names = fields['names']

                    self._extended[ext_type] = []
                    for field in ext_names:
                        self._extended[ext_type].append(field)
                elif builtin == 'free':
                    obj_id = request.json['id']

                    if obj_id in self._py_objs:
                        del self._py_objs[obj_id]

                        result = {}
                    else:
                        result = {
                            'exception': '<type \'exceptions.PaperError\'>',
                            'traceback': 'Traceback (most recent call last):\n'
                                         'PaperError: Unknown PyObj "{}".'
                                         .format(obj_id)
                        }
                elif builtin == 'import':
                    module = request.json['module']

                    result = {
                        '__name__': module
                    }

                    try:
                        mod = __import__(module)
                        names = dir(mod)

                        # Fetch the imported names
                        for name in names:
                            if name in self._ignored_imports:
                                continue

                            result[name] = self._js_obj(mod, name)

                        # Save the newly created object
                        obj_name = id(mod)
                        self._py_objs[obj_name] = mod

                        result['__id__'] = obj_name

                        # Return a reference to that object
                        data = result
                    except:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        tb = traceback.format_exc(exc_traceback)

                        data = {
                            'exception': str(exc_type),
                            'traceback': tb
                        }
            elif is_call:
                if 'owner' not in request.json:
                    print(request.json)

                c_type = request.json['type']
                call = request.json['call']
                owner = request.json['owner']
                args = request.json['args']

                for i, arg in enumerate(args):
                    if arg['type'] in ['string', 'number', 'array', 'boolean']:
                        args[i] = arg['value']
                    elif arg['type'] == 'tuple':
                        args[i] = tuple(arg['data'])
                    elif arg['type'] == 'complex':
                        args[i] = complex(arg['real'], arg['imag'])
                    elif arg['type'] == 'function':
                        args[i] = JSFunction(self, arg['code'])
                    elif arg['type'] == 'object':
                        if 'id' in arg:
                            args[i] = self._py_objs[arg['id']]
                        else:
                            args[i] = arg['data']
                    elif arg['type'] == 'none':
                        args[i] = None
                try:
                    if c_type == 'func':
                        if owner == '__anon__':
                            result = self._py_objs[owner][call](*args)
                        else:
                            result = getattr(self._py_objs[owner], call)(*args)
                    elif c_type == 'attr':
                        if call == '__self__':
                            result = self._py_objs[owner]
                            print(result)
                        else:
                            result = getattr(self._py_objs[owner], call)

                    if type(result) in [str, int, float, list, dict, bool]:
                        data = {
                            'type': type(result).__name__,
                            'value': result
                        }
                    elif type(result) == tuple:
                        data = {
                            'type': 'tuple',
                            'value': result
                        }
                    elif type(result) == complex:
                        data = {
                            'type': 'complex',
                            'real': result.real,
                            'imag': result.imag
                        }
                    elif callable(result):
                        func_id = id(result)
                        self._py_objs['__anon__'][func_id] = result

                        data = {
                            '__id__': '__anon__',
                            'type': 'function',
                            'name': func_id
                        }
                    elif result is None:
                        data = {
                            'type': 'none'
                        }
                    else:
                        if type in self._extended:
                            obj_type = type(result).__name__
                        else:
                            obj_type = 'object'

                        data = {
                            'type': obj_type,
                            'value': {}
                        }

                        # Save the newly created object
                        obj_name = id(result)
                        self._py_objs[obj_name] = result

                        data['value']['__id__'] = obj_name

                        for name in dir(result):
                            if name.startswith('__'):
                                continue

                            data['value'][name] = self._js_obj(result, name)
                except KeyboardInterrupt:
                    sys.exit()
                except:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    tb = traceback.format_exc(exc_traceback)

                    data = {
                        'exception': str(exc_type),
                        'traceback': tb
                    }

            try:
                if 'value' in data:
                    if type(data['value']) in [list, dict, tuple]:
                        return json.dumps(data, default=self._js_obj_loop(data['value']))

                return json.dumps(data)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exc(exc_traceback)

                data = {
                    'exception': str(exc_type),
                    'traceback': tb
                }

                return json.dumps(data)
                
    def initserver(self):
         try:
            # Start server
            server = threading.Thread(target=run, kwargs={'host': '127.0.0.1',
                                                          'port': 1406,
                                                          'quiet': False})
            server.start()
            print('started')
            # Start WebView
            def webview():

                debug=False
                debugjs='''
                // debug_utils.js
                // 1) custom console object
                console = new Object();
                console.log = function(log) {
                // create then remove an iframe, to communicate with 
                //webview delegate
                var iframe = document.createElement("IFRAME");
                iframe.setAttribute("src", "ios-log:" + log);
                document.documentElement.appendChild(iframe);
                iframe.parentNode.removeChild(iframe);
                iframe = null;    };
                // TODO: give each log level an identifier in the log
                console.debug = console.log;
                console.info = console.log;
                console.warn = console.log;
                console.error = console.log;
                window.onerror = (function(error, url, line,col,errorobj) {
                	console.log("error: "+error+"%0Aurl:"+url+" line:"+line+"col:"+col+"stack:"+errorobj);})
                console.log("logging activated");
                '''            
                import requests
                unquote=requests.utils.unquote
                class debugDelegate (object):
                    def webview_should_start_load(self,
                        webview, url, nav_type):
                        if url.startswith('ios-log'):
                            print (unquote(url))
                        return True
    	
                self._js = ui.WebView()
                self._js.delegate=debugDelegate()
                self._js.eval_js(debugjs)
                print('presenting')
                self._js.present('sheet')
                self._js.load_url('http://127.0.0.1:1406')
            ui.delay(webview,1.9)

            # run(host='127.0.0.1', port=1406, quiet=True)
         except KeyboardInterrupt:
            sys.exit()


def app(root, all_builtins=False):
    return PaperApp(root, all_builtins)
