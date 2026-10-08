"""Common-problem mathematical models, not reproductions of institution studies.

Equal-enrollment exams are interchangeable in this capacity-only problem. Integer
counts z[c,t] exactly replace the larger binary assignment matrix. Reconstruction
assigns every individual exam to one slot without splitting it.
"""
from time import perf_counter
import math
import numpy as np
from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model


def solve_mathematical(name, p, capacity, seed, seconds):
    started = perf_counter()
    lower = p.lower_bound()
    result = {"algorithm": name, "seed": seed, "metrics": None, "history": [],
              "evaluations": 0, "lower_bound": lower, "status": "no_solution",
              "solver_status": "BUILD_TIME_LIMIT", "history_kind": "incumbents" if name == "ilp" else "final_only"}
    def finish():
        result["runtime_seconds"] = perf_counter()-started
        return result
    if lower > capacity:
        result["solver_status"] = "INFEASIBLE_BY_LOWER_BOUND"
        return finish()
    weights, inverse, multiplicities = np.unique(p.counts, return_inverse=True, return_counts=True)
    groups, slots = len(weights), len(p.starts)
    is_cp = name == "ilp"
    engine = cp_model.CpModel() if is_cp else pywraplp.Solver.CreateSolver("CBC")
    if engine is None:
        result["solver_status"] = "SOLVER_UNAVAILABLE"
        return finish()
    z = []
    for g in range(groups):
        if perf_counter()-started >= seconds:
            return finish()
        bound = int(multiplicities[g])
        variables = [(engine.NewIntVar(0, bound, f"z{g}_{t}") if is_cp else engine.IntVar(0, bound, f"z{g}_{t}")) for t in range(slots)]
        engine.Add(sum(variables) == bound)
        z.append(variables)
    totals = []
    for t in range(slots):
        if perf_counter()-started >= seconds:
            return finish()
        load = engine.NewIntVar(0, capacity, f"L{t}") if is_cp else engine.NumVar(0, capacity, f"L{t}")
        engine.Add(load == sum(int(weights[g])*z[g][t] for g in range(groups)))
        totals.append(load)
    peak = engine.NewIntVar(lower, capacity, "P") if is_cp else engine.NumVar(lower, capacity, "P")
    for h in range(p.overlap.shape[1]):
        engine.Add(sum(totals[int(t)] for t in np.flatnonzero(p.overlap[:, h])) <= peak)
    if name == "goal":
        deviation = engine.NumVar(0, capacity-lower, "positive_deviation")
        engine.Add(peak == lower + deviation)
        engine.Minimize(deviation)
        result["goal_target"] = lower
    else:
        engine.Minimize(peak)
    remaining = seconds-(perf_counter()-started)
    result["build_seconds"] = perf_counter()-started
    if remaining <= 0:
        return finish()
    if is_cp:
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = remaining
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = seed
        class Incumbents(cp_model.CpSolverSolutionCallback):
            def on_solution_callback(self):
                realized_peak = int((np.array([self.Value(v) for v in totals], dtype=np.int64) @ p.overlap).max())
                if result["history"] and realized_peak >= result["history"][-1]["peak"]:
                    return
                result["history"].append({"evaluation": len(result["history"])+1,
                    "seconds": perf_counter()-started, "peak": realized_peak, "feasible": True})
        status = solver.Solve(engine, Incumbents())
        result["solver_status"] = solver.StatusName(status)
        result["lower_bound"] = max(lower, math.ceil(solver.BestObjectiveBound()-1e-6))
        feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        value = solver.Value
        optimal = status == cp_model.OPTIMAL
    else:
        engine.SetTimeLimit(max(1, int(remaining*1000)))
        engine.SetNumThreads(1)
        status = engine.Solve()
        result["solver_status"] = {0:"OPTIMAL",1:"FEASIBLE",2:"INFEASIBLE",3:"UNBOUNDED",4:"ABNORMAL",5:"MODEL_INVALID",6:"NOT_SOLVED"}.get(status,str(status))
        feasible = status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE)
        value = lambda v: v.solution_value()
        optimal = status == pywraplp.Solver.OPTIMAL
        bound = engine.Objective().BestBound()
        if math.isfinite(bound) and status in (0, 1, 6):
            result["lower_bound"] = max(lower, math.ceil(bound+(lower if name=="goal" else 0)-1e-6))
    if not feasible:
        return finish()
    assignment = np.empty(len(p.ids), dtype=int)
    for g in range(groups):
        indices = np.flatnonzero(inverse == g)
        destinations = [t for t in range(slots) for _ in range(int(round(value(z[g][t]))))]
        if len(destinations) != len(indices):
            raise RuntimeError("Integer reconstruction failed")
        assignment[indices] = destinations
    metrics = p.metrics(assignment, capacity)
    if not metrics["feasible"]:
        raise RuntimeError("Solver result failed independent capacity validation")
    if not is_cp:
        result["history"] = [{"evaluation": 1, "seconds": perf_counter()-started, "peak": metrics["peak"], "feasible": True}]
    result.update(metrics=metrics, assignment=assignment.tolist(), status="feasible", optimal=optimal,
                  evaluations=len(result["history"]))
    return finish()
