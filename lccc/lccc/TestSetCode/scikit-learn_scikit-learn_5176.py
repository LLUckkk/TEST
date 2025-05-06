import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import inspect
from sklearn.base import BaseEstimator


#############change###########
def _get_pos_label(self):
    if "pos_label" in self._kwargs:
        return self._kwargs["pos_label"]
    score_func_params = inspect.signature(self._score_func).parameters
    if "pos_label" in score_func_params:
        return score_func_params["pos_label"].default
    return None


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
    class TestEstimator1(BaseEstimator):
        def __init__(self):
            self._kwargs = {"pos_label": 1}
            self._score_func = lambda y_true, y_pred: sum(y_true == y_pred)

        def _get_pos_label(self):
            if "pos_label" in self._kwargs:
                return self._kwargs["pos_label"]
            score_func_params = inspect.signature(self._score_func).parameters
            if "pos_label" in score_func_params:
                return score_func_params["pos_label"].default
            return None

    estimator1 = TestEstimator1()
    pos_label1 = estimator1._get_pos_label()

    return pos_label1  # 修改为返回 pos_label1


# 定义测试用例2
def testcase_2():
    class TestEstimator2(BaseEstimator):
        def __init__(self):
            self._kwargs = {}
            self._score_func = lambda y_true, y_pred, pos_label=None: sum(y_true == y_pred)

        def _get_pos_label(self):
            if "pos_label" in self._kwargs:
                return self._kwargs["pos_label"]
            score_func_params = inspect.signature(self._score_func).parameters
            if "pos_label" in score_func_params:
                return score_func_params["pos_label"].default
            return None

    estimator2 = TestEstimator2()
    pos_label2 = estimator2._get_pos_label()

    return pos_label2  # 修改为返回 pos_label2


# 定义测试用例3
def testcase_3():
    class TestEstimator3(BaseEstimator):
        def __init__(self):
            self._kwargs = {"pos_label": "positive"}
            self._score_func = lambda y_true, y_pred, pos_label="positive": sum(y_true == y_pred)

        def _get_pos_label(self):
            if "pos_label" in self._kwargs:
                return self._kwargs["pos_label"]
            score_func_params = inspect.signature(self._score_func).parameters
            if "pos_label" in score_func_params:
                return score_func_params["pos_label"].default
            return None

    estimator3 = TestEstimator3()
    pos_label3 = estimator3._get_pos_label()

    return pos_label3  # 修改为返回 pos_label3


# 定义测试用例4
def testcase_4():
    class TestEstimator4(BaseEstimator):
        def __init__(self):
            self._kwargs = {}
            self._score_func = lambda y_true, y_pred: sum(y_true == y_pred)

        def _get_pos_label(self):
            if "pos_label" in self._kwargs:
                return self._kwargs["pos_label"]
            score_func_params = inspect.signature(self._score_func).parameters
            if "pos_label" in score_func_params:
                return score_func_params["pos_label"].default
            return None

    estimator4 = TestEstimator4()
    pos_label4 = estimator4._get_pos_label()

    return pos_label4  # 修改为返回 pos_label4


# 定义测试用例5
def testcase_5():
    class TestEstimator5(BaseEstimator):
        def __init__(self):
            self._kwargs = {"pos_label": 0}
            self._score_func = lambda y_true, y_pred, pos_label=0: sum(y_true == y_pred)

        def _get_pos_label(self):
            if "pos_label" in self._kwargs:
                return self._kwargs["pos_label"]
            score_func_params = inspect.signature(self._score_func).parameters
            if "pos_label" in score_func_params:
                return score_func_params["pos_label"].default
            return None

    estimator5 = TestEstimator5()
    pos_label5 = estimator5._get_pos_label()

    return pos_label5  # 修改为返回 pos_label5


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
