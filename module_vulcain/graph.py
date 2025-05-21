# rando_sim/graph.py
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point, LineString
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

class GraphBuilder:
    def __init__(self, processed_data_dir):
        self.processed_data_dir = Path(processed_data_dir)
        self.graph = nx.DiGraph()  # Graphe orienté pour tenir compte des pentes
        self.network = None
    
    def load_network(self):
        """Charge le réseau avec élévation."""
        network_path = self.processed_data_dir / "network_with_elevation.gpkg"
        if not network_path.exists():
            network_path = self.processed_data_dir / "unified_network.gpkg"
            if not network_path.exists():
                raise FileNotFoundError("Aucun fichier de réseau trouvé")
        
        self.network = gpd.read_file(network_path)
        return self.network
    
    def _add_edge_with_attributes(self, start_node, end_node, idx, row):
        """Ajoute une arête dans les deux sens avec les attributs appropriés."""
        # Récupérer ou calculer les attributs nécessaires
        surface_type = row.get('surface_type', 'chemin')
        
        # Utiliser shapely pour calculer la longueur si elle n'est pas disponible
        length_m = row.get('length_m', row.geometry.length)
        
        # Gestion de la pente
        if 'slope_percent' in row and not pd.isna(row['slope_percent']):
            slope_percent = row['slope_percent']
        else:
            # Si pas de pente disponible, utiliser 0
            slope_percent = 0
        
        # Calculer les coûts de déplacement
        costs = self.calculate_costs({
            'length_m': length_m,
            'slope_percent': slope_percent,
            'surface_type': surface_type
        })
        
        # Ajout de l'arête au graphe (sens aller)
        self.graph.add_edge(
            start_node, 
            end_node, 
            id=idx,
            geometry=row.geometry,
            surface_type=surface_type,
            length_m=length_m,
            slope_percent=slope_percent,
            **costs['forward']
        )
        
        # Ajout de l'arête dans l'autre sens (avec des coûts différents)
        reverse_slope = -slope_percent
        reverse_costs = self.calculate_costs({
            'length_m': length_m,
            'slope_percent': reverse_slope,
            'surface_type': surface_type
        })
        
        self.graph.add_edge(
            end_node, 
            start_node, 
            id=f"{idx}_rev",
            geometry=row.geometry,
            surface_type=surface_type,
            length_m=length_m,
            slope_percent=reverse_slope,
            **reverse_costs['forward']
        )
    
    def build_graph(self):
        """Construit le graphe à partir du réseau."""
        if self.network is None:
            self.load_network()
        
        # Vérifiez les types de géométries dans le réseau
        geom_types = self.network.geometry.type.value_counts()
        print("Types de géométries dans le réseau :")
        for geom_type, count in geom_types.items():
            print(f"  - {geom_type}: {count}")
        
        # Dictionnaire pour stocker les nœuds {(x, y): node_id}
        all_nodes = {}
        node_counter = 0
        
        print("Construction des nœuds...")
        for _, row in self.network.iterrows():
            # Gérer à la fois LineString et MultiLineString
            if row.geometry.type == 'LineString':
                # Pour les LineString, traitement direct
                start_point = row.geometry.coords[0]
                end_point = row.geometry.coords[-1]
                
                # Ajouter les points comme nœuds
                if start_point not in all_nodes:
                    all_nodes[start_point] = node_counter
                    self.graph.add_node(node_counter, x=start_point[0], y=start_point[1], point=Point(start_point))
                    node_counter += 1
                
                if end_point not in all_nodes:
                    all_nodes[end_point] = node_counter
                    self.graph.add_node(node_counter, x=end_point[0], y=end_point[1], point=Point(end_point))
                    node_counter += 1
                    
            elif row.geometry.type == 'MultiLineString':
                # Pour les MultiLineString, traiter chaque LineString contenue
                for line in row.geometry.geoms:
                    if len(line.coords) > 0:
                        start_point = line.coords[0]
                        end_point = line.coords[-1]
                        
                        # Ajouter les points comme nœuds
                        if start_point not in all_nodes:
                            all_nodes[start_point] = node_counter
                            self.graph.add_node(node_counter, x=start_point[0], y=start_point[1], point=Point(start_point))
                            node_counter += 1
                        
                        if end_point not in all_nodes:
                            all_nodes[end_point] = node_counter
                            self.graph.add_node(node_counter, x=end_point[0], y=end_point[1], point=Point(end_point))
                            node_counter += 1
        
        print(f"Nombre de nœuds créés : {node_counter}")
        
        # Ajouter les arêtes
        print("Construction des arêtes...")
        edge_counter = 0
        for idx, row in self.network.iterrows():
            if row.geometry.type == 'LineString':
                # Traitement direct pour LineString
                start_point = row.geometry.coords[0]
                end_point = row.geometry.coords[-1]
                
                if start_point in all_nodes and end_point in all_nodes:
                    start_node = all_nodes[start_point]
                    end_node = all_nodes[end_point]
                    
                    # Ajouter l'arête avec ses attributs
                    self._add_edge_with_attributes(start_node, end_node, idx, row)
                    edge_counter += 2  # +2 car on ajoute les arêtes dans les deux sens
                
            elif row.geometry.type == 'MultiLineString':
                # Pour les MultiLineString, traiter chaque LineString contenue
                for i, line in enumerate(row.geometry.geoms):
                    if len(line.coords) > 0:
                        start_point = line.coords[0]
                        end_point = line.coords[-1]
                        
                        if start_point in all_nodes and end_point in all_nodes:
                            start_node = all_nodes[start_point]
                            end_node = all_nodes[end_point]
                            
                            # Créer un identifiant unique pour cette partie de MultiLineString
                            sub_idx = f"{idx}_{i}"
                            
                            # Créer une copie des attributs avec la géométrie mise à jour
                            line_row = row.copy()
                            # Remplacer la géométrie MultiLineString par la LineString actuelle
                            line_row.geometry = line
                            
                            # Ajouter l'arête avec ses attributs
                            self._add_edge_with_attributes(start_node, end_node, sub_idx, line_row)
                            edge_counter += 2
        
        print(f"Nombre d'arêtes créées : {edge_counter}")
        
        return self.graph
    
    def calculate_costs(self, segment):
        """Calcule les coûts de déplacement pour un segment."""
        # Paramètres de base
        length_m = segment['length_m']
        slope = segment['slope_percent']
        surface_type = segment['surface_type']
        
        # Vitesse de base selon le type de surface (km/h)
        base_speeds = {
            'sentier_balisé': 4.0,
            'chemin': 3.5,
            'piste': 5.0,
            'route': 5.5,
            'hors_sentier': 2.5,
            'zone_rocheuse': 1.8,
            'cours_eau': 0.8,
        }
        
        # Facteur de ralentissement selon la pente
        if slope > 0:  # Montée
            slope_factor = 1 - min(0.8, slope / 100)
        else:  # Descente
            slope_factor = 1 - min(0.4, abs(slope) / 100)
        
        # Vitesse effective
        speed = base_speeds.get(surface_type, 3.0) * slope_factor
        
        # Temps en secondes
        time_s = length_m / 1000 / speed * 3600
        
        # Effort (formule simplifiée)
        effort = time_s * (1 + abs(slope) / 20)
        
        return {
            'forward': {
                'distance': length_m,
                'time': time_s,
                'effort': effort
            }
        }
    
    def save_graph(self, filename=None):
        """Sauvegarde le graphe au format GraphML."""
        if filename is None:
            filename = self.processed_data_dir / "routing_graph.graphml"
        else:
            filename = Path(filename)
        
        # Créer une copie du graphe pour la sauvegarde
        save_graph = nx.DiGraph()
        
        # Copier les nœuds en convertissant les objets Shapely en WKT
        for node, data in self.graph.nodes(data=True):
            # Copier les attributs en supprimant ou convertissant ceux incompatibles
            node_attrs = {}
            for key, value in data.items():
                if key == 'point':
                    # Convertir Point en string WKT
                    node_attrs['point_wkt'] = value.wkt
                elif isinstance(value, (int, float, str, bool)) or value is None:
                    # Garder seulement les types compatibles GraphML
                    node_attrs[key] = value
            
            save_graph.add_node(node, **node_attrs)
        
        # Copier les arêtes en convertissant les objets Shapely en WKT
        for u, v, data in self.graph.edges(data=True):
            # Copier les attributs en supprimant ou convertissant ceux incompatibles
            edge_attrs = {}
            for key, value in data.items():
                if key == 'geometry':
                    # Convertir LineString/MultiLineString en string WKT
                    edge_attrs['geometry_wkt'] = value.wkt
                elif isinstance(value, (int, float, str, bool)) or value is None:
                    # Garder seulement les types compatibles GraphML
                    edge_attrs[key] = value
            
            save_graph.add_edge(u, v, **edge_attrs)
        
        # Sauvegarder le graphe nettoyé
        print(f"Sauvegarde du graphe dans {filename}...")
        nx.write_graphml(save_graph, filename)
        print(f"Graphe sauvegardé dans {filename}")
        
        return filename
    
    def load_graph(self, filename=None):
        """Charge un graphe à partir d'un fichier GraphML et reconvertit les WKT en objets Shapely."""
        if filename is None:
            filename = self.processed_data_dir / "routing_graph.graphml"
        else:
            filename = Path(filename)
        
        if not filename.exists():
            raise FileNotFoundError(f"Le fichier {filename} n'existe pas")
        
        # Charger le graphe
        print(f"Chargement du graphe depuis {filename}...")
        loaded_graph = nx.read_graphml(filename)
        
        # Créer un nouveau graphe avec objets Shapely reconstitués
        self.graph = nx.DiGraph()
        
        # Traiter les nœuds
        from shapely import wkt
        
        for node, data in loaded_graph.nodes(data=True):
            # Reconstituer les attributs
            node_attrs = {}
            for key, value in data.items():
                if key == 'point_wkt':
                    # Reconvertir WKT en Point
                    node_attrs['point'] = wkt.loads(value)
                else:
                    node_attrs[key] = value
            
            self.graph.add_node(node, **node_attrs)
        
        # Traiter les arêtes
        for u, v, data in loaded_graph.edges(data=True):
            # Reconstituer les attributs
            edge_attrs = {}
            for key, value in data.items():
                if key == 'geometry_wkt':
                    # Reconvertir WKT en LineString/MultiLineString
                    edge_attrs['geometry'] = wkt.loads(value)
                else:
                    edge_attrs[key] = value
            
            self.graph.add_edge(u, v, **edge_attrs)
        
        print(f"Graphe chargé avec {len(self.graph.nodes())} nœuds et {len(self.graph.edges())} arêtes")
        return self.graph
    
    def visualize_sample(self, radius=30, output_file=None):
        """Visualise un échantillon du graphe."""
        if not self.graph:
            raise ValueError("Le graphe n'est pas construit")
        
        # Extraire un sous-graphe centré sur un nœud aléatoire
        center_node = list(self.graph.nodes())[0]
        subgraph = nx.ego_graph(self.graph, center_node, radius=radius)
        
        # Construire un dictionnaire des positions
        pos = {n: (float(self.graph.nodes[n]['x']), float(self.graph.nodes[n]['y'])) 
               for n in subgraph.nodes()}
        
        # Visualiser le sous-graphe
        plt.figure(figsize=(12, 10))
        nx.draw(subgraph, pos, with_labels=False, 
                node_size=10, node_color='blue', 
                edge_color='gray', width=1.0, alpha=0.7)
        
        # Ajouter un titre
        plt.title(f"Échantillon du graphe (rayon={radius} nœuds)", fontsize=14)
        
        # Sauvegarder ou afficher
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"Visualisation sauvegardée dans {output_file}")
        else:
            plt.show()