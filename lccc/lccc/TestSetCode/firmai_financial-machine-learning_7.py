import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import pandas as pd
import os

# 项目的根目录，可以手动指定路径或从环境变量中读取
PROJECT_ROOT_DIR = os.path.dirname(__file__)


def get_repo_path(url: str) -> str:
    """
    从 GitHub 仓库 URL 提取 repo_path，格式如 'user/repo'。
    假设 URL 的格式为 'https://github.com/user/repo'。
    """
    parts = url.split('/')
    if len(parts) > 3:
        return f"{parts[3]}/{parts[4]}"
    return ""


#############change###########
def get_repo_list():
    repo_df = pd.read_csv(os.path.join(PROJECT_ROOT_DIR, 'raw_data', 'url_list.csv'))
    if 'repo_path' not in repo_df.columns:
        repo_df['repo_path'] = repo_df['url'].apply(get_repo_path)
    return repo_df


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


# 定义测试用例1
def testcase_1():
    data = {
        'category': ['Machine Learning', 'Data Science'],
        'url': ['https://github.com/user/repo1', 'https://github.com/user/repo2'],
        'comment': ['Great repo', 'Useful repo'],
        'created_at': ['2021-01-01', '2021-06-01'],
        'last_commit': ['2023-01-01', '2023-06-01'],
        'star_count': [150, 200],
        'repo_status': ['active', 'inactive'],
        'rating': [4.5, 4.0]
    }
    repo_df = pd.DataFrame(data)
    repo_df.to_csv(os.path.join(PROJECT_ROOT_DIR, 'raw_data', 'url_list.csv'), index=False)

    return get_repo_list()


# 定义测试用例2
def testcase_2():
    data = {
        'category': ['Web Development', 'Mobile Development'],
        'url': ['https://github.com/user/repo3', 'https://github.com/user/repo4'],
        'comment': ['Popular repo', 'Trending repo'],
        'created_at': ['2020-05-01', '2020-08-01'],
        'last_commit': ['2023-02-01', '2023-07-01'],
        'star_count': [300, 400],
        'repo_status': ['active', 'active'],
        'rating': [4.8, 4.9]
    }
    repo_df = pd.DataFrame(data)
    repo_df.to_csv(os.path.join(PROJECT_ROOT_DIR, 'raw_data', 'url_list.csv'), index=False)

    return get_repo_list()


# 定义测试用例3
def testcase_3():
    data = {
        'category': ['DevOps', 'Cloud Computing'],
        'url': ['https://github.com/user/repo5', 'https://github.com/user/repo6'],
        'comment': ['Essential repo', 'Cloud repo'],
        'created_at': ['2019-03-01', '2019-09-01'],
        'last_commit': ['2023-03-01', '2023-08-01'],
        'star_count': [500, 600],
        'repo_status': ['inactive', 'active'],
        'rating': [4.7, 4.6]
    }
    repo_df = pd.DataFrame(data)
    repo_df.to_csv(os.path.join(PROJECT_ROOT_DIR, 'raw_data', 'url_list.csv'), index=False)

    return get_repo_list()


# 定义测试用例4
def testcase_4():
    data = {
        'category': ['Artificial Intelligence', 'Big Data'],
        'url': ['https://github.com/user/repo7', 'https://github.com/user/repo8'],
        'comment': ['AI repo', 'Big Data repo'],
        'created_at': ['2018-11-01', '2018-12-01'],
        'last_commit': ['2023-04-01', '2023-09-01'],
        'star_count': [700, 800],
        'repo_status': ['active', 'inactive'],
        'rating': [4.9, 4.2]
    }
    repo_df = pd.DataFrame(data)
    repo_df.to_csv(os.path.join(PROJECT_ROOT_DIR, 'raw_data', 'url_list.csv'), index=False)

    return get_repo_list()


# 定义测试用例5
def testcase_5():
    data = {
        'category': ['Cybersecurity', 'Blockchain'],
        'url': ['https://github.com/user/repo9', 'https://github.com/user/repo10'],
        'comment': ['Security repo', 'Blockchain repo'],
        'created_at': ['2021-08-01', '2021-09-01'],
        'last_commit': ['2023-01-01', '2023-02-01'],
        'star_count': [1000, 1200],
        'repo_status': ['active', 'active'],
        'rating': [4.6, 4.9]
    }
    repo_df = pd.DataFrame(data)
    repo_df.to_csv(os.path.join(PROJECT_ROOT_DIR, 'raw_data', 'url_list.csv'), index=False)

    return get_repo_list()


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def serialize_result(obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")

    output = {
        "ans1": serialize_result(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": serialize_result(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": serialize_result(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": serialize_result(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": serialize_result(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    raw_data_path = os.path.join(PROJECT_ROOT_DIR, 'raw_data')
    os.makedirs(raw_data_path, exist_ok=True)
    main()
