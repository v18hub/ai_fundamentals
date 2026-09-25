"""
Tabular data preprocessing pipeline.

Fixes vs. the original script:
    * Statistics (medians, "no enquiry" fill value, encoder/scaler params) are
      now computed on X_train ONLY and re-applied to X_val / X_test. The
      original code computed a separate median / fill value per split, which
      leaks split-specific information and makes val/test preprocessing
      inconsistent with train.
    * `_log_transform` now actually drops the original column
      (the original called `df.drop(...)` without `inplace=True` or
      reassignment, so the source column was silently never removed).
    * The log transform is applied consistently to train, val, AND test
      (the original forgot to call it on X_test).
    * `.fillna(..., inplace=True)` on a DataFrame slice (which can silently
      no-op / raise `SettingWithCopyWarning`) is replaced with direct
      assignment.
    * Every stage validates its inputs (missing columns, empty frames,
      non-numeric columns passed to numeric-only ops, etc.) and raises a
      clear, specific exception instead of failing deep inside pandas/sklearn.
    * Structured as a fit/transform class so it can be reused on new data
      (e.g. at inference time) without duplicating logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

try:
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor

    _STATSMODELS_AVAILABLE = True
except ImportError:  # statsmodels is optional; only needed for VIF
    _STATSMODELS_AVAILABLE = False

logger = logging.getLogger(__name__)
if not logger.handlers:
    # Sensible default so the module logs something even if the host
    # application hasn't configured logging itself.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class PreprocessingError(Exception):
    """Base class for all errors raised by this module."""


class MissingColumnsError(PreprocessingError):
    """Raised when expected columns are absent from a DataFrame."""

    def __init__(self, missing: List[str], context: str):
        self.missing = missing
        self.context = context
        super().__init__(f"Missing column(s) {missing} required for '{context}'.")


class EmptyDataFrameError(PreprocessingError):
    """Raised when an operation receives a DataFrame with no rows."""


class NotFittedError(PreprocessingError):
    """Raised when `.transform()` is called before `.fit()`."""


# --------------------------------------------------------------------------- #
# Small validation helpers
# --------------------------------------------------------------------------- #
def _check_columns_exist(df: pd.DataFrame, columns: List[str], context: str) -> None:
    """Raise MissingColumnsError if any of `columns` is not in `df`."""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise MissingColumnsError(missing, context)


def _check_not_empty(df: pd.DataFrame, context: str) -> None:
    """Raise EmptyDataFrameError if `df` has zero rows."""
    if df.shape[0] == 0:
        raise EmptyDataFrameError(f"DataFrame passed to '{context}' has 0 rows.")


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass
class PreprocessConfig:
    """Column groups and constants driving the pipeline."""

    high_missing: List[str] = field(default_factory=list)  # columns to drop entirely
    median_cols: List[str] = field(default_factory=list)  # sentinel -> train median
    zero_cols: List[str] = field(default_factory=list)  # sentinel -> 0
    log_transform_cols: List[str] = field(default_factory=list)  # numeric -> log1p
    recent_enq_col: str = "time_since_recent_enq"
    missing_sentinel: int = -99999


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
class TabularPreprocessor:
    """
    Fit/transform preprocessing pipeline for train/val/test tabular splits.

    Usage
    -----
        cfg = PreprocessConfig(
            high_missing=[...], median_cols=[...],
            zero_cols=[...], log_transform_cols=[...],
        )
        pre = TabularPreprocessor(cfg)
        X_train_p, X_val_p, X_test_p = pre.fit_transform(X_train, X_val, X_test)

    All statistics used to fill missing values, plus the fitted
    StandardScaler / OneHotEncoder, are learned from X_train only and then
    reused for X_val / X_test to avoid data leakage.
    """

    def __init__(self, config: PreprocessConfig):
        self.config = config
        self._is_fitted = False

        # Learned during fit()
        self._train_medians: dict = {}
        self._recent_enq_fill_value: Optional[float] = None
        self._column_transformer: Optional[ColumnTransformer] = None

    # ------------------------------------------------------------------ #
    # Stage 1: drop high-missing columns
    # ------------------------------------------------------------------ #
    def _drop_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = [c for c in self.config.high_missing if c in df.columns]
        skipped = set(self.config.high_missing) - set(cols)
        if skipped:
            logger.warning(
                "Columns %s listed in high_missing were not found; skipping.",
                sorted(skipped),
            )
        return df.drop(columns=cols)

    # ------------------------------------------------------------------ #
    # Stage 2: sentinel -> median (median learned on train only)
    # ------------------------------------------------------------------ #
    def _fit_medians(self, df: pd.DataFrame) -> None:
        _check_columns_exist(df, self.config.median_cols, "median fill (fit)")
        for col in self.config.median_cols:
            cleaned = df[col].replace(self.config.missing_sentinel, np.nan)
            median_value = cleaned.median()
            if pd.isna(median_value):
                raise PreprocessingError(
                    f"Column '{col}' is entirely missing/sentinel in the "
                    f"training set; cannot compute a median to fill it with."
                )
            self._train_medians[col] = median_value
            logger.info("Fitted median for '%s' = %s", col, median_value)

    def _apply_medians(self, df: pd.DataFrame) -> pd.DataFrame:
        _check_columns_exist(df, self.config.median_cols, "median fill (transform)")
        df = df.copy()
        for col in self.config.median_cols:
            fill_value = self._train_medians.get(col)
            if fill_value is None:
                raise NotFittedError(
                    f"No fitted median found for column '{col}'. Call fit() first."
                )
            df[col] = df[col].replace(self.config.missing_sentinel, np.nan)
            df[col] = df[col].fillna(fill_value)
        return df

    # ------------------------------------------------------------------ #
    # Stage 3: sentinel -> 0
    # ------------------------------------------------------------------ #
    def _replace_with_zero(self, df: pd.DataFrame) -> pd.DataFrame:
        _check_columns_exist(df, self.config.zero_cols, "zero fill")
        df = df.copy()
        df[self.config.zero_cols] = df[self.config.zero_cols].replace(
            self.config.missing_sentinel, 0
        )
        return df

    # ------------------------------------------------------------------ #
    # Stage 4: "no enquiry" sentinel handling on a single time column
    # ------------------------------------------------------------------ #
    def _fit_recent_enq(self, df: pd.DataFrame) -> None:
        col = self.config.recent_enq_col
        if col not in df.columns:
            logger.warning("'%s' not present; skipping no-enquiry handling.", col)
            self._recent_enq_fill_value = None
            return

        mask = df[col] == self.config.missing_sentinel
        observed = df.loc[~mask, col]
        if observed.empty:
            raise PreprocessingError(
                f"Every value in '{col}' is the missing sentinel "
                f"({self.config.missing_sentinel}); cannot derive a "
                f"'longer than the longest observed gap' fill value."
            )
        # Semantically: "no enquiry ever" should read as *longer* than any
        # observed gap, not as an arbitrary interpolated value.
        self._recent_enq_fill_value = observed.max() + 1
        logger.info(
            "Fitted no-enquiry fill value for '%s' = %s",
            col,
            self._recent_enq_fill_value,
        )

    def _apply_recent_enq(self, df: pd.DataFrame) -> pd.DataFrame:
        col = self.config.recent_enq_col
        if col not in df.columns or self._recent_enq_fill_value is None:
            return df  # nothing to do, already warned during fit

        df = df.copy()
        mask = df[col] == self.config.missing_sentinel
        df["no_enquiry_flag"] = mask.astype(int)
        df[col] = df[col].replace(
            self.config.missing_sentinel, self._recent_enq_fill_value
        )
        return df

    # ------------------------------------------------------------------ #
    # Stage 5: log1p transform (adds `<col>_log`, drops the original)
    # ------------------------------------------------------------------ #
    def _log_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.config.log_transform_cols:
            return df
        _check_columns_exist(df, self.config.log_transform_cols, "log transform")
        df = df.copy()
        for col in self.config.log_transform_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise PreprocessingError(
                    f"Cannot log-transform non-numeric column '{col}'."
                )
            if (df[col] < -1).any():
                raise PreprocessingError(
                    f"Column '{col}' has values < -1; log1p is undefined "
                    f"there. Clean/clip the column before log-transforming."
                )
            df[f"{col}_log"] = np.log1p(df[col])
            df = df.drop(columns=[col])  # actually drop the original column
        return df

    # ------------------------------------------------------------------ #
    # Stage 6: scale numeric / one-hot encode categorical
    # ------------------------------------------------------------------ #
    def _fit_column_transformer(self, df: pd.DataFrame) -> None:
        numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
        categorical_columns = df.select_dtypes(include="object").columns.tolist()

        if not numeric_columns and not categorical_columns:
            raise PreprocessingError(
                "No numeric or categorical columns found to fit the "
                "ColumnTransformer on."
            )

        self._column_transformer = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_columns),
                (
                    "cat",
                    OneHotEncoder(
                        handle_unknown="ignore", drop="first", sparse_output=False
                    ),
                    categorical_columns,
                ),
            ]
        )
        try:
            self._column_transformer.fit(df)
        except Exception as exc:  # re-raise with more context
            raise PreprocessingError(f"Failed to fit ColumnTransformer: {exc}") from exc

        logger.info(
            "Fitted ColumnTransformer on %d numeric and %d categorical columns.",
            len(numeric_columns),
            len(categorical_columns),
        )

    def _transform_columns(self, df: pd.DataFrame) -> np.ndarray:
        if self._column_transformer is None:
            raise NotFittedError("ColumnTransformer not fitted. Call fit() first.")
        try:
            return self._column_transformer.transform(df)
        except Exception as exc:
            raise PreprocessingError(
                f"Failed to transform data with fitted ColumnTransformer: {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Public: shared pre-encoding pipeline (drop / median / zero / enq / log)
    # ------------------------------------------------------------------ #
    def _run_common_stages(self, df: pd.DataFrame, split_name: str) -> pd.DataFrame:
        _check_not_empty(df, split_name)
        df = self._drop_columns(df)
        df = self._apply_medians(df)
        df = self._replace_with_zero(df)
        df = self._apply_recent_enq(df)
        df = self._log_transform(df)
        return df

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def fit(self, X_train: pd.DataFrame) -> "TabularPreprocessor":
        """Learn all fill values / scaling / encoding statistics from X_train."""
        _check_not_empty(X_train, "X_train")

        df = self._drop_columns(X_train)
        self._fit_medians(df)
        df = self._apply_medians(df)
        df = self._replace_with_zero(df)
        self._fit_recent_enq(df)
        df = self._apply_recent_enq(df)
        df = self._log_transform(df)
        self._fit_column_transformer(df)

        self._is_fitted = True
        logger.info("TabularPreprocessor fit complete.")
        return self

    def transform(self, X: pd.DataFrame, split_name: str = "data") -> np.ndarray:
        """Apply the fitted pipeline to a new split (val/test/inference)."""
        if not self._is_fitted:
            raise NotFittedError("Call fit() before transform().")
        df = self._run_common_stages(X, split_name)
        return self._transform_columns(df)

    def fit_transform(
        self, X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Fit on X_train, then transform train/val/test consistently."""
        self.fit(X_train)
        X_train_processed = self.transform(X_train, "X_train")
        X_val_processed = self.transform(X_val, "X_val")
        X_test_processed = self.transform(X_test, "X_test")
        logger.info("Data processing complete! Ready for model training.")
        return X_train_processed, X_val_processed, X_test_processed

    # ------------------------------------------------------------------ #
    # VIF support
    # ------------------------------------------------------------------ #
    def get_feature_names(self) -> List[str]:
        """Column names of the fitted ColumnTransformer's output, in order."""
        if self._column_transformer is None:
            raise NotFittedError("ColumnTransformer not fitted. Call fit() first.")
        try:
            return list(self._column_transformer.get_feature_names_out())
        except Exception as exc:
            raise PreprocessingError(
                f"Could not retrieve feature names from ColumnTransformer: {exc}"
            ) from exc

    def transform_numeric_df(
        self, X: pd.DataFrame, split_name: str = "data"
    ) -> pd.DataFrame:
        """
        Run the fitted pipeline on `X` and return ONLY the scaled numeric
        block as a DataFrame with real column names.

        Intended for diagnostics like VIF, where one-hot dummy columns
        should generally be excluded (dummies are trivially collinear with
        each other, which inflates VIF without telling you anything about
        genuine numeric multicollinearity).
        """
        processed = self.transform(X, split_name)  # full (num + cat) array
        all_names = self.get_feature_names()
        full_df = pd.DataFrame(processed, columns=all_names, index=X.index)

        numeric_names = [c for c in all_names if c.startswith("num__")]
        if not numeric_names:
            raise PreprocessingError(
                "No numeric columns found in the fitted ColumnTransformer's "
                "output; nothing to compute VIF on."
            )
        return full_df[numeric_names]

    def compute_vif(self, X: pd.DataFrame, split_name: str = "data") -> pd.DataFrame:
        """
        Compute Variance Inflation Factor for each scaled numeric feature.

        Parameters
        ----------
        X : the raw (pre-preprocessing) DataFrame to score, e.g. X_train.
        split_name : label used only in error/log messages.

        Returns
        -------
        DataFrame with columns ['feature', 'VIF'], sorted descending by VIF.

        Raises
        ------
        PreprocessingError
            If statsmodels isn't installed, fewer than 2 numeric columns are
            available, or the design matrix is singular (perfectly
            collinear columns -> VIF is undefined / infinite).
        """
        if not _STATSMODELS_AVAILABLE:
            raise PreprocessingError(
                "statsmodels is required for VIF calculation. "
                "Install it with `pip install statsmodels`."
            )

        numeric_df = self.transform_numeric_df(X, split_name)

        if numeric_df.shape[1] < 2:
            raise PreprocessingError(
                f"Need at least 2 numeric columns to compute VIF, got "
                f"{numeric_df.shape[1]}."
            )

        # Drop any column with (near) zero variance -- these make the
        # design matrix singular and blow up VIF to inf/NaN.
        near_constant = numeric_df.columns[numeric_df.std() < 1e-8].tolist()
        if near_constant:
            logger.warning(
                "Dropping near-constant column(s) before VIF: %s", near_constant
            )
            numeric_df = numeric_df.drop(columns=near_constant)

        if numeric_df.shape[1] < 2:
            raise PreprocessingError(
                "Fewer than 2 non-constant numeric columns remain after "
                "dropping near-constant columns; cannot compute VIF."
            )

        if numeric_df.isnull().any().any():
            raise PreprocessingError(
                "NaNs found in the numeric block passed to VIF; check the "
                "imputation stages upstream."
            )

        # IMPORTANT: statsmodels' variance_inflation_factor assumes the
        # regression it runs internally includes an intercept. Without an
        # explicit constant column, it silently fits a no-intercept
        # regression, which understates VIF for any data that isn't
        # centered at exactly zero -- and val/test won't be exactly
        # zero-centered here, since they're scaled using train's mean/std,
        # not their own. Skipping this step gives artificially low,
        # split-inconsistent VIF values.
        design = sm.add_constant(numeric_df, has_constant="add")
        values = design.to_numpy()
        records = []
        # Column 0 is the constant we just added; skip it, but pass the
        # full `values` matrix (constant included) into the VIF call --
        # that's what makes the underlying regression include an intercept.
        for i, col in enumerate(numeric_df.columns, start=1):
            try:
                vif = variance_inflation_factor(values, i)
            except Exception as exc:
                logger.warning(
                    "VIF computation failed for column '%s' (likely a "
                    "singular/near-singular design matrix): %s",
                    col,
                    exc,
                )
                vif = np.nan
            records.append({"feature": col, "VIF": vif})

        result = pd.DataFrame(records).sort_values(
            "VIF", ascending=False, na_position="last"
        )
        result = result.reset_index(drop=True)
        return result

    def compare_vif_across_splits(
        self,
        X_train: pd.DataFrame,
        X_val: pd.DataFrame,
        X_test: pd.DataFrame,
        flag_threshold: float = 10.0,
        jump_ratio: float = 2.0,
    ) -> pd.DataFrame:
        """
        Compute VIF separately on train/val/test (all using train's fitted
        scaler -- no leakage) and flag features whose multicollinearity
        looks fine in train but is notably worse in val/test. That pattern
        usually means the *relationship between features* has shifted
        between splits, not that anything is wrong with the fit itself.

        Parameters
        ----------
        flag_threshold : a split's VIF above this value is considered
            "problematic" on its own (10 is the common rule-of-thumb cutoff).
        jump_ratio : a feature is flagged as "shifted" if VIF_val or
            VIF_test is at least this many times larger than VIF_train
            (guards against comparing 1.01 -> 1.3, which is noise, not shift).

        Returns
        -------
        DataFrame with one row per feature and columns:
            ['feature', 'VIF_train', 'VIF_val', 'VIF_test', 'flag']
        where 'flag' explains *why* a row was flagged, or is empty if none
        of the checks tripped. Features missing from a split (e.g. dropped
        there for near-zero variance) show up as NaN for that split's VIF,
        with a note in 'flag' rather than a silent gap.
        """
        vif_frames = {}
        for name, split in (("train", X_train), ("val", X_val), ("test", X_test)):
            try:
                vif_frames[name] = self.compute_vif(split, f"X_{name}").set_index(
                    "feature"
                )["VIF"]
            except PreprocessingError as exc:
                # Don't let one split's failure (e.g. too few numeric cols)
                # kill the whole comparison -- report it and continue.
                logger.warning("VIF computation failed for split '%s': %s", name, exc)
                vif_frames[name] = pd.Series(dtype=float)

        merged = pd.DataFrame(
            {
                "VIF_train": vif_frames["train"],
                "VIF_val": vif_frames["val"],
                "VIF_test": vif_frames["test"],
            }
        )

        if merged.empty:
            raise PreprocessingError(
                "No features could be compared across splits (VIF failed "
                "for every split)."
            )

        def _flag(row: pd.Series) -> str:
            reasons = []
            missing = [c for c, v in row.items() if pd.isna(v)]
            if missing:
                reasons.append(f"missing in {missing}")

            train_vif = row["VIF_train"]
            for split_name, col in (("val", "VIF_val"), ("test", "VIF_test")):
                split_vif = row[col]
                if pd.isna(split_vif) or pd.isna(train_vif):
                    continue
                if split_vif >= flag_threshold and train_vif < flag_threshold:
                    reasons.append(
                        f"clean in train ({train_vif:.1f}) but high in {split_name} ({split_vif:.1f})"
                    )
                elif (
                    train_vif > 0
                    and split_vif / train_vif >= jump_ratio
                    and split_vif >= flag_threshold / 2
                ):
                    reasons.append(
                        f"VIF jumped {split_vif / train_vif:.1f}x from train to {split_name}"
                    )
            return "; ".join(reasons)

        merged["flag"] = merged.apply(_flag, axis=1)
        merged = merged.reset_index().rename(columns={"index": "feature"})
        merged = merged.sort_values(
            by=["flag", "VIF_train"],
            key=lambda s: s if s.name != "flag" else s.eq("").astype(int),
        )
        merged = merged.reset_index(drop=True)

        n_flagged = (merged["flag"] != "").sum()
        if n_flagged:
            logger.warning(
                "%d feature(s) show train-vs-val/test multicollinearity "
                "shift; inspect the 'flag' column.",
                n_flagged,
            )
        else:
            logger.info("No train-vs-val/test VIF shift detected.")

        return merged


# --------------------------------------------------------------------------- #
# Tree-model configuration
# --------------------------------------------------------------------------- #
@dataclass
class TreePreprocessConfig:
    """
    Settings for `TreeModelPreprocessor`.

    Unlike `PreprocessConfig` (built for linear/logistic regression), this
    intentionally does NOT scale numeric features or one-hot encode
    categoricals: tree splits are invariant to monotonic transforms of a
    single feature, so `StandardScaler` changes nothing except runtime, and
    one-hot encoding just fragments a categorical into many low-information
    binary splits that trees generally handle worse than a single
    ordinal-encoded (or native-categorical) column.
    """

    missing_sentinel: int = -99999
    # Columns whose null fraction (computed on train, AFTER the sentinel is
    # treated as missing) exceeds this are dropped entirely.
    null_threshold: float = 0.98
    # How to turn categorical (object/category dtype) columns into numbers:
    #   "ordinal"  -> sklearn OrdinalEncoder (works with any sklearn tree:
    #                 RandomForest, GradientBoosting, HistGradientBoosting, ...)
    #   "category" -> cast to pandas 'category' dtype and leave as-is
    #                 (for LightGBM / CatBoost, which consume categoricals
    #                 natively and can split on them directly)
    #   "none"     -> leave columns untouched (e.g. feeding CatBoost's Pool
    #                 with an explicit cat_features list, which wants raw
    #                 strings, not encoded numbers)
    categorical_encoding: str = "ordinal"

    def __post_init__(self):
        if not 0.0 < self.null_threshold <= 1.0:
            raise ValueError(
                f"null_threshold must be in (0, 1], got {self.null_threshold}."
            )
        valid_encodings = {"ordinal", "category", "none"}
        if self.categorical_encoding not in valid_encodings:
            raise ValueError(
                f"categorical_encoding must be one of {sorted(valid_encodings)}, "
                f"got '{self.categorical_encoding}'."
            )


# --------------------------------------------------------------------------- #
# Tree-model preprocessor
# --------------------------------------------------------------------------- #
class TreeModelPreprocessor:
    """
    Lightweight fit/transform preprocessor for tree-based models (random
    forest, gradient boosting, XGBoost, LightGBM, CatBoost, ...).

    Differences from `TabularPreprocessor`, by design:
        * No `StandardScaler` -- trees split on raw thresholds, so scaling
          is a no-op for model quality and only costs you interpretability
          of the original units.
        * No median/zero imputation -- many tree libraries (XGBoost,
          LightGBM, HistGradientBoostingClassifier) natively learn a
          direction to send missing values in during a split, which is
          often more informative than an imputed constant. So the sentinel
          is mapped to a real `NaN` and left there, not filled in.
        * Columns that are almost entirely missing (> `null_threshold` on
          train) are dropped outright, since a column that's 95%+ null
          carries little a tree can split on and mostly adds noise/overfit
          risk.
        * Categorical handling is the "encode categories, don't explode
          them" option (ordinal or native-category), rather than one-hot.

    All statistics (which columns to drop, encoder categories) are learned
    from X_train only and reapplied to X_val / X_test, for the same reason
    as `TabularPreprocessor`: whatever you compute at training time has to
    be reproducible at inference time from a single incoming row, which
    rules out re-deriving anything from val/test itself.
    """

    def __init__(self, config: TreePreprocessConfig):
        self.config = config
        self._is_fitted = False

        # Learned during fit()
        self._dropped_columns: List[str] = []
        self._categorical_columns: List[str] = []
        self._categorical_encoder: Optional[OrdinalEncoder] = None

    # ------------------------------------------------------------------ #
    # Sentinel -> NaN (shared by fit and transform)
    # ------------------------------------------------------------------ #
    def _sentinel_to_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        # `replace` is elementwise and dtype-aware: it only touches numeric
        # cells that literally equal the sentinel, so string/category
        # columns are left alone even though the same call covers the
        # whole DataFrame.
        return df.replace(self.config.missing_sentinel, np.nan)

    # ------------------------------------------------------------------ #
    # Fit: decide which columns to drop, fit the categorical encoder
    # ------------------------------------------------------------------ #
    def fit(self, X_train: pd.DataFrame) -> "TreeModelPreprocessor":
        _check_not_empty(X_train, "X_train")

        df = self._sentinel_to_nan(X_train)

        null_fraction = df.isnull().mean()
        self._dropped_columns = null_fraction[
            null_fraction > self.config.null_threshold
        ].index.tolist()

        if self._dropped_columns:
            logger.info(
                "Dropping %d column(s) with > %.0f%% nulls (train): %s",
                len(self._dropped_columns),
                self.config.null_threshold * 100,
                self._dropped_columns,
            )
        else:
            logger.info(
                "No columns exceeded the %.0f%% null threshold; none dropped.",
                self.config.null_threshold * 100,
            )

        df = df.drop(columns=self._dropped_columns)

        self._categorical_columns = df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()

        if self._categorical_columns and self.config.categorical_encoding == "ordinal":
            try:
                # encoded_missing_value keeps NaN as NaN through the encoder
                # instead of erroring (sklearn >= 1.1).
                self._categorical_encoder = OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                    encoded_missing_value=-2,
                )
            except TypeError:
                # Older sklearn without encoded_missing_value support.
                self._categorical_encoder = OrdinalEncoder(
                    handle_unknown="use_encoded_value", unknown_value=-1
                )
            try:
                self._categorical_encoder.fit(df[self._categorical_columns])
            except Exception as exc:
                raise PreprocessingError(
                    f"Failed to fit OrdinalEncoder on categorical columns "
                    f"{self._categorical_columns}: {exc}"
                ) from exc
            logger.info(
                "Fitted OrdinalEncoder on %d categorical column(s): %s",
                len(self._categorical_columns),
                self._categorical_columns,
            )

        self._is_fitted = True
        logger.info("TreeModelPreprocessor fit complete.")
        return self

    # ------------------------------------------------------------------ #
    # Transform: apply drop / sentinel->NaN / categorical encoding
    # ------------------------------------------------------------------ #
    def transform(self, X: pd.DataFrame, split_name: str = "data") -> pd.DataFrame:
        if not self._is_fitted:
            raise NotFittedError("Call fit() before transform().")
        _check_not_empty(X, split_name)

        df = X.copy()

        cols_to_drop = [c for c in self._dropped_columns if c in df.columns]
        missing_from_split = set(self._dropped_columns) - set(cols_to_drop)
        if missing_from_split:
            logger.warning(
                "Column(s) %s were already absent from '%s'; nothing to drop.",
                sorted(missing_from_split),
                split_name,
            )
        df = df.drop(columns=cols_to_drop)

        df = self._sentinel_to_nan(df)

        if self._categorical_columns:
            _check_columns_exist(
                df, self._categorical_columns, f"categorical encoding ({split_name})"
            )
            if self.config.categorical_encoding == "ordinal":
                if self._categorical_encoder is None:
                    raise NotFittedError(
                        "No fitted categorical encoder found. Call fit() first."
                    )
                try:
                    encoded = self._categorical_encoder.transform(
                        df[self._categorical_columns]
                    )
                except Exception as exc:
                    raise PreprocessingError(
                        f"Failed to apply OrdinalEncoder to '{split_name}': {exc}"
                    ) from exc
                df[self._categorical_columns] = encoded
            elif self.config.categorical_encoding == "category":
                for col in self._categorical_columns:
                    df[col] = df[col].astype("category")
            # "none": leave the raw categorical values as-is.

        return df

    def fit_transform(
        self, X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Fit on X_train, then transform train/val/test consistently."""
        self.fit(X_train)
        X_train_processed = self.transform(X_train, "X_train")
        X_val_processed = self.transform(X_val, "X_val")
        X_test_processed = self.transform(X_test, "X_test")
        logger.info("Tree-model data processing complete.")
        return X_train_processed, X_val_processed, X_test_processed

    def get_dropped_columns(self) -> List[str]:
        """Columns removed for exceeding the null threshold (fit on train)."""
        if not self._is_fitted:
            raise NotFittedError("Call fit() before get_dropped_columns().")
        return list(self._dropped_columns)


# --------------------------------------------------------------------------- #
# Random-forest preprocessor (no validation split)
# --------------------------------------------------------------------------- #
class RandomForestPreprocessor(TreeModelPreprocessor):
    """
    `TreeModelPreprocessor` variant for bagged models (Random Forest) that
    don't need a held-out validation split.

    Random Forest gets a validation-like signal for free: each tree is fit
    on a bootstrap sample that leaves ~37% of training rows unseen (the
    "out-of-bag" rows for that tree). Averaging each row's predictions
    across only the trees that never saw it (`oob_score=True` in
    `RandomForestClassifier`/`RandomForestRegressor`) gives an estimate of
    held-out performance without sacrificing any rows to a separate
    `X_val`. Boosted trees (XGBoost/LightGBM/CatBoost/GradientBoosting)
    don't have this property -- they build trees sequentially against the
    full training set with no bootstrap-and-leave-out step -- so this
    subclass is specifically for the bagging case, not tree models generally.

    Everything else (drop >null_threshold columns, sentinel -> NaN left
    unfilled, categorical encoding) is identical to `TreeModelPreprocessor`;
    only the split signature changes: `fit_transform` takes just
    (X_train, X_test) instead of (X_train, X_val, X_test).

    Note: OOB is derived from training data, so it's good for hyperparameter
    tuning, but you should still keep a genuinely untouched test set (as
    this class does) for the final, unbiased performance number.
    """

    def __init__(self, config: TreePreprocessConfig):
        super().__init__(config)

    def fit_transform(
        self, X_train: pd.DataFrame, X_test: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fit on X_train, then transform train/test only -- no X_val.

        Use `RandomForestClassifier(oob_score=True)` /
        `RandomForestRegressor(oob_score=True)` on the returned
        `X_train_processed` for the validation-like signal instead.
        """
        self.fit(X_train)
        X_train_processed = self.transform(X_train, "X_train")
        X_test_processed = self.transform(X_test, "X_test")
        logger.info(
            "Random-forest data processing complete (no validation split; "
            "use oob_score=True for held-out estimates)."
        )
        return X_train_processed, X_test_processed


# --------------------------------------------------------------------------- #
# Backwards-compatible functional wrapper
# --------------------------------------------------------------------------- #
def load_and_process(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    high_missing: List[str],
    median_cols: List[str],
    zero_cols: List[str],
    log_transform_cols: List[str],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Drop-in replacement for the original `load_and_process` function.

    Internally builds a `TabularPreprocessor` so that all statistics are
    learned on X_train only and applied consistently to X_val / X_test.
    Raises `PreprocessingError` subclasses on bad input instead of failing
    with an opaque pandas/sklearn traceback.
    """
    config = PreprocessConfig(
        high_missing=high_missing,
        median_cols=median_cols,
        zero_cols=zero_cols,
        log_transform_cols=log_transform_cols,
    )
    preprocessor = TabularPreprocessor(config)
    return preprocessor.fit_transform(X_train, X_val, X_test)


def load_and_process_for_trees(
    X_train: pd.DataFrame,
    X_val: pd.DataFrame,
    X_test: pd.DataFrame,
    null_threshold: float = 0.95,
    categorical_encoding: str = "ordinal",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Functional convenience wrapper around `TreeModelPreprocessor`, mirroring
    the style of `load_and_process` above.

    Drops columns that are more than `null_threshold` fraction null on
    train (sentinel included), replaces the missing-value sentinel with
    real `NaN` (left as NaN, not imputed -- most tree libraries handle it
    natively), and encodes categoricals per `categorical_encoding`
    ("ordinal" | "category" | "none").
    """
    config = TreePreprocessConfig(
        null_threshold=null_threshold,
        categorical_encoding=categorical_encoding,
    )
    preprocessor = TreeModelPreprocessor(config)
    return preprocessor.fit_transform(X_train, X_val, X_test)


def load_and_process_for_random_forest(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    null_threshold: float = 0.95,
    categorical_encoding: str = "ordinal",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Functional convenience wrapper around `RandomForestPreprocessor`.

    No `X_val` -- pair the returned `X_train_processed` with
    `RandomForestClassifier(oob_score=True)` (or the Regressor equivalent)
    to get a held-out performance estimate from out-of-bag rows instead.
    """
    config = TreePreprocessConfig(
        null_threshold=null_threshold,
        categorical_encoding=categorical_encoding,
    )
    preprocessor = RandomForestPreprocessor(config)
    return preprocessor.fit_transform(X_train, X_test)
