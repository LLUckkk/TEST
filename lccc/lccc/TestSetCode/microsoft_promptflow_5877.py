import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

PromptTemplate = str


# 补充 Jinja 渲染函数（简化版本，实际中你可能用 jinja2）
def render_jinja_template(template_str, **kwargs):
    """简单模拟 Jinja2 模板渲染"""
    from jinja2 import Template
    if isinstance(template_str, str):
        template = Template(template_str)
    elif hasattr(template_str, 'template'):  # 如果是 PromptTemplate 对象
        template = Template(template_str.template)
    else:
        raise ValueError("Unsupported prompt type")
    return template.render(**kwargs)


def to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("1", "true", "yes", "on")
    return bool(val)


class DummyClient:
    """模拟的 client 对象，生成固定内容"""
    def __init__(self):
        self.completions = self

    def create(self, **kwargs):
        # 构造模拟 response
        class Choice:
            def __init__(self, text):
                self.text = text

        class Response:
            def __init__(self, text):
                self.choices = [Choice(text)]

        prompt = kwargs.get("prompt", "")
        return Response(f"Echo: {prompt[:min(100, len(prompt))]}")  # 模拟返回前100字符

class Dummy:
    def __init__(self):
        self._client = DummyClient()


#############change###########
def completion(
        self,
        prompt: PromptTemplate,
        deployment_name: str,
        suffix: str = None,
        max_tokens: int = 16,
        temperature: float = 1.0,
        top_p: float = 1.0,
        n: int = 1,
        stream: bool = False,
        logprobs: int = None,
        echo: bool = False,
        stop: list = None,
        presence_penalty: float = None,
        frequency_penalty: float = None,
        best_of: int = 1,
        logit_bias: dict = {},
        user: str = "",
        **kwargs,
):
    prompt = render_jinja_template(prompt, trim_blocks=True, keep_trailing_newline=True, **kwargs)
    echo = to_bool(echo)
    stream = to_bool(stream)
    params = {}
    if presence_penalty is not None:
        params["presence_penalty"] = presence_penalty
    if frequency_penalty is not None:
        params["frequency_penalty"] = frequency_penalty

    response = self._client.completions.create(
        prompt=prompt,
        model=deployment_name,
        suffix=suffix if suffix else None,
        max_tokens=int(max_tokens) if max_tokens is not None else None,
        temperature=float(temperature),
        top_p=float(top_p),
        n=int(n),
        stream=stream,
        logprobs=int(logprobs) if logprobs else None,
        echo=echo,
        stop=stop if stop else None,
        best_of=int(best_of),
        logit_bias=logit_bias if logit_bias else {},
        user=user,
        extra_headers={"ms-azure-ai-promptflow-called-from": "aoai-tool"},
        **params
    )

    if stream:
        def generator():
            for chunk in response:
                if chunk.choices:
                    yield chunk.choices[0].text if hasattr(chunk.choices[0], 'text') and \
                                                   chunk.choices[0].text is not None else ""

        return generator()
    else:
        return response.choices[0].text


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


def testcase_1():
    self = Dummy()
    return completion(self, "What is the capital of France?", "text-davinci-003")


def testcase_2():
    self = Dummy()
    return completion(self, "Translate the following English text to French: 'Hello, how are you?'", "text-davinci-003")


def testcase_3():
    self = Dummy()
    return completion(self, "Write a short story about a dragon and a knight.", "text-davinci-003")


def testcase_4():
    self = Dummy()
    return completion(self, "Summarize the following article: 'The quick brown fox jumps over the lazy dog.'", "text-davinci-003")


def testcase_5():
    self = Dummy()
    return completion(self, "Generate a list of 10 creative business ideas.", "text-davinci-003")


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
