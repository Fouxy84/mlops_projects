from pathlib import Path
import pandas as pd
import joblib

from src.preprocessing.train_tfidf import train_tfidf_vectorizer



def test_tfidf_training_and_transform(tmp_path):
    # Fake dataset
    df = pd.DataFrame({
        "text_clean": [
            "produit test",
            "autre produit",
            "encore un produit"
        ]
    })

    data_path = tmp_path / "data.csv"
    df.to_csv(data_path, index=False)

    artifacts_dir = tmp_path / "artifacts"
    X, vectorizer = train_tfidf_vectorizer(
        data_path=data_path,
        artifacts_dir=artifacts_dir,
        max_features=10
    )

    assert X.shape[0] == 3
    assert (artifacts_dir / "tfidf.joblib").exists()
    
    vec_path = artifacts_dir / "tfidf.joblib"
    loaded_vectorizer = joblib.load(vec_path)
    X_new = loaded_vectorizer.transform(["nouveau produit"])

    assert X_new.shape[0] == 1
