import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pyparsing
import typing
from some_module import EditablePartial, ConverterState, railroad


#############change###########
def _to_diagram_element(
    element: pyparsing.ParserElement,
    parent: typing.Optional[EditablePartial],
    lookup: ConverterState = None,
    vertical: int = None,
    index: int = 0,
    name_hint: str = None,
    show_results_names: bool = False,
    show_groups: bool = False,
) -> typing.Optional[EditablePartial]:
    
    exprs = element.recurse()
    name = name_hint or element.customName or element.__class__.__name__

    el_id = id(element)

    element_results_name = element.resultsName

    if not element.customName:
        if isinstance(
            element,
            (
                pyparsing.Located,
            ),
        ):
            if exprs:
                if not exprs[0].customName:
                    propagated_name = name
                else:
                    propagated_name = None

                return _to_diagram_element(
                    element.expr,
                    parent=parent,
                    lookup=lookup,
                    vertical=vertical,
                    index=index,
                    name_hint=propagated_name,
                    show_results_names=show_results_names,
                    show_groups=show_groups,
                )

    if _worth_extracting(element):
        if el_id in lookup:
            looked_up = lookup[el_id]
            looked_up.mark_for_extraction(el_id, lookup, name=name_hint)
            ret = EditablePartial.from_call(railroad.NonTerminal, text=looked_up.name)
            return ret

        elif el_id in lookup.diagrams:
            ret = EditablePartial.from_call(
                railroad.NonTerminal, text=lookup.diagrams[el_id].kwargs["name"]
            )
            return ret

    if isinstance(element, pyparsing.And):
        if not exprs:
            return None
        if len(set((e.name, e.resultsName) for e in exprs)) == 1:
            ret = EditablePartial.from_call(
                railroad.OneOrMore, item="", repeat=str(len(exprs))
            )
        elif _should_vertical(vertical, exprs):
            ret = EditablePartial.from_call(railroad.Stack, items=[])
        else:
            ret = EditablePartial.from_call(railroad.Sequence, items=[])
    elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
        if not exprs:
            return None
        if _should_vertical(vertical, exprs):
            ret = EditablePartial.from_call(railroad.Choice, 0, items=[])
        else:
            ret = EditablePartial.from_call(railroad.HorizontalChoice, items=[])
    elif isinstance(element, pyparsing.Each):
        if not exprs:
            return None
        ret = EditablePartial.from_call(EachItem, items=[])
    elif isinstance(element, pyparsing.NotAny):
        ret = EditablePartial.from_call(AnnotatedItem, label="NOT", item="")
    elif isinstance(element, pyparsing.FollowedBy):
        ret = EditablePartial.from_call(AnnotatedItem, label="LOOKAHEAD", item="")
    elif isinstance(element, pyparsing.PrecededBy):
        ret = EditablePartial.from_call(AnnotatedItem, label="LOOKBEHIND", item="")
    elif isinstance(element, pyparsing.Group):
        if show_groups:
            ret = EditablePartial.from_call(AnnotatedItem, label="", item="")
        else:
            ret = EditablePartial.from_call(railroad.Group, label="", item="")
    elif isinstance(element, pyparsing.TokenConverter):
        ret = EditablePartial.from_call(
            AnnotatedItem, label=type(element).__name__.lower(), item=""
        )
    elif isinstance(element, pyparsing.Opt):
        ret = EditablePartial.from_call(railroad.Optional, item="")
    elif isinstance(element, pyparsing.OneOrMore):
        ret = EditablePartial.from_call(railroad.OneOrMore, item="")
    elif isinstance(element, pyparsing.ZeroOrMore):
        ret = EditablePartial.from_call(railroad.ZeroOrMore, item="")
    elif isinstance(element, pyparsing.Group):
        ret = EditablePartial.from_call(
            railroad.Group, item=None, label=element_results_name
        )
    elif isinstance(element, pyparsing.Empty) and not element.customName:
        ret = None
    elif len(exprs) > 1:
        ret = EditablePartial.from_call(railroad.Sequence, items=[])
    elif len(exprs) > 0 and not element_results_name:
        ret = EditablePartial.from_call(railroad.Group, item="", label=name)
    else:
        terminal = EditablePartial.from_call(railroad.Terminal, element.defaultName)
        ret = terminal

    if ret is None:
        return

    lookup[el_id] = ElementState(
        element=element,
        converted=ret,
        parent=parent,
        parent_index=index,
        number=lookup.generate_index(),
    )
    if element.customName:
        lookup[el_id].mark_for_extraction(el_id, lookup, element.customName)

    i = 0
    for expr in exprs:
        if "items" in ret.kwargs:
            ret.kwargs["items"].insert(i, None)

        item = _to_diagram_element(
            expr,
            parent=ret,
            lookup=lookup,
            vertical=vertical,
            index=i,
            show_results_names=show_results_names,
            show_groups=show_groups,
        )

        if item is not None:
            if "item" in ret.kwargs:
                ret.kwargs["item"] = item
            elif "items" in ret.kwargs:
                ret.kwargs["items"][i] = item
                i += 1
        elif "items" in ret.kwargs:
            del ret.kwargs["items"][i]

    if ret and (
        ("items" in ret.kwargs and len(ret.kwargs["items"]) == 0)
        or ("item" in ret.kwargs and ret.kwargs["item"] is None)
    ):
        ret = EditablePartial.from_call(railroad.Terminal, name)

    if el_id in lookup:
        lookup[el_id].complete = True

    if el_id in lookup and lookup[el_id].extract and lookup[el_id].complete:
        lookup.extract_into_diagram(el_id)
        if ret is not None:
            ret = EditablePartial.from_call(
                railroad.NonTerminal, text=lookup.diagrams[el_id].kwargs["name"]
            )

    return ret
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
    element = pyparsing.Word(pyparsing.alphas)
    parent = None
    lookup = ConverterState()
    vertical = 3
    index = 0
    name_hint = "word"
    show_results_names = False
    show_groups = False
    
    return _to_diagram_element(element, parent, lookup, vertical, index, name_hint, show_results_names, show_groups, )

# 定义测试用例2
def testcase_2():
    element = pyparsing.And([pyparsing.Word(pyparsing.nums), pyparsing.Word(pyparsing.alphas)])
    parent = EditablePartial.from_call(railroad.Sequence, items=[])
    lookup = ConverterState()
    vertical = 5
    index = 1
    name_hint = None
    show_results_names = True
    show_groups = True
    
    return _to_diagram_element(element, parent, lookup, vertical, index, name_hint, show_results_names, show_groups, )

# 定义测试用例3
def testcase_3():
    element = pyparsing.Or([pyparsing.Word(pyparsing.nums), pyparsing.Word(pyparsing.alphas)])
    parent = EditablePartial.from_call(railroad.Choice, 0, items=[])
    lookup = ConverterState()
    vertical = False
    index = 2
    name_hint = "choice"
    show_results_names = False
    show_groups = True
    
    return _to_diagram_element(element, parent, lookup, vertical, index, name_hint, show_results_names, show_groups, )

# 定义测试用例4
def testcase_4():
    element = pyparsing.Group(pyparsing.Word(pyparsing.alphas))
    parent = EditablePartial.from_call(railroad.Group, item=None, label="group")
    lookup = ConverterState()
    vertical = True
    index = 3
    name_hint = "group"
    show_results_names = True
    show_groups = False
    
    return _to_diagram_element(element, parent, lookup, vertical, index, name_hint, show_results_names, show_groups, )

# 定义测试用例5
def testcase_5():
    element = pyparsing.Optional(pyparsing.Word(pyparsing.alphas))
    parent = EditablePartial.from_call(railroad.Optional, item="")
    lookup = ConverterState()
    vertical = 2
    index = 4
    name_hint = "optional"
    show_results_names = False
    show_groups = True
    
    return _to_diagram_element(element, parent, lookup, vertical, index, name_hint, show_results_names, show_groups, )

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
   