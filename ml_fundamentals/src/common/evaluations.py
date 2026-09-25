from sklearn.metrics import (
    r2_score,
    mean_absolute_error,
    root_mean_squared_error,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


def evaluate_regression(model, X_te, y_te):
    y_pred = model.predict(X_te)
    return {
        "r2": r2_score(y_te, y_pred),
        "mae": mean_absolute_error(y_te, y_pred),
        "rmse": root_mean_squared_error(y_te, y_pred),
    }


def evaluate_classification(model, X_te, y_te, binary):
    y_pred = model.predict(X_te)
    metrics = {
        "accuracy": accuracy_score(y_te, y_pred),
        "f1_macro": f1_score(y_te, y_pred, average="macro", zero_division=0),
        "precision_macro": precision_score(
            y_te, y_pred, average="macro", zero_division=0
        ),
        "recall_macro": recall_score(y_te, y_pred, average="macro", zero_division=0),
        # Weighted averages
        "precision_weighted": precision_score(
            y_te, y_pred, average="weighted", zero_division=0
        ),
        "recall_weighted": recall_score(
            y_te, y_pred, average="weighted", zero_division=0
        ),
        "f1_weighted": f1_score(y_te, y_pred, average="weighted", zero_division=0),
        # Confusion Matrix
        "confusion_matrix": confusion_matrix(y_te, y_pred),
    }
    if binary and hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_te)[:, 1]
        metrics["roc_auc"] = roc_auc_score(y_te, y_prob)

    print(classification_report(y_te, y_pred))
    return metrics
