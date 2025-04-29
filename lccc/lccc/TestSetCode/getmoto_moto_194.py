import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
from typing import Dict


#############change###########
class IntegrationResponse:
    def __init__(self, status_code, selection_pattern, response_templates, response_parameters, content_handling):
        self.status_code = status_code
        self.selection_pattern = selection_pattern
        self.response_templates = response_templates
        self.response_parameters = response_parameters
        self.content_handling = content_handling

    def __repr__(self):
        return json.dumps(self.__dict__, indent=2)


def create_integration_response(
        self,
        status_code: str,
        selection_pattern: str,
        response_templates: Dict[str, str],
        response_parameters: Dict[str, str],
        content_handling: str,
) -> IntegrationResponse:
    integration_response = IntegrationResponse(
        status_code,
        selection_pattern,
        response_templates or None,
        response_parameters,
        content_handling,
    )
    if self.integration_responses is None:
        self.integration_responses = {}
    self.integration_responses[status_code] = integration_response
    return integration_response


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
def make_dummy():
    class Dummy:
        def __init__(self):
            self.integration_responses = None

    return Dummy()


def testcase_1():
    self = make_dummy()
    return create_integration_response(
        self,
        "200",
        "",
        {"application/json": '{"message": "Success"}'},
        {"method.response.header.Content-Type": "'application/json'"},
        "CONVERT_TO_BINARY"
    )


def testcase_2():
    self = make_dummy()
    return create_integration_response(
        self,
        "404",
        ".*NotFound.*",
        {"application/json": '{"error": "Resource not found"}'},
        {"method.response.header.Content-Type": "'application/json'"},
        "CONVERT_TO_TEXT"
    )


def testcase_3():
    self = make_dummy()
    return create_integration_response(
        self,
        "500",
        ".*InternalServerError.*",
        {"application/json": '{"error": "Internal server error"}'},
        {"method.response.header.Content-Type": "'application/json'"},
        "CONVERT_TO_BINARY"
    )


def testcase_4():
    self = make_dummy()
    return create_integration_response(
        self,
        "403",
        ".*Forbidden.*",
        {"application/json": '{"error": "Access denied"}'},
        {"method.response.header.Content-Type": "'application/json'"},
        "CONVERT_TO_TEXT"
    )


def testcase_5():
    self = make_dummy()
    return create_integration_response(
        self,
        "301",
        ".*MovedPermanently.*",
        {"application/json": '{"message": "Resource moved permanently"}'},
        {"method.response.header.Location": "'https://newlocation.com'"},
        "CONVERT_TO_BINARY"
    )


def main():
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def serialize(obj):
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return obj

    output = {
        key: serialize(res["result"]) if res["success"] else None
        for key, res in test_results.items()
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
