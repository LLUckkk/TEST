import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import matplotlib.pyplot as plt


#############change###########
def _despine(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["bottom", "left"]:
        ax.spines[s].set_bounds(0, 1)


#############change###########


# 上下文管理 requests
@contextmanager
def request_context():
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    result_queue = queue.Queue()
    event = threading.Event()

    def worker():
        try:
            with request_context() as session:
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
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()

    start_time = time.time()
    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()

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


# 定义测试用例
def testcase_1():
    ax = plt.figure().add_subplot()
    _despine(ax)
    result = {
        "visible": {s: ax.spines[s].get_visible() for s in ["top", "right"]},
        "bounds": {s: ax.spines[s].get_bounds() for s in ["bottom", "left"]}
    }
    return result


def testcase_2():
    fig, ax = plt.subplots()
    _despine(ax)
    result = {
        "visible": {s: ax.spines[s].get_visible() for s in ["top", "right"]},
        "bounds": {s: ax.spines[s].get_bounds() for s in ["bottom", "left"]}
    }
    return result


def testcase_3():
    fig = plt.figure()
    ax = fig.add_subplot(111)
    _despine(ax)
    result = {
        "visible": {s: ax.spines[s].get_visible() for s in ["top", "right"]},
        "bounds": {s: ax.spines[s].get_bounds() for s in ["bottom", "left"]}
    }
    return result


def testcase_4():
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    _despine(ax)
    result = {
        "visible": {s: ax.spines[s].get_visible() for s in ["top", "right"]},
        "bounds": {s: ax.spines[s].get_bounds() for s in ["bottom", "left"]}
    }
    return result


def testcase_5():
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    _despine(ax)
    result = {
        "visible": {s: ax.spines[s].get_visible() for s in ["top", "right"]},
        "bounds": {s: ax.spines[s].get_bounds() for s in ["bottom", "left"]}
    }
    return result


def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        k: v["result"] if v["success"] else {"error": v["error"]}
        for k, v in test_results.items()
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
