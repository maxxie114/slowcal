"""
Quick test to verify the API fix works
"""
import requests
import pandas as pd

print("🧪 Testing the fixed API call...")
print("="*60)

url = 'https://data.sfgov.org/resource/g8m3-pdis.json'
params = {
    "$limit": 10  # Small test
}

try:
    print(f"⬇️ Downloading from {url}...")
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    
    data = response.json()
    df = pd.DataFrame(data)
    
    print(f"✅ SUCCESS! Downloaded {len(df)} records")
    print(f"\n📋 Columns available:")
    for col in df.columns:
        print(f"   - {col}")
    
    print(f"\n👀 Sample data:")
    print(df[['certificate_number', 'dba_name', 'city', 'dba_start_date']].head())
    
    print("\n" + "="*60)
    print("✅ The API is working correctly!")
    print("="*60)
    print("\n🎯 Your notebook should now work. Next steps:")
    print("   1. Reload the notebook in your editor")
    print("   2. Restart the kernel")
    print("   3. Run all cells from the beginning")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nIf you're still getting errors, check your internet connection.")
