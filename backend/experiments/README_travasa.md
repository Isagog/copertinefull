# Travasa - Weaviate Data Migration Script

## Overview

Travasa is a Python script designed to migrate data between two Weaviate instances. It connects to an "old" Weaviate instance and a "new" Weaviate instance, then copies all objects from the old Copertine collection to the new one, avoiding duplicates based on the `editionId` property.

## Configuration

The script connects to two Weaviate instances:

- **Old Weaviate**: `localhost:8080` (GRPC: `50051`)
- **New Weaviate**: `localhost:8090` (GRPC: `50091`)

## Environment Variables

The script uses the following environment variables from the `.secrets` file:

- `COP_COPERTINE_COLLNAME`: Name of the Copertine collection (defaults to "Copertine")
- `COP_WEAVIATE_API_KEY`: API key for Weaviate authentication (optional)

## Usage

Run the script from the backend directory:

```bash
cd backend
poetry run python experiments/travasa.py
```

**Note**: Make sure both Weaviate instances are running before executing the script:
- Old Weaviate should be accessible at `localhost:8080`
- New Weaviate should be accessible at `localhost:8090`

## Features

- **Duplicate Prevention**: Checks if objects already exist in the new collection based on `editionId`
- **Progress Logging**: Logs progress every 100 processed objects
- **Error Handling**: Robust error handling with detailed logging
- **Statistics**: Provides a summary of migration results
- **Resource Cleanup**: Properly closes Weaviate connections

## Output

The script will:

1. Connect to both Weaviate instances
2. Ensure the Copertine collection exists in both instances
3. Iterate through all objects in the old collection
4. Check for duplicates in the new collection
5. Insert non-duplicate objects into the new collection
6. Display a summary with statistics

## Logging

The script creates a log file `travasa_migration.log` with detailed information about the migration process.

## Migration Statistics

At the end of the migration, you'll see a summary like:

```
==================================================
MIGRATION SUMMARY
==================================================
Total objects processed: 1500
Objects already existing: 200
Objects successfully migrated: 1250
Objects failed to migrate: 50
==================================================
```

## Error Handling

The script handles various error scenarios:

- Connection failures to Weaviate instances
- Missing collections (automatically creates them)
- Individual object insertion failures
- Network timeouts and other exceptions

## Schema

The script migrates all properties defined in the Copertine collection schema:

- `testataName`
- `editionId`
- `editionDateIsoStr`
- `editionImageFnStr`
- `captionStr`
- `kickerStr`
- `captionAIStr`
- `imageAIDeStr`
- `modelAIName`
