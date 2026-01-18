import json

def calculate_calories(sex, age, weight_kg, avg_hr, total_time_min):
    if sex == "Male":
        # Calories per minute = [(-55.0969 + (0.6309 × avg_hr) + (0.1988 × weight_kg) + (0.2017 × age)) / 4.184]
        cpm = (-55.0969 + (0.6309 * avg_hr) + (0.1988 * weight_kg) + (0.2017 * age)) / 4.184
    else:
        # Calories per minute = [(-20.4022 + (0.4472 × avg_hr) - (0.1263 × weight_kg) + (0.074 × age)) / 4.184]
        cpm = (-20.4022 + (0.4472 * avg_hr) - (0.1263 * weight_kg) + (0.074 * age)) / 4.184
    
    return round(cpm * total_time_min, 2)

def verify_calories():
    print("Verifying Calorie Calculation Logic...")
    
    # Test Case 1: Male
    # Age: 30, Weight: 80kg, HR: 140 bpm, Time: 20 mins
    # Formula: ((-55.0969 + (0.6309 * 140) + (0.1988 * 80) + (0.2017 * 30)) / 4.184) * 20
    # Numerator: -55.0969 + 88.326 + 15.904 + 6.051 = 55.1841
    # CPM: 55.1841 / 4.184 = 13.189
    # Total: 13.189 * 20 = 263.78
    
    cal_m = calculate_calories("Male", 30, 80, 140, 20)
    print(f"Male Test: {cal_m} kcal (Expected: ~263.78)")
    assert 263 < cal_m < 264
    
    # Test Case 2: Female
    # Age: 30, Weight: 60kg, HR: 140 bpm, Time: 20 mins
    # Formula: ((-20.4022 + (0.4472 * 140) - (0.1263 * 60) + (0.074 * 30)) / 4.184) * 20
    # Numerator: -20.4022 + 62.608 - 7.578 + 2.22 = 36.8478
    # CPM: 36.8478 / 4.184 = 8.806
    # Total: 8.806 * 20 = 176.13
    
    cal_f = calculate_calories("Female", 30, 60, 140, 20)
    print(f"Female Test: {cal_f} kcal (Expected: ~176.13)")
    assert 176 < cal_f < 177
    
    print("\nSUCCESS: Logic verification passed.")

if __name__ == "__main__":
    verify_calories()
