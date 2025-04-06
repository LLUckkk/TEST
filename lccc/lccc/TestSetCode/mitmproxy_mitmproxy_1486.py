import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
from typing import AnyStr
import socket
import re

_authority_re = re.compile(
    r'^(?P<host>(?:[a-zA-Z0-9-._~%]+|(?:\[[a-fA-F0-9:]+\])))'  # host 部分：域名或者 IPv6 地址
    r'(?::(?P<port>\d+))?$'  # port 部分（可选）
)


def is_valid_port(port: int) -> bool:
    """
    检查给定的端口号是否有效。
    有效端口号范围是 1 到 65535。
    """
    return isinstance(port, int) and 1 <= port <= 65535


def is_valid_host(host: str) -> bool:
    """
    检查给定的主机名是否有效。
    支持检查有效的 IPv4 地址、IPv6 地址或域名。
    """
    try:
        # 尝试解析主机名为一个有效的 IP 地址（IPv4 或 IPv6）
        socket.getaddrinfo(host, None)
        return True
    except socket.gaierror:
        # 如果解析失败，说明主机名无效
        return False


def always_str(data: bytes | str, encoding: str = "utf-8", errors: str = "strict") -> str:
    """
    将数据转换为字符串。如果数据是字节类型（bytes），则解码为字符串。
    如果数据已经是字符串，则直接返回。
    :param data: 输入数据，可以是字节类型（bytes）或字符串（str）
    :param encoding: 用于解码字节的编码方式，默认为 "utf-8"
    :param errors: 错误处理方式，默认为 "strict"
    :return: 转换后的字符串
    """
    if isinstance(data, bytes):
        return data.decode(encoding, errors=errors)
    elif isinstance(data, str):
        return data
    else:
        raise TypeError(f"Expected bytes or str, got {type(data)}")


#############change###########
def parse_authority(authority: AnyStr, check: bool) -> tuple[str, int | None]:
    try:
        if isinstance(authority, bytes):
            m = _authority_re.match(authority.decode("utf-8"))
            if not m:
                raise ValueError
            host = m["host"].encode("utf-8").decode("idna")
        else:
            m = _authority_re.match(authority)
            if not m:
                raise ValueError
            host = m.group("host")

        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        if not is_valid_host(host):
            raise ValueError

        if m.group("port"):
            port = int(m.group("port"))
            if not is_valid_port(port):
                raise ValueError
            return host, port
        else:
            return host, None

    except ValueError:
        if check:
            raise
        else:
            return always_str(authority, "utf-8", "surrogateescape"), None


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
    authority = "example.com:8080"
    check = True

    return parse_authority(authority, check)


# 定义测试用例2
def testcase_2():
    authority = b"example.com:443"
    check = False

    return parse_authority(authority, check)


# 定义测试用例3
def testcase_3():
    authority = "invalid_host:99999"
    check = True

    return parse_authority(authority, check)


# 定义测试用例4
def testcase_4():
    authority = b"[2001:db8::1]:80"
    check = False

    return parse_authority(authority, check)


# 定义测试用例5
def testcase_5():
    authority = "localhost"
    check = True

    return parse_authority(authority, check)


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
