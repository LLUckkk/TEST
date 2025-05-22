import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests


#############change###########
def get_msg(self, block=True, timeout=None):
    if timeout is None:
        timeout = 604800
    return self._in_queue.get(block, timeout)


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
            print(e)
            if not event.is_set():
                result_queue.put(('error', str(e)))
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


# 修改后的测试用例们

def testcase_1():
    class Dummy:
        pass

    self = Dummy()
    self._in_queue = queue.Queue()
    self._in_queue.put("message from testcase_1")
    block = True
    timeout = None
    return get_msg(self, block, timeout)


def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self._in_queue = queue.Queue()
    self._in_queue.put("message from testcase_2")
    block = False
    timeout = 5
    return get_msg(self, block, timeout)


def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self._in_queue = queue.Queue()
    self._in_queue.put("message from testcase_3")
    block = True
    timeout = 10
    return get_msg(self, block, timeout)


def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self._in_queue = queue.Queue()
    # 不放入任何消息，模拟队列为空时的 timeout 行为
    block = False
    timeout = 0.1
    try:
        return get_msg(self, block, timeout)
    except queue.Empty:
        return "queue.Empty"


def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self._in_queue = queue.Queue()
    self._in_queue.put("message from testcase_5")
    block = True
    timeout = 3600
    return get_msg(self, block, timeout)


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
