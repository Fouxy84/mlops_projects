
from pathlib import Path
import joblib
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from torchvision import transforms
from PIL import Image
import sys
import pandas as pd

# =========================
# PATHS
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR)) 
TEXT_MODELS_DIR = BASE_DIR / "models" / "text"
IMAGE_MODELS_DIR = BASE_DIR / "models" / "images"
LABEL_NAME_DIR = BASE_DIR /"data" / "processed" 
df_labels = pd.read_csv(LABEL_NAME_DIR / "train_clean.csv")
LABEL_ID_TO_NAME = (df_labels.set_index("label")["label_name"].to_dict())

from src.train_models.train_cnn import SimpleCNN
IMAGE_ROOTS = BASE_DIR / "data"/ "raw" / "image_train"


# =========================
# LOAD TEXT MODEL
# =========================
tfidf = joblib.load(TEXT_MODELS_DIR / "tfidf.joblib")
svm = joblib.load(TEXT_MODELS_DIR / "svm.joblib")

# =========================
# LOAD CNN MODEL
# =========================
NUM_CLASSES = 8
DEVICE = torch.device("cpu")

cnn_model = SimpleCNN(NUM_CLASSES)
cnn_model.load_state_dict(
    torch.load(IMAGE_MODELS_DIR / "cnn.pt", map_location=DEVICE)
)
cnn_model.to(DEVICE)
cnn_model.eval()

# =========================
# IMAGE TRANSFORM
# =========================
IMAGE_SIZE = 128

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5]*3, std=[0.5]*3),
])



# =========================
# FASTAPI
# =========================
app = FastAPI(
    title="Rakuten MLOps Inference API (local)",
    description="Text and Image classification"
)

# =========================
# SCHEMAS
# =========================
class PredictTextRequest(BaseModel):
    text: str

class PredictImageRequest(BaseModel):
    image_path: str

class PredictResponse(BaseModel):
    predicted_label: int
    label_name : str
    decision_score: Optional[list[float]] = None

# =========================
# ENDPOINTS
# =========================
@app.get("/health")
def health():
    return {"status": "ok","service":"API REST local"}

@app.post("/predict/svm", response_model=PredictResponse)
def predict_svm(request: PredictTextRequest):
    X = tfidf.transform([request.text])
    pred = svm.predict(X)[0]
    
    response = {"predicted_label": int(pred),"label_name":LABEL_ID_TO_NAME.get(pred,"unkown")}
    if hasattr(svm, "decision_function"):
        response["decision_score"] = svm.decision_function(X)[0].tolist()

    return response

@app.post("/predict/cnn", response_model=PredictResponse)
def predict_cnn(request: PredictImageRequest):
    try:
        image_path = IMAGE_ROOTS / request.image_path
        if not image_path.is_absolute():
            image_path = BASE_DIR / image_path

        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image not found: {image_path}")

        image = Image.open(image_path)
        tensor = transform(image).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            outputs = cnn_model(tensor)
            pred1 = outputs.argmax(dim=1).item()

        return {"predicted_label": pred1,"label_name":LABEL_ID_TO_NAME.get(pred1,"unkown")}

    except Exception as e:
        print("CNN inference error:", e)
        raise HTTPException(status_code=500, detail=str(e))
        

        
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
