#!/bin/bash

# Black Box Challenge - Test Runner
# This script runs a specific test case from a JSON file and compares the output.
# Usage: ./test.sh <test_case_number (1-based)>

# --- 1. Validate Input and Files ---
if [ -z "$1" ]; then
    echo "Error: No test case number provided."
    echo "Usage: $0 <test_case_number (1-based)>"
    exit 1
fi

# Check if input is a positive integer
if ! [[ "$1" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: Test case number must be a positive integer."
    echo "Usage: $0 <test_case_number (1-based)>"
    exit 1
fi

USER_PROVIDED_INDEX=$1
TEST_CASE_INDEX=$((USER_PROVIDED_INDEX - 1))
JSON_FILE="public_cases.json"

if [ ! -f "$JSON_FILE" ]; then
    echo "Error: Test case file not found at '$JSON_FILE'"
    exit 1
fi

# --- 2. Extract Test Case Data with jq ---
TEST_CASE=$(jq ".[$TEST_CASE_INDEX]" "$JSON_FILE")

if [ "null" == "$TEST_CASE" ]; then
    echo "Error: Test case number $USER_PROVIDED_INDEX is out of bounds."
    # Get array length for a better error message
    ARRAY_LENGTH=$(jq 'length' "$JSON_FILE")
    echo "Valid range is from 1 to ${ARRAY_LENGTH}."
    exit 1
fi

# Extract individual values
TRIP_DURATION=$(echo "$TEST_CASE" | jq '.input.trip_duration_days')
MILES_TRAVELED=$(echo "$TEST_CASE" | jq '.input.miles_traveled')
RECEIPTS_AMOUNT=$(echo "$TEST_CASE" | jq '.input.total_receipts_amount')
EXPECTED_OUTPUT=$(echo "$TEST_CASE" | jq '.expected_output')

echo "--- Running Test Case #${USER_PROVIDED_INDEX} ---"
echo "  Duration: ${TRIP_DURATION} days"
echo "  Miles:    ${MILES_TRAVELED}"
echo "  Receipts: \$${RECEIPTS_AMOUNT}"
echo "-----------------------------------"
echo "Running script with --debug to get trace and result..."

# --- 3. Run the Calculation and Extract Result ---
# Run with --debug and capture the full output
DEBUG_OUTPUT=$(python3 calculate_reimbursement.py "$TRIP_DURATION" "$MILES_TRAVELED" "$RECEIPTS_AMOUNT" --debug)

# Extract the final reimbursement value from the last line of the trace.
# The line looks like: "FINAL: Total reimbursement: $123.45"
# We grep for the line, then use sed to extract the number.
ACTUAL_OUTPUT=$(echo "$DEBUG_OUTPUT" | grep "FINAL: Total reimbursement:" | sed 's/FINAL: Total reimbursement: \$//')

# --- 4. Compare Results ---
echo "Expected:   \$${EXPECTED_OUTPUT}"
echo "Actual:     \$${ACTUAL_OUTPUT}"
echo "-----------------------------------"

if [ -z "$ACTUAL_OUTPUT" ]; then
    echo "❌ FAILED: Could not extract actual output from the script."
    echo "Full debug output:"
    echo "$DEBUG_OUTPUT"
    exit 1
fi

# Using bc for floating point comparison. Note that bc returns 1 for true and 0 for false.
if (( $(echo "$ACTUAL_OUTPUT == $EXPECTED_OUTPUT" | bc -l) )); then
    echo "✅ PASSED: Output matches expected value."
else
    echo "❌ FAILED: Output does not match expected value."
    DIFFERENCE=$(echo "$EXPECTED_OUTPUT - $ACTUAL_OUTPUT" | bc)
    echo "   Difference: \$$DIFFERENCE"
fi

# --- 5. Show Full Debug Output ---
echo ""
echo "--- Full Debug Trace ---"
echo "$DEBUG_OUTPUT"