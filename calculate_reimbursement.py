import sys
import argparse
import math

# Configuration for reimbursement calculations.
# Version based on feedback.md and distilled.interviews.md
REIMBURSEMENT_RATES = {
    # Base Rates
    "PER_DIEM_RATE": 100.00,

    # Mileage Tiers
    "MILEAGE_TIER1_THRESHOLD": 100.0,
    "MILEAGE_RATE_TIER1": 0.58,
    "MILEAGE_RATE_TIER2": 0.45,

    # Receipt Reimbursement
    "RECEIPT_REIMBURSEMENT_BASE_RATE": 0.6,
    "RECEIPT_DIMINISHING_RETURN_FACTOR": 0.001,

    # Optimal Daily Spending Thresholds (from interviews)
    "OPTIMAL_SPENDING_SHORT_TRIP_DAYS": 3,
    "OPTIMAL_SPENDING_SHORT_TRIP_MAX": 75.0,
    "OPTIMAL_SPENDING_MEDIUM_TRIP_DAYS": 6,
    "OPTIMAL_SPENDING_MEDIUM_TRIP_MAX": 120.0,
    "OPTIMAL_SPENDING_LONG_TRIP_MAX": 90.0,

    # Bonuses (fixed days, tunable amounts)
    "CENTS_BONUS_CENTS": [49, 99],
    "CENTS_BONUS_AMOUNT": 5.01,
    "FIVE_DAY_TRIP_BONUS_DAYS": 5,
    "FIVE_DAY_TRIP_BONUS_AMOUNT": 50.0,
    "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN": 180,
    "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX": 220,
    "MILES_PER_DAY_EFFICIENCY_BONUS": 75.0,

    # Penalties
    "LOW_RECEIPT_PENALTY_TRIP_DAYS": 2,
    "LOW_RECEIPT_PENALTY_THRESHOLD": 30.0,
    "LOW_RECEIPT_PENALTY_AMOUNT": 75.0,
    "HIGH_SPENDING_PENALTY_PERCENT": 0.15,

    # Key Interaction Effects / Trip Profiles (fixed days, tunable bonuses/penalties)
    "SWEET_SPOT_COMBO_DAYS": 5,
    "SWEET_SPOT_COMBO_MILES_PER_DAY": 180,
    "SWEET_SPOT_COMBO_SPENDING_PER_DAY": 100.0,
    "SWEET_SPOT_COMBO_BONUS": 200.0,
    "VACATION_PENALTY_DAYS": 8,
    "VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR": 1.2,  # More restrictive than normal long trip threshold
    "VACATION_PENALTY_AMOUNT": 250.0,


        "MILEAGE_TIER1_THRESHOLD": 87.3242,
    "MILEAGE_RATE_TIER1": 0.4000,
    "MILEAGE_RATE_TIER2": 0.3788,
    "RECEIPT_REIMBURSEMENT_BASE_RATE": 0.4659,
    "RECEIPT_DIMINISHING_RETURN_FACTOR": 0.0001,
    "OPTIMAL_SPENDING_SHORT_TRIP_MAX": 75.0000,
    "OPTIMAL_SPENDING_MEDIUM_TRIP_MAX": 120.0000,
    "OPTIMAL_SPENDING_LONG_TRIP_MAX": 90.0000,
    "CENTS_BONUS_AMOUNT": 1,
    "FIVE_DAY_TRIP_BONUS_AMOUNT": 76.6963,
    "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN": 180.0000,
    "MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX": 220.0000,
    "MILES_PER_DAY_EFFICIENCY_BONUS": 90.2941,
    "LOW_RECEIPT_PENALTY_TRIP_DAYS": 2,
    "LOW_RECEIPT_PENALTY_THRESHOLD": 30.0000,
    "LOW_RECEIPT_PENALTY_AMOUNT": 57.9780,
    "HIGH_SPENDING_PENALTY_PERCENT": 0.0500,
    "SWEET_SPOT_COMBO_MILES_PER_DAY": 180.0000,
    "SWEET_SPOT_COMBO_SPENDING_PER_DAY": 100.0000,
    "SWEET_SPOT_COMBO_BONUS": 194.7575,
    "VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR": 1.2000,
    "VACATION_PENALTY_AMOUNT": 400.0000,
}


def calculate_reimbursement(trip_duration_days, miles_traveled, total_receipts_amount, debug=False):
    debug_log = []

    # Use a shorter alias for the rates dictionary
    R = REIMBURSEMENT_RATES

    # --- Initial Calculations & Helper Variables ---
    total_reimbursement = 0.0
    # Avoid division by zero for 0-day trips
    miles_per_day = miles_traveled / trip_duration_days if trip_duration_days > 0 else 0
    spending_per_day = total_receipts_amount / trip_duration_days if trip_duration_days > 0 else 0

    debug_log.append(f"INIT: Trip Duration: {trip_duration_days} days, Miles: {miles_traveled}, Receipts: ${total_receipts_amount:.2f}")
    debug_log.append(f"INIT: Miles/Day: {miles_per_day:.2f}, Spending/Day: ${spending_per_day:.2f}")

    # --- 1. Per Diem Calculation ---
    per_diem_reimbursement = trip_duration_days * R["PER_DIEM_RATE"]
    total_reimbursement += per_diem_reimbursement
    debug_log.append(f"CALC: Base Per Diem: {trip_duration_days} days * ${R['PER_DIEM_RATE']}/day = ${per_diem_reimbursement:.2f}")

    # --- 2. Mileage Reimbursement (Tiered) ---
    miles_tier1 = min(miles_traveled, R["MILEAGE_TIER1_THRESHOLD"])
    miles_tier2 = miles_traveled - miles_tier1
    mileage_reimbursement = (miles_tier1 * R["MILEAGE_RATE_TIER1"]) + (miles_tier2 * R["MILEAGE_RATE_TIER2"])
    total_reimbursement += mileage_reimbursement
    debug_log.append(f"CALC: Mileage Reimbursement (Tiered): ${mileage_reimbursement:.2f} ({miles_tier1:.1f}mi @ ${R['MILEAGE_RATE_TIER1']}/mi, {miles_tier2:.1f}mi @ ${R['MILEAGE_RATE_TIER2']}/mi)")

    # --- 3. Receipt Reimbursement (with Diminishing Returns) ---
    diminishing_rate = R["RECEIPT_REIMBURSEMENT_BASE_RATE"] * math.exp(-spending_per_day * R["RECEIPT_DIMINISHING_RETURN_FACTOR"])
    receipt_reimbursement = total_receipts_amount * diminishing_rate
    total_reimbursement += receipt_reimbursement
    debug_log.append(f"CALC: Receipt Reimbursement: ${total_receipts_amount:.2f} * {diminishing_rate:.2%} (Rate based on ${spending_per_day:.2f}/day spending) = ${receipt_reimbursement:.2f}")

    debug_log.append(f"SUBTOTAL after base calculations: ${total_reimbursement:.2f}")

    # --- 4. Bonuses and Penalties based on Trip Profile ---
    # These are applied to the subtotal.
    # Check for major penalty profile first, as it overrides most bonuses

    # Profile: "Vacation Penalty" (Guaranteed Penalty - overrides most bonuses)
    if (trip_duration_days >= R["VACATION_PENALTY_DAYS"] and
          spending_per_day > (R["OPTIMAL_SPENDING_LONG_TRIP_MAX"] * R["VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR"])):
        penalty = R["VACATION_PENALTY_AMOUNT"]
        total_reimbursement -= penalty
        debug_log.append(f"PENALTY: 'Vacation Penalty' profile triggered. -${penalty:.2f}")

    else: # Apply bonuses if not in vacation penalty territory
        # Profile: "Sweet Spot Combo" (Guaranteed Bonus - can stack with other bonuses)
        if (trip_duration_days == R["SWEET_SPOT_COMBO_DAYS"] and
            miles_per_day >= R["SWEET_SPOT_COMBO_MILES_PER_DAY"] and
            spending_per_day < R["SWEET_SPOT_COMBO_SPENDING_PER_DAY"]):
            bonus = R["SWEET_SPOT_COMBO_BONUS"]
            total_reimbursement += bonus
            debug_log.append(f"BONUS: 'Sweet Spot Combo' profile triggered. +${bonus:.2f}")

        # 5-Day Trip Bonus (can apply even with Sweet Spot Combo)
        if trip_duration_days == R["FIVE_DAY_TRIP_BONUS_DAYS"]:
            bonus = R["FIVE_DAY_TRIP_BONUS_AMOUNT"]
            total_reimbursement += bonus
            debug_log.append(f"BONUS: Standard 5-Day Trip. +${bonus:.2f}")

        # Mileage Efficiency Bonus
        if R["MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MIN"] <= miles_per_day <= R["MILES_PER_DAY_EFFICIENCY_SWEET_SPOT_MAX"]:
            bonus = R["MILES_PER_DAY_EFFICIENCY_BONUS"]
            total_reimbursement += bonus
            debug_log.append(f"BONUS: Mileage Efficiency in sweet spot ({miles_per_day:.2f} miles/day). +${bonus:.2f}")

        # High Spending Penalty
        is_short_trip = trip_duration_days <= R["OPTIMAL_SPENDING_SHORT_TRIP_DAYS"]
        is_medium_trip = R["OPTIMAL_SPENDING_SHORT_TRIP_DAYS"] < trip_duration_days <= R["OPTIMAL_SPENDING_MEDIUM_TRIP_DAYS"]
        high_spending = False
        if is_short_trip and spending_per_day > R["OPTIMAL_SPENDING_SHORT_TRIP_MAX"]:
            high_spending = True
            debug_log.append(f"INFO: High daily spending detected for short trip.")
        elif is_medium_trip and spending_per_day > R["OPTIMAL_SPENDING_MEDIUM_TRIP_MAX"]:
            high_spending = True
            debug_log.append(f"INFO: High daily spending detected for medium trip.")
        elif not is_short_trip and not is_medium_trip and spending_per_day > R["OPTIMAL_SPENDING_LONG_TRIP_MAX"]:
            high_spending = True
            debug_log.append(f"INFO: High daily spending detected for long trip.")

        if high_spending:
            penalty_amount = total_reimbursement * R["HIGH_SPENDING_PENALTY_PERCENT"]
            total_reimbursement -= penalty_amount
            debug_log.append(f"PENALTY: High daily spending penalty applied. -${penalty_amount:.2f}")

    # --- 5. Final Adjustments (apply universally) ---

    # Penalty for Low Receipts on multi-day trips
    if (trip_duration_days >= R["LOW_RECEIPT_PENALTY_TRIP_DAYS"] and
        0 < total_receipts_amount < R["LOW_RECEIPT_PENALTY_THRESHOLD"]):
        penalty = R["LOW_RECEIPT_PENALTY_AMOUNT"]
        total_reimbursement -= penalty
        debug_log.append(f"PENALTY: Low receipts (${total_receipts_amount:.2f}) for a {trip_duration_days}-day trip. -${penalty:.2f}")

    # Cents-Based Bonus
    cents = round(total_receipts_amount * 100) % 100
    if cents in R["CENTS_BONUS_CENTS"]:
        bonus = R["CENTS_BONUS_AMOUNT"]
        total_reimbursement += bonus
        debug_log.append(f"BONUS: Receipt cents value is {cents}. +${bonus:.2f}")

    # --- Finalization ---
    final_reimbursement = max(0, total_reimbursement)
    if final_reimbursement != total_reimbursement:
        debug_log.append(f"FINAL: Reimbursement capped at $0 (was ${total_reimbursement:.2f}).")

    debug_log.append(f"FINAL: Total reimbursement: ${final_reimbursement:.2f}")

    if debug:
        print("\n--- Reimbursement Calculation Trace ---")
        for line in debug_log:
            print(line)
        print("---------------------------------------")

    return final_reimbursement


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate employee travel reimbursement.")
    parser.add_argument("trip_duration_days", type=int, help="Duration of the trip in days.")
    parser.add_argument("miles_traveled", type=float, help="Total miles traveled.")
    parser.add_argument("total_receipts_amount", type=float, help="Total amount of receipts.")
    parser.add_argument("--debug", action="store_true", help="Enable debug prints to see calculation steps.")

    args = parser.parse_args()

    reimbursement_amount = calculate_reimbursement(
        args.trip_duration_days,
        args.miles_traveled,
        args.total_receipts_amount,
        debug=args.debug
    )

    if not args.debug:
        print(f"{reimbursement_amount:.2f}")