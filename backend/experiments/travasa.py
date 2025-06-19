"""
Travasa - Weaviate Data Migration Script

This script migrates data from an old Weaviate instance to a new one.
It connects to two Weaviate instances:
- oldweaviate: localhost:8080 (GRPC: 50051)
- newweaviate: localhost:8090 (GRPC: 50091)

The script fetches all objects from the old Copertine collection and
inserts them into the new collection if they don't already exist
(based on editionId).
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv
from weaviate.classes.init import Auth

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.includes.weschema import COPERTINE_COLL_CONFIG


class WeaviateMigrationError(Exception):
    """Base exception for migration errors."""
    
    def __init__(self, message: str = "Migration error occurred"):
        self.message = message
        super().__init__(self.message)


class WeaviateMigrator:
    """Migrates data between two Weaviate instances."""
    
    def __init__(self):
        self._setup_logging()
        self._load_environment()
        self.old_client = None
        self.new_client = None
        self.old_collection = None
        self.new_collection = None
        
    def _setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            handlers=[
                logging.FileHandler("travasa_migration.log"),
                logging.StreamHandler(),
            ],
        )
        # Reduce noise from external libraries
        for lib in ["weaviate", "httpx", "httpcore"]:
            logging.getLogger(lib).setLevel(logging.WARNING)
        
        self.logger = logging.getLogger(__name__)
    
    def _load_environment(self):
        """Load environment variables."""
        secrets_path = Path(__file__).parent.parent / '.secrets'
        load_dotenv(dotenv_path=secrets_path, override=True)
        
        # Get collection name from environment
        self.collection_name = os.getenv("COP_COPERTINE_COLLNAME", "Copertine")
        self.logger.info(f"Using collection name: {self.collection_name}")
    
    def _initialize_weaviate_client(self, host: str, port: int, grpc_port: int, api_key: str = "") -> weaviate.WeaviateClient:
        """Initialize a Weaviate client with the given parameters."""
        try:
            if api_key and api_key.strip():
                client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=grpc_port,
                    auth_credentials=Auth.api_key(api_key),
                )
            else:
                client = weaviate.connect_to_local(
                    host=host,
                    port=port,
                    grpc_port=grpc_port,
                )
            
            self.logger.info(f"Successfully connected to Weaviate at {host}:{port}")
            
        except Exception:
            self.logger.exception(f"Failed to connect to Weaviate at {host}:{port}")
            raise WeaviateMigrationError() from None
        else:
            return client
    
    def _ensure_collection_exists(self, client: weaviate.WeaviateClient, collection_name: str):
        """Ensure the collection exists in the given Weaviate instance."""
        try:
            collections = client.collections.list_all()
            
            if collection_name not in collections:
                collection = client.collections.create_from_dict(COPERTINE_COLL_CONFIG)
                self.logger.info(f"Created {collection_name} collection")
                return collection
            else:
                collection = client.collections.get(collection_name)
                self.logger.info(f"Found existing {collection_name} collection")
                return collection
                
        except Exception:
            self.logger.exception(f"Failed to ensure collection {collection_name} exists")
            raise WeaviateMigrationError() from None
    
    def initialize_connections(self):
        """Initialize connections to both Weaviate instances."""
        # Get API key from environment (if any)
        api_key = os.getenv("COP_WEAVIATE_API_KEY", "")
        
        # Initialize old Weaviate client (localhost:8080, GRPC: 50051)
        self.logger.info("Connecting to old Weaviate instance (localhost:8080)...")
        self.old_client = self._initialize_weaviate_client("localhost", 8080, 50051, api_key)
        self.old_collection = self._ensure_collection_exists(self.old_client, self.collection_name)
        
        # Initialize new Weaviate client (localhost:8090, GRPC: 50091)
        self.logger.info("Connecting to new Weaviate instance (localhost:8090)...")
        self.new_client = self._initialize_weaviate_client("localhost", 8090, 50091, api_key)
        self.new_collection = self._ensure_collection_exists(self.new_client, self.collection_name)
    
    def _object_exists_in_new_collection(self, edition_id: str) -> bool:
        """Check if an object with the given editionId exists in the new collection."""
        try:
            existing_objects = self.new_collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property("editionId").equal(edition_id),
                limit=1
            )
            return len(existing_objects.objects) > 0
        except Exception:
            self.logger.exception(f"Error checking if object exists with editionId {edition_id}")
            return True  # Assume it exists to avoid duplicates on error
    
    def _extract_object_properties(self, obj) -> dict[str, Any]:
        """Extract properties from a Weaviate object."""
        properties = {}
        
        # Get all the properties defined in the schema
        expected_properties = [
            "testataName", "editionId", "editionDateIsoStr", "editionImageFnStr",
            "captionStr", "kickerStr", "captionAIStr", "imageAIDeStr", "modelAIName"
        ]
        
        # Access properties as dictionary
        obj_props = obj.properties if hasattr(obj, 'properties') else {}
        
        for prop in expected_properties:
            if prop in obj_props:
                value = obj_props[prop]
                if value is not None:
                    properties[prop] = value
        
        return properties
    
    def _insert_object_to_new_collection(self, properties: dict[str, Any]) -> bool:
        """Insert an object into the new collection."""
        try:
            insert_result = self.new_collection.data.insert(properties=properties)
            edition_id = properties.get("editionId", "unknown")
            self.logger.info(f"Successfully inserted object with editionId {edition_id}, UUID: {insert_result}")
        except Exception:
            edition_id = properties.get("editionId", "unknown")
            self.logger.exception(f"Failed to insert object with editionId {edition_id}")
            return False
        else:
            return True
    
    def migrate_data(self):
        """Main migration logic."""
        self.logger.info("Starting data migration...")
        
        # Statistics
        total_objects = 0
        existing_objects = 0
        migrated_objects = 0
        failed_objects = 0
        
        try:
            # Fetch all objects from the old collection
            self.logger.info("Fetching all objects from old collection...")
            
            # Use iterator to handle large datasets efficiently
            for obj in self.old_collection.iterator():
                total_objects += 1
                
                # Extract properties
                properties = self._extract_object_properties(obj)
                edition_id = properties.get("editionId")
                
                if not edition_id:
                    self.logger.warning(f"Object {obj.uuid} has no editionId, skipping...")
                    failed_objects += 1
                    continue
                
                # Check if object already exists in new collection
                if self._object_exists_in_new_collection(edition_id):
                    self.logger.debug(f"Object with editionId {edition_id} already exists in new collection, skipping...")
                    existing_objects += 1
                    continue
                
                # Insert object into new collection
                if self._insert_object_to_new_collection(properties):
                    migrated_objects += 1
                else:
                    failed_objects += 1
                
                # Log progress every 100 objects
                if total_objects % 100 == 0:
                    self.logger.info(f"Processed {total_objects} objects so far...")
        
        except Exception:
            self.logger.exception("Error during migration")
            raise WeaviateMigrationError() from None
        
        # Log final statistics
        self.logger.info("Migration completed!")
        self.logger.info(f"Total objects processed: {total_objects}")
        self.logger.info(f"Objects already existing: {existing_objects}")
        self.logger.info(f"Objects successfully migrated: {migrated_objects}")
        self.logger.info(f"Objects failed to migrate: {failed_objects}")
        
        return {
            "total": total_objects,
            "existing": existing_objects,
            "migrated": migrated_objects,
            "failed": failed_objects
        }
    
    def cleanup(self):
        """Clean up resources."""
        if self.old_client:
            try:
                self.old_client.close()
                self.logger.info("Closed old Weaviate client")
            except Exception:
                self.logger.exception("Error closing old Weaviate client")
        
        if self.new_client:
            try:
                self.new_client.close()
                self.logger.info("Closed new Weaviate client")
            except Exception:
                self.logger.exception("Error closing new Weaviate client")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def main():
    """Main entry point."""
    try:
        with WeaviateMigrator() as migrator:
            # Initialize connections to both Weaviate instances
            migrator.initialize_connections()
            
            # Perform the migration
            stats = migrator.migrate_data()
            
            # Print summary
            print("\n" + "="*50)
            print("MIGRATION SUMMARY")
            print("="*50)
            print(f"Total objects processed: {stats['total']}")
            print(f"Objects already existing: {stats['existing']}")
            print(f"Objects successfully migrated: {stats['migrated']}")
            print(f"Objects failed to migrate: {stats['failed']}")
            print("="*50)
            
        logging.getLogger(__name__).info("Migration completed successfully.")
        
    except WeaviateMigrationError:
        logging.getLogger(__name__).exception("Migration error")
        sys.exit(1)
    except Exception:
        logging.getLogger(__name__).exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
