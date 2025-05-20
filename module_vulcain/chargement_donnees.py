# scripts/import_and_process.py
from data_loader import IGNDataLoader
from pathlib import Path

if __name__ == "__main__":
    raw_data_dir = Path("./data/raw")
    processed_data_dir = Path("./data/processed")
    
    # Charger et prétraiter les données
    loader = IGNDataLoader(raw_data_dir, processed_data_dir)
    data = loader.preprocess_and_save()
    
    print("Import terminé.")
    print(f"Nombre de jeux de données chargés : {len(data['topo_data'])}")
    print(f"Nombre de fichiers MNT détectés : {len(data['mnt_data'])}")