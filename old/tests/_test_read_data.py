
import pandas as pd
from pathlib import Path


def test_can_read_raw_data():
    X = pd.read_csv("data/raw/X_train_update.csv")
    y = pd.read_csv("data/raw/Y_train_CVw08PX.csv")
    assert len(X) > 0
    assert len(y) > 0
    

def test_raw_train_data_exists():
    assert Path("data/raw/X_train_update.csv").exists()
    assert Path("data/raw/Y_train_CVw08PX.csv").exists()
    assert Path("data/raw/image_train").exists()

def test_raw_test_data_exists():
    assert Path("data/raw_test/X_test_update.csv").exists()
    assert Path("data/raw_test/image_test").exists()
