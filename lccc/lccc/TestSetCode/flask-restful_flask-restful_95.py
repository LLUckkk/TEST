import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import six
from werkzeug.datastructures import MultiDict
from unittest.mock import Mock


#############change###########
def source(self, request):
    if isinstance(self.location, six.string_types):
        value = getattr(request, self.location, MultiDict())
        if callable(value):
            value = value()
        if value is not None:
            return value
    else:
        values = MultiDict()
        for l in self.location:
            value = getattr(request, l, None)
            if callable(value):
                value = value()
            if value is not None:
                values.update(value)
        return values

    return MultiDict()


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
            print(e)
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
    class Dummy:
        def __init__(self):
            self.location = "args"  # 单个字段名

    self = Dummy()
    request = Mock(['args', 'headers', 'values'])
    request.args = {'param1': 'value1'}
    request.headers = {'header1': 'value2'}
    request.values = {'param2': 'value3'}

    return source(self, request)


# 定义测试用例2
def testcase_2():
    class Dummy:
        def __init__(self):
            self.location = ["form", "cookies"]  # 多个字段名

    self = Dummy()
    request = Mock(['form', 'cookies'])
    request.form = {'form_field': 'form_value'}
    request.cookies = {'cookie_name': 'cookie_value'}

    return source(self, request)


# 定义测试用例3
def testcase_3():
    class Dummy:
        def __init__(self):
            self.location = ["json", "files"]

    self = Dummy()
    request = Mock(['json', 'files'])
    request.json = {'json_key': 'json_value'}
    request.files = {'file_key': 'file_value'}

    return source(self, request)


def testcase_4():
    class Dummy:
        def __init__(self):
            self.location = 'method'  # 关键修改：改为字符串形式

    self = Dummy()
    request = Mock(['method'])
    request.method = 'POST'

    result = source(self, request)
    if isinstance(result, str):
        md = MultiDict()
        md['method'] = result
        return md
    return result


# 定义测试用例5
def testcase_5():
    class Dummy:
        def __init__(self):
            self.location = ["values", "headers"]

    self = Dummy()
    request = Mock(['values', 'headers'])
    request.values = {'param3': 'value4'}
    request.headers = {'header2': 'value5'}

    return source(self, request)


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
