import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import threading

from streamlit.runtime.fragment import MemoryFragmentStorage
from streamlit.runtime.memory_uploaded_file_manager import MemoryUploadedFileManager
from streamlit.runtime.pages_manager import PagesManager
from streamlit.runtime.scriptrunner import ScriptRunContext
from streamlit.runtime.state import SafeSessionState, SessionState


#############change###########
def create_mock_script_run_ctx() -> ScriptRunContext:
    return ScriptRunContext(
        session_id="mock_session_id",
        _enqueue=lambda msg: None,
        query_string="mock_query_string",
        session_state=SafeSessionState(SessionState(), lambda: None),
        uploaded_file_mgr=MemoryUploadedFileManager("/mock/upload"),
        main_script_path="",
        user_info={"email": "mock@example.com"},
        fragment_storage=MemoryFragmentStorage(),
        pages_manager=PagesManager(""),
    )


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
    session_id = "test_session_1"
    _enqueue = lambda msg: print(f"Enqueue message: {msg}")
    query_string = "SELECT * FROM test_table"
    session_state = SafeSessionState(SessionState(), lambda: print("Session state callback"))
    uploaded_file_mgr = MemoryUploadedFileManager("/test/upload")
    main_script_path = "/test/script.py"
    user_info = {"email": "test1@example.com"}
    fragment_storage = MemoryFragmentStorage()
    pages_manager = PagesManager("/test/pages")

    return create_mock_script_run_ctx()


# 定义测试用例2
def testcase_2():
    session_id = "test_session_2"
    _enqueue = lambda msg: print(f"Enqueue message: {msg}")
    query_string = "SELECT * FROM another_table"
    session_state = SafeSessionState(SessionState(), lambda: print("Session state callback"))
    uploaded_file_mgr = MemoryUploadedFileManager("/another/upload")
    main_script_path = "/another/script.py"
    user_info = {"email": "test2@example.com"}
    fragment_storage = MemoryFragmentStorage()
    pages_manager = PagesManager("/another/pages")

    return create_mock_script_run_ctx()


# 定义测试用例3
def testcase_3():
    session_id = "mock_session_3"
    _enqueue = lambda msg: print(f"Enqueue message: {msg}")
    query_string = "SELECT id, name FROM users"
    session_state = SafeSessionState(SessionState(), lambda: print("Session state callback"))
    uploaded_file_mgr = MemoryUploadedFileManager("/mock/upload")
    main_script_path = "/mock/script.py"
    user_info = {"email": "mock3@example.com"}
    fragment_storage = MemoryFragmentStorage()
    pages_manager = PagesManager("/mock/pages")

    return create_mock_script_run_ctx()


# 定义测试用例4
def testcase_4():
    session_id = "mock_session_4"
    _enqueue = lambda msg: print(f"Enqueue message: {msg}")
    query_string = "SELECT * FROM orders"
    session_state = SafeSessionState(SessionState(), lambda: print("Session state callback"))
    uploaded_file_mgr = MemoryUploadedFileManager("/orders/upload")
    main_script_path = "/orders/script.py"
    user_info = {"email": "mock4@example.com"}
    fragment_storage = MemoryFragmentStorage()
    pages_manager = PagesManager("/orders/pages")

    return create_mock_script_run_ctx()


# 定义测试用例5
def testcase_5():
    session_id = "mock_session_5"
    _enqueue = lambda msg: print(f"Enqueue message: {msg}")
    query_string = "SELECT * FROM products"
    session_state = SafeSessionState(SessionState(), lambda: print("Session state callback"))
    uploaded_file_mgr = MemoryUploadedFileManager("/products/upload")
    main_script_path = "/products/script.py"
    user_info = {"email": "mock5@example.com"}
    fragment_storage = MemoryFragmentStorage()
    pages_manager = PagesManager("/products/pages")
    return create_mock_script_run_ctx()


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def script_run_ctx_to_dict(ctx: ScriptRunContext) -> dict:
        """将 ScriptRunContext 转换为字典"""
        return {
            "session_id": ctx.session_id,
            "query_string": ctx.query_string,
            "user_info": ctx.user_info,
            "main_script_path": ctx.main_script_path,
            # 如果需要其他属性，也可以继续添加
        }

    output = {
        "ans1": script_run_ctx_to_dict(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": script_run_ctx_to_dict(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": script_run_ctx_to_dict(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": script_run_ctx_to_dict(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": script_run_ctx_to_dict(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
