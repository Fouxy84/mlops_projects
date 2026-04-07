from pathlib import Path
from src.preprocessing.text_cleaning import clean_text, preprocess_training_data

def test_clean_text_html():
    assert clean_text("<b>Hello</b> World!") == "hello world"


def test_preprocess_pipeline(tmp_path):
    out = tmp_path / "train_clean.csv"
    preprocess_training_data(
        Path("data/raw/X_train_update.csv"),
        Path("data/raw/Y_train_CVw08PX.csv"),
        out,
    )
    assert out.exists()
