from distributedinference.domain.node import is_node_performant

MODEL_8B = "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8"
MODEL_70B = "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16"


def test_0_0():
    assert not is_node_performant.execute(0, 0, 1, MODEL_8B)


def test_1_0():
    assert not is_node_performant.execute(1, 0, 1, MODEL_8B)


def test_0_1():
    assert not is_node_performant.execute(0, 1, 1, MODEL_8B)


def test_small_prompts():
    assert is_node_performant.execute(2, 1, 1, MODEL_8B)
    assert is_node_performant.execute(2, 1, 100, MODEL_8B)

    # ttft=2 is too long for short prompts
    assert not is_node_performant.execute(3, 1, 1, MODEL_8B)
    assert not is_node_performant.execute(3, 1, 100, MODEL_8B)


def test_8k_prompt():
    # ttft=7 is good for 8k context
    assert is_node_performant.execute(7, 1, 8000, MODEL_8B)
    # ttft=8 is NOT good for 8k context
    assert not is_node_performant.execute(8, 1, 8000, MODEL_8B)


def test_70b_model():
    assert is_node_performant.execute(8, 1, 8000, MODEL_70B)
