# rando_sim/data_loader.py
import geopandas as gpd
import rasterio
from pathlib import Path
import os

class IGNDataLoader:
    def __init__(self, raw_data_dir, processed_data_dir):
        self.raw_data_dir = Path(raw_data_dir)
        self.processed_data_dir = Path(processed_data_dir)
        
        # Créer les répertoires s'ils n'existent pas
        os.makedirs(self.processed_data_dir, exist_ok=True)
    
    def load_bd_topo(self):
        """Charge les fichiers pertinents de la BD TOPO."""
        # Chemins et routes
        roads_path = self.raw_data_dir / "BDTOPO/1_DONNEES/TRANSPORT/ROUTE_NUMEROTEE_OU_NOMMEE.shp"
        paths_path = self.raw_data_dir / "BDTOPO/1_DONNEES/TRANSPORT/TRONCON_DE_ROUTE.shp"
        
        # Obstacles
        buildings_path = self.raw_data_dir / "BDTOPO/1_DONNEES/BATI/BATIMENT.shp"
        water_path = self.raw_data_dir / "BDTOPO/1_DONNEES/HYDROGRAPHIE/PLAN_D_EAU.shp"
        rivers_path = self.raw_data_dir / "BDTOPO/1_DONNEES/HYDROGRAPHIE/TRONCON_HYDROGRAPHIQUE.shp"
        
        # Occupation du sol
        land_use_path = self.raw_data_dir / "BD_TOPO/1_DONNEES/OCCUPATION_SOL/ZONE_DE_VEGETATION.shp"
        
        # Chargement des données
        data = {}
        if roads_path.exists():
            data['roads'] = gpd.read_file(roads_path)
        if paths_path.exists():
            data['paths'] = gpd.read_file(paths_path)
        if buildings_path.exists():
            data['buildings'] = gpd.read_file(buildings_path)
        if water_path.exists():
            data['water'] = gpd.read_file(water_path)
        if rivers_path.exists():
            data['rivers'] = gpd.read_file(rivers_path)
        if land_use_path.exists():
            data['land_use'] = gpd.read_file(land_use_path)
        
        return data
    
    def load_mnt(self):
        """Charge le Modèle Numérique de Terrain (MNT)."""
        mnt_files = list(self.raw_data_dir.glob("**/RGEALTI*.asc"))
        
        if not mnt_files:
            print("Aucun fichier MNT trouvé !")
            return None
        
        mnt_data = []
        for mnt_file in mnt_files:
            with rasterio.open(mnt_file) as src:
                print(f"Chargement du MNT: {mnt_file}")
                print(f"  Taille: {src.width}x{src.height}")
                print(f"  CRS: {src.crs}")
                
                # Ici on pourrait charger les données, mais pour les MNT volumineux,
                # on préférera garder les chemins des fichiers et y accéder plus tard
                mnt_data.append({
                    'path': str(mnt_file),
                    'bounds': src.bounds,
                    'crs': 'EPSG:2154' #src.crs.to_string()
                })
        
        return mnt_data
    
    def preprocess_and_save(self):
        """Charge, prétraite et sauvegarde les données au format GeoPackage."""
        # Chargement des données
        topo_data = self.load_bd_topo()
        mnt_data = self.load_mnt()
        
        # Sauvegarder l'information des MNT pour référence ultérieure
        import json
        with open(self.processed_data_dir / "mnt_metadata.json", 'w') as f:
            json.dump(mnt_data, f)
        
        # Sauvegarder les données vectorielles en GeoPackage
        for name, gdf in topo_data.items():
            output_path = self.processed_data_dir / f"{name}.gpkg"
            print(f"Sauvegarde de {name} vers {output_path}")
            gdf.to_file(output_path, driver="GPKG")
        
        return {
            'topo_data': topo_data,
            'mnt_data': mnt_data
        }

if __name__ == "__main__":
    raw_data_dir = Path("./data/raw")
    processed_data_dir = Path("./data/processed")
    
    # Charger et prétraiter les données
    loader = IGNDataLoader(raw_data_dir, processed_data_dir)
    data = loader.preprocess_and_save()
    
    print("Import terminé.")
    print(f"Nombre de jeux de données chargés : {len(data['topo_data'])}")
    print(f"Nombre de fichiers MNT détectés : {len(data['mnt_data'])}")