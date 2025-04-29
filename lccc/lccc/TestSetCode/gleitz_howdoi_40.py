import json
import logging
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import os
import argparse
import random

#############change###########
# Dummy definitions for missing parts

# 颜色输出（这里简单处理）
GREEN = ''
END_FORMAT = ''

# 支持的搜索引擎（这里只放一个假的）
SUPPORTED_SEARCH_ENGINES = ['google', 'bing']


# 模拟异常
class RequestsConnectionError(Exception):
    pass


class SSLError(Exception):
    pass


class BlockError(Exception):
    pass


BLOCKED_ENGINES = []

NO_RESULTS_MESSAGE = "No results found"


# 简单模拟缓存
class SimpleCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


cache = SimpleCache()


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('query', nargs='+')
    parser.add_argument('--search_engine', default=None)
    parser.add_argument('--explain', action='store_true')
    parser.add_argument('-C', '--clear_cache', action='store_true')
    return parser


def _get_cache_key(args):
    return ' '.join(args['query'])


def _is_help_query(query):
    return 'howdoi' in query.lower()


def _get_help_instructions():
    return "Help: howdoi [query]"


def _parse_cmd(args, res):
    if 'error' in res:
        return {"error": res['error']}
    return {"answer": res.get('answer', 'No answer')}


def _get_from_cache(cache_key):
    return cache.get(cache_key)


def _get_answers(args):
    # 模拟搜索返回
    fake_answers = [
        f"Fake answer to '{' '.join(args['query'])}'",
        f"Another fake answer to '{' '.join(args['query'])}'",
    ]
    return {'answer': random.choice(fake_answers)}


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


# 你的测试用例
def howdoi(raw_query):
    if isinstance(raw_query, str):
        parser = get_parser()
        args = vars(parser.parse_args(raw_query.split(' ')))
    else:
        args = raw_query

    search_engine = args['search_engine'] or os.getenv('HOWDOI_SEARCH_ENGINE') or 'google'
    os.environ['HOWDOI_SEARCH_ENGINE'] = search_engine
    if search_engine not in SUPPORTED_SEARCH_ENGINES:
        supported_search_engines = ', '.join(SUPPORTED_SEARCH_ENGINES)
        message = f'Unsupported engine {search_engine}. The supported engines are: {supported_search_engines}'
        res = {'error': message}
        return _parse_cmd(args, res)

    args['query'] = ' '.join(args['query']).replace('?', '')
    cache_key = _get_cache_key(args)

    if _is_help_query(args['query']):
        return _get_help_instructions() + '\n'

    res = _get_from_cache(cache_key)

    if res:
        logging.info('Using cached response (add -C to clear the cache)')
        return _parse_cmd(args, res)

    logging.info('Fetching answers for query: %s', args["query"])

    try:
        res = _get_answers(args)
        if not res:
            message = NO_RESULTS_MESSAGE
            if not args['explain']:
                message = f'{message} (use --explain to learn why)'
            res = {'error': message}
        cache.set(cache_key, res)
    except (RequestsConnectionError, SSLError):
        res = {'error': f'Unable to reach {search_engine}. Do you need to use a proxy?\n'}
    except BlockError:
        BLOCKED_ENGINES.append(search_engine)
        next_engine = next((engine for engine in SUPPORTED_SEARCH_ENGINES if engine not in BLOCKED_ENGINES), None)
        if next_engine is None:
            res = {'error': 'Unable to get a response from any search engine\n'}
        else:
            args['search_engine'] = next_engine
            args['query'] = args['query'].split()
            logging.info('%sRetrying search with %s%s', GREEN, next_engine, END_FORMAT)
            return howdoi(args)
    return _parse_cmd(args, res)


def testcase_1():
    raw_query = "how to format date in bash"
    return howdoi(raw_query)


def testcase_2():
    raw_query = "python unittest"
    return howdoi(raw_query)


def testcase_3():
    raw_query = "parse html regex"
    return howdoi(raw_query)


def testcase_4():
    raw_query = "delete remote git branch"
    return howdoi(raw_query)


def testcase_5():
    raw_query = "make a log scale d3"
    return howdoi(raw_query)


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

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
