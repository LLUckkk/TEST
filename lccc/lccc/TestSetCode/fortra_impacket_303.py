import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import io
import sys


#############change###########
def printTable(items, header):
    colLen = []
    for i, col in enumerate(header):
        rowMaxLen = max([len(row[i]) for row in items])
        colLen.append(max(rowMaxLen, len(col)))

    outputFormat = ' '.join(['{%d:%ds} ' % (num, width) for num, width in enumerate(colLen)])

    print(outputFormat.format(*header))
    print('  '.join(['-' * itemLen for itemLen in colLen]))

    for row in items:
        print(outputFormat.format(*row))


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
    """完全解决线程残留问题的执行器，并捕获stdout"""
    result_queue = queue.Queue()
    event = threading.Event()  # 线程协调事件

    def worker():
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()  # 👈 重定向标准输出
        try:
            with request_context() as session:
                if 'session' in testcase_func.__code__.co_varnames:
                    testcase_func(session=session)
                else:
                    testcase_func()
            if not event.is_set():
                result_queue.put(('success', buffer.getvalue()))  # 👈 获取输出
        except Exception as e:
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            sys.stdout = old_stdout  # 👈 恢复标准输出
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True

    start_time = time.time()
    t.start()

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


# 定义测试用例1
def testcase_1():
    items = [
        ["Alice", "User", "Unconstrained", "N/A", "True"],
        ["Bob", "User", "Constrained", "Service1", "False"],
        ["Charlie", "Computer", "Constrained w/ Protocol Transition", "Service2", "True"]
    ]
    header = ["AccountName", "AccountType", "DelegationType", "DelegationRightsTo", "SPN Exists"]

    return printTable(items, header)


# 定义测试用例2
def testcase_2():
    items = [
        ["Server01", "Computer", "Unconstrained", "N/A", "False"],
        ["Database01", "Service", "Constrained", "DBAccess", "True"]
    ]
    header = ["AccountName", "AccountType", "DelegationType", "DelegationRightsTo", "SPN Exists"]

    return printTable(items, header)


# 定义测试用例3
def testcase_3():
    items = [
        ["User1", "User", "Constrained", "WebService", "True"],
        ["User2", "User", "Constrained", "FileService", "False"],
        ["User3", "User", "Unconstrained", "N/A", "True"],
        ["User4", "User", "Constrained w/ Protocol Transition", "MailService", "True"]
    ]
    header = ["AccountName", "AccountType", "DelegationType", "DelegationRightsTo", "SPN Exists"]

    return printTable(items, header)


# 定义测试用例4
def testcase_4():
    items = [
        ["Admin", "Admin", "Unconstrained", "N/A", "True"],
        ["Guest", "User", "Constrained", "LimitedAccess", "False"]
    ]
    header = ["AccountName", "AccountType", "DelegationType", "DelegationRightsTo", "SPN Exists"]

    return printTable(items, header)


# 定义测试用例5
def testcase_5():
    items = [
        ["ServiceAccount", "Service", "Constrained", "APIService", "True"],
        ["BackupService", "Service", "Constrained w/ Protocol Transition", "BackupAccess", "False"],
        ["NetworkDevice", "Device", "Unconstrained", "N/A", "True"]
    ]
    header = ["AccountName", "AccountType", "DelegationType", "DelegationRightsTo", "SPN Exists"]

    return printTable(items, header)


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
