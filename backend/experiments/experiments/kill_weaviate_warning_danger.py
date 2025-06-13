import weaviate

# Initialize the Weaviate client
client = weaviate.connect_to_local()

# Name of the class (collection) to delete
collection_name = "Copertine"

# Delete the class
try:
    client.collections.delete(collection_name)
    print(f"Class '{collection_name}' has been deleted.")
except Exception as e:
    print(f"Failed to delete class '{collection_name}': {e}")
finally:
    client.close()
