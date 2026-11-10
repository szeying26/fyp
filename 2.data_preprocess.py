import pandas as pd
import numpy as np

def load_data(filepath):
    """Load data from CSV file."""
    return pd.read_csv(filepath)

def convert_date(df):
    """Convert Date column to datetime, drop invalid dates, and sort rows."""
    df = df.copy()
    if 'Date' not in df.columns:
        raise KeyError("The dataset must contain a 'Date' column.")

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df

def remove_duplicates(df):
    """Remove duplicate rows based on Date."""
    return df.drop_duplicates(subset='Date', keep='first').reset_index(drop=True)

def handle_missing_values(df, method='drop'):
    """Handle missing values by dropping rows or filling numeric columns."""
    df = df.copy()

    if method == 'drop':
        return df.dropna().reset_index(drop=True)
    elif method == 'fill':
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].fillna(df[numeric_columns].mean())
        return df
    return df

def clean_data(filepath, output_filepath):
    """Main cleaning pipeline."""
    df = load_data(filepath)
    df = convert_date(df)
    df = remove_duplicates(df)
    df = handle_missing_values(df, method='drop')
    df.to_csv(output_filepath, index=False)
    print(df.shape)
    return df

if __name__ == "__main__":
    clean_data("malaysia_stocks.csv", "cleaned_malaysia_stocks.csv")
