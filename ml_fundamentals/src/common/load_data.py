import pandas as pd
from sklearn.model_selection import train_test_split


def load_data(data_path: str):
    df = pd.read_csv(data_path)
    df = df.drop(columns=["Unnamed: 0"])
    # convert the columns names into lowercase and trim extra spaces
    df.columns = [col.lower().strip() for col in df.columns]
    print(df.duplicated().sum())
    return df


def drop_targets(df: pd.DataFrame):
    X = df.drop(columns=["approved_flag", "credit_score"])
    y_lin_reg = df["credit_score"]
    y_multiclass = df["approved_flag"].astype(str)

    binary_map = {"P1": 1, "P2": 1, "P3": 0, "P4": 0}
    y_binary = df["approved_flag"].map(binary_map)

    assert y_binary.isna().sum() == 0, "approved_flag has values outside P1-P4"

    return X, y_lin_reg, y_binary, y_multiclass


def get_test_val_sets(X: pd.DataFrame, y: pd.DataFrame, test_size: float):
    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
    )
    X_val, X_Test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        random_state=42,
    )
    return (X_train, X_val, X_Test, y_train, y_val, y_test)


def get_test_sets(X: pd.DataFrame, y: pd.DataFrame, test_size: float):
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.15,
        random_state=42,
    )
    return (X_train, X_test, y_train, y_test)
