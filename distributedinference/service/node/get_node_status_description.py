from distributedinference.domain.node.entities import NodeStatus


def execute(status: NodeStatus) -> str:
    description = "Unknown"
    match status:
        case NodeStatus.RUNNING:
            description = "Running"
        case NodeStatus.RUNNING_BENCHMARKING:
            description = "Running - verifying performance"
        case NodeStatus.RUNNING_DEGRADED:
            description = "Running - performance degraded"
        case NodeStatus.RUNNING_DISABLED:
            description = "Running"
        case NodeStatus.STOPPED:
            description = "Stopped"
        case NodeStatus.STOPPED_BENCHMARK_FAILED:
            description = "Stopped"
        case NodeStatus.STOPPED_DEGRADED:
            description = "Stopped"
        case NodeStatus.STOPPED_DISABLED:
            description = "Stopped"
    return description
