import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.preprocessing import label_binarize


def plot_loss_curve(train_loss, val_loss, title="Training vs Validation Loss"):
    plt.figure(figsize=(8, 5))

    plt.plot(train_loss, label="Train Loss")
    plt.plot(val_loss, label="Validation Loss")

    plt.xlabel("Iteration / Epoch")
    plt.ylabel("Loss")
    plt.title(title)

    plt.legend()
    plt.grid(True)
    plt.show()


def plot_roc_auc_curve(y_true, y_score, classes=None, pos_label=None, title="ROC Curve"):
    """
    Plot an ROC curve with AUC.

    Binary classification: pass a 1-D `y_score` (probability/score of the
    positive class) and leave `classes` as None. Pass `pos_label` if the
    positive class isn't the "larger" of the two labels.

    Multiclass classification: pass `y_score` as a 2-D array of per-class
    probabilities, shape (n_samples, n_classes), and `classes` as the list
    of class labels in the same column order as `y_score` (e.g.
    `model.classes_`). One one-vs-rest curve is drawn per class.
    """
    plt.figure(figsize=(7, 6))

    if classes is None:
        fpr, tpr, _ = roc_curve(y_true, y_score, pos_label=pos_label)
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, label=f"ROC curve (AUC = {roc_auc:.3f})")
    else:
        y_true_bin = label_binarize(y_true, classes=classes)
        y_score = np.asarray(y_score)
        for i, cls in enumerate(classes):
            fpr, tpr, _ = roc_curve(y_true_bin[:, i], y_score[:, i])
            roc_auc = auc(fpr, tpr)
            plt.plot(fpr, tpr, label=f"{cls} (AUC = {roc_auc:.3f})")

    plt.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Chance")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_precision_recall_curve(
    y_true, y_score, classes=None, pos_label=None, title="Precision-Recall Curve"
):
    """
    Plot a precision-recall curve with average precision (AP).

    Binary classification: pass a 1-D `y_score` and leave `classes` as None.
    Pass `pos_label` if the positive class isn't the "larger" of the two
    labels.

    Multiclass classification: pass `y_score` as a 2-D array of per-class
    probabilities, shape (n_samples, n_classes), and `classes` as the list
    of class labels in the same column order as `y_score` (e.g.
    `model.classes_`). One one-vs-rest curve is drawn per class.
    """
    plt.figure(figsize=(7, 6))

    if classes is None:
        precision, recall, _ = precision_recall_curve(y_true, y_score, pos_label=pos_label)
        avg_precision = average_precision_score(y_true, y_score, pos_label=pos_label)
        plt.plot(recall, precision, label=f"AP = {avg_precision:.3f}")
    else:
        y_true_bin = label_binarize(y_true, classes=classes)
        y_score = np.asarray(y_score)
        for i, cls in enumerate(classes):
            precision, recall, _ = precision_recall_curve(y_true_bin[:, i], y_score[:, i])
            avg_precision = average_precision_score(y_true_bin[:, i], y_score[:, i])
            plt.plot(recall, precision, label=f"{cls} (AP = {avg_precision:.3f})")

    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.show()
