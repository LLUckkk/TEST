import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pandas as pd
import numpy as np
from pandas import Series
from pandas._libs.internals import BlockPlacement
from pandas.core.internals import Block, BlockManager, make_block


#############change###########
def _constructor_from_mgr(self, mgr, axes):
    ser = Series._from_mgr(mgr, axes=axes)
    ser._name = None

    if type(self) is Series:
        return ser

    return self._constructor(ser)


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
                print(f'Exception occurred in worker thread: {e}')
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
    class Dummy:
        pass

    self = Dummy()

    # 创建一维数据
    data = np.array([1, 2, 3])

    # 使用 BlockPlacement 来代替 slice
    placement = BlockPlacement([0])  # 这里表示数据的位置（单列）
    block = Block(data.reshape(-1, 1), placement=placement, ndim=2)  # ndim=2 表示二维数据

    # axes 需要两个轴：
    # 第 1 个轴是行索引（index）
    # 第 2 个轴是列索引（columns）
    mgr = BlockManager([block], [pd.Index(['a', 'b', 'c']), pd.Index(['A'])])  # 管理器
    axes = [pd.Index(['a', 'b', 'c']), pd.Index(['A'])]  # 两个轴

    return _constructor_from_mgr(self, mgr, axes)


def testcase_2():
    class Dummy:
        pass

    self = Dummy()

    # 创建一维数据
    data = np.array([4, 5, 6])

    # 使用 BlockPlacement 来代替 slice
    placement = BlockPlacement([0])
    block = Block(data.reshape(-1, 1), placement=placement, ndim=2)

    # axes 需要两个轴：
    mgr = BlockManager([block], [pd.Index(['x', 'y', 'z']), pd.Index(['B'])])
    axes = [pd.Index(['x', 'y', 'z']), pd.Index(['B'])]

    return _constructor_from_mgr(self, mgr, axes)


def testcase_3():
    class Dummy:
        pass

    self = Dummy()

    # 创建一维数据
    data = np.array([7, 8, 9])

    # 使用 BlockPlacement 来代替 slice
    placement = BlockPlacement([0])
    block = Block(data.reshape(-1, 1), placement=placement, ndim=2)

    # axes 需要两个轴：
    mgr = BlockManager([block], [pd.Index(['foo', 'bar', 'baz']), pd.Index(['C'])])
    axes = [pd.Index(['foo', 'bar', 'baz']), pd.Index(['C'])]

    return _constructor_from_mgr(self, mgr, axes)


def testcase_4():
    class Dummy:
        pass

    self = Dummy()

    # 创建一维数据
    data = np.array([10, 11, 12])

    # 使用 BlockPlacement 来代替 slice
    placement = BlockPlacement([0])
    block = Block(data.reshape(-1, 1), placement=placement, ndim=2)

    # axes 需要两个轴：
    mgr = BlockManager([block], [pd.Index(['one', 'two', 'three']), pd.Index(['D'])])
    axes = [pd.Index(['one', 'two', 'three']), pd.Index(['D'])]

    return _constructor_from_mgr(self, mgr, axes)


def testcase_5():
    class Dummy:
        pass

    self = Dummy()

    # 创建一维数据
    data = np.array([13, 14, 15])

    # 使用 BlockPlacement 来代替 slice
    placement = BlockPlacement([0])
    block = Block(data.reshape(-1, 1), placement=placement, ndim=2)

    # axes 需要两个轴：
    mgr = BlockManager([block], [pd.Index(['alpha', 'beta', 'gamma']), pd.Index(['E'])])
    axes = [pd.Index(['alpha', 'beta', 'gamma']), pd.Index(['E'])]

    return _constructor_from_mgr(self, mgr, axes)


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
