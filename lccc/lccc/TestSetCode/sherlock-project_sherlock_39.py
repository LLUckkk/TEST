import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import re

from enum import Enum
from dataclasses import dataclass


# 模拟的查询状态枚举
class QueryStatus(Enum):
    CLAIMED = "CLAIMED"
    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"


# 模拟的状态包装器
@dataclass
class StatusWrapper:
    status: QueryStatus


# 模拟的查询通知类（可空实现）
class QueryNotify:
    def __init__(self):
        pass


# 模拟的 sherlock 查询函数
def sherlock(username: str, site_data: dict, query_notify: QueryNotify) -> dict:
    results = {}
    for site, info in site_data.items():
        pattern = info.get("regexCheck", r".*")
        url_template = info.get("url", "{}")
        url = url_template.format(username)

        # 简单的正则检查 + 模拟是否存在
        if not re.match(pattern, username):
            status = QueryStatus.UNKNOWN
        else:
            # 模拟：用户名中含有"valid"或"pro"时为已注册
            if any(x in username.lower() for x in ["valid", "pro", "insta", "reddit"]):
                status = QueryStatus.CLAIMED
            else:
                status = QueryStatus.AVAILABLE

        results[site] = {
            "url": url,
            "status": StatusWrapper(status)
        }
    return results


#############change###########
def simple_query(sites_info: dict, site: str, username: str) -> QueryStatus:
    query_notify = QueryNotify()
    site_data: dict = {}
    site_data[site] = sites_info[site]
    return sherlock(
        username=username,
        site_data=site_data,
        query_notify=query_notify,
    )[site]['status'].status


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
    sites_info = {
        'GitHub': {
            'regexCheck': r'^[a-zA-Z0-9_-]+$',
            'url': 'https://github.com/{}',
        }
    }
    site = 'GitHub'
    username = 'validUser123'

    return simple_query(sites_info, site, username)


# 定义测试用例2
def testcase_2():
    sites_info = {
        'Twitter': {
            'regexCheck': r'^[a-zA-Z0-9_]{1,15}$',
            'url': 'https://twitter.com/{}',
        }
    }
    site = 'Twitter'
    username = 'another_user'

    return simple_query(sites_info, site, username)


# 定义测试用例3
def testcase_3():
    sites_info = {
        'Instagram': {
            'regexCheck': r'^[a-zA-Z0-9._]+$',
            'url': 'https://instagram.com/{}',
        }
    }
    site = 'Instagram'
    username = 'insta.user'

    return simple_query(sites_info, site, username)


# 定义测试用例4
def testcase_4():
    sites_info = {
        'Reddit': {
            'regexCheck': r'^[a-zA-Z0-9_-]{3,20}$',
            'url': 'https://reddit.com/user/{}',
        }
    }
    site = 'Reddit'
    username = 'redditUser'

    return simple_query(sites_info, site, username)


# 定义测试用例5
def testcase_5():
    sites_info = {
        'LinkedIn': {
            'regexCheck': r'^[a-zA-Z0-9-]+$',
            'url': 'https://linkedin.com/in/{}',
        }
    }
    site = 'LinkedIn'
    username = 'professional-profile'

    return simple_query(sites_info, site, username)


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
        if isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
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
