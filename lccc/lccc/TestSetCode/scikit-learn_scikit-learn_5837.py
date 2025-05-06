import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from scipy import stats


#############change###########
def _naive_lmvnpdf_diag(X, means, covars):
    resp = np.empty((len(X), len(means)))
    stds = np.sqrt(covars)
    for i, (mean, std) in enumerate(zip(means, stds)):
        resp[:, i] = stats.norm.logpdf(X, mean, std).sum(axis=1)
    return resp


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
# 定义测试用例1
def testcase_1():
    X = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]] * 100)
    means = np.array([[0.1, 0.2, 0.3, 0.4, 0.5],
                      [0.5, 0.4, 0.3, 0.2, 0.1],
                      [0.3, 0.3, 0.3, 0.3, 0.3]])
    covars = np.array([[0.1, 0.1, 0.1, 0.1, 0.1]] * 3)

    return _naive_lmvnpdf_diag(X, means, covars)


# 定义测试用例2
def testcase_2():
    X = np.full((50, 10), 0.2)
    means = np.full((4, 10), 0.3)
    covars = np.full((4, 10), 0.05)

    return _naive_lmvnpdf_diag(X, means, covars)


# 定义测试用例3
def testcase_3():
    X = np.array([[0.1, 0.4, 0.7]] * 200)
    means = np.array([[0.2, 0.3, 0.6],
                      [0.5, 0.5, 0.5]])
    covars = np.array([[0.1, 0.1, 0.1],
                       [0.2, 0.2, 0.2]])

    return _naive_lmvnpdf_diag(X, means, covars)


# 定义测试用例4
def testcase_4():
    X = np.tile(np.linspace(0.1, 0.7, 7), (150, 1))
    means = np.tile(np.linspace(0.2, 0.8, 7), (5, 1))
    covars = np.full((5, 7), 0.05)

    return _naive_lmvnpdf_diag(X, means, covars)


# 定义测试用例5
def testcase_5():
    X = np.ones((300, 8)) * 0.6
    means = np.ones((6, 8)) * 0.5
    covars = np.ones((6, 8)) * 0.2

    return _naive_lmvnpdf_diag(X, means, covars)


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
