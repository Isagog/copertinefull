import os
import weaviate
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the .secrets file
secrets_path = Path(__file__).parent.parent / '.secrets'
load_dotenv(dotenv_path=secrets_path)

# Fetch class names from environment variables
COP_COPERTINE_COLLNAME = os.getenv(
    "COP_COPERTINE_COLLNAME", "Copertine",
)

# Weaviate connection
weaviate_url = os.getenv("COP_WEAVIATE_URL")
weaviate_api_key = os.getenv("COP_WEAVIATE_API_KEY")

if "localhost" in weaviate_url or "127.0.0.1" in weaviate_url:
    from urllib.parse import urlparse
    parsed_url = urlparse(weaviate_url)
    weaviate_client = weaviate.connect_to_local(
        host=parsed_url.hostname,
        port=parsed_url.port,
    )
else:
    weaviate_client = weaviate.connect_to_wcs(
        cluster_url=weaviate_url,
        auth_credentials=weaviate.auth.AuthApiKey(weaviate_api_key),
    )

# Delete the collection
if weaviate_client.collections.exists(COP_COPERTINE_COLLNAME):
    weaviate_client.collections.delete(COP_COPERTINE_COLLNAME)
    print(f"Collection '{COP_COPERTINE_COLLNAME}' deleted.")
else:
    print(f"Collection '{COP_COPERTINE_COLLNAME}' does not exist.")

weaviate_client.close()
