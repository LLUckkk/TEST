import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


#############change###########
def SequenceConstructImpl(*tensors: np.ndarray) -> list[np.ndarray]:
    return list(tensors)


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
    x = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
    y = np.array([[7, 8, 9], [10, 11, 12]], dtype=np.float32)
    z = np.array([[13, 14, 15], [16, 17, 18]], dtype=np.float32)

    tensors = [x, y, z]
    return SequenceConstructImpl(*tensors)


# 定义测试用例2
def testcase_2():
    a = np.zeros((3, 3), dtype=np.int32)
    b = np.ones((3, 3), dtype=np.int32)
    c = np.full((3, 3), 5, dtype=np.int32)

    tensors = [a, b, c]
    return SequenceConstructImpl(*tensors)


# 定义测试用例3
def testcase_3():
    p = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    q = np.array([[0.5, 0.6], [0.7, 0.8]], dtype=np.float32)
    r = np.array([[0.9, 1.0], [1.1, 1.2]], dtype=np.float32)

    tensors = [p, q, r]
    return SequenceConstructImpl(*tensors)


# 定义测试用例4
def testcase_4():
    m = np.array([1.5, 2.5, 3.5], dtype=np.float64)
    n = np.array([4.5, 5.5, 6.5], dtype=np.float64)

    tensors = [m, n]
    return SequenceConstructImpl(*tensors)


# 定义测试用例5
def testcase_5():
    u = np.array([[1, 0], [0, 1]], dtype=np.int64)
    v = np.array([[2, 2], [2, 2]], dtype=np.int64)
    w = np.array([[3, 3], [3, 3]], dtype=np.int64)

    tensors = [u, v, w]
    return SequenceConstructImpl(*tensors)


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
        if isinstance(obj, list):
            return list(map(json_serializable, obj))
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, tuple):
            return [json_serializable(i) for i in obj]
        else:
            return str(obj)

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
