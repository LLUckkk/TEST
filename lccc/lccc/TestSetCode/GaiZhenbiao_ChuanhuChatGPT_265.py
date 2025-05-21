import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import enum


class ModelType(enum.Enum):
    OpenAIVision = 1
    OpenAI = 2
    OpenAIInstruct = 3
    ChatGLM = 4
    Groq = 5
    LLaMA = 6
    XMChat = 7
    StableLM = 8
    MOSS = 9
    YuanAI = 10
    Minimax = 11
    ChuanhuAgent = 12
    GooglePaLM = 13
    GoogleGemini = 14
    LangchainChat = 15
    Midjourney = 16
    Spark = 17
    Claude = 18
    Qwen = 19
    ERNIE = 20
    DALLE3 = 21
    Ollama = 22
    GoogleGemma = 23
    Unknown = 24


MODEL_METADATA = {
    "GPT-3": {"model_type": "OpenAI", "multimodal": False},
    "ChatGLM-6B": {"model_type": "ChatGLM", "multimodal": False},
    "Claude-v1": {"model_type": "Claude", "multimodal": False},
    "StableLM-alpha": {"model_type": "StableLM", "multimodal": False},
    "Midjourney-v4": {"model_type": "Midjourney", "multimodal": True},
}


#############change###########
def get_type(cls, model_name: str):
    model_type = MODEL_METADATA[model_name]["model_type"]
    if model_type is not None:
        for member in cls:
            if member.name == model_type:
                return member

    model_type = None
    model_name_lower = model_name.lower()
    if "gpt" in model_name_lower:
        try:
            assert MODEL_METADATA[model_name]["multimodal"] == True
            model_type = ModelType.OpenAIVision
        except:
            if "instruct" in model_name_lower:
                model_type = ModelType.OpenAIInstruct
            elif "vision" in model_name_lower:
                model_type = ModelType.OpenAIVision
            else:
                model_type = ModelType.OpenAI
    elif "chatglm" in model_name_lower:
        model_type = ModelType.ChatGLM
    elif "groq" in model_name_lower:
        model_type = ModelType.Groq
    elif "ollama" in model_name_lower:
        model_type = ModelType.Ollama
    elif "llama" in model_name_lower or "alpaca" in model_name_lower:
        model_type = ModelType.LLaMA
    elif "xmchat" in model_name_lower:
        model_type = ModelType.XMChat
    elif "stablelm" in model_name_lower:
        model_type = ModelType.StableLM
    elif "moss" in model_name_lower:
        model_type = ModelType.MOSS
    elif "yuanai" in model_name_lower:
        model_type = ModelType.YuanAI
    elif "minimax" in model_name_lower:
        model_type = ModelType.Minimax
    elif "川虎助理" in model_name_lower:
        model_type = ModelType.ChuanhuAgent
    elif "palm" in model_name_lower:
        model_type = ModelType.GooglePaLM
    elif "gemini" in model_name_lower:
        model_type = ModelType.GoogleGemini
    elif "midjourney" in model_name_lower:
        model_type = ModelType.Midjourney
    elif "azure" in model_name_lower or "api" in model_name_lower:
        model_type = ModelType.LangchainChat
    elif "讯飞星火" in model_name_lower:
        model_type = ModelType.Spark
    elif "claude" in model_name_lower:
        model_type = ModelType.Claude
    elif "qwen" in model_name_lower:
        model_type = ModelType.Qwen
    elif "ernie" in model_name_lower:
        model_type = ModelType.ERNIE
    elif "dall" in model_name_lower:
        model_type = ModelType.DALLE3
    elif "gemma" in model_name_lower:
        model_type = ModelType.GoogleGemma
    else:
        model_type = ModelType.LLaMA
    return model_type


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
    cls = ModelType
    model_name = "GPT-3"

    return get_type(cls, model_name)


# 定义测试用例2
def testcase_2():
    cls = ModelType
    model_name = "ChatGLM-6B"

    return get_type(cls, model_name)


# 定义测试用例3
def testcase_3():
    cls = ModelType
    model_name = "Claude-v1"

    return get_type(cls, model_name)


# 定义测试用例4
def testcase_4():
    cls = ModelType
    model_name = "StableLM-alpha"

    return get_type(cls, model_name)


# 定义测试用例5
def testcase_5():
    cls = ModelType
    model_name = "Midjourney-v4"

    return get_type(cls, model_name)


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

    def json_serialize(obj):
        if isinstance(obj, enum.Enum):
            return {
                "Type": obj.name,
                "Value": obj.value
            }
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    print(json.dumps(output, indent=2, default=json_serialize))


if __name__ == '__main__':
    main()
