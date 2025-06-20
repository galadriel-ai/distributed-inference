from uuid import UUID

from pytest import approx

from distributedinference.domain.metrics import calculate_node_costs
from distributedinference.domain.node.entities import NodeBenchmark

NODE_ID = UUID("93a38d42-e947-46e5-8bc9-f79724fe59c1")


def test_empty():
    result = calculate_node_costs.execute([])
    assert result == {}


def test_one_node():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
            )
        ]
    )
    assert result == {"model1": 0.4}


def test_one_node_two_gpus():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
                gpu_count=2,
            )
        ]
    )
    assert result == {"model1": 0.8}


def test_two_node():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
            ),
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
            ),
        ]
    )
    assert result == {"model1": 0.8}


def test_two_node_with_3_gpus():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
                gpu_count=2,
            ),
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
                gpu_count=1,
            ),
        ]
    )
    assert result == {"model1": approx(1.2)}


def test_two_node_different_gpus():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
            ),
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4080",
            ),
        ]
    )
    assert result == {"model1": 0.7}


def test_two_node_different_multiple_gpus():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
                gpu_count=2,
            ),
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4080",
                gpu_count=1,
            ),
        ]
    )
    assert result == {"model1": approx(1.1)}


def test_two_node_different_models():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
            ),
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model2",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
            ),
        ]
    )
    assert result == {"model1": 0.4, "model2": 0.4}


def test_two_node_different_models_multiple_gpus():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
                gpu_count=2,
            ),
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model2",
                benchmark_tokens_per_second=100,
                gpu_model="NVIDIA GeForce RTX 4090",
                gpu_count=1,
            ),
        ]
    )
    assert result == {"model1": 0.8, "model2": 0.4}


def test_one_node_not_exact_match():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="Some 4090 GPU",
            )
        ]
    )
    assert result == {"model1": 0.4}


def test_one_node_not_exact_match_multiple_gpus():
    result = calculate_node_costs.execute(
        [
            NodeBenchmark(
                node_id=NODE_ID,
                model_name="model1",
                benchmark_tokens_per_second=100,
                gpu_model="Some 4090 GPU",
                gpu_count=3,
            )
        ]
    )
    assert result == {"model1": approx(1.2)}
