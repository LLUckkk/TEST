import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MaxAbsScaler


#############change###########
def _digits_dataset(n_samples=None, dtype=np.float32):
    X, y = load_digits(return_X_y=True)
    X = X.astype(dtype, copy=False)
    X = MaxAbsScaler().fit_transform(X)
    X = X[:n_samples]
    y = y[:n_samples]

    X, X_val, y, y_val = train_test_split(X, y, test_size=0.1, random_state=0)
    return X, X_val, y, y_val


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
    n_samples = 100
    dtype = np.float32

    return _digits_dataset(n_samples, dtype)


# 定义测试用例2
def testcase_2():
    n_samples = 200
    dtype = np.float64

    return _digits_dataset(n_samples, dtype)


# 定义测试用例3
def testcase_3():
    n_samples = None
    dtype = np.float32

    return _digits_dataset(n_samples, dtype)


# 定义测试用例4
def testcase_4():
    n_samples = 50
    dtype = np.float64

    return _digits_dataset(n_samples, dtype)


# 定义测试用例5
def testcase_5():
    n_samples = 300
    dtype = np.float32

    return _digits_dataset(n_samples, dtype)


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

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
