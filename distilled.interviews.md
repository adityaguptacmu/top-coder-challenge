# Distilled Facts for Reimbursement Calculation

This document summarizes the core rules and heuristics for the expense reimbursement system, distilled from employee interviews. The primary constraint is that the calculation logic **cannot use any date-based information** (e.g., time of year, day of week), as this data is not provided in the input.

The calculation is based on three inputs:
1.  `trip_duration_days`
2.  `miles_traveled`
3.  `total_receipts_amount`

The final reimbursement is not a simple sum of parts but is determined by the *interaction* between these factors. Different "trip profiles" receive different calculations.

---

## 1. Per Diem (Base Daily Rate)

*   There appears to be a **base daily rate of $100**.
*   This base rate is the starting point before numerous adjustments are made based on other trip parameters.

## 2. Trip Duration Effects

*   Trip duration is a significant factor in bonus and penalty calculations.
*   **4-6 Day "Sweet Spot":** Trips in this range are often considered optimal and receive favorable calculations.
*   **5-Day Trip Bonus:** A specific, consistent bonus is applied to 5-day trips.
*   **Long Trip Penalty:** Trips lasting 8 days or more are often subject to a penalty, especially when combined with high spending.

## 3. Mileage Calculation

*   Mileage reimbursement is not linear.
*   **Tiered Rate:** The reimbursement rate is higher for the first ~100 miles (estimated around $0.58/mile) and then decreases for subsequent miles. The drop-off follows a curve, not a simple step-down.
*   **Efficiency Bonus (Miles per Day):** The ratio of `miles_traveled / trip_duration_days` is a critical factor.
    *   A "sweet spot" for maximizing bonuses exists for efficiency between **180-220 miles/day**.
    *   Efficiency ratios that are too low or too high result in smaller bonuses or even penalties.

## 4. Receipt Handling and Spending

*   The way receipts are handled is complex and depends heavily on the spending rate relative to the trip length.
*   **Penalty for Low Receipts:** Submitting a very small `total_receipts_amount` for a multi-day trip is penalized. The final reimbursement can be less than the base per diem would have been if no receipts were submitted.
*   **Diminishing Returns for High Receipts:** Reimbursement for receipts is not 1-to-1. As the total receipt amount grows, the percentage that is paid back decreases.
*   **Optimal Daily Spending:** The system rewards "optimal" daily spending rates, which vary by trip duration. This rate can be calculated as `total_receipts_amount / trip_duration_days`.
    *   **Short Trips (1-3 days):** Optimal spending is under **$75/day**.
    *   **Medium Trips (4-6 days):** Optimal spending is up to **$120/day**.
    *   **Long Trips (7+ days):** Spending should be kept under **$90/day** to avoid penalties.
*   **Cents-Based Bonus:** A small, consistent bonus is often applied if the cents value of `total_receipts_amount` is `.49` or `.99`. This is believed to be a rounding anomaly in the system.

## 5. Key Interaction Effects & Trip Profiles

The most important takeaway is that the rules are not applied independently. The system seems to categorize trips based on a combination of factors.

*   **Good Profile (High Mileage, Low Spending):** Trips with a high number of miles and modest spending (within the optimal daily rates) generally receive favorable reimbursement.
*   **Bad Profile (Low Mileage, High Spending):** Trips with few miles traveled but high expenses are often penalized.
*   **"Sweet Spot Combo" (Guaranteed Bonus):** This specific combination results in a guaranteed bonus:
    *   `trip_duration_days` = 5
    *   `miles_traveled / trip_duration_days` >= 180
    *   `total_receipts_amount / trip_duration_days` < $100
*   **"Vacation Penalty" (Guaranteed Penalty):** This combination results in a guaranteed penalty:
    *   `trip_duration_days` >= 8
    *   High daily spending (likely exceeding the ~$90/day guideline for long trips).