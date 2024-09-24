# Shopware 5 to Shopware 6 Product Media Migration Script

This script migrates product media, descriptions, meta titles, meta descriptions, and categories from Shopware 5 to Shopware 6. It updates existing products in Shopware 6 by matching them based on the product number.

## **Features**

- Updates product descriptions, meta titles, and meta descriptions.
- Maps categories from SW5 to SW6 by matching category names.
- Transfers all product images from SW5 to SW6, preserving filenames and alt texts.
- Sets the first image as the cover image for the product.
- Handles pagination to process all products.

## **Prerequisites**

- Python 3.6 or higher.
- Access to the Shopware 5 and Shopware 6 APIs with appropriate permissions.

## **Installation**

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ju-nu/sw5-to-sw6-migration.git
   cd sw5-to-sw6-migration
   ```

2. **Create a virtual environment (optional but recommended):**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install required packages:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create and configure the `.env` file:**

   Copy the `.env.example` file to `.env` and update the values with your actual credentials.

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file:

   ```ini
   SW5_API_URL=https://your-sw5-shop-url
   SW5_API_USER=your_sw5_username
   SW5_API_KEY=your_sw5_api_key

   SW6_API_URL=https://your-sw6-shop-url
   SW6_ACCESS_KEY=your_sw6_access_key
   SW6_SECRET_KEY=your_sw6_secret_key

   SALES_CHANNEL_NAME=YourSalesChannelName
   SW6_MEDIA_FOLDER_NAME=YourMediaFolderName
   ```

## **Usage**

Run the script:

```bash
python3 main.py
```

The script will process all products in Shopware 6, update their descriptions, meta information, categories, and transfer associated images from Shopware 5.

## **Configuration**

- **SW5_API_URL**: Base URL of your Shopware 5 store (without trailing `/api`).
- **SW5_API_USER**: API username for Shopware 5.
- **SW5_API_KEY**: API key for Shopware 5.
- **SW6_API_URL**: Base URL of your Shopware 6 store (without trailing `/api`).
- **SW6_ACCESS_KEY**: Access key for Shopware 6 API.
- **SW6_SECRET_KEY**: Secret key for Shopware 6 API.
- **SALES_CHANNEL_NAME**: Name of the sales channel in Shopware 6.
- **SW6_MEDIA_FOLDER_NAME**: Name of the media folder in Shopware 6 where images will be stored.

## **Notes**

- Ensure that category names in SW6 match those in SW5 for correct mapping.
- The script assumes that product numbers are unique and used to match products between SW5 and SW6.
- If a product is not found in SW5, it will be skipped.
- If an image fails to upload, the script will continue processing other images and products.

## **License**

This project is licensed under the MIT License.