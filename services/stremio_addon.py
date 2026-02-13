import requests
import time


def fetch_manifest(manifest_url):
    """Fetch and validate the Stremio addon manifest."""
    try:
        response = requests.get(manifest_url, timeout=10)
        response.raise_for_status()
        manifest = response.json()
        
        if "catalogs" not in manifest:
            print("[ERROR] Manifest does not contain 'catalogs'")
            return None
        
        return manifest
    except Exception as e:
        print(f"[ERROR] Failed to fetch manifest: {e}")
        return None


def extract_catalog_ids(manifest_url, max_pages=5, stop_check=None, select_catalog_func=None):
    """
    Fetch catalog from Stremio addon and extract IMDb/TMDB IDs.
    Returns a list of IDs (tt... for IMDb,tmdb:... for TMDB).
    max_pages: Maximum number of pages to fetch (default 5)
    stop_check: Callback function that returns True if we should stop early
    select_catalog_func: Function(catalogs) -> selected_catalog (or None)
    """
    if stop_check and stop_check():
        return []

    manifest = fetch_manifest(manifest_url)
    if not manifest:
        return []
    
    catalogs = manifest.get("catalogs", [])
    if not catalogs:
        print("[ERROR] No catalogs found in manifest")
        return []
    
    # Filter only movie/series catalogs if needed, but lets keep it generic
    # If multiple catalogs and select function provided, ask user
    catalog = catalogs[0]
    
    if len(catalogs) > 1 and select_catalog_func:
        print(f"[INFO] Manifest has {len(catalogs)} catalogs. Asking user to select...")
        selected = select_catalog_func(catalogs)
        if selected:
            catalog = selected
            print(f"[INFO] User selected catalog: {catalog.get('name', 'Unknown')}")
        else:
            print("[WARN] User cancelled catalog selection.")
            return []

    if stop_check and stop_check():
        return []

    catalog_id = catalog.get("id")
    catalog_type = catalog.get("type", "movie")
    page_size = catalog.get("pageSize", 100)
    
    print(f"[INFO] Using catalog: {catalog_id} (type: {catalog_type})")
    
    # Compute base URL (remove /manifest.json)
    base_url = manifest_url.replace("/manifest.json", "")
    
    # Fetch catalog items with pagination
    all_ids = []
    skip = 0
    pages_fetched = 0
    
    while pages_fetched < max_pages:
        if stop_check and stop_check():
            print("[INFO] Stop requested during catalog fetch.")
            break

        catalog_url = f"{base_url}/catalog/{catalog_type}/{catalog_id}.json?skip={skip}"
        print(f"[INFO] Fetching catalog page {pages_fetched+1}/{max_pages} (skip={skip})...")
        
        try:
            response = requests.get(catalog_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            metas = data.get("metas", [])
            if not metas:
                print("[INFO] No more items in catalog")
                break
            
            # Extract IDs from metas
            for meta in metas:
                item_id = meta.get("id", "")
                
                # Extract TMDB or IMDb ID
                if item_id.startswith("tmdb:"):
                    # TMDB ID
                    all_ids.append(item_id)
                elif item_id.startswith("tt"):
                    # IMDb ID
                    all_ids.append(item_id)
            
            print(f"[INFO] Found {len(metas)} items in this page, total collected: {len(all_ids)}")
            pages_fetched += 1
            
            # Move to next page
            skip += page_size
            time.sleep(0.5)  # Be nice to the addon server
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch catalog page: {e}")
            break
    
    print(f"[INFO] Total IDs extracted from addon: {len(all_ids)}")
    return all_ids
