# scripts/build_graph.py
from data_processor import DataProcessor
from graph import GraphBuilder
from pathlib import Path

if __name__ == "__main__":
    processed_data_dir = Path("./data/processed")
    
    # 1. Traitement des données
    print("Traitement des données spatiales...")
    processor = DataProcessor(processed_data_dir)
    processor.load_processed_data()
    network = processor.create_unified_network()
    
    try:
        # Cette étape peut échouer si le MNT n'est pas disponible
        network = processor.add_elevation_to_network()
        print("Élévation ajoutée au réseau.")
    except Exception as e:
        print(f"Impossible d'ajouter l'élévation: {e}")
        print("Utilisation du réseau sans information d'élévation.")
    
    # 2. Construction du graphe
    print("\nConstruction du graphe de déplacement...")
    builder = GraphBuilder(processed_data_dir)
    graph = builder.build_graph()
    
    # 3. Sauvegarde du graphe
    graph_path = builder.save_graph()
    
    # 4. Visualisation d'un échantillon
    print("\nCréation d'une visualisation...")
    viz_path = processed_data_dir / "graph_sample.png"
    builder.visualize_sample(radius=20, output_file=viz_path)
    
    print("\nTraitement terminé!")
    print(f"Graphe créé avec {len(graph.nodes())} nœuds et {len(graph.edges())} arêtes.")