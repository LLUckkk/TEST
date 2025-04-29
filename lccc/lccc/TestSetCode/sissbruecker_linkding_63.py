import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

from typing import List
from unittest.mock import MagicMock


def expect(mock_obj):
    # 返回一个具有断言方法的 MagicMock 对象
    expectation = MagicMock()
    expectation.to_have_count = MagicMock()
    expectation.to_be_visible = MagicMock()
    return expectation


#############change###########
def assertVisibleTags(self, titles: List[str]):
    tag_tags = self.page.locator(".tag-cloud .unselected-tags a")
    expect(tag_tags).to_have_count(len(titles))

    for title in titles:
        matching_tag = tag_tags.filter(has_text=title)
        expect(matching_tag).to_be_visible()


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


def build_mocked_self():
    tag_locator = MagicMock()
    tag_locator.filter.return_value = MagicMock()
    mocked_self = MagicMock()
    mocked_self.page.locator.return_value = tag_locator
    return mocked_self


# 定义测试用例们
def testcase_1():
    self = build_mocked_self()
    titles = ["Tag 1", "Tag 2", "Tag 3"]
    try:
        assertVisibleTags(self, titles)
        return "Testcase 1 passed"
    except Exception as e:
        return f"Testcase 1 failed: {str(e)}"


def testcase_2():
    self = build_mocked_self()
    titles = ["Archived Tag 1", "Archived Tag 2"]
    try:
        assertVisibleTags(self, titles)
        return "Testcase 2 passed"
    except Exception as e:
        return f"Testcase 2 failed: {str(e)}"


def testcase_3():
    self = build_mocked_self()
    titles = ["Shared Tag 1", "Shared Tag 2", "Shared Tag 3"]
    try:
        assertVisibleTags(self, titles)
        return "Testcase 3 passed"
    except Exception as e:
        return f"Testcase 3 failed: {str(e)}"


def testcase_4():
    self = build_mocked_self()
    titles = ["Bookmark Tag A", "Bookmark Tag B"]
    try:
        assertVisibleTags(self, titles)
        return "Testcase 4 passed"
    except Exception as e:
        return f"Testcase 4 failed: {str(e)}"


def testcase_5():
    self = build_mocked_self()
    titles = ["Important Tag", "Urgent Tag", "Optional Tag"]
    try:
        assertVisibleTags(self, titles)
        return "Testcase 5 passed"
    except Exception as e:
        return f"Testcase 5 failed: {str(e)}"


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
