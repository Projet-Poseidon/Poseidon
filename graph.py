# rando_sim/graph.py
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point, LineString
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

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
    
    def build_graph(self):
        """Construit le graphe à partir du réseau."""
        if self.network is None:
            self.load_network()
        
        # Extraire tous les points de début et de fin comme nœuds potentiels
        all_nodes = {}  # dictionnaire pour stocker {(x, y): node_id}
        node_counter = 0

        print(self.network)
        
        print("Construction des nœuds...")
        for _, row in self.network.iterrows():
            if isinstance(row.geometry, LineString):
                # Point de départ
                start_point = row.geometry.coords[0]
                if start_point not in all_nodes:
                    all_nodes[start_point] = node_counter
                    self.graph.add_node(node_counter, 
                                        x=start_point[0], 
                                        y=start_point[1],
                                        point=Point(start_point))
                    node_counter += 1
                
                # Point d'arrivée
                end_point = row.geometry.coords[-1]
                if end_point not in all_nodes:
                    all_nodes[end_point] = node_counter
                    self.graph.add_node(node_counter, 
                                        x=end_point[0], 
                                        y=end_point[1],
                                        point=Point(end_point))
                    node_counter += 1
        
        print(f"Nombre de nœuds créés : {node_counter}")
        
        # Ajouter les arêtes
        print("Construction des arêtes...")
        edge_counter = 0
        for idx, row in self.network.iterrows():
            if isinstance(row.geometry, LineString):
                start_point = row.geometry.coords[0]
                end_point = row.geometry.coords[-1]
                
                start_node = all_nodes[start_point]
                end_node = all_nodes[end_point]
                
                # Récupérer ou calculer les attributs nécessaires
                surface_type = row.get('surface_type', 'chemin')
                length_m = row.get('length_m', row.geometry.length)
                
                # Si l'élévation est disponible, calculer la pente
                slope_percent = row.get('slope_percent', 0)
                if np.isnan(slope_percent):
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
                    id=idx,
                    geometry=row.geometry,
                    surface_type=surface_type,
                    length_m=length_m,
                    slope_percent=reverse_slope,
                    **reverse_costs['forward']
                )
                
                edge_counter += 2  # +2 car on ajoute deux arêtes (aller-retour)
        
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
        
        # Convertir les valeurs numpy en types Python standard
        for u, v, data in self.graph.edges(data=True):
            for key, value in data.items():
                if isinstance(value, (np.int64, np.int32)):
                    data[key] = int(value)
                elif isinstance(value, (np.float64, np.float32)):
                    data[key] = float(value)
        
        nx.write_graphml(self.graph, filename)
        print(f"Graphe sauvegardé dans {filename}")
        
        return filename
    
    def load_graph(self, filename=None):
        """Charge un graphe à partir d'un fichier GraphML."""
        if filename is None:
            filename = self.processed_data_dir / "routing_graph.graphml"
        else:
            filename = Path(filename)
        
        if not filename.exists():
            raise FileNotFoundError(f"Le fichier {filename} n'existe pas")
        
        self.graph = nx.read_graphml(filename)
        print(f"Graphe chargé depuis {filename}")
        
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