import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import re
from faker import Faker


#############change###########
def legal_person_nit_with_check_digit(self) -> str:
    nit = self.legal_person_nit()
    check_digit = nit_check_digit(nit)
    return f"{nit}-{check_digit}"


#############change###########


def nit_check_digit(nit: str) -> str:
    """
    简化版 NIT 校验码生成算法：取所有数字的和对 10 取模
    """
    digits = [int(d) for d in nit if d.isdigit()]
    return str(sum(digits) % 10)


def legal_person_nit(self) -> str:
    """
    生成符合格式的 9 位数 NIT（为对拍稳定性固定前缀）
    """
    return "123456789"  # 固定返回，确保对拍稳定


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


############# Dummy 对象 #############
class Dummy:
    def __init__(self):
        self.fake = Faker()
        self._LEGAL_PERSON_NIT_REGEX = re.compile(r'^\d{9}$')
        self._CHECK_DIGIT_REGEX = re.compile(r'^\d$')

    def legal_person_nit(self):
        # 生成一个合法的 NIT（例如，9位数字）
        return self.fake.numerify('#########')


############# 测试用例 #############
def testcase_1():
    return legal_person_nit_with_check_digit(Dummy())


def testcase_2():
    return legal_person_nit_with_check_digit(Dummy())


def testcase_3():
    return legal_person_nit_with_check_digit(Dummy())


def testcase_4():
    return legal_person_nit_with_check_digit(Dummy())


def testcase_5():
    return legal_person_nit_with_check_digit(Dummy())


############# 主程序入口 #############
def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        k: v["result"] if v["success"] else {"error": v["error"]}
        for k, v in test_results.items()
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
