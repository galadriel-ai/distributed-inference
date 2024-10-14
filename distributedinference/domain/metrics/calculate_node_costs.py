from typing import Dict
from typing import List

from distributedinference.domain.node.entities import NodeBenchmark

PRICES = {
    # Consumer
    "NVIDIA GeForce RTX 4090": 0.4,
    "NVIDIA GeForce RTX 4080": 0.3,
    "NVIDIA GeForce RTX 4070 Ti SUPER": 0.4,
    "NVIDIA GeForce RTX 3080 Ti": 0.25,
    "NVIDIA GeForce RTX 3070": 0.1,
    "NVIDIA GeForce GTX 1050 Ti": 0.1,
    # Enterprise
    "NVIDIA H100 PCIe": 1.6,
    "NVIDIA H100 80GB HBM3": 1.6,
    "NVIDIA RTX A4000": 0.2,
    "NVIDIA A10G": 0.1,
}

FUZZY_PRICES = {
    # Consumer
    "4090": 0.4,
    "4080": 0.2,
    "4070": 0.2,
    "4060": 0.2,
    "3090": 0.3,
    "3080": 0.17,
    "3070": 0.15,
    "3060": 0.1,
    # Enterprise
    "H200": 2.0,
    "H100": 1.6,
    "A100": 1.1,
    "RTX6000 Ada": 0.8,
    "A6000": 0.4,
    "RTX5000 Ada": 0.35,
    "V100": 0.29,
    "A40": 0.39,
    "L40": 1.00,
    "A5000": 0.3,
    "L4": 0.43,
    "RTX8000": 0.62,
    "RTX4000 Ada": 0.38,
    "A4500": 0.25,
    "A4000": 0.2,
    "P100": 0.1,
}


def execute(nodes: List[NodeBenchmark]) -> Dict:
    result = {}
    for node in nodes:
        if node.model_name in result:
            result[node.model_name] = result[node.model_name] + _get_gpu_price(
                node.gpu_model
            )
        else:
            result[node.model_name] = _get_gpu_price(node.gpu_model)
    return result


def _get_gpu_price(gpu_model: str) -> float:
    if gpu_model in PRICES:
        return PRICES[gpu_model]

    for gpu, price in FUZZY_PRICES.items():
        if gpu in gpu_model:
            return price
    return 0.0
