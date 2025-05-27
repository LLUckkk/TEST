import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from matplotlib import _api


#############change###########
def _h_arrows(self, length):
    minsh = self.minshaft * self.headlength
    N = len(length)
    length = length.reshape(N, 1)
    np.clip(length, 0, 2 ** 16, out=length)
    x = np.array([0, -self.headaxislength,
                  -self.headlength, 0],
                 np.float64)
    x = x + np.array([0, 1, 1, 1]) * length
    y = 0.5 * np.array([1, 1, self.headwidth, 0], np.float64)
    y = np.repeat(y[np.newaxis, :], N, axis=0)
    x0 = np.array([0, minsh - self.headaxislength,
                   minsh - self.headlength, minsh], np.float64)
    y0 = 0.5 * np.array([1, 1, self.headwidth, 0], np.float64)
    ii = [0, 1, 2, 3, 2, 1, 0, 0]
    X = x[:, ii]
    Y = y[:, ii]
    Y[:, 3:-1] *= -1
    X0 = x0[ii]
    Y0 = y0[ii]
    Y0[3:-1] *= -1
    shrink = length / minsh if minsh != 0. else 0.
    X0 = shrink * X0[np.newaxis, :]
    Y0 = shrink * Y0[np.newaxis, :]
    short = np.repeat(length < minsh, 8, axis=1)
    np.copyto(X, X0, where=short)
    np.copyto(Y, Y0, where=short)
    if self.pivot == 'middle':
        X -= 0.5 * X[:, 3, np.newaxis]
    elif self.pivot == 'tip':
        X = X - X[:, 3, np.newaxis]
    elif self.pivot != 'tail':
        _api.check_in_list(["middle", "tip", "tail"], pivot=self.pivot)

    tooshort = length < self.minlength
    if tooshort.any():
        th = np.arange(0, 8, 1, np.float64) * (np.pi / 3.0)
        x1 = np.cos(th) * self.minlength * 0.5
        y1 = np.sin(th) * self.minlength * 0.5
        X1 = np.repeat(x1[np.newaxis, :], N, axis=0)
        Y1 = np.repeat(y1[np.newaxis, :], N, axis=0)
        tooshort = np.repeat(tooshort, 8, 1)
        np.copyto(X, X1, where=tooshort)
        np.copyto(Y, Y1, where=tooshort)
    return X, Y


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


def create_dummy():
    d = type('Dummy', (), {})()
    d.minshaft = 0.5
    d.headlength = 5
    d.headaxislength = 2
    d.headwidth = 1
    d.minlength = 1
    d.pivot = 'tail'
    return d


# 定义测试用例1
def testcase_1():
    self = create_dummy()
    length = np.array([10, 20, 30, 40, 50], dtype=np.float64)

    return _h_arrows(self, length)


# 定义测试用例2
def testcase_2():
    self = create_dummy()
    length = np.array([5, 15, 25, 35, 45, 55, 65], dtype=np.float64)

    return _h_arrows(self, length)


# 定义测试用例3
def testcase_3():
    self = create_dummy()
    length = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=np.float64)

    return _h_arrows(self, length)


# 定义测试用例4
def testcase_4():
    self = create_dummy()
    length = np.array([100, 200, 300, 400, 500, 600, 700, 800], dtype=np.float64)

    return _h_arrows(self, length)


# 定义测试用例5
def testcase_5():
    self = create_dummy()
    length = np.array([0.1, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5], dtype=np.float64)

    return _h_arrows(self, length)


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
            return json_serializable(obj.tolist())  # 再递归转换内容
        elif isinstance(obj, (np.generic,)):
            return json_serializable(obj.item())  # 转成 Python 原生类型后继续处理
        elif isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        elif isinstance(obj, list):
            return [json_serializable(i) for i in obj]
        elif isinstance(obj, tuple):
            return tuple(json_serializable(i) for i in obj)
        elif isinstance(obj, dict):
            return {str(k): json_serializable(v) for k, v in obj.items()}
        else:
            return obj  # 假设是基本类型（int、float、str、bool、None）

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
