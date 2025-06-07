import pandas as pd
import numpy as np
from scipy.optimize import minimize
from calculate_reimbursement import calculate_reimbursement, REIMBURSEMENT_RATES
import json

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


def objective_function(new_constants, data, initial_rates_config):
    """
    The function to minimize. It calculates the total absolute error for a given
    set of constants, inspired by the eval.sh script's error metric.
    """
    # Create a mutable copy of the rates configuration
    current_rates = initial_rates_config.copy()

    # Update the rates with the new values from the optimizer
    for i, key in enumerate(CONSTANTS_TO_OPTIMIZE):
        current_rates[key] = new_constants[i]

    total_absolute_error = 0

    # Temporarily override the global configuration for the calculation
    # This is a simple way to pass the new constants to the function
    import calculate_reimbursement as cr
    original_rates = cr.REIMBURSEMENT_RATES
    cr.REIMBURSEMENT_RATES = current_rates

    try:
        for _, row in data.iterrows():
            # Unpack row data
            days = row['trip_duration_days']
            miles = row['miles_traveled']
            receipts = row['total_receipts_amount']
            expected_reimbursement = row['expected_reimbursement']

            # Calculate reimbursement with the current set of constants
            calculated_reimbursement = cr.calculate_reimbursement(days, miles, receipts)

            # Check for numerical instability
            if not np.isfinite(calculated_reimbursement):
                # Return a large error if calculation is unstable
                return 1e12

            # Calculate the absolute error and add it to the total
            error = calculated_reimbursement - expected_reimbursement
            total_absolute_error += abs(error)

    except (OverflowError, ValueError) as e:
        # If a math error occurs, this set of constants is invalid.
        # Return a large error value to penalize it.
        # print(f"Numerical error with constants: {new_constants}. Error: {e}")
        return 1e12

    finally:
        # Restore the original rates to avoid side effects
        cr.REIMBURSEMENT_RATES = original_rates

    # We want to minimize this value
    if not np.isfinite(total_absolute_error):
        return 1e12

    return total_absolute_error


def main():
    """Main function to run the optimization."""
    # Load the ground truth data
    print(f"Loading data from {DATA_FILE}...")
    data = load_data(DATA_FILE)
    print("Data loaded successfully.")

    # Get the initial guess from the existing configuration file
    initial_guess = [REIMBURSEMENT_RATES[k] for k in CONSTANTS_TO_OPTIMIZE]

    # Define more specific bounds to guide the optimizer.
    bounds_map = {
        # Mileage Tiers
        "MILEAGE_TIER1_THRESHOLD": (50, 150),
        "MILEAGE_RATE_TIER1": (0.4, 0.8),
        "MILEAGE_RATE_TIER2": (0.3, 0.6),
        # Receipt Reimbursement
        "RECEIPT_REIMBURSEMENT_BASE_RATE": (0.3, 0.9),
        "RECEIPT_DIMINISHING_RETURN_FACTOR": (1e-4, 1e-2),
        # Optimal Spending Thresholds
        "OPTIMAL_SPENDING_SHORT_TRIP_MAX": (50, 100),
        "OPTIMAL_SPENDING_MEDIUM_TRIP_MAX": (100, 150),
        "OPTIMAL_SPENDING_LONG_TRIP_MAX": (70, 110),
        # Bonuses
        "CENTS_BONUS_AMOUNT": (1, 20),
        "FIVE_DAY_TRIP_BONUS_AMOUNT": (25, 100),
        "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN": (150, 250),
        "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX": (200, 300),
        "MILES_PER_DAY_EFFICIENCY_BONUS": (50, 150),
        # Penalties
        "LOW_RECEIPT_PENALTY_TRIP_DAYS": (1, 5),
        "LOW_RECEIPT_PENALTY_THRESHOLD": (10, 50),
        "LOW_RECEIPT_PENALTY_AMOUNT": (50, 150),
        "HIGH_SPENDING_PENALTY_PERCENT": (0.05, 0.5),
        # Key Interaction Effects / Trip Profiles
        "SWEET_SPOT_COMBO_MILES_PER_DAY": (150, 250),
        "SWEET_SPOT_COMBO_SPENDING_PER_DAY": (80, 120),
        "SWEET_SPOT_COMBO_BONUS": (100, 300),
        "VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR": (0.5, 2.0),
        "VACATION_PENALTY_AMOUNT": (100, 400),
    }
    bounds = [bounds_map.get(k, (0, None)) for k in CONSTANTS_TO_OPTIMIZE]


    print("Starting optimization... (this may take a while)")

    # Run the optimization
    result = minimize(
        objective_function,
        initial_guess,
        args=(data, REIMBURSEMENT_RATES),
        method='L-BFGS-B',  # A good choice that supports bounds
        bounds=bounds,
        options={'disp': True, 'maxiter': 5000, 'ftol': 1e-9} # Increased maxiter and adjusted tolerance
    )

    if result.success:
        print("\nOptimization successful!")
        print(f"Final error (sum of absolute differences): {result.fun}")
        print("Best constants found:")
        optimized_constants = result.x
        for i, key in enumerate(CONSTANTS_TO_OPTIMIZE):
            # For integer-like constants, round the result
            if "DAYS" in key or "CENTS" in key:
                 print(f'    "{key}": {round(optimized_constants[i])},')
            else:
                 print(f'    "{key}": {optimized_constants[i]:.4f},')
    else:
        print("\nOptimization failed.")
        print(f"Message: {result.message}")
        print(f"Final error: {result.fun}")


if __name__ == "__main__":
    main()