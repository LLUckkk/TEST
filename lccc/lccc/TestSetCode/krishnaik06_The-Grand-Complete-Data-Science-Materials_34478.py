import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import matplotlib.transforms as mtransforms
from matplotlib.transforms import Bbox


#############change###########
def splitx(self, *args):
    xf = [0, *args, 1]
    x0, y0, x1, y1 = self.extents
    w = x1 - x0
    return [Bbox([[x0 + xf0 * w, y0], [x0 + xf1 * w, y1]])
            for xf0, xf1 in zip(xf[:-1], xf[1:])]


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


# 修改后的测试用例1
def testcase_1():
    class Dummy:
        def __init__(self):
            self.extents = (0, 0, 10, 10)  # 设置extents属性

    self = Dummy()
    args = (0.25, 0.5, 0.75)
    return splitx(self, *args)


# 修改后的测试用例2
def testcase_2():
    class Dummy:
        def __init__(self):
            self.extents = (0, 0, 5, 5)  # 设置extents属性

    self = Dummy()
    args = (0.1, 0.3, 0.6, 0.9)
    return splitx(self, *args)


# 修改后的测试用例3
def testcase_3():
    class Dummy:
        def __init__(self):
            self.extents = (0, 0, 20, 20)  # 设置extents属性

    self = Dummy()
    args = (0.2, 0.4, 0.6, 0.8)
    return splitx(self, *args)


# 修改后的测试用例4
def testcase_4():
    class Dummy:
        def __init__(self):
            self.extents = (-5, -5, 5, 5)  # 设置extents属性

    self = Dummy()
    args = (0.33, 0.66)
    return splitx(self, *args)


# 修改后的测试用例5
def testcase_5():
    class Dummy:
        def __init__(self):
            self.extents = (0, 0, 15, 15)  # 设置extents属性

    self = Dummy()
    args = (0.1, 0.2, 0.3, 0.4, 0.5)
    return splitx(self, *args)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def serialize_bbox(bbox):
        x0, y0, x1, y1 = bbox.extents
        return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}

    def serialize_bboxes(bbox_list):
        return [serialize_bbox(bbox) for bbox in bbox_list]

    def serialize_result(res):
        return serialize_bboxes(res["result"]) if res["success"] else None

    output = {
        "ans1": serialize_result(test_results["ans1"]),
        "ans2": serialize_result(test_results["ans2"]),
        "ans3": serialize_result(test_results["ans3"]),
        "ans4": serialize_result(test_results["ans4"]),
        "ans5": serialize_result(test_results["ans5"])
    }
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
