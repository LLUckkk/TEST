import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pandas as pd
import numpy as np


def is_integer(x):
    return isinstance(x, int) or isinstance(x, np.integer)


#############change###########
def isetitem(self, loc, value) -> None:
    if isinstance(value, pd.DataFrame):
        if is_integer(loc):
            loc = [loc]

        if len(loc) != len(value.columns):
            raise ValueError(
                f"Got {len(loc)} positions but value has {len(value.columns)} "
                f"columns."
            )

        for i, idx in enumerate(loc):
            arraylike, refs = self._sanitize_column(value.iloc[:, i])
            self._iset_item_mgr(idx, arraylike, inplace=False, refs=refs)
        return

    arraylike, refs = self._sanitize_column(value)
    self._iset_item_mgr(loc, arraylike, inplace=False, refs=refs)


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


class Dummy:
    def __init__(self):
        self.log = []

    def _sanitize_column(self, value):
        return value, f"refs_for_{str(value)}"

    def _iset_item_mgr(self, idx, arraylike, inplace=False, refs=None):
        self.log.append({
            "idx": idx,
            "value": arraylike.tolist() if hasattr(arraylike, "tolist") else str(arraylike),
            "refs": refs
        })


# 测试用例 1~5：调用 isetitem 后读取 self.log 返回
def testcase_1():
    self = Dummy()
    loc = 1
    value = [5, 6]
    isetitem(self, loc, value)
    return self.log


def testcase_2():
    self = Dummy()
    loc = [0, 2]
    value = pd.DataFrame({"X": [10, 11, 12], "Y": [13, 14, 15]})
    isetitem(self, loc, value)
    return self.log


def testcase_3():
    self = Dummy()
    loc = 0
    value = pd.Series([7, 8, 9])
    isetitem(self, loc, value)
    return self.log


def testcase_4():
    self = Dummy()
    loc = [0, 1]
    value = pd.DataFrame({"X": [5, 6], "Y": [7, 8]})
    isetitem(self, loc, value)
    return self.log


def testcase_5():
    self = Dummy()
    loc = 2
    value = np.array([10, 11, 12])
    isetitem(self, loc, value)
    return self.log


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
