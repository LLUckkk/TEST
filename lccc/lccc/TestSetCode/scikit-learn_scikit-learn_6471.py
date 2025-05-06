import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


#############change###########
def _update_mean_variance(n_past, mu, var, X, sample_weight=None):
    if X.shape[0] == 0:
        return mu, var

    if sample_weight is not None:
        n_new = float(sample_weight.sum())
        if np.isclose(n_new, 0.0):
            return mu, var
        new_mu = np.average(X, axis=0, weights=sample_weight)
        new_var = np.average((X - new_mu) ** 2, axis=0, weights=sample_weight)
    else:
        n_new = X.shape[0]
        new_var = np.var(X, axis=0)
        new_mu = np.mean(X, axis=0)

    if n_past == 0:
        return new_mu, new_var

    n_total = float(n_past + n_new)

    total_mu = (n_new * new_mu + n_past * mu) / n_total

    old_ssd = n_past * var
    new_ssd = n_new * new_var
    total_ssd = old_ssd + new_ssd + (n_new * n_past / n_total) * (mu - new_mu) ** 2
    total_var = total_ssd / n_total

    return total_mu, total_var


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
    n_past = 100
    mu = np.array([1.0, 2.0, 3.0])
    var = np.array([0.5, 0.5, 0.5])
    X = np.array([[1.1, 2.1, 3.1], [0.9, 1.9, 2.9], [1.2, 2.2, 3.2]])
    sample_weight = np.array([0.5, 0.3, 0.2])

    return _update_mean_variance(n_past, mu, var, X, sample_weight)


# 定义测试用例2
def testcase_2():
    n_past = 50
    mu = np.array([0.0, 0.0])
    var = np.array([1.0, 1.0])
    X = np.array([[0.1, -0.1], [-0.1, 0.1], [0.2, -0.2]])
    sample_weight = None

    return _update_mean_variance(n_past, mu, var, X, sample_weight)


# 定义测试用例3
def testcase_3():
    n_past = 200
    mu = np.array([5.0])
    var = np.array([2.0])
    X = np.array([[4.8], [5.2], [5.0]])
    sample_weight = np.array([1.0, 1.0, 1.0])

    return _update_mean_variance(n_past, mu, var, X, sample_weight)


# 定义测试用例4
def testcase_4():
    n_past = 0
    mu = np.array([0.0, 0.0, 0.0])
    var = np.array([0.0, 0.0, 0.0])
    X = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])
    sample_weight = None

    return _update_mean_variance(n_past, mu, var, X, sample_weight)


# 定义测试用例5
def testcase_5():
    n_past = 150
    mu = np.array([10.0, 20.0])
    var = np.array([5.0, 10.0])
    X = np.array([[9.5, 19.5], [10.5, 20.5], [10.0, 20.0]])
    sample_weight = np.array([0.4, 0.4, 0.2])

    return _update_mean_variance(n_past, mu, var, X, sample_weight)


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
