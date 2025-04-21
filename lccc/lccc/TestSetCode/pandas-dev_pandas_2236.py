import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
import pandas as pd
from pandas.core.dtypes.generic import ABCNDFrame

REDUCTION_ALIASES = {
    "sum": "sum",
    "prod": "prod",
    "min": "min",
    "max": "max",
    "mean": "mean",
    "std": "std",
    "var": "var",
    "any": "any",
    "all": "all"
}


def safe_result_format(obj):
    if isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.tolist()  # 或者用 .to_dict() 更直观
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif obj is NotImplemented:
        return "NotImplemented"
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    else:
        return str(obj)


#############change###########
def dispatch_reduction_ufunc(self, ufunc: np.ufunc, method: str, *inputs, **kwargs):
    assert method == "reduce"

    if len(inputs) != 1 or inputs[0] is not self:
        return NotImplemented

    if ufunc.__name__ not in REDUCTION_ALIASES:
        return NotImplemented

    method_name = REDUCTION_ALIASES[ufunc.__name__]

    if not hasattr(self, method_name):
        return NotImplemented

    if self.ndim > 1:
        if isinstance(self, ABCNDFrame):
            kwargs["numeric_only"] = False

        if "axis" not in kwargs:
            kwargs["axis"] = 0

    return getattr(self, method_name)(skipna=False, **kwargs)


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
    self = pd.Series([1, 2, 3, 4])
    ufunc = np.add
    method = "reduce"
    inputs = (self,)
    kwargs = {}

    return dispatch_reduction_ufunc(self, ufunc, method, *inputs, **kwargs)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self = pd.DataFrame([[1, 2], [3, 4]])
    ufunc = np.sum
    method = "reduce"
    inputs = (self,)
    kwargs = {"axis": 1}

    return dispatch_reduction_ufunc(self, ufunc, method, *inputs, **kwargs)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self = pd.Series([5, 6, 7, 8])
    ufunc = np.prod
    method = "reduce"
    inputs = (self,)
    kwargs = {}

    return dispatch_reduction_ufunc(self, ufunc, method, *inputs, **kwargs)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self = pd.DataFrame([[1, 2, 3], [4, 5, 6]])
    ufunc = np.min
    method = "reduce"
    inputs = (self,)
    kwargs = {"axis": 0}

    return dispatch_reduction_ufunc(self, ufunc, method, *inputs, **kwargs)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self = pd.Series([10, 20, 30, 40])
    ufunc = np.max
    method = "reduce"
    inputs = (self,)
    kwargs = {}

    return dispatch_reduction_ufunc(self, ufunc, method, *inputs, **kwargs)


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
        "ans1": safe_result_format(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": safe_result_format(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": safe_result_format(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": safe_result_format(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": safe_result_format(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
