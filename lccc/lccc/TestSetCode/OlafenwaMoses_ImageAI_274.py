import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


#############change###########
def compute_overlap(a, b):
    area = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])

    iw = np.minimum(np.expand_dims(a[:, 2], axis=1), b[:, 2]) - np.maximum(np.expand_dims(a[:, 0], 1), b[:, 0])
    ih = np.minimum(np.expand_dims(a[:, 3], axis=1), b[:, 3]) - np.maximum(np.expand_dims(a[:, 1], 1), b[:, 1])

    iw = np.maximum(iw, 0)
    ih = np.maximum(ih, 0)

    ua = np.expand_dims((a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1]), axis=1) + area - iw * ih

    ua = np.maximum(ua, np.finfo(float).eps)

    intersection = iw * ih

    return intersection / ua


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
    a = np.array([[10, 20, 30, 40], [50, 60, 70, 80]])
    b = np.array([[15, 25, 35, 45], [55, 65, 75, 85]])

    return compute_overlap(a, b)


# 定义测试用例2
def testcase_2():
    a = np.array([[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]])
    b = np.array([[5, 5, 15, 15], [25, 25, 35, 35]])

    return compute_overlap(a, b)


# 定义测试用例3
def testcase_3():
    a = np.array([[100, 100, 200, 200], [150, 150, 250, 250]])
    b = np.array([[110, 110, 210, 210], [160, 160, 260, 260], [170, 170, 270, 270]])

    return compute_overlap(a, b)


# 定义测试用例4
def testcase_4():
    a = np.array([[5, 5, 15, 15], [10, 10, 20, 20], [15, 15, 25, 25]])
    b = np.array([[0, 0, 10, 10], [20, 20, 30, 30], [30, 30, 40, 40]])

    return compute_overlap(a, b)


# 定义测试用例5
def testcase_5():
    a = np.array([[50, 50, 100, 100], [60, 60, 110, 110], [70, 70, 120, 120]])
    b = np.array([[55, 55, 105, 105], [65, 65, 115, 115], [75, 75, 125, 125], [85, 85, 135, 135]])

    return compute_overlap(a, b)


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
