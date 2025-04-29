import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import altair as alt
from typing import Any


#############change###########
def DateTime(
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        milliseconds: int = 0,
        utc: bool | None = None,
) -> alt.DateTime:
    kwds: dict[str, Any] = {}
    if utc is True:
        kwds.update(utc=utc)
    if (hour, minute, second, milliseconds) != (0, 0, 0, 0):
        kwds.update(
            hours=hour, minutes=minute, seconds=second, milliseconds=milliseconds
        )
    return alt.DateTime(year=year, month=month, date=day, **kwds)


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
    year_1 = 2023
    month_1 = 5
    day_1 = 15
    hour_1 = 14
    minute_1 = 30
    second_1 = 45
    milliseconds_1 = 500
    utc_1 = True

    return DateTime(year_1, month_1, day_1, hour_1, minute_1, second_1, milliseconds_1, utc_1)


# 定义测试用例2
def testcase_2():
    year_2 = 1999
    month_2 = 12
    day_2 = 31
    hour_2 = 23
    minute_2 = 59
    second_2 = 59
    milliseconds_2 = 999
    utc_2 = False

    return DateTime(year_2, month_2, day_2, hour_2, minute_2, second_2, milliseconds_2, utc_2)


# 定义测试用例3
def testcase_3():
    year_3 = 2000
    month_3 = 1
    day_3 = 1
    hour_3 = 0
    minute_3 = 0
    second_3 = 0
    milliseconds_3 = 0
    utc_3 = None

    return DateTime(year_3, month_3, day_3, hour_3, minute_3, second_3, milliseconds_3, utc_3)


# 定义测试用例4
def testcase_4():
    year_4 = 2024
    month_4 = 2
    day_4 = 29
    hour_4 = 6
    minute_4 = 15
    second_4 = 30
    milliseconds_4 = 250
    utc_4 = True

    return DateTime(year_4, month_4, day_4, hour_4, minute_4, second_4, milliseconds_4, utc_4)


# 定义测试用例5
def testcase_5():
    year_5 = 1980
    month_5 = 7
    day_5 = 4
    hour_5 = 12
    minute_5 = 0
    second_5 = 0
    milliseconds_5 = 0
    utc_5 = False

    return DateTime(year_5, month_5, day_5, hour_5, minute_5, second_5, milliseconds_5, utc_5)


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
        "ans1": test_results["ans1"]["result"].to_dict() if test_results["ans1"]["success"] else None,
        "ans2": test_results["ans2"]["result"].to_dict() if test_results["ans2"]["success"] else None,
        "ans3": test_results["ans3"]["result"].to_dict() if test_results["ans3"]["success"] else None,
        "ans4": test_results["ans4"]["result"].to_dict() if test_results["ans4"]["success"] else None,
        "ans5": test_results["ans5"]["result"].to_dict() if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
