import weaviate
import weaviate.classes as wvc

def delete_objects_by_edition_id():
    """Delete all objects in Copertine collection with editionId = '18-06-2025'"""
    
    # Connect to local Weaviate instance
    client = weaviate.connect_to_local(host="localhost", port=8090)
    
    try:
        # Get the Copertine collection
        collection = client.collections.get("Copertine")
        
        # Query for objects with editionId = '18-06-2025'
        query_resp = collection.query.fetch_objects(
            filters=wvc.query.Filter.by_property("editionId").equal("18-06-2025"),
            limit=10  # Adjust if you expect more objects
        )
        
        objects_to_delete = query_resp.objects
        
        if objects_to_delete:
            print(f"Found {len(objects_to_delete)} objects with editionId '18-06-2025'")
            
            # Delete each object
            deleted_count = 0
            for obj in objects_to_delete:
                try:
                    collection.data.delete_by_id(obj.uuid)
                    deleted_count += 1
                    print(f"Deleted object with UUID: {obj.uuid}")
                except Exception as e:
                    print(f"Failed to delete object {obj.uuid}: {e}")
            
            print(f"Successfully deleted {deleted_count}/{len(objects_to_delete)} objects")
        else:
            print("No objects found with editionId '18-06-2025'")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always close the client
        client.close()

if __name__ == "__main__":
    delete_objects_by_edition_id()