from dataclasses import dataclass
from server_profiles import build_server_config

_DEFAULT = build_server_config()


@dataclass(frozen=True)
class VarsayilanConfig:
    cpu_per_student: float = _DEFAULT.cpu_per_student
    ram_per_student: float = _DEFAULT.ram_per_student
    bandwidth_per_student: float = _DEFAULT.bandwidth_per_student
    max_cpu: float = _DEFAULT.max_cpu
    max_ram: float = _DEFAULT.max_ram
    max_bandwidth: float = _DEFAULT.max_bandwidth
    max_concurrent_students: int = _DEFAULT.max_concurrent_students
    random_seed: int = 42


@dataclass(frozen=True)
class PenaltyWeights:
    hard_conflict: float = 1_000_000.0
    capacity: float = 100_000.0
    consecutive_exam: float = 50.0
    load_variance: float = 5.0
    balance: float = 20.0
    department: float = 25.0
    crowded_large_exam: float = 10.0


VARSAYILAN_CONFIG = VarsayilanConfig()
PENALTY_WEIGHTS = PenaltyWeights()

