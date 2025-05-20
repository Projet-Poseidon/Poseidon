# rando_sim/data_processor.py
import geopandas as gpd
from shapely.geometry import LineString, Point
import numpy as np
from pathlib import Path
import rasterio
from rasterio.windows import Window
import pandas as pd

class DataProcessor:
    def __init__(self, processed_data_dir):
        self.processed_data_dir = Path(processed_data_dir)
        self.data = {}
        self.network = None
        self.mnt_metadata = None
    
    def load_processed_data(self):
        """Charge les données prétraitées."""
        # Charger les fichiers GeoPackage
        for file_path in self.processed_data_dir.glob("*.gpkg"):
            name = file_path.stem
            print(f"Chargement de {name}...")
            self.data[name] = gpd.read_file(file_path)
        
        # Charger les métadonnées MNT
        import json
        mnt_path = self.processed_data_dir / "mnt_metadata.json"
        if mnt_path.exists():
            with open(mnt_path, 'r') as f:
                self.mnt_metadata = json.load(f)
        
        return self.data
    
    def create_unified_network(self):
        """Crée un réseau unifié à partir des chemins et routes."""
        
        if 'roads' not in self.data or 'paths' not in self.data:
             raise ValueError("Les données de routes et chemins ne sont pas chargées")
        
        # Extrait les colonnes pertinentes et ajoute le type
        roads = self.data['roads'].copy()
        roads['network_type'] = 'route'
        
        paths = self.data['paths'].copy()
        paths['network_type'] = 'sentier'
        
        # Sélection et renommage des colonnes communes
        roads_cols = ['geometry', 'network_type', 'TYPE_ROUTE']
        roads = roads[roads_cols].copy()
        roads['nature'] = roads['TYPE_ROUTE']
        roads = roads[['geometry', 'network_type', 'nature']]

        paths['nature'] = paths['NATURE']
        paths = paths[['geometry', 'network_type', 'nature']]

        # Fusion des deux sources
        network = gpd.pd.concat([roads, paths], ignore_index=True)
        
        # Conversion en GeoDataFrame et vérification de la validité des géométries
        network = gpd.GeoDataFrame(network, geometry='geometry', crs=roads.crs)
        network = network[network.is_valid]  # Filtrer les géométries invalides
        
        # Classification des types de surface
        network['surface_type'] = network.apply(self._classify_surface_type, axis=1)
        
        # Sauvegarde du réseau unifié
        self.network = network
        network.to_file(self.processed_data_dir / "unified_network.gpkg", driver="GPKG")
        
        return network
    
    def _classify_surface_type(self, row):
        """Classifie le type de surface en fonction des attributs."""
        if row['network_type'] == 'sentier':
            if 'Sentier' in str(row['nature']):
                return 'sentier_balisé'
            elif 'Piste cyclable' in str(row['nature']):
                return 'piste'
            else:
                return 'sentier_balisé'
        elif row['network_type'] == 'route':
            if 'Chemin' in str(row['nature']):
                return 'chemin'
            elif 'Sentier' in str(row['nature']):
                return 'sentier_balisé'
            elif 'Route' in str(row['nature']):
                return 'route'
            else:
                return 'chemin'
        return 'chemin'  # Valeur par défaut
    
    def extract_elevation_for_points(self, points_gdf):
        """Extrait l'élévation pour une série de points."""
        if not self.mnt_metadata:
            raise ValueError("Les métadonnées MNT ne sont pas chargées")
        
        # Ajouter une colonne pour stocker l'élévation
        points_gdf['elevation'] = np.nan
        
        # Pour chaque fichier MNT
        for mnt_info in self.mnt_metadata:
            mnt_path = mnt_info['path']
            
            with rasterio.open(mnt_path) as src:
                # Filtrer les points qui sont dans les limites de ce MNT
                bounds = mnt_info['bounds']
                mask = points_gdf.cx[bounds[0]:bounds[2], bounds[1]:bounds[3]].index
                
                if len(mask) == 0:
                    continue
                
                # Pour chaque point dans les limites
                for idx in mask:
                    point = points_gdf.loc[idx, 'geometry']
                    
                    # Convertir les coordonnées du point en indices raster
                    x, y = src.index(point.x, point.y)
                    
                    # Vérifier que les indices sont valides
                    if 0 <= x < src.width and 0 <= y < src.height:
                        # Lire la valeur d'élévation
                        window = Window(x, y, 1, 1)
                        data = src.read(1, window=window)
                        
                        # Si la valeur n'est pas NO_DATA
                        if data[0, 0] != src.nodata:
                            points_gdf.at[idx, 'elevation'] = float(data[0, 0])
        
        return points_gdf
    
    def add_elevation_to_network(self):
        """Ajoute l'information d'élévation au réseau."""
        if self.network is None:
            raise ValueError("Le réseau unifié n'est pas créé")
        
        # Extraire les points de début et de fin de chaque segment
        start_points = []
        end_points = []
        
        for idx, row in self.network.iterrows():
            if isinstance(row.geometry, LineString):
                start_points.append(Point(row.geometry.coords[0]))
                end_points.append(Point(row.geometry.coords[-1]))
            else:
                # Skip geometries that are not LineStrings
                start_points.append(None)
                end_points.append(None)
        
        # Créer des GeoDataFrames pour les points
        start_gdf = gpd.GeoDataFrame({'geometry': start_points}, 
                                     geometry='geometry', 
                                     crs=self.network.crs)
        end_gdf = gpd.GeoDataFrame({'geometry': end_points}, 
                                   geometry='geometry', 
                                   crs=self.network.crs)
        
        # Filtrer les géométries None
        start_gdf = start_gdf[~start_gdf.geometry.isna()]
        end_gdf = end_gdf[~end_gdf.geometry.isna()]
        
        # Extraire l'élévation
        start_gdf = self.extract_elevation_for_points(start_gdf)
        end_gdf = self.extract_elevation_for_points(end_gdf)
        
        # Ajouter l'élévation au réseau
        self.network['elevation_start'] = np.nan
        self.network['elevation_end'] = np.nan
        
        # Mapper les élévations aux segments correspondants
        for i, (idx, row) in enumerate(self.network.iterrows()):
            if i < len(start_gdf) and i < len(end_gdf):
                self.network.at[idx, 'elevation_start'] = start_gdf.iloc[i].get('elevation', np.nan)
                self.network.at[idx, 'elevation_end'] = end_gdf.iloc[i].get('elevation', np.nan)
        
        # Calculer la pente
        self.network['length_m'] = self.network.geometry.length
        self.network['slope_percent'] = 100 * (self.network['elevation_end'] - self.network['elevation_start']) / self.network['length_m']
        
        # Sauvegarder le réseau avec élévation
        self.network.to_file(self.processed_data_dir / "network_with_elevation.gpkg", driver="GPKG")
        
        return self.network
