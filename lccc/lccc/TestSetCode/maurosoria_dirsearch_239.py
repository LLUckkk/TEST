import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import time


# 模拟接口环境
class DummyInterface:
    def new_line(self, message, do_save=True):
        print(f"[new_line] {message} (save={do_save})")
        self.last_message = message  # 为测试用例记录下来


def set_color(message, fore=None, style=None):
    return f"[{style or ''} {fore or ''}] {message}"


#############change###########
def warning(self, message, do_save=True):
    message = set_color(message, fore="yellow", style="bright")
    self.new_line(message, do_save=do_save)


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


def testcase_1():
    self = DummyInterface()
    message = "This is a warning message."
    do_save = True
    warning(self, message, do_save)
    return self.last_message


def testcase_2():
    self = DummyInterface()
    message = "Another warning message with save disabled."
    do_save = False
    warning(self, message, do_save)
    return self.last_message


def testcase_3():
    self = DummyInterface()
    message = "Warning: Task is about to complete."
    do_save = True
    warning(self, message, do_save)
    return self.last_message


def testcase_4():
    self = DummyInterface()
    message = "Warning: An error occurred while processing."
    do_save = False
    warning(self, message, do_save)
    return self.last_message


def testcase_5():
    self = DummyInterface()
    message = "Warning: Pausing threads due to user interruption."
    do_save = False
    warning(self, message, do_save)
    return self.last_message


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

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
