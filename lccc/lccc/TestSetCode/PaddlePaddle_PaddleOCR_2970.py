import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import os
import paddle
import pickle


#############change###########
def load_model(config, model, optimizer=None, model_type="det"):
    
    logger = get_logger()
    global_config = config["Global"]
    checkpoints = global_config.get("checkpoints")
    pretrained_model = global_config.get("pretrained_model")
    best_model_dict = {}
    is_float16 = False
    is_nlp_model = model_type == "kie" and config["Architecture"]["algorithm"] not in [
        "SDMGR"
    ]

    if is_nlp_model is True:
        if config["Architecture"]["algorithm"] in ["Distillation"]:
            return best_model_dict
        checkpoints = config["Architecture"]["Backbone"]["checkpoints"]
        if checkpoints:
            if os.path.exists(os.path.join(checkpoints, "metric.states")):
                with open(os.path.join(checkpoints, "metric.states"), "rb") as f:
                    states_dict = pickle.load(f, encoding="latin1")
                best_model_dict = states_dict.get("best_model_dict", {})
                if "epoch" in states_dict:
                    best_model_dict["start_epoch"] = states_dict["epoch"] + 1
            logger.info("resume from {}".format(checkpoints))

            if optimizer is not None:
                if checkpoints[-1] in ["/", "\\"]:
                    checkpoints = checkpoints[:-1]
                if os.path.exists(checkpoints + ".pdopt"):
                    optim_dict = paddle.load(checkpoints + ".pdopt")
                    optimizer.set_state_dict(optim_dict)
                else:
                    logger.warning(
                        "{}.pdopt is not exists, params of optimizer is not loaded".format(
                            checkpoints
                        )
                    )

        return best_model_dict

    if checkpoints:
        if checkpoints.endswith(".pdparams"):
            checkpoints = checkpoints.replace(".pdparams", "")
        assert os.path.exists(
            checkpoints + ".pdparams"
        ), "The {}.pdparams does not exists!".format(checkpoints)

        params = paddle.load(checkpoints + ".pdparams")
        state_dict = model.state_dict()
        new_state_dict = {}
        for key, value in state_dict.items():
            if key not in params:
                logger.warning(
                    "{} not in loaded params {} !".format(key, params.keys())
                )
                continue
            pre_value = params[key]
            if pre_value.dtype == paddle.float16:
                is_float16 = True
            if pre_value.dtype != value.dtype:
                pre_value = pre_value.astype(value.dtype)
            if list(value.shape) == list(pre_value.shape):
                new_state_dict[key] = pre_value
            else:
                logger.warning(
                    "The shape of model params {} {} not matched with loaded params shape {} !".format(
                        key, value.shape, pre_value.shape
                    )
                )
        model.set_state_dict(new_state_dict)
        if is_float16:
            logger.info(
                "The parameter type is float16, which is converted to float32 when loading"
            )
        if optimizer is not None:
            if os.path.exists(checkpoints + ".pdopt"):
                optim_dict = paddle.load(checkpoints + ".pdopt")
                optimizer.set_state_dict(optim_dict)
            else:
                logger.warning(
                    "{}.pdopt is not exists, params of optimizer is not loaded".format(
                        checkpoints
                    )
                )

        if os.path.exists(checkpoints + ".states"):
            with open(checkpoints + ".states", "rb") as f:
                states_dict = pickle.load(f, encoding="latin1")
            best_model_dict = states_dict.get("best_model_dict", {})
            best_model_dict["acc"] = 0.0
            if "epoch" in states_dict:
                best_model_dict["start_epoch"] = states_dict["epoch"] + 1
        logger.info("resume from {}".format(checkpoints))
    elif pretrained_model:
        is_float16 = load_pretrained_params(model, pretrained_model)
    else:
        logger.info("train from scratch")
    best_model_dict["is_float16"] = is_float16
    return best_model_dict
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
    config = {
        "Global": {
            "checkpoints": "path/to/checkpoint",
            "pretrained_model": None
        },
        "Architecture": {
            "algorithm": "Det",
            "model_type": "det"
        }
    }
    model = paddle.nn.Layer()
    optimizer = paddle.optimizer.Adam(parameters=model.parameters())
    model_type = "det"
    
    return load_model(config, model, optimizer, model_type)

# 定义测试用例2
def testcase_2():
    config = {
        "Global": {
            "checkpoints": "path/to/checkpoint",
            "pretrained_model": "path/to/pretrained/model"
        },
        "Architecture": {
            "algorithm": "Rec",
            "model_type": "rec"
        }
    }
    model = paddle.nn.Layer()
    optimizer = paddle.optimizer.Adam(parameters=model.parameters())
    model_type = "rec"
    
    return load_model(config, model, optimizer, model_type)

# 定义测试用例3
def testcase_3():
    config = {
        "Global": {
            "checkpoints": None,
            "pretrained_model": "path/to/pretrained/model"
        },
        "Architecture": {
            "algorithm": "SR",
            "model_type": "sr"
        }
    }
    model = paddle.nn.Layer()
    optimizer = paddle.optimizer.Adam(parameters=model.parameters())
    model_type = "sr"
    
    return load_model(config, model, optimizer, model_type)

# 定义测试用例4
def testcase_4():
    config = {
        "Global": {
            "checkpoints": "path/to/checkpoint",
            "pretrained_model": None
        },
        "Architecture": {
            "algorithm": "KIE",
            "model_type": "kie"
        }
    }
    model = paddle.nn.Layer()
    optimizer = paddle.optimizer.Adam(parameters=model.parameters())
    model_type = "kie"
    
    return load_model(config, model, optimizer, model_type)

# 定义测试用例5
def testcase_5():
    config = {
        "Global": {
            "checkpoints": None,
            "pretrained_model": None
        },
        "Architecture": {
            "algorithm": "Distillation",
            "model_type": "dist"
        }
    }
    model = paddle.nn.Layer()
    optimizer = paddle.optimizer.Adam(parameters=model.parameters())
    model_type = "dist"
    
    return load_model(config, model, optimizer, model_type)

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
   