# 🔧 Fix for SF.gov API 400 Error

## Problem
The notebook is getting a **400 Bad Request** error when downloading data from the SF.gov API:
```
❌ Error: 400 Client Error: Bad Request for url: https://data.sfgov.org/resource/g8m3-pdis.json?%24limit=50000&%24order=record_id+DESC
```

## Root Cause
The code in **Cell 3** (lines 134-137) is trying to order the API results by `record_id DESC`, but **this field doesn't exist** in the dataset. The API rejects this invalid parameter with a 400 error.

### Current (Broken) Code:
```python
params = {
    "$limit": limit,
    "$order": "record_id DESC"  # ❌ This field doesn't exist!
}
```

## Solution

### Option 1: Remove the $order Parameter (Recommended)
Simply remove the ordering - it's not necessary for the analysis:

```python
params = {
    "$limit": limit
}
```

### Option 2: Order by a Valid Field
If you want to maintain ordering, use a field that actually exists:

```python
params = {
    "$limit": limit,
    "$order": "certificate_number DESC"  # ✅ This field exists
}
```

## Available Fields in the Dataset
Based on the API response, here are the actual fields available:
- `uniqueid`
- `certificate_number`
- `ttxid`
- `ownership_name`
- `dba_name`
- `full_business_address`
- `city`
- `state`
- `business_zip`
- `dba_start_date`
- `dba_end_date`
- `location_start_date`
- `location_end_date`
- `parking_tax`
- `transient_occupancy_tax`
- `location`
- `data_as_of`
- `data_loaded_at`

## How to Fix in Your Notebook

1. **Open the notebook**: `sf_business_risk_prediction.ipynb`

2. **Find Cell 3**: The cell titled "Cell 3: Download Data Functions"

3. **Locate the `download_sf_data` function** (around line 122)

4. **Find the params dictionary** (lines 134-137):
   ```python
   params = {
       "$limit": limit,
       "$order": "record_id DESC"
   }
   ```

5. **Replace it with**:
   ```python
   params = {
       "$limit": limit
   }
   ```

6. **Save the notebook** and **restart the kernel**

7. **Re-run all cells** from the beginning

## Alternative: Use the Fixed Script

I've created a standalone script `fix_api_download.py` with the corrected function. You can:

1. Import it in your notebook:
   ```python
   from fix_api_download import download_sf_data
   ```

2. Or copy the corrected function directly into Cell 3

## Testing the Fix

After making the change, run this test in a new cell:

```python
# Quick test
test_df = download_sf_data(
    'https://data.sfgov.org/resource/g8m3-pdis.json',
    limit=10
)
print(f"✅ Downloaded {len(test_df)} records")
print(f"Columns: {list(test_df.columns)}")
```

If you see records downloaded without errors, the fix is working! 🎉

## Why This Happened

The SF.gov Open Data API uses the Socrata platform. When using the `$order` parameter, you must specify a field that exists in the dataset. The error occurred because:

1. The code assumed there would be a `record_id` field
2. This field doesn't exist in the registered business dataset
3. The API rejected the invalid parameter with a 400 error

## Next Steps

After fixing this issue:
1. The data download should work
2. You'll be able to proceed with the rest of the analysis
3. The same fix may be needed for the other datasets (building permits, code violations) if they also don't have a `record_id` field

---

**Need Help?** If you're still having issues after applying this fix, check:
- Your internet connection
- The SF.gov API status (https://data.sfgov.org)
- Whether you need to increase the timeout value (currently 60 seconds)
