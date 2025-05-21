import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests


#############change###########
def get(self, key, default=None):
    return self.node.get(key, default)


#############change###########


@contextmanager
def request_context():
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    result_queue = queue.Queue()
    event = threading.Event()

    def worker():
        try:
            with request_context() as session:
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
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

    start_time = time.time()
    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()

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


# 测试用例定义
def testcase_1():
    class Dummy:
        def __init__(self):
            self.node = {"children": ["node1", "node2"]}

    self = Dummy()
    return get(self, "children", None)


def testcase_2():
    class Dummy:
        def __init__(self):
            self.node = {"visible": False}

    self = Dummy()
    return get(self, "visible", True)


def testcase_3():
    class Dummy:
        def __init__(self):
            self.node = {"backgroundColor": "#000000"}

    self = Dummy()
    return get(self, "backgroundColor", "#FFFFFF")


def testcase_4():
    class Dummy:
        def __init__(self):
            self.node = {"id": "element_123"}

    self = Dummy()
    return get(self, "id", "default_id")


def testcase_5():
    class Dummy:
        def __init__(self):
            self.node = {}

    self = Dummy()
    return get(self, "exportSettings", [])


def main():
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
