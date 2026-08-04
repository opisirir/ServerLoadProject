from dataclasses import dataclass


@dataclass(frozen=True)
class VarsayilanConfig:
    cpu_per_student: float = 0.02
    ram_per_student: float = 0.05
    bandwidth_per_student: float = 0.2
    max_cpu: float = 100.0
    max_ram: float = 256.0
    max_bandwidth: float = 1000.0
    max_concurrent_students: int = 5000
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

