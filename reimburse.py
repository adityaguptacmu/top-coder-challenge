import math
import argparse

# Configuration constants
PER_DIEM_RATE = 100.00
MILEAGE_RATE_TIER1 = 0.4000
MILEAGE_RATE_TIER2 = 0.3788
MILEAGE_THRESHOLD = 87.3242
RECEIPT_REIMBURSEMENT_BASE_RATE = 0.4659
RECEIPT_DIMINISHING_RETURN_FACTOR = 0.0001
VACATION_PENALTY_AMOUNT = 400.0000
VACATION_PENALTY_DURATION_THRESHOLD = 8
OPTIMAL_SPENDING_LONG_TRIP_MAX = 90.0000
VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR = 1.2000
SWEET_SPOT_DURATION = 5
SWEET_SPOT_MILES_PER_DAY_MIN = 180.0000
SWEET_SPOT_SPENDING_PER_DAY_MAX = 100.0000
SWEET_SPOT_COMBO_BONUS = 194.7575
TRIP_5_DAY_BONUS = 76.6963
TRIP_4_OR_6_DAY_BONUS = 25.0
MILEAGE_EFFICIENCY_MIN = 180.0000
MILEAGE_EFFICIENCY_MAX = 220.0000
MILEAGE_EFFICIENCY_BONUS = 90.2941
SHORT_TRIP_MAX_DAYS = 3
MEDIUM_TRIP_MIN_DAYS = 4
MEDIUM_TRIP_MAX_DAYS = 6
SHORT_TRIP_SPENDING_THRESHOLD = 75.0000
MEDIUM_TRIP_SPENDING_THRESHOLD = 120.0000
LONG_TRIP_SPENDING_THRESHOLD = 90.0000
HIGH_SPENDING_PENALTY_RATE = 0.05
LOW_RECEIPT_THRESHOLD = 30.0000
LOW_RECEIPT_PENALTY = 57.9780
LOW_RECEIPT_MIN_DAYS = 2
CENTS_BONUS_AMOUNT = 1.0000

# Adjustment constants for better alignment with test cases
PER_DAY_ADJUSTMENT = 8.9233  # Small per-day bonus to align with test cases
LONG_TRIP_DEDUCTION = 150.00  # Deduction for trips >7 days without vacation penalty

def calculate_reimbursement(trip_duration_days, miles_traveled, total_receipts_amount):
    """
    Calculate travel reimbursement based on trip duration, miles traveled, and receipts.

    Args:
        trip_duration_days (int): Number of days of the trip
        miles_traveled (float): Total miles traveled
        total_receipts_amount (float): Total amount of receipts submitted

    Returns:
        float: Total reimbursement amount, rounded to 2 decimal places
    """
    # 1. Per Diem Reimbursement
    per_diem_reimbursement = trip_duration_days * PER_DIEM_RATE

    # 2. Mileage Reimbursement
    if miles_traveled <= MILEAGE_THRESHOLD:
        mileage_reimbursement = miles_traveled * MILEAGE_RATE_TIER1
    else:
        mileage_reimbursement = (MILEAGE_THRESHOLD * MILEAGE_RATE_TIER1) + \
                                ((miles_traveled - MILEAGE_THRESHOLD) * MILEAGE_RATE_TIER2)

    # 3. Receipt Reimbursement
    spending_per_day = total_receipts_amount / trip_duration_days if trip_duration_days > 0 else 0
    diminishing_rate = RECEIPT_REIMBURSEMENT_BASE_RATE * math.exp(-spending_per_day * RECEIPT_DIMINISHING_RETURN_FACTOR)
    receipt_reimbursement = total_receipts_amount * diminishing_rate

    # Initial subtotal
    subtotal = per_diem_reimbursement + mileage_reimbursement + receipt_reimbursement

    # 4. Bonuses and Penalties
    miles_per_day = miles_traveled / trip_duration_days if trip_duration_days > 0 else 0

    # Vacation Penalty
    vacation_spending_threshold = OPTIMAL_SPENDING_LONG_TRIP_MAX * VACATION_PENALTY_SPENDING_THRESHOLD_FACTOR
    vacation_penalty = 0
    if trip_duration_days >= VACATION_PENALTY_DURATION_THRESHOLD and spending_per_day > vacation_spending_threshold:
        vacation_penalty = VACATION_PENALTY_AMOUNT

    # Sweet Spot Combo Bonus
    sweet_spot_bonus = 0
    if (trip_duration_days == SWEET_SPOT_DURATION and
        miles_per_day >= SWEET_SPOT_MILES_PER_DAY_MIN and
        spending_per_day < SWEET_SPOT_SPENDING_PER_DAY_MAX):
        sweet_spot_bonus = SWEET_SPOT_COMBO_BONUS

    # Trip Duration Bonuses
    duration_bonus = 0
    if trip_duration_days == 5:
        duration_bonus = TRIP_5_DAY_BONUS
    elif trip_duration_days in (4, 6):
        duration_bonus = TRIP_4_OR_6_DAY_BONUS

    # Mileage Efficiency Bonus
    efficiency_bonus = 0
    if MILEAGE_EFFICIENCY_MIN <= miles_per_day <= MILEAGE_EFFICIENCY_MAX:
        efficiency_bonus = MILEAGE_EFFICIENCY_BONUS

    # Apply bonuses (vacation penalty overrides most bonuses except sweet spot)
    if vacation_penalty > 0:
        subtotal -= vacation_penalty
        subtotal += sweet_spot_bonus  # Sweet spot bonus can still apply
    else:
        subtotal += sweet_spot_bonus + duration_bonus + efficiency_bonus

    # High Spending Penalty
    high_spending_penalty = 0
    if trip_duration_days <= SHORT_TRIP_MAX_DAYS and spending_per_day > SHORT_TRIP_SPENDING_THRESHOLD:
        high_spending_penalty = subtotal * HIGH_SPENDING_PENALTY_RATE
    elif (MEDIUM_TRIP_MIN_DAYS <= trip_duration_days <= MEDIUM_TRIP_MAX_DAYS and
          spending_per_day > MEDIUM_TRIP_SPENDING_THRESHOLD):
        high_spending_penalty = subtotal * HIGH_SPENDING_PENALTY_RATE
    elif trip_duration_days > MEDIUM_TRIP_MAX_DAYS and spending_per_day > LONG_TRIP_SPENDING_THRESHOLD:
        high_spending_penalty = subtotal * HIGH_SPENDING_PENALTY_RATE
    subtotal -= high_spending_penalty

    # 5. Final Adjustments
    # Low Receipt Penalty
    if (trip_duration_days >= LOW_RECEIPT_MIN_DAYS and
        0 < total_receipts_amount < LOW_RECEIPT_THRESHOLD):
        subtotal -= LOW_RECEIPT_PENALTY

    # Cents Bonus
    cents = int(round(total_receipts_amount * 100)) % 100
    if cents in (49, 99):
        subtotal += CENTS_BONUS_AMOUNT

    # Adjustment for long trips without vacation penalty
    if trip_duration_days > 7 and vacation_penalty == 0:
        subtotal -= LONG_TRIP_DEDUCTION

    # Per-day adjustment to align with test cases
    adjustment_bonus = trip_duration_days * PER_DAY_ADJUSTMENT
    subtotal += adjustment_bonus

    # Ensure non-negative reimbursement
    total_reimbursement = max(0, subtotal)

    return total_reimbursement

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
    )

    print(f"{reimbursement_amount:.2f}")