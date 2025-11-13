"""
Risk Interpreter - Initial Strategy
Evolves context interpretation for financial risk optimization.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple
from utils.sentiment_analysis import analyze_news


"""
Interpret financial context and generate optimization parameters.

This function evolves to learn better context interpretation.

Args:
    context: Dictionary containing:
        - news: str (market news/events)
        - market_signals: dict (vix, prices, volatility)
        - regulations: dict (regulatory constraints)
        - portfolio: dict (current portfolio state)
        - risk_appetite: str (conservative/moderate/aggressive)

Returns:
    Dictionary with optimization parameters:
        - risk_weight: float (0-1, importance of risk in objective)
        - cost_weight: float (0-1, importance of cost in objective)
        - protection_level: float (0-1, minimum protection required)
        - instruments: list of str (which instruments to consider)
        - max_cost_pct: float (maximum cost as % of portfolio)

    The function uses the analyze_news utility to extract sentiment and signals from news text.
    The analyze_news function returns:
        Dictionary with:
            - sentiment: float (-1 to 1)
                -1 = very negative (bearish)
                 0 = neutral
                 1 = very positive (bullish)
            - volatility_signal: bool
                True if text mentions volatility/uncertainty
            - policy_signal: bool
                True if text mentions policy/regulatory changes
            - stress_level: float (0 to 1)
                0 = calm market signals
                1 = high stress/crisis signals

CRITICAL RULES:
- Do NOT implement your own analyze_news() or import external libraries like nltk
- Do NOT add functions outside the EVOLVE-BLOCK
- ONLY modify code inside EVOLVE-BLOCK markers
- USE the provided analyze_news utility - it's already implemented in utils/
"""
# EVOLVE-BLOCK-START
def interpret_context(context: Dict[str, Any]) -> Dict[str, Any]:
    # Seed Strategy: Simple conservative baseline
    params = {
        'risk_weight': 0.7,
        'cost_weight': 0.3,
        'protection_level': 0.65,
        'instruments': ['put_otm', 'put_atm', 'collar'],
        'max_cost_pct': 0.03
    }

    # Analyze news for sentiment and signals
    news_text = context.get('news', '')
    if news_text:
        news_analysis = analyze_news(news_text)
        sentiment = news_analysis['sentiment']
        volatility_signal = news_analysis['volatility_signal']
        stress_level = news_analysis['stress_level']

        # Adjust risk and cost weights based on sentiment
        if sentiment < -0.5 or stress_level > 0.7 or volatility_signal:
            # Negative sentiment or high stress - prioritize risk protection
            params['risk_weight'] = min(1.0, params['risk_weight'] + 0.2)
            params['cost_weight'] = max(0.0, params['cost_weight'] - 0.2)
            params['protection_level'] = min(1.0, params['protection_level'] + 0.1)
        elif sentiment > 0.5 and stress_level < 0.3:
            # Positive sentiment - allow more cost efficiency
            params['risk_weight'] = max(0.0, params['risk_weight'] - 0.2)
            params['cost_weight'] = min(1.0, params['cost_weight'] + 0.2)
            params['protection_level'] = max(0.0, params['protection_level'] - 0.1)

    # Basic context awareness
    risk_appetite = context.get('risk_appetite', 'moderate')
    
    if risk_appetite == 'conservative':
        params['risk_weight'] = 0.8
        params['cost_weight'] = 0.2
        params['protection_level'] = 0.75
    elif risk_appetite == 'aggressive':
        params['risk_weight'] = 0.5
        params['cost_weight'] = 0.5
        params['protection_level'] = 0.75
    
    return params
# EVOLVE-BLOCK-END


def run_experiment(scenario_path: str = None) -> Tuple[Dict, str]:
    """
    Run experiment on a scenario.
    Called by evaluate.py during evolution.
    
    Returns:
        (metrics_dict, feedback_text)
    """
    # Load scenario
    if scenario_path is None:
        scenario_path = _get_default_scenario_path()
    
    with open(scenario_path, 'r') as f:
        scenario = json.load(f)
    
    # Run interpretation
    interpretation = interpret_context(scenario['context'])
    
    # Formulate optimization problem
    problem = _formulate_problem(interpretation, scenario)
    
    # Solve with discrete optimizer
    solution = _solve_problem(problem)
    
    # Evaluate solution quality
    metrics = _evaluate_solution(solution, scenario, interpretation)
    
    # Generate feedback text
    feedback = _generate_feedback(metrics, interpretation, scenario['name'])
    
    return metrics, feedback


def _get_default_scenario_path() -> str:
    """Get path to default test scenario."""
    script_dir = Path(__file__).parent
    return str(script_dir / 'scenarios' / 'boj_policy.json')


def _formulate_problem(interpretation: Dict, scenario: Dict) -> Dict:
    """Convert interpretation to optimization problem structure."""
    from examples.risk_interpreter.utils.instruments import INSTRUMENTS
    
    portfolio_value = scenario['context']['portfolio']['value']
    
    # Decision variables: how many contracts of each instrument
    variables = {}
    for instrument_name in interpretation['instruments']:
        if instrument_name not in INSTRUMENTS:
            continue
        
        instrument = INSTRUMENTS[instrument_name]
        variables[instrument_name] = {
            'type': 'integer',
            'min': 0,
            'max': 200,  # Max contracts
            'cost_per_unit': instrument['cost_pct'] * portfolio_value / 100,
            'protection_per_unit': instrument['protection_factor']
        }
    
    # Objective weights
    objective = {
        'risk_weight': interpretation['risk_weight'],
        'cost_weight': interpretation['cost_weight']
    }
    
    # Constraints
    constraints = [
        {
            'type': 'cost_limit',
            'value': interpretation['max_cost_pct'] * portfolio_value
        },
        {
            'type': 'min_protection',
            'value': interpretation['protection_level']
        }
    ]
    
    return {
        'variables': variables,
        'objective': objective,
        'constraints': constraints,
        'portfolio_value': portfolio_value
    }


def _solve_problem(problem: Dict) -> Dict:
    """Solve discrete optimization problem."""
    from utils.solver import solve_optimization
    
    solution = solve_optimization(problem)
    return solution


def _evaluate_solution(
    solution: Dict,
    scenario: Dict,
    interpretation: Dict
) -> Dict:
    """Evaluate solution quality."""

    portfolio_value = scenario['context']['portfolio']['value']

    # Calculate metrics
    total_cost = solution.get('total_cost', 0)
    cost_pct = total_cost / portfolio_value if portfolio_value > 0 else 0

    protection = solution.get('protection_level', 0)
    num_instruments = len(solution.get('selected_instruments', {}))

    # Check constraint satisfaction
    constraints_ok = solution.get('feasible', False)
    within_budget = cost_pct <= interpretation['max_cost_pct']
    meets_protection = protection >= interpretation['protection_level']

    num_constraints_satisfied = sum([
        constraints_ok,
        within_budget,
        meets_protection
    ])

    # Compute score (higher is better)
    # Reward protection, penalize cost, reward constraint satisfaction
    score = (
        protection * 100 +                    # 0-100 points for protection
        (1 - cost_pct / 0.05) * 50 +         # 0-50 points for low cost
        num_constraints_satisfied * 20        # 0-60 points for constraints
    )

    metrics = {
        'score': float(score),
        'cost_pct': float(cost_pct),
        'protection': float(protection),
        'num_instruments': int(num_instruments),
        'constraints_satisfied': int(num_constraints_satisfied),
        'feasible': bool(constraints_ok)
    }

    # Include diagnostics if solution is infeasible
    if not constraints_ok:
        metrics['infeasibility_reason'] = solution.get('infeasibility_reason', 'Unknown reason')
        metrics['diagnostics'] = solution.get('diagnostics', [])

    return metrics


def _generate_feedback(
    metrics: Dict, 
    interpretation: Dict, 
    scenario_name: str
) -> str:
    """Generate human-readable feedback."""
    
    feedback = f"Scenario: {scenario_name}\n"
    feedback += f"Score: {metrics['score']:.1f}\n"
    feedback += f"Cost: {metrics['cost_pct']:.2%}\n"
    feedback += f"Protection: {metrics['protection']:.2%}\n"
    feedback += f"Instruments used: {metrics['num_instruments']}\n"
    feedback += f"Constraints satisfied: {metrics['constraints_satisfied']}/3\n"
    feedback += f"\nInterpretation: risk_weight={interpretation['risk_weight']:.2f}, "
    feedback += f"cost_weight={interpretation['cost_weight']:.2f}\n"
    
    return feedback


if __name__ == "__main__":
    # Test run
    metrics, feedback = run_experiment()
    print(feedback)
    print(f"\nMetrics: {metrics}")
