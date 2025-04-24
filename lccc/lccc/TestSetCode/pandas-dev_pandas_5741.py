import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
from typing import Hashable

import requests

import pandas as pd
import numpy as np
from pandas import DataFrame, Series
from pandas import Index


#############change###########
def _generate_marginal_results_without_values(
        table: DataFrame,
        data: DataFrame,
        rows,
        cols,
        aggfunc,
        kwargs,
        observed: bool,
        margins_name: Hashable = "All",
):
    margin_keys: list | Index
    if len(cols) > 0:
        margin_keys = []

        def _all_key():
            if len(cols) == 1:
                return margins_name
            return (margins_name,) + ("",) * (len(cols) - 1)

        if len(rows) > 0:
            margin = data.groupby(rows, observed=observed)[rows].apply(
                aggfunc, **kwargs
            )
            all_key = _all_key()
            table[all_key] = margin
            result = table
            margin_keys.append(all_key)

        else:
            margin = data.groupby(level=0, observed=observed).apply(aggfunc, **kwargs)
            all_key = _all_key()
            table[all_key] = margin
            result = table
            margin_keys.append(all_key)
            return result
    else:
        result = table
        margin_keys = table.columns

    if len(cols):
        row_margin = data.groupby(cols, observed=observed)[cols].apply(
            aggfunc, **kwargs
        )
    else:
        row_margin = Series(np.nan, index=result.columns)

    return result, margin_keys, row_margin


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
    table = pd.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6]
    })
    data = pd.DataFrame({
        'A': [1, 2, 3, 1, 2, 3],
        'B': [4, 5, 6, 4, 5, 6],
        'C': [7, 8, 9, 7, 8, 9]
    })
    rows = ['A']
    cols = ['B']
    aggfunc = np.sum
    kwargs = {}
    observed = False
    margins_name = "All"

    return _generate_marginal_results_without_values(table, data, rows, cols, aggfunc, kwargs, observed, margins_name, )


# 定义测试用例2
def testcase_2():
    table = pd.DataFrame({
        'X': [10, 20, 30],
        'Y': [40, 50, 60]
    })
    data = pd.DataFrame({
        'X': [10, 20, 30, 10, 20, 30],
        'Y': [40, 50, 60, 40, 50, 60],
        'Z': [70, 80, 90, 70, 80, 90]
    })
    rows = ['X']
    cols = ['Y']
    aggfunc = np.mean
    kwargs = {}
    observed = True
    margins_name = "Total"

    return _generate_marginal_results_without_values(table, data, rows, cols, aggfunc, kwargs, observed, margins_name, )


# 定义测试用例3
def testcase_3():
    table = pd.DataFrame({
        'D': [100, 200, 300],
        'E': [400, 500, 600]
    })
    data = pd.DataFrame({
        'D': [100, 200, 300, 100, 200, 300],
        'E': [400, 500, 600, 400, 500, 600],
        'F': [700, 800, 900, 700, 800, 900]
    })
    rows = ['D']
    cols = ['E']
    aggfunc = np.max
    kwargs = {}
    observed = False
    margins_name = "Sum"

    return _generate_marginal_results_without_values(table, data, rows, cols, aggfunc, kwargs, observed, margins_name, )


# 定义测试用例4
def testcase_4():
    table = pd.DataFrame({
        'G': [1000, 2000, 3000],
        'H': [4000, 5000, 6000]
    })
    data = pd.DataFrame({
        'G': [1000, 2000, 3000, 1000, 2000, 3000],
        'H': [4000, 5000, 6000, 4000, 5000, 6000],
        'I': [7000, 8000, 9000, 7000, 8000, 9000]
    })
    rows = ['G']
    cols = ['H']
    aggfunc = np.min
    kwargs = {}
    observed = True
    margins_name = "Overall"

    return _generate_marginal_results_without_values(table, data, rows, cols, aggfunc, kwargs, observed, margins_name, )


# 定义测试用例5
def testcase_5():
    table = pd.DataFrame({
        'J': [10000, 20000, 30000],
        'K': [40000, 50000, 60000]
    })
    data = pd.DataFrame({
        'J': [10000, 20000, 30000, 10000, 20000, 30000],
        'K': [40000, 50000, 60000, 40000, 50000, 60000],
        'L': [70000, 80000, 90000, 70000, 80000, 90000]
    })
    rows = ['J']
    cols = ['K']
    aggfunc = np.median
    kwargs = {}
    observed = False
    margins_name = "Summary"

    return _generate_marginal_results_without_values(table, data, rows, cols, aggfunc, kwargs, observed, margins_name, )


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
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
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
