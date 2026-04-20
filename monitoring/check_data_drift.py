import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = "data/raw/X_train_update.csv"
DEFAULT_CURRENT = "data/raw_test/X_test_update.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "monitoring" / "reports"
DEFAULT_DAGSHUB_CACHE_DIR = PROJECT_ROOT / "monitoring" / "dagshub_data"
DEFAULT_DAGSHUB_REPO_URL = os.getenv("DAGSHUB_REPO_URL", "https://dagshub.com/Fouxy84/mlops_projects")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check data drift with Evidently and export HTML/JSON reports.",
    )
    parser.add_argument("--reference", default=DEFAULT_REFERENCE)
    parser.add_argument("--current", default=DEFAULT_CURRENT)
    parser.add_argument(
        "--data-source",
        choices=("dagshub", "local"),
        default="dagshub",
        help="Use DagsHub/DVC by default. Use 'local' to read existing local files.",
    )
    parser.add_argument("--dagshub-repo-url", default=DEFAULT_DAGSHUB_REPO_URL)
    parser.add_argument(
        "--dagshub-rev",
        default=os.getenv("DAGSHUB_DATA_REV", ""),
        help="Optional Git commit, branch, or tag to read data from.",
    )
    parser.add_argument("--dagshub-cache-dir", type=Path, default=DEFAULT_DAGSHUB_CACHE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-name", default="data_drift")
    parser.add_argument(
        "--columns",
        default="",
        help="Comma-separated source columns to include in addition to derived data-state features.",
    )
    parser.add_argument("--sample-size", type=int, default=5000)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit with code 2 when dataset drift is detected.",
    )
    return parser.parse_args()


def repo_relative_path(path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"Absolute DagsHub paths must be inside the project root: {path_value}"
            ) from exc
    return Path(path_value).as_posix()


def local_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def dvc_get_from_dagshub(repo_url: str, repo_path: str, output_path: Path, rev: str = "") -> Path:
    dvc_executable = shutil.which("dvc")
    if dvc_executable is None:
        raise RuntimeError(
            "DVC is not installed. Install it with: pip install \"dvc[s3]\""
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        dvc_executable,
        "get",
        repo_url,
        repo_path,
        "--out",
        str(output_path),
        "--force",
    ]
    if rev:
        command.extend(["--rev", rev])

    env = os.environ.copy()
    env["DVC_NO_ANALYTICS"] = "true"
    if env.get("DAGSHUB_USER") and env.get("DAGSHUB_TOKEN"):
        env.setdefault("AWS_ACCESS_KEY_ID", env["DAGSHUB_USER"])
        env.setdefault("AWS_SECRET_ACCESS_KEY", env["DAGSHUB_TOKEN"])

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "Could not download data from DagsHub/DVC. "
            "Check DAGSHUB_USER, DAGSHUB_TOKEN, DAGSHUB_REPO_URL and DVC remote access. "
            f"Details: {message}"
        )
    return output_path


def prepare_input_file(path_value: str, role: str, args: argparse.Namespace) -> Path:
    if args.data_source == "local":
        return local_path(path_value)

    repo_path = repo_relative_path(path_value)
    output_path = args.dagshub_cache_dir.resolve() / f"{role}_{Path(repo_path).name}"
    return dvc_get_from_dagshub(
        repo_url=args.dagshub_repo_url,
        repo_path=repo_path,
        output_path=output_path,
        rev=args.dagshub_rev,
    )


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path, low_memory=False)
    unnamed_columns = [col for col in df.columns if str(col).startswith("Unnamed") or str(col) == ""]
    if unnamed_columns:
        df = df.drop(columns=unnamed_columns)
    return df


def sample_frame(df: pd.DataFrame, sample_size: int, random_state: int) -> pd.DataFrame:
    if sample_size <= 0 or len(df) <= sample_size:
        return df.reset_index(drop=True)
    return df.sample(n=sample_size, random_state=random_state).reset_index(drop=True)


def text_length(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.len()


def build_data_state_frame(df: pd.DataFrame, extra_columns: list[str]) -> pd.DataFrame:
    data_state = pd.DataFrame(index=df.index)

    if "designation" in df.columns:
        data_state["designation_length"] = text_length(df["designation"])
        data_state["designation_missing"] = df["designation"].isna().astype(int)

    if "description" in df.columns:
        data_state["description_length"] = text_length(df["description"])
        data_state["description_missing"] = df["description"].isna().astype(int)

    if {"designation", "description"}.issubset(df.columns):
        combined_text = df["designation"].fillna("").astype(str) + " " + df["description"].fillna("").astype(str)
        data_state["combined_text_length"] = combined_text.str.strip().str.len()

    if "text_clean" in df.columns:
        data_state["text_clean_length"] = text_length(df["text_clean"])
        data_state["text_clean_missing"] = df["text_clean"].isna().astype(int)

    for target_column in ("label", "label_name", "prdtypecode"):
        if target_column in df.columns:
            data_state[target_column] = df[target_column]

    for column in extra_columns:
        if column in df.columns and column not in data_state.columns:
            data_state[column] = df[column]

    if data_state.empty:
        data_state = df.copy()

    all_empty_columns = [col for col in data_state.columns if data_state[col].isna().all()]
    if all_empty_columns:
        data_state = data_state.drop(columns=all_empty_columns)

    return data_state


def align_frames(reference: pd.DataFrame, current: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_columns = [col for col in reference.columns if col in current.columns]
    if not common_columns:
        raise ValueError("No common columns available for drift detection.")
    return reference[common_columns].copy(), current[common_columns].copy()


def run_evidently_report(reference: pd.DataFrame, current: pd.DataFrame, html_path: Path, json_path: Path) -> dict:
    try:
        from evidently import Report
        from evidently.presets import DataDriftPreset, DataSummaryPreset

        report = Report([DataDriftPreset(), DataSummaryPreset()], include_tests=True)
        snapshot = report.run(current_data=current, reference_data=reference)
        snapshot.save_html(str(html_path))
        snapshot.save_json(str(json_path))
        return json.loads(snapshot.json())
    except ImportError as exc:
        raise RuntimeError(
            "Evidently is not installed. Install it with: pip install evidently"
        ) from exc
    except (AttributeError, TypeError):
        from evidently.metric_preset import DataDriftPreset, DataQualityPreset
        from evidently.report import Report

        report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
        report.run(reference_data=reference, current_data=current)
        report.save_html(str(html_path))
        report.save_json(str(json_path))
        if hasattr(report, "as_dict"):
            return report.as_dict()
        return json.loads(report.json())


def collect_values(payload: Any, key_name: str) -> list[Any]:
    values = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == key_name:
                values.append(value)
            values.extend(collect_values(value, key_name))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(collect_values(item, key_name))
    return values


def extract_drift_summary(payload: dict) -> dict:
    summary = {}
    for key in (
        "dataset_drift",
        "share_drifted_features",
        "share_of_drifted_columns",
        "n_drifted_features",
        "number_of_drifted_columns",
        "drifted_columns_count",
    ):
        values = collect_values(payload, key)
        if values:
            summary[key] = values[0]
    return summary


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        reference_path = prepare_input_file(args.reference, "reference", args)
        current_path = prepare_input_file(args.current, "current", args)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    extra_columns = [column.strip() for column in args.columns.split(",") if column.strip()]
    reference_raw = sample_frame(read_csv(reference_path), args.sample_size, args.random_state)
    current_raw = sample_frame(read_csv(current_path), args.sample_size, args.random_state)

    reference_state = build_data_state_frame(reference_raw, extra_columns)
    current_state = build_data_state_frame(current_raw, extra_columns)
    reference_state, current_state = align_frames(reference_state, current_state)

    html_path = output_dir / f"{args.report_name}.html"
    json_path = output_dir / f"{args.report_name}.json"
    status_path = output_dir / f"{args.report_name}_status.json"

    try:
        payload = run_evidently_report(reference_state, current_state, html_path, json_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    drift_summary = extract_drift_summary(payload)
    dataset_drift = bool(drift_summary.get("dataset_drift", False))

    status_payload = {
        "status": "drift_detected" if dataset_drift else "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": args.data_source,
        "dagshub_repo_url": args.dagshub_repo_url if args.data_source == "dagshub" else None,
        "dagshub_rev": args.dagshub_rev or None,
        "reference": str(reference_path),
        "current": str(current_path),
        "reference_rows": len(reference_state),
        "current_rows": len(current_state),
        "columns_checked": list(reference_state.columns),
        "drift_summary": drift_summary,
        "report_html": str(html_path),
        "report_json": str(json_path),
    }
    status_path.write_text(json.dumps(status_payload, indent=2), encoding="utf-8")

    print(json.dumps(status_payload, indent=2))
    if args.fail_on_drift and dataset_drift:
        return 2
    return 0


if __name__ == "__main__":python monitoring/check_data_drift.py --data-source local
    sys.exit(main())
