import os
import random
import pandas as pd

# =========================
# PARAMÈTRES
# =========================
#SEED = 42
#random.seed(SEED)

image_dir = r"C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects\data\raw\image_train"
csv_path = r"C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects\data\processed\train_clean.csv"

# =========================
# IMAGE RANDOM
# =========================
def get_random_image(image_dir):
    images = [f for f in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, f))]
    
    if not images:
        raise ValueError("Aucune image trouvée")

    selected_image = random.choice(images)
    return selected_image

# =========================
# TEXTE RANDOM
# =========================
def get_random_text(csv_path):
    df = pd.read_csv(csv_path)

    if 'text_clean' not in df.columns:
        raise ValueError("Colonne 'text' introuvable")

    selected_row = df.sample(n=1)#, random_state=random.randint(0, 50000))
    return selected_row.iloc[0]['text_clean']

# =========================
# SIMULATION INFERENCE
# =========================
def simulate_inference_input():
    image_name = get_random_image(image_dir)
    text = get_random_text(csv_path)

    print("===== INPUT INFERENCE =====")
    print(f"Image : {image_name}")
    print(f"Texte : {text}")
    print("===========================")

    return image_name, text

# =========================
# EXECUTION
# =========================
if __name__ == "__main__":
    simulate_inference_input()