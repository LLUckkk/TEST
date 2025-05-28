import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


#############change###########
def array_to_string(array, col_delim=" ", row_delim="\n", digits=8, value_format="{}"):
    array = np.asanyarray(array)
    digits = int(digits)
    row_delim = str(row_delim)
    col_delim = str(col_delim)
    value_format = str(value_format)

    if len(array.shape) > 2:
        raise ValueError("conversion only works on 1D/2D arrays not %s!", str(array.shape))

    if array.dtype.names is not None:
        raise ValueError("array is  structured, use structured_array_to_string instead")

    repeats = value_format.count("{")

    if array.dtype.kind in ["i", "u"]:
        format_str = value_format + col_delim
    elif array.dtype.kind == "f":
        format_str = value_format.replace("{}", "{:." + str(digits) + "f}") + col_delim
    else:
        raise ValueError("dtype %s not convertible!", array.dtype.name)

    end_junk = len(col_delim)
    if len(array.shape) == 2:
        format_str *= array.shape[1]
        format_str = format_str[: -len(col_delim)] + row_delim
        end_junk = len(row_delim)

    format_str *= len(array)

    shaped = np.tile(array.reshape((-1, 1)), (1, repeats)).reshape(-1)

    formatted = format_str.format(*shaped)[:-end_junk]

    return formatted


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
    array = np.array([1.23456789, 2.34567891, 3.45678912])
    col_delim = ", "
    row_delim = "\n"
    digits = 5
    value_format = "{}"

    return array_to_string(array, col_delim, row_delim, digits, value_format)


# 定义测试用例2
def testcase_2():
    array = np.array([[1.1, 2.2, 3.3], [4.4, 5.5, 6.6]])
    col_delim = "; "
    row_delim = "\n"
    digits = 2
    value_format = "{}"

    return array_to_string(array, col_delim, row_delim, digits, value_format)


# 定义测试用例3
def testcase_3():
    array = np.array([10, 20, 30, 40])
    col_delim = " | "
    row_delim = "\n"
    digits = 0
    value_format = "{}"

    return array_to_string(array, col_delim, row_delim, digits, value_format)


# 定义测试用例4
def testcase_4():
    array = np.array([[123, 456], [789, 101]])
    col_delim = " - "
    row_delim = " | "
    digits = 0
    value_format = "{}"

    return array_to_string(array, col_delim, row_delim, digits, value_format)


# 定义测试用例5
def testcase_5():
    array = np.array([[0.123456789, 0.987654321], [0.111111111, 0.999999999]])
    col_delim = " "
    row_delim = "\n"
    digits = 9
    value_format = "{:.2e}"

    return array_to_string(array, col_delim, row_delim, digits, value_format)


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
