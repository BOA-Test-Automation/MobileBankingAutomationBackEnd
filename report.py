import os
import pandas as pd

def analyze_report():
    base_path = "D:/BOA/Djangoreact/Django/Reserve/report/ARIF PAY 2"
    all_data = []
    result = []

    for month in os.listdir(base_path):
        month_path = os.path.join(base_path, month)
        if os.path.isdir(month_path):
            for file in os.listdir(month_path):
                if file.endswith((".xls", ".xlsx")) and "ARIF PAY" in file:
                    file_path = os.path.join(month_path, file)
                    try:
                        # Read Excel file with correct header position
                        df = pd.read_excel(
                            file_path,
                            sheet_name=0,
                            header=3,  # Header is on row 6 (0-indexed)
                            engine='openpyxl' if file.endswith('.xlsx') else 'xlrd'
                        )
                        
                        # Add metadata
                        df['source_month'] = month
                        df['source_file'] = file
                        all_data.append(df)
                        print(f"✅ Loaded {file}")
                    except Exception as e:
                        print(f"❌ Error loading {file_path}: {str(e)}")

    if not all_data:
        print("No valid files found!")
        return

    # Combine all DataFrames
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 Combined DataFrame shape: {combined_df.shape}")

    # Process the combined data
    for month in combined_df['source_month'].unique():
        month_df = combined_df[combined_df['source_month'] == month].copy()
        
        # Explicitly use "Amount" column (no need for detection)
        amount_column = "Amount"
        
        # Convert amount to numeric
        month_df.loc[:, amount_column] = pd.to_numeric(month_df[amount_column], errors='coerce')
        month_df = month_df.dropna(subset=[amount_column])

        num_txns = len(month_df)
        amount_sum = month_df[amount_column].sum()
        unique_files = month_df['source_file'].nunique()

        print(f"\n📊 {month} Summary:")
        print(f"  - Total Transactions: {num_txns}")
        print(f"  - Total Amount: {amount_sum:.2f} ETB")
        print(f"  - Files Processed: {unique_files}\n")

        result.append({
            "Month": month,
            "Total Files": unique_files,
            "Total Transactions": num_txns,
            "Total Amount (ETB)": amount_sum
        })

    # Save final summary
    summary_df = pd.DataFrame(result)
    summary_df.to_excel("arif_monthly_summary.xlsx", index=False)
    print("📁 Summary saved to 'monthly_summary.xlsx'")

analyze_report()