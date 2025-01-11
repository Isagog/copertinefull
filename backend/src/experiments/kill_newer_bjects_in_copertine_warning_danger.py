import weaviate
from weaviate.classes.query import Filter


def delete_recent_copertine():
    # Initialize the Weaviate client
    client = weaviate.connect_to_local()

    try:
        # Get the Copertine collection
        collection = client.collections.get("Copertine")

        # Set the filter date
        filter_time = "2024-12-31T23:59:59.00Z"

        # Query objects with date >= 2025-01-01
        response = collection.query.fetch_objects(
            filters=Filter.by_property("editionDateIsoStr").greater_than(filter_time)
        )

        # Delete each object
        deleted_count = 0
        for obj in response.objects:
            collection.data.delete_by_id(obj.uuid)
            print(f"Deleted object with ID: {obj.uuid}")
            deleted_count += 1

        print(f"Successfully deleted {deleted_count} objects")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    delete_recent_copertine()