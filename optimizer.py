import pandas as pd
import numpy as np
from scipy.optimize import minimize, differential_evolution, basinhopping
from calculate_reimbursement import calculate_reimbursement, REIMBURSEMENT_RATES
import json
import warnings
warnings.filterwarnings('ignore')

# --- Configuration ---
DATA_FILE = "public_cases.json"

# Optimizing constants for the reimbursement model in calculate_reimbursement.py
CONSTANTS_TO_OPTIMIZE = [
    # Mileage Tiers
    "MILEAGE_TIER1_THRESHOLD",
    "MILEAGE_RATE_TIER1",
    "MILEAGE_RATE_TIER2",
    # Receipt Reimbursement
    "RECEIPT_REIMBURSEMENT_BASE_RATE",
    "RECEIPT_DIMINISHING_RETURN_FACTOR",
    # Optimal Spending Thresholds
    "OPTIMAL_SPENDING_SHORT_TRIP_MAX",
    "OPTIMAL_SPENDING_MEDIUM_TRIP_MAX",
    "OPTIMAL_SPENDING_LONG_TRIP_MAX",
    # Bonuses
    "CENTS_BONUS_AMOUNT",
    "FIVE_DAY_TRIP_BONUS_AMOUNT",
    "FOUR_DAY_TRIP_BONUS_AMOUNT",
    "SIX_DAY_TRIP_BONUS_AMOUNT",
    "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN",
    "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX",
    "MILES_PER_DAY_EFFICIENCY_BONUS",
    # Penalties
    "LOW_RECEIPT_PENALTY_TRIP_DAYS",
    "LOW_RECEIPT_PENALTY_THRESHOLD",
    "LOW_RECEIPT_PENALTY_AMOUNT",
    "HIGH_SPENDING_PENALTY_PERCENT",
    # Key Interaction Effects / Trip Profiles
    "SWEET_SPOT_COMBO_MILES_PER_DAY",
    "SWEET_SPOT_COMBO_SPENDING_PER_DAY",
    "SWEET_SPOT_COMBO_BONUS",
    "VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR",
    "VACATION_PENALTY_AMOUNT",
]

def load_data(file_path):
    """Loads the reimbursement data from the public JSON file."""
    try:
        with open(file_path, 'r') as f:
            raw_data = json.load(f)

        # Normalize the nested JSON structure into a flat list of dictionaries
        processed_data = []
        for item in raw_data:
            flat_item = {
                "trip_duration_days": item["input"]["trip_duration_days"],
                "miles_traveled": item["input"]["miles_traveled"],
                "total_receipts_amount": item["input"]["total_receipts_amount"],
                "expected_reimbursement": item["expected_output"]
            }
            processed_data.append(flat_item)

        return pd.DataFrame(processed_data)

    except FileNotFoundError:
        print(f"Error: Data file not found at '{file_path}'.")
        print("Please make sure the file exists.")
        exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error processing JSON file '{file_path}': {e}")
        print("Please ensure the file is valid JSON and has the expected nested structure ('input', 'expected_output').")
        exit(1)


def objective_function(new_constants, data, initial_rates_config, penalty_weight=0.01):
    """
    Objective function that matches eval.sh calculation exactly.
    """
    # Create a mutable copy of the rates configuration
    current_rates = initial_rates_config.copy()

    # Update the rates with the new values from the optimizer
    for i, key in enumerate(CONSTANTS_TO_OPTIMIZE):
        current_rates[key] = new_constants[i]

    # Add constraint penalties for logical relationships (much smaller weight)
    penalty = 0

    # Mileage rates should be decreasing (tier1 >= tier2)
    if current_rates["MILEAGE_RATE_TIER1"] < current_rates["MILEAGE_RATE_TIER2"]:
        penalty += 100

    # Spending thresholds should make sense (short <= medium, but long can be different)
    if current_rates["OPTIMAL_SPENDING_SHORT_TRIP_MAX"] > current_rates["OPTIMAL_SPENDING_MEDIUM_TRIP_MAX"]:
        penalty += 50

    # Efficiency sweet spot should be a valid range
    if current_rates["MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN"] >= current_rates["MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX"]:
        penalty += 50

    # Temporarily override the global configuration for the calculation
    import calculate_reimbursement as cr
    original_rates = cr.REIMBURSEMENT_RATES
    cr.REIMBURSEMENT_RATES = current_rates

    try:
        total_absolute_error = 0
        exact_matches = 0

        for _, row in data.iterrows():
            # Unpack row data
            days = int(row['trip_duration_days'])
            miles = float(row['miles_traveled'])
            receipts = float(row['total_receipts_amount'])
            expected_reimbursement = float(row['expected_reimbursement'])

            # Calculate reimbursement with the current set of constants
            calculated_reimbursement = cr.calculate_reimbursement(days, miles, receipts)

            # Check for numerical instability
            if not np.isfinite(calculated_reimbursement) or calculated_reimbursement < 0:
                return 1e12

            # Calculate absolute error (matches eval.sh exactly)
            error = abs(calculated_reimbursement - expected_reimbursement)
            total_absolute_error += error

            # Count exact matches (within $0.01)
            if error < 0.01:
                exact_matches += 1

        # Calculate score exactly like eval.sh:
        # score = avg_error * 100 + (num_cases - exact_matches) * 0.1
        num_cases = len(data)
        avg_error = total_absolute_error / num_cases
        eval_script_score = avg_error * 100 + (num_cases - exact_matches) * 0.1

        # Use the eval.sh score as our primary objective
        final_score = eval_script_score + penalty * penalty_weight

    except (OverflowError, ValueError, ZeroDivisionError) as e:
        return 1e12

    finally:
        # Restore the original rates to avoid side effects
        cr.REIMBURSEMENT_RATES = original_rates

    if not np.isfinite(final_score):
        return 1e12

    return final_score


def run_optimization_strategy(strategy_name, data, initial_rates_config, initial_guess, bounds):
    """Run a specific optimization strategy."""
    print(f"\n--- Running {strategy_name} ---")

    if strategy_name == "L-BFGS-B":
        result = minimize(
            objective_function,
            initial_guess,
            args=(data, initial_rates_config),
            method='L-BFGS-B',
            bounds=bounds,
            options={'disp': False, 'maxiter': 2000, 'ftol': 1e-9}
        )

    elif strategy_name == "Differential Evolution":
        result = differential_evolution(
            objective_function,
            bounds,
            args=(data, initial_rates_config),
            seed=42,
            maxiter=300,
            popsize=15,
            atol=1e-8,
            disp=False
        )

    elif strategy_name == "Basin Hopping":
        # Use L-BFGS-B as the local minimizer for basin hopping
        minimizer_kwargs = {
            "method": "L-BFGS-B",
            "bounds": bounds,
            "args": (data, initial_rates_config),
            "options": {"maxiter": 500}
        }
        result = basinhopping(
            objective_function,
            initial_guess,
            minimizer_kwargs=minimizer_kwargs,
            niter=50,
            T=10.0,
            stepsize=0.1,
            disp=False
        )

    elif strategy_name == "SLSQP":
        result = minimize(
            objective_function,
            initial_guess,
            args=(data, initial_rates_config),
            method='SLSQP',
            bounds=bounds,
            options={'disp': False, 'maxiter': 1000, 'ftol': 1e-9}
        )

    print(f"{strategy_name} - Final error: {result.fun:.2f}")
    print(f"{strategy_name} - Success: {result.success}")

    return result


def main():
    """Main function to run multiple optimization strategies."""
    # Load the ground truth data
    print(f"Loading data from {DATA_FILE}...")
    data = load_data(DATA_FILE)
    print(f"Data loaded successfully. {len(data)} test cases.")

    # Get the initial guess from the existing configuration file
    initial_guess = [REIMBURSEMENT_RATES[k] for k in CONSTANTS_TO_OPTIMIZE]

    # Define refined bounds based on interview insights and logical constraints
    bounds_map = {
        # Mileage Tiers - refined based on typical IRS rates
        "MILEAGE_TIER1_THRESHOLD": (50, 200),
        "MILEAGE_RATE_TIER1": (0.35, 0.70),  # Should be higher than tier2
        "MILEAGE_RATE_TIER2": (0.25, 0.55),  # Should be lower than tier1

        # Receipt Reimbursement - more conservative bounds
        "RECEIPT_REIMBURSEMENT_BASE_RATE": (0.3, 0.8),
        "RECEIPT_DIMINISHING_RETURN_FACTOR": (1e-5, 5e-3),

        # Optimal Spending Thresholds - based on interview data
        "OPTIMAL_SPENDING_SHORT_TRIP_MAX": (60, 90),
        "OPTIMAL_SPENDING_MEDIUM_TRIP_MAX": (100, 140),
        "OPTIMAL_SPENDING_LONG_TRIP_MAX": (75, 105),

        # Bonuses - reasonable ranges
        "CENTS_BONUS_AMOUNT": (0.5, 15),
        "FIVE_DAY_TRIP_BONUS_AMOUNT": (30, 120),
        "FOUR_DAY_TRIP_BONUS_AMOUNT": (20, 80),
        "SIX_DAY_TRIP_BONUS_AMOUNT": (20, 80),
        "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN": (160, 200),
        "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX": (200, 250),
        "MILES_PER_DAY_EFFICIENCY_BONUS": (60, 120),

        # Penalties - reasonable ranges
        "LOW_RECEIPT_PENALTY_TRIP_DAYS": (1, 4),
        "LOW_RECEIPT_PENALTY_THRESHOLD": (20, 40),
        "LOW_RECEIPT_PENALTY_AMOUNT": (40, 100),
        "HIGH_SPENDING_PENALTY_PERCENT": (0.03, 0.25),

        # Key Interaction Effects
        "SWEET_SPOT_COMBO_MILES_PER_DAY": (160, 200),
        "SWEET_SPOT_COMBO_SPENDING_PER_DAY": (85, 115),
        "SWEET_SPOT_COMBO_BONUS": (150, 250),
        "VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR": (1.0, 1.5),
        "VACATION_PENALTY_AMOUNT": (200, 500),
    }
    bounds = [bounds_map.get(k, (0, None)) for k in CONSTANTS_TO_OPTIMIZE]

    # Run multiple optimization strategies
    strategies = [
        "Differential Evolution",  # Global optimizer - good for exploration
        "L-BFGS-B",               # Local optimizer - good for refinement
        "Basin Hopping",          # Global + local - good for escaping local minima
        "SLSQP",                  # Alternative local optimizer
    ]

    best_result = None
    best_error = float('inf')

    for strategy in strategies:
        try:
            result = run_optimization_strategy(strategy, data, REIMBURSEMENT_RATES, initial_guess, bounds)

            if result.success and result.fun < best_error:
                best_error = result.fun
                best_result = result
                print(f"*** New best result from {strategy}: {best_error:.2f} ***")

        except Exception as e:
            print(f"Strategy {strategy} failed: {e}")
            continue

    if best_result is not None:
        print(f"\n=== BEST OPTIMIZATION RESULT ===")
        print(f"Best error (sum of absolute differences): {best_result.fun:.2f}")
        print("Best constants found:")
        optimized_constants = best_result.x

        print("\n# Optimized constants for calculate_reimbursement.py:")
        for i, key in enumerate(CONSTANTS_TO_OPTIMIZE):
            # For integer-like constants, round the result
            if "DAYS" in key:
                print(f'    "{key}": {int(round(optimized_constants[i]))},')
            else:
                print(f'    "{key}": {optimized_constants[i]:.4f},')

        # Test the optimized constants
        print(f"\n=== TESTING OPTIMIZED CONSTANTS ===")
        import calculate_reimbursement as cr
        original_rates = cr.REIMBURSEMENT_RATES.copy()

        # Apply optimized constants
        for i, key in enumerate(CONSTANTS_TO_OPTIMIZE):
            cr.REIMBURSEMENT_RATES[key] = optimized_constants[i]

        # Calculate final error exactly like eval.sh
        total_absolute_error = 0
        exact_matches = 0
        close_matches = 0
        successful_runs = 0

        for _, row in data.iterrows():
            calculated = cr.calculate_reimbursement(
                int(row['trip_duration_days']),
                float(row['miles_traveled']),
                float(row['total_receipts_amount'])
            )
            expected = float(row['expected_reimbursement'])

            if np.isfinite(calculated) and calculated >= 0:
                successful_runs += 1
                error = abs(calculated - expected)
                total_absolute_error += error

                # Count exact matches (within $0.01)
                if error < 0.01:
                    exact_matches += 1

                # Count close matches (within $1.00)
                if error < 1.0:
                    close_matches += 1

        # Calculate metrics exactly like eval.sh
        avg_error = total_absolute_error / successful_runs if successful_runs > 0 else float('inf')
        exact_pct = (exact_matches * 100 / successful_runs) if successful_runs > 0 else 0
        close_pct = (close_matches * 100 / successful_runs) if successful_runs > 0 else 0
        eval_score = avg_error * 100 + (len(data) - exact_matches) * 0.1

        print(f"Total test cases: {len(data)}")
        print(f"Successful runs: {successful_runs}")
        print(f"Exact matches (±$0.01): {exact_matches} ({exact_pct:.1f}%)")
        print(f"Close matches (±$1.00): {close_matches} ({close_pct:.1f}%)")
        print(f"Average error: ${avg_error:.2f}")
        print(f"Eval.sh Score: {eval_score:.2f} (lower is better)")
        print(f"Verification: Total absolute error = {total_absolute_error:.2f}")

        # Restore original rates
        cr.REIMBURSEMENT_RATES = original_rates

    else:
        print("\nAll optimization strategies failed.")


if __name__ == "__main__":
    main()