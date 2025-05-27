import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import copy

from numpy.f2py.auxfuncs import errmess, isintent_callback, isoptional, outmess, show
from numpy.f2py.crackfortran import setmesstext, true_intent_list


#############change###########
def vars2fortran(block, vars, args, tab='', as_interface=False):
    setmesstext(block)
    ret = ''
    nout = []
    for a in args:
        if a in block['vars']:
            nout.append(a)
    if 'commonvars' in block:
        for a in block['commonvars']:
            if a in vars:
                if a not in nout:
                    nout.append(a)
            else:
                errmess(
                    'vars2fortran: Confused?!: "%s" is not defined in vars.\n' % a)
    if 'varnames' in block:
        nout.extend(block['varnames'])
    if not as_interface:
        for a in list(vars.keys()):
            if a not in nout:
                nout.append(a)
    for a in nout:
        if 'depend' in vars[a]:
            for d in vars[a]['depend']:
                if d in vars and 'depend' in vars[d] and a in vars[d]['depend']:
                    errmess(
                        'vars2fortran: Warning: cross-dependence between variables "%s" and "%s"\n' % (a, d))
        if 'externals' in block and a in block['externals']:
            if isintent_callback(vars[a]):
                ret = '%s%sintent(callback) %s' % (ret, tab, a)
            ret = '%s%sexternal %s' % (ret, tab, a)
            if isoptional(vars[a]):
                ret = '%s%soptional %s' % (ret, tab, a)
            if a in vars and 'typespec' not in vars[a]:
                continue
            cont = 1
            for b in block['body']:
                if a == b['name'] and b['block'] == 'function':
                    cont = 0
                    break
            if cont:
                continue
        if a not in vars:
            show(vars)
            outmess('vars2fortran: No definition for argument "%s".\n' % a)
            continue
        if a == block['name']:
            if block['block'] != 'function' or block.get('result'):
                continue
        if 'typespec' not in vars[a]:
            if 'attrspec' in vars[a] and 'external' in vars[a]['attrspec']:
                if a in args:
                    ret = '%s%sexternal %s' % (ret, tab, a)
                continue
            show(vars[a])
            outmess('vars2fortran: No typespec for argument "%s".\n' % a)
            continue
        vardef = vars[a]['typespec']
        if vardef == 'type' and 'typename' in vars[a]:
            vardef = '%s(%s)' % (vardef, vars[a]['typename'])
        selector = {}
        if 'kindselector' in vars[a]:
            selector = vars[a]['kindselector']
        elif 'charselector' in vars[a]:
            selector = vars[a]['charselector']
        if '*' in selector:
            if selector['*'] in ['*', ':']:
                vardef = '%s*(%s)' % (vardef, selector['*'])
            else:
                vardef = '%s*%s' % (vardef, selector['*'])
        else:
            if 'len' in selector:
                vardef = '%s(len=%s' % (vardef, selector['len'])
                if 'kind' in selector:
                    vardef = '%s,kind=%s)' % (vardef, selector['kind'])
                else:
                    vardef = '%s)' % (vardef)
            elif 'kind' in selector:
                vardef = '%s(kind=%s)' % (vardef, selector['kind'])
        c = ' '
        if 'attrspec' in vars[a]:
            attr = [l for l in vars[a]['attrspec']
                    if l not in ['external']]
            if as_interface and 'intent(in)' in attr and 'intent(out)' in attr:
                attr.remove('intent(out)')
            if attr:
                vardef = '%s, %s' % (vardef, ','.join(attr))
                c = ','
        if 'dimension' in vars[a]:
            vardef = '%s%sdimension(%s)' % (
                vardef, c, ','.join(vars[a]['dimension']))
            c = ','
        if 'intent' in vars[a]:
            lst = true_intent_list(vars[a])
            if lst:
                vardef = '%s%sintent(%s)' % (vardef, c, ','.join(lst))
            c = ','
        if 'check' in vars[a]:
            vardef = '%s%scheck(%s)' % (vardef, c, ','.join(vars[a]['check']))
            c = ','
        if 'depend' in vars[a]:
            vardef = '%s%sdepend(%s)' % (
                vardef, c, ','.join(vars[a]['depend']))
            c = ','
        if '=' in vars[a]:
            v = vars[a]['=']
            if vars[a]['typespec'] in ['complex', 'double complex']:
                try:
                    v = eval(v)
                    v = '(%s,%s)' % (v.real, v.imag)
                except Exception:
                    pass
            vardef = '%s :: %s=%s' % (vardef, a, v)
        else:
            vardef = '%s :: %s' % (vardef, a)
        ret = '%s%s%s' % (ret, tab, vardef)
    return ret


#############change###########


@contextmanager
def request_context():
    """确保requests会话被正确关闭的上下文管理器"""
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    """完全解决线程残留问题的执行器"""
    result_queue = queue.Queue()
    event = threading.Event()  # 线程协调事件

    def worker():
        try:
            with request_context() as session:
                # 将session传递给测试函数（如果需要）
                if 'session' in testcase_func.__code__.co_varnames:
                    result = testcase_func(session=session)
                else:
                    result = testcase_func()

                if not event.is_set():
                    result_queue.put(('success', result))
        except Exception as e:
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            event.set()  # 标记线程已完成

    t = threading.Thread(target=worker)
    t.daemon = True  # 必须设置为守护线程

    start_time = time.time()
    t.start()

    # 等待线程完成或超时
    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()  # 通知线程终止

    if not result_queue.empty():
        status, data = result_queue.get_nowait()
        return {
            'success': status == 'success',
            'result': data if status == 'success' else None,
            'error': None if status == 'success' else str(data),
            'traceback': traceback.format_exc() if status == 'error' else None
        }

    return {
        'success': False,
        'error': f'Timeout after {timeout} seconds',
        'traceback': 'Test execution timed out'
    }


# 定义测试用例1
def testcase_1():
    block = {
        'vars': {
            'a': {'typespec': 'integer', 'attrspec': ['intent(in)']},
            'b': {'typespec': 'real', 'attrspec': ['intent(out)'], 'dimension': ['10']}
        },
        'commonvars': ['a'],
        'varnames': ['b'],
        'externals': ['b'],
        'body': [{'name': 'func1', 'block': 'function'}],
        'name': 'test_function',
        'block': 'function'
    }
    vars = copy.deepcopy(block['vars'])
    args = ['a', 'b']
    tab = '    '
    as_interface = False

    return vars2fortran(block, vars, args, tab, as_interface)


# 定义测试用例2
def testcase_2():
    block = {
        'vars': {
            'x': {'typespec': 'real', 'attrspec': ['intent(inout)'], 'dimension': ['5']},
            'y': {'typespec': 'complex', 'attrspec': ['intent(in)'], '=': '(1.0, 2.0)'}
        },
        'varnames': ['x', 'y'],
        'externals': ['x'],
        'body': [{'name': 'func2', 'block': 'function'}],
        'name': 'test_subroutine',
        'block': 'subroutine'
    }
    vars = copy.deepcopy(block['vars'])
    args = ['x', 'y']
    tab = '  '
    as_interface = True

    return vars2fortran(block, vars, args, tab, as_interface)


# 定义测试用例3
def testcase_3():
    block = {
        'vars': {
            'm': {'typespec': 'integer', 'attrspec': ['intent(in)'], 'dimension': ['3', '3']},
            'n': {'typespec': 'double precision', 'attrspec': ['intent(out)']}
        },
        'commonvars': ['m'],
        'varnames': ['n'],
        'externals': ['n'],
        'body': [{'name': 'func3', 'block': 'function'}],
        'name': 'matrix_operation',
        'block': 'function'
    }
    vars = copy.deepcopy(block['vars'])
    args = ['m', 'n']
    tab = '\t'
    as_interface = False

    return vars2fortran(block, vars, args, tab, as_interface)


# 定义测试用例4
def testcase_4():
    block = {
        'vars': {
            'p': {'typespec': 'character', 'attrspec': ['intent(in)'], 'charselector': {'len': '10'}},
            'q': {'typespec': 'logical', 'attrspec': ['intent(out)']}
        },
        'varnames': ['p', 'q'],
        'externals': ['p'],
        'body': [{'name': 'func4', 'block': 'function'}],
        'name': 'string_check',
        'block': 'function'
    }
    vars = copy.deepcopy(block['vars'])
    args = ['p', 'q']
    tab = '    '
    as_interface = False

    return vars2fortran(block, vars, args, tab, as_interface)


# 定义测试用例5
def testcase_5():
    block = {
        'vars': {
            'u': {'typespec': 'type', 'typename': 'custom_type', 'attrspec': ['intent(inout)']},
            'v': {'typespec': 'integer', 'attrspec': ['intent(in)'], 'depend': ['u']}
        },
        'commonvars': ['u'],
        'varnames': ['v'],
        'externals': ['v'],
        'body': [{'name': 'func5', 'block': 'function'}],
        'name': 'custom_type_handler',
        'block': 'function'
    }
    vars = copy.deepcopy(block['vars'])
    args = ['u', 'v']
    tab = ''
    as_interface = True

    return vars2fortran(block, vars, args, tab, as_interface)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        "ans1": test_results["ans1"]["result"] if test_results["ans1"]["success"] else None,
        "ans2": test_results["ans2"]["result"] if test_results["ans2"]["success"] else None,
        "ans3": test_results["ans3"]["result"] if test_results["ans3"]["success"] else None,
        "ans4": test_results["ans4"]["result"] if test_results["ans4"]["success"] else None,
        "ans5": test_results["ans5"]["result"] if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
