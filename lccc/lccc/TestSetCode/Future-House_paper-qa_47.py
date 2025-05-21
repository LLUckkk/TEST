import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

from typing import List
from dataclasses import dataclass


@dataclass
class Context:
    score: float
    text: str
    doc: 'Document'


@dataclass
class Document:
    dockey: str
    other: dict


@dataclass
class Session:
    contexts: List[Context]
    cost: float


class EnvironmentState:
    RELEVANT_SCORE_CUTOFF = 0.5
    session: Session

    def __init__(self, contexts, cost):
        self.session = Session(contexts=contexts, cost=cost)


#############change###########
def get_relevant_contexts(self) -> list[Context]:
    return [
        c for c in self.session.contexts if c.score > self.RELEVANT_SCORE_CUTOFF
    ]


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
            print(f'Error in testcase: {e}')
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


def testcase_1():
    contexts_1 = [
        Context(score=0.6, text="Context 1", doc=Document(dockey="doc1", other={})),
        Context(score=0.4, text="Context 2", doc=Document(dockey="doc2", other={})),
        Context(score=0.7, text="Context 3", doc=Document(dockey="doc3", other={})),
    ]
    state_1 = EnvironmentState(contexts=contexts_1, cost=100.0)
    return get_relevant_contexts(state_1)


def testcase_2():
    contexts_2 = [
        Context(score=0.2, text="Context A", doc=Document(dockey="docA", other={})),
        Context(score=0.9, text="Context B", doc=Document(dockey="docB", other={})),
        Context(score=0.8, text="Context C", doc=Document(dockey="docC", other={})),
        Context(score=0.3, text="Context D", doc=Document(dockey="docD", other={})),
    ]
    state_2 = EnvironmentState(contexts=contexts_2, cost=200.0)
    return get_relevant_contexts(state_2)


def testcase_3():
    contexts_3 = [
        Context(score=0.5, text="Context X", doc=Document(dockey="docX", other={})),
        Context(score=0.6, text="Context Y", doc=Document(dockey="docY", other={})),
        Context(score=0.4, text="Context Z", doc=Document(dockey="docZ", other={})),
    ]
    state_3 = EnvironmentState(contexts=contexts_3, cost=150.0)
    return get_relevant_contexts(state_3)


def testcase_4():
    contexts_4 = [
        Context(score=0.1, text="Context M", doc=Document(dockey="docM", other={})),
        Context(score=0.9, text="Context N", doc=Document(dockey="docN", other={})),
    ]
    state_4 = EnvironmentState(contexts=contexts_4, cost=50.0)
    return get_relevant_contexts(state_4)


def testcase_5():
    contexts_5 = [
        Context(score=0.55, text="Context P", doc=Document(dockey="docP", other={})),
        Context(score=0.65, text="Context Q", doc=Document(dockey="docQ", other={})),
        Context(score=0.45, text="Context R", doc=Document(dockey="docR", other={})),
        Context(score=0.75, text="Context S", doc=Document(dockey="docS", other={})),
    ]
    state_5 = EnvironmentState(contexts=contexts_5, cost=300.0)
    return get_relevant_contexts(state_5)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def context_to_dict(c: Context):
        return {
            "score": c.score,
            "text": c.text,
            "doc": {
                "dockey": c.doc.dockey,
                "other": c.doc.other
            }
        }

    output = {}
    for k, v in test_results.items():
        if v["success"] and v["result"] is not None:
            output[k] = [context_to_dict(c) for c in v["result"]]
        else:
            output[k] = None

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
