from datetime import datetime, timedelta, timezone

import weaviate
from weaviate.classes.query import Filter, Sort

client = weaviate.connect_to_local()

collection = client.collections.get("Copertine")

# Calculate date 30 days ago from today
today = datetime.now(timezone.utc)
thirty_days_ago = today - timedelta(days=30)
thirty_days_ago_iso = thirty_days_ago.isoformat()

# Query articles from last 30 days
response = collection.query.fetch_objects(
    filters=Filter.by_property("editionDateIsoStr").greater_than(thirty_days_ago_iso),
    sort=Sort.by_property(name="editionDateIsoStr", ascending=False),
    limit=30
)

for o in response.objects:
    props = o.properties
    #print("Full properties:", props)
    if 'editionId' in props or 'captionStr' in props:
        print(f"editionId: {props.get('editionId', 'N/A')}")
        print(f"captionStr: {props.get('captionStr', 'N/A')}")
        print("-" * 50)
client.close()
