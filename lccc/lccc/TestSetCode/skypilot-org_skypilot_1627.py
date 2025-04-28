import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import logging
from typing import Callable

from enum import Enum

# ==== Mock 修复开始 ====

# logger修复
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 模拟db_utils
class DummyCursor:
    def execute(self, sql, params):
        logger.info(f"Executing SQL: {sql} with params {params}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class db_utils:
    @staticmethod
    def safe_cursor(db_path):
        return DummyCursor()


_DB_PATH = '/path/to/db'  # 随便给个假的


# 模拟ManagedJobStatus
class ManagedJobStatus(Enum):
    RECOVERING = 'RECOVERING'


# ==== Mock 修复结束 ====


#############change###########
CallbackType = Callable[[str], None]


def set_recovering(job_id: int, task_id: int, callback_func: CallbackType):
    logger.info('=== Recovering... ===')
    with db_utils.safe_cursor(_DB_PATH) as cursor:
        cursor.execute(
            """\
                UPDATE spot SET
                status=(?), job_duration=job_duration+(?)-last_recovered_at
                WHERE spot_job_id=(?) AND
                task_id=(?)""",
            (ManagedJobStatus.RECOVERING.value, time.time(), job_id, task_id))
    callback_func('RECOVERING')
    return f"Recovery set for job {job_id}, task {task_id}"


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
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
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


# 测试用例们
def testcase_1():
    job_id = 101
    task_id = 1
    callback_func = lambda status: print(f"Callback called with status: {status}")
    return set_recovering(job_id, task_id, callback_func)


def testcase_2():
    job_id = 202
    task_id = 2
    callback_func = lambda status: print(f"Job is now in {status} state")
    return set_recovering(job_id, task_id, callback_func)


def testcase_3():
    job_id = 303
    task_id = 3
    callback_func = lambda status: print(f"Status updated to: {status}")
    return set_recovering(job_id, task_id, callback_func)


def testcase_4():
    job_id = 404
    task_id = 4
    callback_func = lambda status: print(f"Current status: {status}")
    return set_recovering(job_id, task_id, callback_func)


def testcase_5():
    job_id = 505
    task_id = 5
    callback_func = lambda status: print(f"Task status changed to: {status}")
    return set_recovering(job_id, task_id, callback_func)


def main():
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
