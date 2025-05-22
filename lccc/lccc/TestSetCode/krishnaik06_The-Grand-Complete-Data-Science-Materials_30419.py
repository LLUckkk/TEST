import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import matplotlib.pyplot as plt
import numpy as np
import datetime


#############change###########
def barh(
        y, width, height=0.8, left=None, *, align='center',
        data=None, **kwargs):
    return plt.gca().barh(
        y, width, height=height, left=left, align=align,
        **({"data": data} if data is not None else {}), **kwargs)


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
    y = [1, 2, 3]
    width = [4, 5, 6]
    height = 0.5
    left = [0, 1, 2]
    align = 'center'
    data = None
    kwargs = {'color': 'blue'}

    return barh(y, width, height, left, **kwargs)


# 定义测试用例2
def testcase_2():
    y = [10, 20, 30]
    width = [7, 8, 9]
    height = 1.0
    left = [5, 5, 5]
    align = 'edge'
    data = None
    kwargs = {'edgecolor': 'red'}

    return barh(y, width, height, left, **kwargs)


# 定义测试用例3
def testcase_3():
    y = [datetime.datetime(2023, 1, 1), datetime.datetime(2023, 1, 2)]
    width = [1, 2]
    height = datetime.timedelta(days=1)
    left = [datetime.datetime(2023, 1, 1)]
    align = 'center'
    data = None
    kwargs = {'alpha': 0.7}

    return barh(y, width, height, left, **kwargs)


# 定义测试用例4
def testcase_4():
    y = np.array([0.1, 0.2, 0.3])
    width = np.array([0.4, 0.5, 0.6])
    height = 0.3
    left = np.array([0.05, 0.05, 0.05])
    align = 'center'
    data = None
    kwargs = {'linewidth': 2}

    return barh(y, width, height, left, **kwargs)


# 定义测试用例5
def testcase_5():
    y = ['a', 'b', 'c']
    width = [10, 20, 30]
    height = 0.8
    left = [1, 2, 3]
    align = 'center'
    data = None
    kwargs = {'label': 'Test Bars'}

    return barh(y, width, height, left, **kwargs)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def to_serializable(val):
        """将NumPy类型转换为原生Python类型"""
        if isinstance(val, (np.integer, np.int32, np.int64)):
            return int(val)
        elif isinstance(val, (np.floating, np.float32, np.float64)):
            return float(val)
        elif isinstance(val, (datetime.datetime, datetime.date)):
            return val.isoformat()
        elif isinstance(val, (datetime.timedelta,)):
            return val.total_seconds()
        return val  # 其他类型保持原样

    def serialize_bar_container(bar_container):
        return [
            {
                "x": to_serializable(rect.get_x()),
                "y": to_serializable(rect.get_y()),
                "width": to_serializable(rect.get_width()),
                "height": to_serializable(rect.get_height()),
            }
            for rect in bar_container
        ]

    output = {
        "ans1": serialize_bar_container(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": serialize_bar_container(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": serialize_bar_container(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": serialize_bar_container(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": serialize_bar_container(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
