import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


class PNGHeaderAlignmentsDict(dict):
    def __init__(self, x, w, y, h, landmarks_xy, mask, identity):
        super().__init__()
        self["x"] = x
        self["w"] = w
        self["y"] = y
        self["h"] = h
        self["landmarks_xy"] = landmarks_xy
        self["mask"] = mask
        self["identity"] = identity


#############change###########
def to_png_meta(self) -> PNGHeaderAlignmentsDict:
    if (self.left is None or self.width is None or self.top is None or self.height is None):
        raise AssertionError("Some detected face variables have not been initialized")
    alignment = PNGHeaderAlignmentsDict(
        x=self.left,
        w=self.width,
        y=self.top,
        h=self.height,
        landmarks_xy=self.landmarks_xy.tolist(),  # 把 landmarks 也转 list
        mask={name: mask.tolist() for name, mask in self.mask.items()},  # 这里改！
        identity={k: v.tolist() for k, v in self._identity.items()}  # identity 也转 list
    )
    return alignment


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
            print(e)
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
    class Dummy:
        pass

    self = Dummy()
    self.left = 10
    self.width = 100
    self.top = 20
    self.height = 200
    self.landmarks_xy = np.array([[30, 40], [50, 60], [70, 80]])
    self.mask = {"face": np.array([[1, 0], [0, 1]])}
    self._identity = {"id": np.array([1, 2, 3])}

    return to_png_meta(self)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self.left = 15
    self.width = 150
    self.top = 25
    self.height = 250
    self.landmarks_xy = np.array([[35, 45], [55, 65], [75, 85]])
    self.mask = {"face": np.array([[0, 1], [1, 0]])}
    self._identity = {"id": np.array([4, 5, 6])}

    return to_png_meta(self)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self.left = 20
    self.width = 200
    self.top = 30
    self.height = 300
    self.landmarks_xy = np.array([[40, 50], [60, 70], [80, 90]])
    self.mask = {"face": np.array([[1, 1], [1, 1]])}
    self._identity = {"id": np.array([7, 8, 9])}

    return to_png_meta(self)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self.left = 25
    self.width = 250
    self.top = 35
    self.height = 350
    self.landmarks_xy = np.array([[45, 55], [65, 75], [85, 95]])
    self.mask = {"face": np.array([[0, 0], [0, 0]])}
    self._identity = {"id": np.array([10, 11, 12])}

    return to_png_meta(self)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self.left = 30
    self.width = 300
    self.top = 40
    self.height = 400
    self.landmarks_xy = np.array([[50, 60], [70, 80], [90, 100]])
    self.mask = {"face": np.array([[1, 0], [0, 1]])}
    self._identity = {"id": np.array([13, 14, 15])}

    return to_png_meta(self)


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
