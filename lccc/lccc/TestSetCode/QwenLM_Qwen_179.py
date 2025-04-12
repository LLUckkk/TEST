import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import subprocess
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


#############change###########
def run_in_subprocess(cmd):
    try:
        # 使用universal_newlines=True自动处理文本编码
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True  # 自动解码输出为字符串
        )

        stdout, stderr = process.communicate(timeout=10)  # 设置超时时间

        result = {
            "return_code": process.returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }

        if process.returncode != 0:
            raise RuntimeError(stderr)

        return result

    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError("Command timed out")
    except Exception as e:
        logger.error(f"Subprocess execution failed: {str(e)}")
        raise


#############change###########

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


# 测试用例 - 修改为直接返回命令输出
def testcase_1():
    result = run_in_subprocess("echo 'Hello, World!'")
    return result["stdout"] or result["stderr"]


def testcase_2():
    result = run_in_subprocess("ls -la /")
    return result["stdout"] or result["stderr"]


def testcase_3():
    result = run_in_subprocess("python -c 'print(\"Test subprocess execution\")'")
    return result["stdout"] or result["stderr"]


def testcase_4():
    result = run_in_subprocess("uname -a")
    return result["stdout"] or result["stderr"]


def testcase_5():
    result = run_in_subprocess("docker --version")
    return result["stdout"] or result["stderr"]


def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=10),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    # 处理输出结果
    output = {}
    for key, result in test_results.items():
        if result["success"]:
            output[key] = result["result"]
        else:
            output[key] = result.get("error", "Execution failed")

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
