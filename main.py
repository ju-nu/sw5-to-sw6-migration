import os
import requests
import dotenv
import uuid
import time
import json

from urllib.parse import quote

dotenv.load_dotenv()

# SW5 Credentials and API URL
SW5_API_URL = os.getenv('SW5_API_URL').rstrip('/')  # Remove trailing '/'
SW5_API_USER = os.getenv('SW5_API_USER')
SW5_API_KEY = os.getenv('SW5_API_KEY')

# SW6 Credentials and API URL
SW6_API_URL = os.getenv('SW6_API_URL').rstrip('/')
SW6_ACCESS_KEY = os.getenv('SW6_ACCESS_KEY')
SW6_SECRET_KEY = os.getenv('SW6_SECRET_KEY')

# Sales Channel Name
SALES_CHANNEL_NAME = "Picksport"

# Media Folder Name in SW6
SW6_MEDIA_FOLDER_NAME = os.getenv('SW6_MEDIA_FOLDER_NAME')

SW6_TOKEN = None
SW6_TOKEN_EXPIRES_AT = 0

def get_sw6_token():
    global SW6_TOKEN
    global SW6_TOKEN_EXPIRES_AT

    url = f"{SW6_API_URL}/api/oauth/token"
    payload = {
        "client_id": SW6_ACCESS_KEY,
        "client_secret": SW6_SECRET_KEY,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    data = response.json()
    SW6_TOKEN = data['access_token']
    expires_in = data.get('expires_in', 3600)  # Default to 3600 seconds if not provided
    SW6_TOKEN_EXPIRES_AT = time.time() + expires_in - 60  # Refresh 60 seconds before expiry

def ensure_sw6_token():
    if time.time() >= SW6_TOKEN_EXPIRES_AT:
        print("Access token expired or about to expire. Refreshing token...")
        get_sw6_token()

def sw6_headers():
    ensure_sw6_token()
    return {
        'Authorization': f'Bearer {SW6_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

def get_sales_channel_info():
    url = f"{SW6_API_URL}/api/search/sales-channel"
    payload = {
        "filter": [
            {
                "type": "equals",
                "field": "name",
                "value": SALES_CHANNEL_NAME
            }
        ],
        "limit": 1,
        "includes": {
            "sales_channel": ["id", "languageId", "currencyId"]
        }
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()

    if 'errors' in data:
        raise Exception(f"Error retrieving sales channel: {data['errors']}")

    total = data.get('total', 0)
    if total == 0 or not data.get('data'):
        raise Exception(f"Sales channel '{SALES_CHANNEL_NAME}' not found.")

    sales_channel = data['data'][0]
    sales_channel_id = sales_channel['id']
    language_id = sales_channel['languageId']
    currency_id = sales_channel['currencyId']
    return sales_channel_id, language_id, currency_id

def get_sw6_media_folder_id():
    # Search for the media folder by name
    url = f"{SW6_API_URL}/api/search/media-folder"
    payload = {
        "filter": [
            {
                "type": "equals",
                "field": "name",
                "value": SW6_MEDIA_FOLDER_NAME
            }
        ],
        "limit": 1
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()
    total = data.get('total', 0)
    if total > 0 and data.get('data'):
        return data['data'][0]['id']
    else:
        # Media folder does not exist, try to create it
        media_folder_id = create_sw6_media_folder()
        return media_folder_id

def create_sw6_media_folder():
    # Get default configuration ID for media folders
    configuration_id = get_default_media_folder_configuration_id()

    url = f"{SW6_API_URL}/api/media-folder"
    payload = {
        "name": SW6_MEDIA_FOLDER_NAME,
        "useParentConfiguration": True,
        "configurationId": configuration_id
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()

    if response.content:
        data = response.json()
        return data['id']
    else:
        # No content in response, try to find the media folder again
        media_folder_id = get_sw6_media_folder_id()
        if not media_folder_id:
            raise Exception("Failed to create or retrieve media folder.")
        return media_folder_id

def get_default_media_folder_configuration_id():
    # Get default configuration ID for media folders
    url = f"{SW6_API_URL}/api/search/media-folder-configuration"
    payload = {
        "limit": 1
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()
    if data.get('data'):
        return data['data'][0]['id']
    else:
        raise Exception("No media folder configuration found in SW6.")

def get_sw6_products():
    url = f"{SW6_API_URL}/api/search/product"
    products = []
    page = 1
    limit = 500  # Maximum allowed by Shopware

    while True:
        payload = {
            "includes": {
                "product": ["id", "productNumber"]
            },
            "limit": limit,
            "page": page,
            "total-count-mode": 1  # Ensure total count is returned
        }
        response = requests.post(url, json=payload, headers=sw6_headers())
        response.raise_for_status()
        data = response.json()

        total = data.get('total', 0)

        if not data.get('data'):
            break

        products.extend(data['data'])
        print(f"Fetched page {page} with {len(data['data'])} products. Total fetched so far: {len(products)}")

        if len(products) >= total:
            print("All products have been fetched.")
            break

        page += 1

        # Respect Shopware API rate limits
        time.sleep(0.5)  # Adjust the sleep time as needed

    print(f"Total number of products fetched from Shopware: {len(products)}")
    return products

def get_sw5_product(article_number):
    url = f"{SW5_API_URL}/api/articles/{quote(article_number)}"
    auth = (SW5_API_USER, SW5_API_KEY)
    params = {'useNumberAsId': True}
    response = requests.get(url, auth=auth, params=params)
    if response.status_code == 200:
        return response.json()['data']
    elif response.status_code == 404:
        return None
    else:
        response.raise_for_status()

def get_sw5_media(media_id):
    url = f"{SW5_API_URL}/api/media/{media_id}"
    auth = (SW5_API_USER, SW5_API_KEY)
    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        return response.json()['data']
    else:
        print(f"Error fetching media with ID {media_id} from SW5.")
        return None

def get_sw5_media_url_and_extension(media_data):
    # Extract media URL from SW5 media data
    path = media_data['path']
    # If 'path' is already a full URL, use it directly
    if path.startswith('http://') or path.startswith('https://'):
        media_url = path
    else:
        # Construct the full media URL
        base_url = SW5_API_URL.rstrip('/api')
        media_url = f"{base_url}/{path}"
    # Extract the file extension from the path
    extension = os.path.splitext(path)[1][1:]  # Get extension without the dot
    return media_url, extension

def get_existing_media_id(filename_base, extension):
    url = f"{SW6_API_URL}/api/search/media"
    payload = {
        "filter": [
            {"type": "equals", "field": "fileName", "value": filename_base},
            {"type": "equals", "field": "fileExtension", "value": extension}
        ],
        "limit": 1
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()
    if data.get('data'):
        return data['data'][0]['id']
    else:
        return None

def upload_media_to_sw6(media_url, media_folder_id, filename_base, extension, alt_text):
    # Check if media already exists
    existing_media_id = get_existing_media_id(filename_base, extension)
    if existing_media_id:
        print(f"Media '{filename_base}.{extension}' already exists in SW6. Using existing media ID.")
        # Optionally update alt text if needed
        update_media_alt_text(existing_media_id, alt_text)
        return existing_media_id

    # Generate a UUID for the new media entity
    media_id = uuid.uuid4().hex

    # Create a new media entity in SW6 with the specified media_id and mediaFolderId
    url = f"{SW6_API_URL}/api/media"
    payload = {
        "id": media_id,
        "mediaFolderId": media_folder_id,
        "alt": alt_text
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()

    # Upload the media file to SW6 using the media_id by providing the URL of the image
    # Include the filename without extension and the extension separately
    upload_url = f"{SW6_API_URL}/api/_action/media/{media_id}/upload?fileName={quote(filename_base)}&extension={extension}"
    headers = {
        'Authorization': f'Bearer {SW6_TOKEN}',
        'Content-Type': 'application/json'
    }
    upload_payload = {
        "url": media_url
    }
    response = requests.post(upload_url, json=upload_payload, headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Error uploading media for product: {e}")
        print(f"Response content: {response.text}")
        raise

    # Return the media_id to be used for the product
    return media_id

def update_media_alt_text(media_id, alt_text):
    url = f"{SW6_API_URL}/api/media/{media_id}"
    payload = {
        "alt": alt_text
    }
    response = requests.patch(url, json=payload, headers=sw6_headers())
    response.raise_for_status()

def get_existing_product_media(product_id):
    url = f"{SW6_API_URL}/api/search/product-media"
    payload = {
        "filter": [
            {"type": "equals", "field": "productId", "value": product_id}
        ],
        "includes": {
            "product_media": ["id", "mediaId", "position"]
        },
        "limit": 50  # Adjust as needed
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()
    return data.get('data', [])

def get_sw6_category_ids(category_names):
    category_ids = []
    for name in category_names:
        url = f"{SW6_API_URL}/api/search/category"
        payload = {
            "filter": [
                {"type": "equals", "field": "name", "value": name}
            ],
            "limit": 1
        }
        response = requests.post(url, json=payload, headers=sw6_headers())
        response.raise_for_status()
        data = response.json()
        total = data.get('total', 0)
        if total > 0 and data.get('data'):
            category_id = data['data'][0]['id']
            category_ids.append({"id": category_id})
        else:
            print(f"Category '{name}' not found in SW6. Creating category.")
            # Create the category
            category_id = create_sw6_category(name)
            if category_id:
                category_ids.append({"id": category_id})
            else:
                print(f"Failed to create category '{name}'. Skipping this category.")
    return category_ids

def create_sw6_category(name):
    url = f"{SW6_API_URL}/api/category"
    category_id = uuid.uuid4().hex
    payload = {
        "id": category_id,
        "name": name
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    try:
        response.raise_for_status()
        return category_id
    except Exception as e:
        print(f"Error creating category '{name}': {e}")
        print(f"Response content: {response.text}")
        return None

def update_sw6_product(product_id, update_data):
    url = f"{SW6_API_URL}/api/product/{product_id}"
    response = requests.patch(url, json=update_data, headers=sw6_headers())
    response.raise_for_status()

def get_existing_product_visibilities(product_id):
    url = f"{SW6_API_URL}/api/search/product-visibility"
    payload = {
        "filter": [
            {"type": "equals", "field": "productId", "value": product_id}
        ],
        "includes": {
            "product_visibility": ["id", "salesChannelId", "visibility"]
        },
        "limit": 50  # Adjust as needed
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()
    return data.get('data', [])

def to_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() == 'true'
    if isinstance(val, int):
        return bool(val)
    return False

def get_tax_id_by_rate(tax_rate):
    url = f"{SW6_API_URL}/api/search/tax"
    payload = {
        "filter": [
            {
                "type": "equals",
                "field": "taxRate",
                "value": tax_rate
            }
        ],
        "limit": 1
    }
    response = requests.post(url, json=payload, headers=sw6_headers())
    response.raise_for_status()
    data = response.json()
    if data.get('data'):
        return data['data'][0]['id']
    else:
        raise Exception(f"No tax rate {tax_rate}% found in SW6.")

def main():
    get_sw6_token()
    try:
        sales_channel_id, language_id, default_currency_id = get_sales_channel_info()
    except Exception as e:
        print(f"Error retrieving sales channel, language ID, or currency ID: {e}")
        return
    try:
        media_folder_id = get_sw6_media_folder_id()
    except Exception as e:
        print(f"Error retrieving media folder: {e}")
        return

    sw6_products = get_sw6_products()
    total_products = len(sw6_products)  # Total number of products

    for idx, sw6_product in enumerate(sw6_products, start=1):
        article_number = sw6_product.get('productNumber')
        if not article_number:
            print(f"Product ID {sw6_product['id']} does not have a product number.")
            continue

        # Calculate progress
        products_remaining = total_products - idx
        percentage_complete = (idx / total_products) * 100

        # Updated print statement with progress indicators
        print(f"Processing product {idx}/{total_products} with article number: {article_number} "
              f"({products_remaining} remaining, {percentage_complete:.2f}% complete)")

        sw5_product = get_sw5_product(article_number)

        if sw5_product:
            # For debugging: print SW5 product data
            # Uncomment the lines below to see the SW5 product data
            # print(f"SW5 Product Data for {article_number}:")
            # print(json.dumps(sw5_product, indent=4))

            # Get the tax rate from SW5 product
            tax_rate = sw5_product.get('tax', {}).get('tax', 19.0)  # Default to 19% if not specified
            try:
                tax_rate = float(tax_rate)  # Ensure tax_rate is a float
            except ValueError:
                print(f"Invalid tax rate '{tax_rate}' for product {article_number}. Skipping.")
                continue

            # Get the tax ID in SW6 corresponding to this tax rate
            try:
                tax_id = get_tax_id_by_rate(tax_rate)
            except Exception as e:
                print(f"Error retrieving tax ID for tax rate {tax_rate}%: {e}")
                continue

            # Get the standard price from SW5
            prices = sw5_product.get('mainDetail', {}).get('prices', [])
            if prices:
                # Assuming the first price is the standard price
                sw5_price = prices[0].get('price')
            else:
                sw5_price = None

            if sw5_price is not None:
                try:
                    # SW5 price is net price
                    net_price = float(sw5_price)
                except ValueError:
                    print(f"Invalid net price '{sw5_price}' for product {article_number}. Skipping.")
                    continue

                # Calculate gross price based on the net price and tax rate
                gross_price = net_price * (1 + tax_rate / 100)
                gross_price = round(gross_price, 2)  # Optional rounding

                price_data = [
                    {
                        "currencyId": default_currency_id,
                        "gross": gross_price,
                        "net": net_price,
                        "linked": False  # Prices are not linked
                    }
                ]
            else:
                price_data = None

            # Extract data from SW5 product
            description = sw5_product.get('descriptionLong') or sw5_product.get('description')
            meta_title = sw5_product.get('metaTitle')
            meta_description = sw5_product.get('description')  # Use 'description' for metaDescription
            active_state = to_bool(sw5_product.get('active', True))  # Ensure boolean type

            # Fetch existing product media
            existing_product_media = get_existing_product_media(sw6_product['id'])
            existing_media_map = {pm['mediaId']: pm for pm in existing_product_media}

            # Extract images from SW5 product
            images = sw5_product.get('images', [])
            if not images and sw5_product.get('mainDetail', {}).get('images'):
                images = sw5_product['mainDetail']['images']

            media_ids = []

            if images:
                for idx_img, image in enumerate(images):
                    media_id = image.get('mediaId')
                    if not media_id:
                        continue
                    # Fetch media data using media_id
                    media_data = get_sw5_media(media_id)
                    if not media_data:
                        continue
                    # Get media URL, filename base, extension, and alt text
                    sw5_media_url, extension = get_sw5_media_url_and_extension(media_data)
                    filename_base = media_data.get('name', f"image_{idx_img}")
                    filename_base = os.path.splitext(filename_base)[0]  # Remove existing extension
                    if not extension:
                        extension = 'jpg'  # Default to 'jpg' if extension is missing
                    alt_text = media_data.get('description', '')
                    # Upload media to SW6 or use existing media
                    try:
                        print(f"Processing file: {filename_base}.{extension}")
                        sw6_media_id = upload_media_to_sw6(sw5_media_url, media_folder_id, filename_base, extension, alt_text)

                        # Check if media is already associated with the product
                        if sw6_media_id in existing_media_map:
                            print(f"Media {filename_base}.{extension} is already associated with product {article_number}.")
                            # Use existing ProductMedia entry and update position if necessary
                            product_media_entry = existing_media_map[sw6_media_id]
                            product_media_entry['position'] = idx_img
                        else:
                            # Create new ProductMedia entry
                            product_media_id = uuid.uuid4().hex
                            product_media_entry = {
                                "id": product_media_id,
                                "mediaId": sw6_media_id,
                                "position": idx_img
                            }
                        media_ids.append(product_media_entry)

                    except Exception as e:
                        print(f"Error uploading media for product {article_number}: {e}")
                        print(f"Filename: {filename_base}.{extension}")
                        print(f"Media URL: {sw5_media_url}")
                        continue
                # Set the first image as the cover image
                if media_ids:
                    cover_id = media_ids[0]['id']  # Use the 'id' of the product media
                else:
                    cover_id = None
            else:
                media_ids = []
                cover_id = None

            # Combine existing and new media entries, ensuring no duplicates
            all_media_entries = list({pm['mediaId']: pm for pm in existing_product_media + media_ids}.values())

            category_names = [category['name'] for category in sw5_product.get('categories', [])]

            # Get SW6 category IDs (create if not exists)
            sw6_category_ids = get_sw6_category_ids(category_names)
            if not sw6_category_ids:
                print(f"No matching categories found in SW6 for product {article_number}. Skipping category assignment.")
                sw6_category_ids = []

            # Extract custom fields from SW5
            attr4 = sw5_product.get('mainDetail', {}).get('attribute', {}).get('attr4', False)
            warenpost = sw5_product.get('mainDetail', {}).get('attribute', {}).get('warenpost', False)

            # Convert to boolean
            sim_protected_price = to_bool(attr4)
            sim_warenpost = to_bool(warenpost)

            custom_fields = {
                "sim_protected_price": sim_protected_price,
                "sim_warenpost": sim_warenpost
            }

            # Fetch existing visibilities for the product
            existing_visibilities = get_existing_product_visibilities(sw6_product['id'])

            # Prepare the visibility entry
            visibilities = []
            existing_visibility = next(
                (vis for vis in existing_visibilities if vis['salesChannelId'] == sales_channel_id),
                None
            )

            if existing_visibility:
                # Update existing visibility
                visibilities.append({
                    "id": existing_visibility['id'],
                    "productId": sw6_product['id'],
                    "salesChannelId": sales_channel_id,
                    "visibility": 30  # Desired visibility level (30 for "All")
                })
            else:
                # Create new visibility
                visibilities.append({
                    "productId": sw6_product['id'],
                    "salesChannelId": sales_channel_id,
                    "visibility": 30  # Desired visibility level
                })

            # Prepare update data
            update_data = {
                "id": sw6_product['id'],
                "active": active_state,
                "customFields": custom_fields,
                "translations": {
                    language_id: {
                        "description": description,
                        "metaTitle": meta_title,
                        "metaDescription": meta_description
                    }
                },
                "media": all_media_entries,
                "visibilities": visibilities,
                "price": price_data,
                "taxId": tax_id
            }
            if sw6_category_ids:
                update_data["categories"] = sw6_category_ids
            if cover_id:
                update_data["coverId"] = cover_id

            # Update product in SW6
            try:
                update_sw6_product(sw6_product['id'], update_data)
                print(f"Product {article_number} updated successfully.")
            except Exception as e:
                print(f"Error updating product {article_number}: {e}")

        else:
            print(f"Product {article_number} not found in SW5. Skipping.")

if __name__ == "__main__":
    main()
