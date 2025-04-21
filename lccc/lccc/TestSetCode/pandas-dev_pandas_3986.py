import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pandas as pd
import numpy as np
from pandas import MultiIndex, DataFrame


#############change###########
def _to_dict_of_blocks(dataframe):
    mgr = dataframe._mgr
    return {
        k: v.values.tolist()
        for k, v in enumerate(mgr.blocks)  # 使用 enumerate 直接遍历 tuple
    }


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


def testcase_1():
    df = DataFrame({
        "A": np.random.rand(10),
        "B": np.random.randint(0, 100, size=10),
        "C": ["foo", "bar", "baz", "qux", "quux", "corge", "grault", "garply", "waldo", "fred"]
    })
    result = _to_dict_of_blocks(df)
    return {k: v for k, v in result.items()}


def testcase_2():
    df = DataFrame({
        "A": np.array([1.0, 2.0, 3.0], dtype=np.float64),
        "B": np.array([1, 2, 3], dtype=np.int64),
        "C": np.array([True, False, True], dtype=bool)
    })
    result = _to_dict_of_blocks(df)
    return {k: v for k, v in result.items()}


def testcase_3():
    cols = MultiIndex.from_tuples([("first", "A"), ("second", "B"), ("third", "C")])
    df = DataFrame([[1.0, 2, 3], [4.0, 5, 6]], columns=cols)
    result = _to_dict_of_blocks(df)
    return {k: v for k, v in result.items()}


def testcase_4():
    df = DataFrame({
        "A": np.array([1, 2, 3, 4], dtype=np.int32),
        "B": np.array([5.0, 6.0, 7.0, 8.0], dtype=np.float32),
        "C": np.array(["x", "y", "z", "w"], dtype=object)
    })
    result = _to_dict_of_blocks(df)
    return {k: v for k, v in result.items()}


def testcase_5():
    df = DataFrame({
        "A": np.random.default_rng(2).standard_normal(5),
        "B": np.random.default_rng(2).integers(0, 10, size=5),
        "C": ["alpha", "beta", "gamma", "delta", "epsilon"]
    })
    result = _to_dict_of_blocks(df)
    return {k: v for k, v in result.items()}


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
