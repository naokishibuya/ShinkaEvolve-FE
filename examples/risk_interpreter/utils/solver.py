"""
Discrete optimizer using OR-Tools CP-SAT solver.
Respects objective weights from interpret_context().
"""

from ortools.sat.python import cp_model
from typing import Dict


def solve_optimization(problem: Dict) -> Dict:
    """
    Solve discrete optimization using OR-Tools CP-SAT.

    Properly uses objective weights (risk_weight, cost_weight) to
    find optimal instrument allocation within constraints.

    Args:
        problem: Dictionary with:
            - variables: dict of decision variables
            - objective: dict with risk_weight and cost_weight
            - constraints: list of constraint dicts
            - portfolio_value: float

    Returns:
        Dictionary with:
            - selected_instruments: dict mapping instrument to quantity
            - total_cost: float
            - protection_level: float (max protection from selected instruments)
            - feasible: bool
            - solver_status: str
            - infeasibility_reason: str (if infeasible)
            - diagnostics: list of diagnostic messages
    """

    variables = problem['variables']
    objective_weights = problem['objective']
    constraints = problem['constraints']
    portfolio_value = problem['portfolio_value']

    # Extract objective weights
    risk_weight = objective_weights.get('risk_weight', 0.5)
    cost_weight = objective_weights.get('cost_weight', 0.5)

    # Extract constraints
    cost_limit = None
    min_protection = None

    for constraint in constraints:
        if constraint['type'] == 'cost_limit':
            cost_limit = constraint['value']
        elif constraint['type'] == 'min_protection':
            min_protection = constraint['value']

    # Create CP-SAT model
    model = cp_model.CpModel()

    # Decision variables: how many units of each instrument
    instrument_vars = {}
    for name, var_info in variables.items():
        instrument_vars[name] = model.NewIntVar(
            var_info['min'],
            var_info['max'],
            name
        )

    # Constraint 1: Total cost must not exceed limit
    if cost_limit is not None:
        # Scale costs to integers (OR-Tools requires integer arithmetic)
        scaled_costs = []
        for name, var_info in variables.items():
            # Scale by 1000 to preserve precision
            cost_scaled = int(var_info['cost_per_unit'] * 1000)
            scaled_costs.append(instrument_vars[name] * cost_scaled)

        cost_limit_scaled = int(cost_limit * 1000)
        model.Add(sum(scaled_costs) <= cost_limit_scaled)

    # Constraint 2: At least one instrument with sufficient protection must be selected
    # Protection is the MAX protection of any selected instrument
    if min_protection is not None:
        # Find all instruments that meet the protection requirement
        qualifying_instruments = []
        for name, var_info in variables.items():
            if var_info['protection_per_unit'] >= min_protection:
                qualifying_instruments.append(instrument_vars[name])

        if qualifying_instruments:
            # At least one qualifying instrument must have quantity >= 1
            model.Add(sum(qualifying_instruments) >= 1)
        else:
            # No instruments meet the requirement - model is infeasible
            # Add an impossible constraint to make solver return INFEASIBLE
            model.Add(sum(instrument_vars.values()) >= 999999)

    # Objective: Maximize weighted score
    # score = (protection * risk_weight) - (cost * cost_weight)
    objective_terms = []
    for name, var_info in variables.items():
        protection_per_unit = var_info['protection_per_unit']
        cost_per_unit = var_info['cost_per_unit']

        # Scale everything by 10000 to preserve precision
        # Protection term (positive contribution)
        protection_scaled = int(protection_per_unit * risk_weight * 10000)

        # Cost term (negative contribution), normalized by portfolio value
        cost_scaled = int((cost_per_unit / portfolio_value) * cost_weight * 10000)

        # Combined score per unit
        score_per_unit = protection_scaled - cost_scaled

        objective_terms.append(instrument_vars[name] * score_per_unit)

    # Maximize total score
    model.Maximize(sum(objective_terms))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.log_search_progress = False
    status = solver.Solve(model)

    # Build diagnostics
    diagnostics = []
    diagnostics.append(f"Solver status: {_status_name(status)}")
    diagnostics.append(f"Objective weights: risk={risk_weight:.2f}, cost={cost_weight:.2f}")

    # Extract solution
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected = {}
        total_cost = 0.0
        max_protection = 0.0
        total_units = 0

        for name, var in instrument_vars.items():
            quantity = solver.Value(var)
            if quantity > 0:
                selected[name] = int(quantity)
                total_cost += quantity * variables[name]['cost_per_unit']
                max_protection = max(max_protection, variables[name]['protection_per_unit'])
                total_units += quantity

        # Check constraints
        cost_ok = (cost_limit is None) or (total_cost <= cost_limit)
        protection_ok = (min_protection is None) or (max_protection >= min_protection)

        # Add constraint diagnostics
        if cost_limit is not None:
            cost_status = "[PASS]" if cost_ok else "[FAIL]"
            cost_pct = (total_cost / cost_limit * 100) if cost_limit > 0 else 0
            diagnostics.append(
                f"{cost_status} Cost constraint: {total_cost:.2f} / {cost_limit:.2f} ({cost_pct:.1f}%)"
            )

        if min_protection is not None:
            prot_status = "[PASS]" if protection_ok else "[FAIL]"
            prot_pct = (max_protection / min_protection * 100) if min_protection > 0 else 0
            diagnostics.append(
                f"{prot_status} Protection constraint: {max_protection:.3f} / {min_protection:.3f} "
                f"(got {prot_pct:.1f}% of required)"
            )

        # Add selection details
        diagnostics.append(f"Selected {len(selected)} instrument types, {total_units} total units")
        for name, units in sorted(selected.items(), key=lambda x: x[1], reverse=True):
            var_info = variables[name]
            cost = units * var_info['cost_per_unit']
            protection = var_info['protection_per_unit']
            diagnostics.append(f"  - {name}: {units} units (cost: {cost:.2f}, protection: {protection:.3f})")

        return {
            'selected_instruments': selected,
            'total_cost': float(total_cost),
            'protection_level': float(max_protection),
            'feasible': True,
            'total_units': int(total_units),
            'solver_status': 'optimal' if status == cp_model.OPTIMAL else 'feasible',
            'infeasibility_reason': None,
            'diagnostics': diagnostics
        }

    else:
        # No feasible solution found
        diagnostics.append("No feasible solution found")

        if cost_limit is not None:
            diagnostics.append(f"Cost limit: {cost_limit:.2f}")

        if min_protection is not None:
            diagnostics.append(f"Required protection: {min_protection:.3f}")
            # Check which instruments could meet this requirement
            qualifying_instruments = [
                name for name, info in variables.items()
                if info['protection_per_unit'] >= min_protection
            ]
            if qualifying_instruments:
                diagnostics.append(f"Instruments with sufficient protection: {', '.join(qualifying_instruments)}")
                # Check if we can afford any of them
                for name in qualifying_instruments:
                    min_cost = variables[name]['cost_per_unit']
                    if cost_limit and min_cost > cost_limit:
                        diagnostics.append(
                            f"  - {name}: min cost {min_cost:.2f} > budget {cost_limit:.2f} [TOO EXPENSIVE]"
                        )
                    else:
                        diagnostics.append(f"  - {name}: min cost {min_cost:.2f}")
            else:
                max_available_protection = max(
                    info['protection_per_unit'] for info in variables.values()
                )
                diagnostics.append(
                    f"No instruments provide required protection {min_protection:.3f}. "
                    f"Max available: {max_available_protection:.3f}"
                )

        infeasibility_reason = "\n".join(diagnostics)

        return {
            'selected_instruments': {},
            'total_cost': 0.0,
            'protection_level': 0.0,
            'feasible': False,
            'total_units': 0,
            'solver_status': _status_name(status),
            'infeasibility_reason': infeasibility_reason,
            'diagnostics': diagnostics
        }


def _status_name(status: int) -> str:
    """Convert OR-Tools status code to readable string."""
    status_names = {
        cp_model.OPTIMAL: 'optimal',
        cp_model.FEASIBLE: 'feasible',
        cp_model.INFEASIBLE: 'infeasible',
        cp_model.MODEL_INVALID: 'model_invalid',
        cp_model.UNKNOWN: 'unknown'
    }
    return status_names.get(status, f'unknown_status_{status}')
