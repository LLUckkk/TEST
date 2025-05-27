import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

from lib2to3.refactor import RefactoringTool, get_fixers_from_package


def refactor_with_2to3(source_code: str, fixer_names=None, filename=''):
    """
    使用 lib2to3 对代码字符串进行语法转换。
    """
    if fixer_names is None:
        fixer_names = get_fixers_from_package("lib2to3.fixes")
    else:
        # 自动补全为完整路径
        fixer_names = [f if f.startswith("lib2to3.fixes.") else f"lib2to3.fixes.fix_{f}" for f in fixer_names]

    tool = RefactoringTool(fixer_names)
    tree = tool.refactor_string(source_code, name=filename)
    return str(tree)


#############change###########

def refactor(source, fixer_names, ignore=None, filename=''):
    not_found_end_of_file_newline = source and source.rstrip("\r\n") == source
    if not_found_end_of_file_newline:
        input_source = source + "\n"
    else:
        input_source = source

    from lib2to3 import pgen2
    try:
        new_text = refactor_with_2to3(input_source,
                                      fixer_names=fixer_names,
                                      filename=filename)
    except (pgen2.parse.ParseError,
            SyntaxError,
            UnicodeDecodeError,
            UnicodeEncodeError):
        return source

    if ignore:
        if ignore in new_text and ignore not in source:
            return source

    if not_found_end_of_file_newline:
        return new_text.rstrip("\r\n")

    return new_text


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
    source = "print 'Hello, world!'"
    fixer_names = ["print"]
    ignore = None
    filename = "example.py"

    return refactor(source, fixer_names, ignore, filename)


# 定义测试用例2
def testcase_2():
    source = "xrange(10)"
    fixer_names = ["xrange"]
    ignore = "xrange"
    filename = "test.py"

    return refactor(source, fixer_names, ignore, filename)


# 定义测试用例3
def testcase_3():
    source = "import StringIO"
    fixer_names = ["imports"]
    ignore = None
    filename = "script.py"

    return refactor(source, fixer_names, ignore, filename)


# 定义测试用例4
def testcase_4():
    source = "def foo():\n    pass"
    fixer_names = []
    ignore = None
    filename = "foo.py"

    return refactor(source, fixer_names, ignore, filename)


# 定义测试用例5
def testcase_5():
    source = "print 'Hello, world!'\nimport StringIO"
    fixer_names = ["print", "imports"]
    ignore = "StringIO"
    filename = "combined.py"

    return refactor(source, fixer_names, ignore, filename)


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
