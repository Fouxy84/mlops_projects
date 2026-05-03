import os
import shutil
import random
import pandas as pd

# =========================
# PARAMÈTRES
# =========================
N_IMAGES = 50   # nombre d'images à copier
M_ROWS = 100    # nombre de lignes à ajouter
#SEED = 42       # reproductibilité

#random.seed(SEED)

# =========================
# CHEMINS
# =========================
source_images = r"C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects\data\raw_test\image_test"
target_images = r"C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects\data\raw\image_train"

source_csv = r"C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects\data\raw_test\X_test_update.csv"
target_csv = r"C:\Users\coach\Desktop\datascientest\Projet DATASCIENTEST\projet_MLops\mlops_projects\data\raw\X_train_update.csv"

# =========================
# COPIE DES IMAGES
# =========================
def copy_random_images(src, dst, n):
    images = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]

    if n > len(images):
        raise ValueError("Pas assez d'images dans le dossier source")

    selected_images = random.sample(images, n)

    os.makedirs(dst, exist_ok=True)

    for img in selected_images:
        shutil.copy(os.path.join(src, img), os.path.join(dst, img))

    print(f"{n} images copiées.")

    return selected_images


# =========================
# AJOUT DES LIGNES CSV
# =========================
def append_random_rows(src_csv, dst_csv, m):
    df_src = pd.read_csv(src_csv)
    
    if m > len(df_src):
        raise ValueError("Pas assez de lignes dans le CSV source")

    df_sample = df_src.sample(n=m)#, random_state=SEED)

    # Si le fichier cible existe, on append
    if os.path.exists(dst_csv):
        df_dst = pd.read_csv(dst_csv)
        df_final = pd.concat([df_dst, df_sample], ignore_index=True)
    else:
        df_final = df_sample

    df_final.to_csv(dst_csv, index=False)

    print(f"{m} lignes ajoutées au CSV.")


# =========================
# EXECUTION
# =========================
if __name__ == "__main__":
    selected_images = copy_random_images(source_images, target_images, N_IMAGES)
    append_random_rows(source_csv, target_csv, M_ROWS)

    print("Pipeline d'ajout de données terminé 🚀")