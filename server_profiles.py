"""Supplier Moodle profiles; resource demand is a planning estimate, not telemetry."""
from dataclasses import asdict
import json
from pathlib import Path

from models import ServerConfig

SOURCE = "moodle_kullanım_2025-tech spect.docx - Google Dokümanlar.pdf"
DEFAULT_PROFILE = "moodle_3"
PROFILES = {
    "moodle_1": {
        "label": "Moodle 1 — 400–500 concurrent users",
        "concurrent_range": [400, 500], "active_users": "0–3000",
        "network_mbps": 100, "app_vcpu": 16, "app_ram_gb": 32,
        "nodes": [
            ["Proxy / SSL / Security", 4, 8, "50 GB"],
            ["App + MariaDB + Redis", 16, 32, "300 GB"],
        ],
    },
    "moodle_2": {
        "label": "Moodle 2 — 2000–2500 concurrent users",
        "concurrent_range": [2000, 2500], "active_users": "10000–30000",
        "network_mbps": 300, "app_vcpu": 16, "app_ram_gb": 32,
        "nodes": [
            ["App / Nginx / PHP-FPM", 16, 32, "1 TB+"],
            ["SQL / MariaDB or PostgreSQL", 16, 16, "100 GB"],
            ["Cache / Redis", 16, 8, "50 GB"],
        ],
    },
    "moodle_3": {
        "label": "Moodle 3 — 3000–6000 concurrent users",
        "concurrent_range": [3000, 6000], "active_users": "30000–50000+",
        "network_mbps": 1000, "local_network_mbps": 10000,
        "app_vcpu": 48, "app_ram_gb": 96,
        "nodes": [
            ["LB / Nginx proxy", 8, 16, "100 GB"],
            ["App01", 16, 32, "100 GB"], ["App02", 16, 32, "100 GB"],
            ["App03+ (baseline: one node)", 16, 32, "100 GB"],
            ["Storage / NFS or GlusterFS", 8, 16, "1024 GB+"],
            ["SQL proxy", 8, 16, "100 GB"],
            ["SQL1 / master", 16, 16, "100 GB"],
            ["SQL2+ / replica 1", 16, 16, "100 GB"],
            ["SQL2+ / replica 2 (repeated source row)", 16, 16, "100 GB"],
            ["Cache / Redis", 16, 8, "50 GB"],
        ],
    },
}

ASSUMPTION = (
    "Supplier concurrent-user ranges are not measured exam throughput. "
    "Default capacity uses the lower bound. CPU (vCPU), RAM (GB) and network "
    "(Mbps) estimates scale linearly to that bound; coefficients are not measured. "
    "CPU/RAM represent only the application tier, not pooled SQL/cache resources. "
    "Storage and database IOPS are documented but not modeled as constraints."
)


def build_server_config(profile_id=DEFAULT_PROFILE):
    p = PROFILES[profile_id]
    capacity = p["concurrent_range"][0]
    return ServerConfig(
        cpu_per_student=p["app_vcpu"] / capacity,
        ram_per_student=p["app_ram_gb"] / capacity,
        bandwidth_per_student=p["network_mbps"] / capacity,
        max_cpu=p["app_vcpu"], max_ram=p["app_ram_gb"],
        max_bandwidth=p["network_mbps"], max_concurrent_students=capacity,
    )


def save_server_profile(output, profile_id, config):
    Path(output).mkdir(parents=True, exist_ok=True)
    payload = {"profile_id": profile_id, "source": SOURCE,
               "infrastructure": PROFILES[profile_id], "assumptions": ASSUMPTION,
               "config": asdict(config)}
    (Path(output) / "server_profile.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
