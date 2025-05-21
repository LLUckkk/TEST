import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pandas as pd
from pandas.core.indexes.base import _IndexT


#############change###########


def _view(self: _IndexT) -> _IndexT:
    result = self._simple_new(self._values, name=self._name, refs=self._references)

    result._cache = self._cache
    return result


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
    class Dummy:
        pass

    self = Dummy()
    self = pd.Index([1, 2, 3, 4, 5])

    return _view(self)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self = pd.MultiIndex.from_tuples([('a', 1), ('b', 2), ('c', 3)], names=['letter', 'number'])

    return _view(self)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self = pd.DatetimeIndex(['2023-01-01', '2023-01-02', '2023-01-03'], name='date')

    return _view(self)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self = pd.CategoricalIndex(['apple', 'banana', 'cherry'], categories=['apple', 'banana', 'cherry', 'date'],
                               ordered=True)

    return _view(self)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self = pd.TimedeltaIndex(['1 days', '2 days', '3 days'], name='duration')

    return _view(self)


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

    def serialize_result(res):
        if isinstance(res, pd.MultiIndex):
            return [list(t) for t in res.tolist()]
        elif isinstance(res, (pd.DatetimeIndex, pd.TimedeltaIndex, pd.CategoricalIndex)):
            return res.astype(str).tolist()
        elif isinstance(res, pd.Index):
            return res.tolist()
        return res

    output = {
        "ans1": serialize_result(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": serialize_result(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": serialize_result(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": serialize_result(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": serialize_result(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
