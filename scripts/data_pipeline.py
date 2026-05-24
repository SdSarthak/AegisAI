import pandas as pd

def load_data(path):
    return pd.read_csv(path)

def clean_data(df):
    df = df.dropna()
    return df

def preprocess_text(df, column):
    df[column] = df[column].str.lower()
    return df

def save_data(df, output_path):
    df.to_csv(output_path, index=False)

if __name__ == "__main__":
    input_file = "data/raw_data.csv"
    output_file = "data/processed_data.csv"

    df = load_data(input_file)
    df = clean_data(df)

    if "text" in df.columns:
        df = preprocess_text(df, "text")

    save_data(df, output_file)

    print("Data pipeline executed successfully.")