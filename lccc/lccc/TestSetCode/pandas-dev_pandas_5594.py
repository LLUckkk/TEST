import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


#############change###########
def _fill_zeros(result: np.ndarray, x, y) -> np.ndarray:
    if result.dtype.kind == "f":
        return result

    is_variable_type = hasattr(y, "dtype")
    is_scalar_type = not isinstance(y, np.ndarray)

    if not is_variable_type and not is_scalar_type:
        return result

    if is_scalar_type:
        y = np.array(y)

    if y.dtype.kind in "iu":
        ymask = y == 0
        if ymask.any():
            mask = ymask & ~np.isnan(result)

            result = result.astype("float64", copy=False)

            np.putmask(result, mask, np.nan)

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
    result = np.array([0, 1, 2, 0, 4])
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([0, 0, 0, 0, 0])

    return _fill_zeros(result, x, y)


# 定义测试用例2
def testcase_2():
    result = np.array([10, 20, 30, 40, 50])
    x = np.array([2, 4, 6, 8, 10])
    y = 0

    return _fill_zeros(result, x, y)


# 定义测试用例3
def testcase_3():
    result = np.array([0, 1, 2, np.nan, 4])
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([0, 1, 0, 1, 0])

    return _fill_zeros(result, x, y)


# 定义测试用例4
def testcase_4():
    result = np.array([5, 10, 15, 20, 25])
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([1, 0, 1, 0, 1])

    return _fill_zeros(result, x, y)


# 定义测试用例5
def testcase_5():
    result = np.array([0, 0, 0, 0, 0])
    x = np.array([1, 2, 3, 4, 5])
    y = np.array([0, 0, 0, 0, 0])

    return _fill_zeros(result, x, y)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def json_serializable(obj):
        if isinstance(obj, np.ndarray):
            # 将 ndarray 转换为列表
            return obj.tolist()
        raise TypeError(f"Type {type(obj)} not serializable")

    output = {
        "ans1": json_serializable(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": json_serializable(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": json_serializable(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": json_serializable(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": json_serializable(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
