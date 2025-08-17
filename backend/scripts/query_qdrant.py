from qdrant_client import QdrantClient
import yaml
from pathlib import Path

# Get the script's directory
script_dir = Path(__file__).parent.absolute()
config_path = script_dir.parent / 'config' / 'config.yaml'

# Load config
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Connect to Qdrant
client = QdrantClient(url=config['qdrant_url'])

# Get collection info
for collection in ['financial_chunks', 'devices_chunks']:
    print(f"\nCollection: {collection}")
    try:
        # Get collection info
        info = client.get_collection(collection)
        print(f"Vector size: {info.config.params.vectors.size}")
        print(f"Distance: {info.config.params.vectors.distance}")
        
        # Get points count
        count = client.count(collection_name=collection)
        print(f"Total points: {count.count}")
        
        # Get some sample points
        points = client.scroll(
            collection_name=collection,
            limit=5,
            with_payload=True,
            with_vectors=False  # Set to True if you want to see the vectors
        )[0]
        
        print("\nSample records:")
        for point in points:
            print(f"\nPoint ID: {point.id}")
            print(f"Payload: {point.payload}")
            
    except Exception as e:
        print(f"Error accessing collection: {str(e)}")
