import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests


#############change###########
def arg_blend_number(self, name):
    out = []
    blendArgs = self.pop()
    numMasters = len(blendArgs)
    out.append(blendArgs)
    out.append("blend")
    dummy = self.popall()
    return blendArgs


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
    self = type('Test', (object,), {'stack': [[1, 2, 3]], 'pop': lambda self: [4, 5, 6], 'popall': lambda self: []})()
    name = "test_case_1"

    return arg_blend_number(self, name)


# 定义测试用例2
def testcase_2():
    self = type('Test', (object,),
                {'stack': [[7, 8, 9]], 'pop': lambda self: [10, 11, 12], 'popall': lambda self: []})()
    name = "test_case_2"

    return arg_blend_number(self, name)


# 定义测试用例3
def testcase_3():
    self = type('Test', (object,),
                {'stack': [[13, 14, 15]], 'pop': lambda self: [16, 17, 18], 'popall': lambda self: []})()
    name = "test_case_3"

    return arg_blend_number(self, name)


# 定义测试用例4
def testcase_4():
    self = type('Test', (object,),
                {'stack': [[19, 20, 21]], 'pop': lambda self: [22, 23, 24], 'popall': lambda self: []})()
    name = "test_case_4"

    return arg_blend_number(self, name)


# 定义测试用例5
def testcase_5():
    self = type('Test', (object,),
                {'stack': [[25, 26, 27]], 'pop': lambda self: [28, 29, 30], 'popall': lambda self: []})()
    name = "test_case_5"

    return arg_blend_number(self, name)


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
