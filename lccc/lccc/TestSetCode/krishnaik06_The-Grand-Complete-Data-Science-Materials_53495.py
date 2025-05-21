import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from numpy import ndarray, array_repr
from functools import partial


#############change###########
def build_err_msg(arrays, err_msg, header='Items are not equal:',
                  verbose=True, names=('ACTUAL', 'DESIRED'), precision=8):
    msg = ['\n' + header]
    if err_msg:
        if err_msg.find('\n') == -1 and len(err_msg) < 79 - len(header):
            msg = [msg[0] + ' ' + err_msg]
        else:
            msg.append(err_msg)
    if verbose:
        for i, a in enumerate(arrays):

            if isinstance(a, ndarray):
                r_func = partial(array_repr, precision=precision)
            else:
                r_func = repr

            try:
                r = r_func(a)
            except Exception as exc:
                r = f'[repr failed for <{type(a).__name__}>: {exc}]'
            if r.count('\n') > 3:
                r = '\n'.join(r.splitlines()[:3])
                r += '...'
            msg.append(f' {names[i]}: {r}')
    return '\n'.join(msg)


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
    arrays = [np.array([1.00001, 2.00002, 3.00003]), np.array([1.00002, 2.00003, 3.00004])]
    err_msg = 'There is a mismatch'
    header = 'Items are not equal:'
    verbose = True
    names = ('ACTUAL', 'DESIRED')
    precision = 8

    return build_err_msg(arrays, err_msg, header, verbose, names)


# 定义测试用例2
def testcase_2():
    arrays = [np.array([1.00001, 2.00002, 3.00003]), np.array([1.00002, 2.00003, 3.00004])]
    err_msg = 'There is a mismatch'
    header = 'Comparison failed:'
    verbose = False
    names = ('ACTUAL', 'DESIRED')
    precision = 8

    return build_err_msg(arrays, err_msg, header, verbose, names)


# 定义测试用例3
def testcase_3():
    arrays = [np.array([1.00001, 2.00002, 3.00003]), np.array([1.00002, 2.00003, 3.00004])]
    err_msg = 'There is a mismatch'
    header = 'Items are not equal:'
    verbose = True
    names = ('FOO', 'BAR')
    precision = 10

    return build_err_msg(arrays, err_msg, header, verbose, names)


# 定义测试用例4
def testcase_4():
    arrays = [np.array([1.00001, 2.00002, 3.00003]), np.array([1.00002, 2.00003, 3.00004])]
    err_msg = 'Mismatch detected'
    header = 'Comparison failed:'
    verbose = True
    names = ('ACTUAL', 'EXPECTED')
    precision = 6

    return build_err_msg(arrays, err_msg, header, verbose, names)


# 定义测试用例5
def testcase_5():
    arrays = [np.array([1.00001, 2.00002, 3.00003]), np.array([1.00002, 2.00003, 3.00004])]
    err_msg = 'Arrays do not match'
    header = 'Items are not equal:'
    verbose = True
    names = ('ACTUAL', 'DESIRED')
    precision = 8

    return build_err_msg(arrays, err_msg, header, verbose, names)


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
