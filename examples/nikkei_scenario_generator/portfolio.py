from dataclasses import dataclass


@dataclass
class FactorShock:
    """One-step shock in our factor space."""
    eq_ret: float      # Nikkei return (e.g., -0.1 = -10%)
    vol_change: float  # Change in implied vol (absolute, e.g., +0.10 = +10 vol pts)
    fx_ret: float      # USDJPY return (e.g., +0.05 = +5% weaker JPY)
    ir_change: float   # 10Y JGB yield change in absolute (e.g., +0.01 = +1%)


@dataclass
class InstrumentExposure:
    name: str
    base_value: float      # current MTM value in JPY

    # factor sensitivities
    eq_delta: float = 0.0  # dV/d(eq_ret) approx
    eq_gamma: float = 0.0  # d²V/d(eq_ret)²
    vega: float = 0.0      # dV/d(vol_change)
    fx_beta: float = 0.0   # dV/d(fx_ret) approx
    ir_dv01: float = 0.0   # JPY PnL per +1.0 change in yield (e.g., 0.01 = +1%)


@dataclass
class Portfolio:
    name: str
    instruments: list[InstrumentExposure]

    def pnl(self, shock: FactorShock) -> float:
        return sum(instrument_pnl(inst, shock) for inst in self.instruments)


def instrument_pnl(inst: InstrumentExposure, shock: FactorShock) -> float:
    """
    Simple Taylor expansion:
    dV ≈ base_value*(eq_delta*eq + 0.5*eq_gamma*eq^2 + vega*vol)
         + base_value*fx_beta*fx + ir_dv01*ir
    """
    eq = shock.eq_ret
    vol = shock.vol_change
    fx = shock.fx_ret
    ir = shock.ir_change

    dV_eq = inst.base_value * (inst.eq_delta * eq + 0.5 * inst.eq_gamma * eq * eq)
    dV_vol = inst.base_value * inst.vega * vol
    dV_fx = inst.base_value * inst.fx_beta * fx
    dV_ir = inst.ir_dv01 * ir

    return dV_eq + dV_vol + dV_fx + dV_ir


def make_base_nikkei_portfolio() -> Portfolio:
    """
    Example: ¥100B long Nikkei-equity-like exposure.
    """
    eq_inst = InstrumentExposure(
        name="Nikkei_Equity",
        base_value=100_000_000_000,  # 100B JPY
        eq_delta=1.0,
        eq_gamma=0.0,    # no optionality here
        vega=0.0,
        fx_beta=0.0,
        ir_dv01=0.0,
    )
    return Portfolio(name="Base_Nikkei_Long", instruments=[eq_inst])


def make_hedged_portfolio() -> Portfolio:
    """
    Example: base long equity + some futures/options/JGB/FX hedges.
    For now, we just encode their net factor exposures.
    """
    instruments = []

    # Long Nikkei equity
    instruments.append(InstrumentExposure(
        name="Nikkei_Equity",
        base_value=100_000_000_000,
        eq_delta=1.0,
    ))

    # Short Nikkei futures: hedge 80% of delta
    instruments.append(InstrumentExposure(
        name="Short_Nikkei_Futures",
        base_value=-80_000_000_000,  # sign handled via delta
        eq_delta=1.0,
    ))

    # Long NKY put options (downside hedge) - some gamma + vega
    instruments.append(InstrumentExposure(
        name="Long_Nikkei_Puts",
        base_value=5_000_000_000,
        eq_delta=-0.4,   # mild delta hedge
        eq_gamma=2.0,    # benefits from big moves (approx)
        vega=3.0,        # gains when vol up
    ))

    # JGB futures hedge (IR)
    instruments.append(InstrumentExposure(
        name="Long_JGB_Futures",
        base_value=0.0,  # value ignored, only dv01 matters
        ir_dv01= -300_000_000,  # JPY per +1.0 yield change
    ))

    # USDJPY FX hedge (assume we’re long some USD-earnings exposure)
    instruments.append(InstrumentExposure(
        name="Short_USDJPY_Futures",
        base_value=50_000_000_000,
        fx_beta=-1.0,  # loses when USDJPY increases
    ))

    return Portfolio(name="Hedged_Portfolio", instruments=instruments)

