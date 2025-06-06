import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
from unittest.mock import MagicMock
from dagster import OpExecutionContext


#############change###########
def get_client(context: OpExecutionContext):
    return context.resources.client
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


# 定义测试用例1
def testcase_1():
    context = MagicMock()
    context.resources.client = "ClientA"
    return get_client(context)


# 定义测试用例2
def testcase_2():
    context = MagicMock()
    context.resources.client = "ClientB"
    return get_client(context)


# 定义测试用例3
def testcase_3():
    context = MagicMock()
    context.resources.client = "ClientC"
    return get_client(context)


# 定义测试用例4
def testcase_4():
    context = MagicMock()
    context.resources.client = "ClientD"
    return get_client(context)


# 定义测试用例5
def testcase_5():
    context = MagicMock()
    context.resources.client = "ClientE"
    return get_client(context)


def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        "ans1": test_results["ans1"]["result"],
        "ans2": test_results["ans2"]["result"],
        "ans3": test_results["ans3"]["result"],
        "ans4": test_results["ans4"]["result"],
        "ans5": test_results["ans5"]["result"]
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()