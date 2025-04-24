import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pandas as pd
import numpy as np
from pandas import DataFrame, Series, Index

# 添加BlockValuesRefs导入
try:
    from pandas.core.internals.blocks import BlockValuesRefs
except ImportError:
    from typing import Any

    BlockValuesRefs = Any  # 类型提示回退

ArrayLike = BlockValuesRefs | np.ndarray


#############change###########
def _reindex_for_setitem(
        value: DataFrame | Series, index: Index
) -> tuple[ArrayLike, BlockValuesRefs | None]:
    if value.index.equals(index) or not len(index):
        if isinstance(value, Series):
            return value._values, value._references
        return value._values.copy(), None

    try:
        reindexed_value = value.reindex(index)._values
    except ValueError as err:
        if not value.index.is_unique:
            raise err

        raise TypeError(
            "incompatible index of inserted column with frame index"
        ) from err
    return reindexed_value, None


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
    value = pd.Series([10, 20, 30], index=['a', 'b', 'c'])
    index = pd.Index(['a', 'b', 'c'])

    return _reindex_for_setitem(value, index)


# 定义测试用例2
def testcase_2():
    value = pd.Series([1, 2, 3, 4], index=['x', 'y', 'z', 'w'])
    index = pd.Index(['w', 'x', 'y', 'z'])

    return _reindex_for_setitem(value, index)


# 定义测试用例3
def testcase_3():
    value = pd.DataFrame({'col1': [5, 6], 'col2': [7, 8]}, index=['row1', 'row2'])
    index = pd.Index(['row1', 'row2'])

    return _reindex_for_setitem(value, index)


# 定义测试用例4
def testcase_4():
    value = pd.Series([100, 200, 300], index=['one', 'two', 'three'])
    index = pd.Index(['three', 'two', 'one'])

    return _reindex_for_setitem(value, index)


# 定义测试用例5
def testcase_5():
    value = pd.DataFrame({'A': [9, 8, 7], 'B': [6, 5, 4]}, index=['first', 'second', 'third'])
    index = pd.Index(['third', 'first', 'second'])

    return _reindex_for_setitem(value, index)


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
        elif 'BlockValuesRefs' in globals() and isinstance(BlockValuesRefs, type):
            try:
                return {
                    "__type__": "BlockValuesRefs",
                    "length": len(obj) if hasattr(obj, "__len__") else "unknown",
                    "note": "Internal pandas reference block"
                }
            except Exception:
                return {"__type__": "BlockValuesRefs", "note": "Unable to introspect"}
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        elif isinstance(obj, pd.Index):
            return obj.tolist()
        else:
            return str(obj)

    output = {
        "ans1": json_serializable(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": json_serializable(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": json_serializable(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": json_serializable(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": json_serializable(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2, default=json_serializable))


if __name__ == '__main__':
    main()
