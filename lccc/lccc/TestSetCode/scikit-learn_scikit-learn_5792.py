import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from sklearn.mixture._gaussian_mixture import _estimate_gaussian_covariances_diag


#############change###########
def _estimate_gaussian_covariances_spherical(resp, X, nk, means, reg_covar):
    return _estimate_gaussian_covariances_diag(resp, X, nk, means, reg_covar).mean(1)


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
    resp = np.array([[0.5, 0.5], [0.2, 0.8], [0.9, 0.1]])
    X = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    nk = np.array([1.6, 1.4])
    means = np.array([[2.0, 3.0], [4.0, 5.0]])
    reg_covar = 0.01

    return _estimate_gaussian_covariances_spherical(resp, X, nk, means, reg_covar)


# 定义测试用例2
def testcase_2():
    resp = np.array([[0.3, 0.7], [0.4, 0.6], [0.5, 0.5], [0.6, 0.4]])
    X = np.array([[2.0, 3.0], [4.0, 5.0], [6.0, 7.0], [8.0, 9.0]])
    nk = np.array([2.2, 1.8])
    means = np.array([[3.0, 4.0], [5.0, 6.0]])
    reg_covar = 0.05

    return _estimate_gaussian_covariances_spherical(resp, X, nk, means, reg_covar)


# 定义测试用例3
def testcase_3():
    resp = np.array([[0.1, 0.9], [0.3, 0.7], [0.6, 0.4], [0.8, 0.2], [0.5, 0.5]])
    X = np.array([[1.5, 2.5], [3.5, 4.5], [5.5, 6.5], [7.5, 8.5], [9.5, 10.5]])
    nk = np.array([2.5, 2.5])
    means = np.array([[2.5, 3.5], [4.5, 5.5]])
    reg_covar = 0.02

    return _estimate_gaussian_covariances_spherical(resp, X, nk, means, reg_covar)


# 定义测试用例4
def testcase_4():
    resp = np.array([[0.25, 0.75], [0.35, 0.65], [0.45, 0.55], [0.55, 0.45], [0.65, 0.35], [0.75, 0.25]])
    X = np.array([[1.0, 1.5], [2.0, 2.5], [3.0, 3.5], [4.0, 4.5], [5.0, 5.5], [6.0, 6.5]])
    nk = np.array([3.0, 3.0])
    means = np.array([[1.5, 2.0], [3.5, 4.0]])
    reg_covar = 0.03

    return _estimate_gaussian_covariances_spherical(resp, X, nk, means, reg_covar)


# 定义测试用例5
def testcase_5():
    resp = np.array([[0.2, 0.8], [0.4, 0.6], [0.6, 0.4], [0.8, 0.2], [0.7, 0.3], [0.5, 0.5], [0.3, 0.7]])
    X = np.array([[1.0, 2.0], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0], [5.0, 6.0], [6.0, 7.0], [7.0, 8.0]])
    nk = np.array([3.5, 3.5])
    means = np.array([[2.0, 3.0], [4.0, 5.0]])
    reg_covar = 0.04

    return _estimate_gaussian_covariances_spherical(resp, X, nk, means, reg_covar)


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
        if isinstance(obj, tuple) or isinstance(obj, list):
            return [json_serializable(o) for o in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj  # 这些类型本身就可以序列化
        else:
            return str(obj)  # Fallback：防止出错

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
