import requests
import json
import time

# Constants
NOTION_TOKEN = 'secret_4uf4gOTQVK32FUgSwo2eswnoFyNJgJMkdCR2qhnrvVz'  # Replace with your Notion token
DATABASE_ID = 'ea3e144eb4d140c2b7417a048549416a'    # Replace with your Notion database ID
AUTHOR_DATABASE_ID = 'ed43f33a08a64440bc966d0670cab344'      # Replace with your Author database ID
GENRE_DATABASE_ID = '6bdb8b25ca5d45e49cdd09aa615779e2'        # Replace with your Genre database ID
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2021-08-16"
}

# Function to fetch book details from Google Books API
def get_book_details(title):
    google_books_url = f"https://www.googleapis.com/books/v1/volumes?q={title}"
    response = requests.get(google_books_url)
    if response.status_code != 200:
        print(f"Error fetching data from Google Books API: {response.status_code}, {response.text}")
        return None

    data = response.json()
    if "items" in data:
        book_info = data["items"][0]["volumeInfo"]
        description = book_info.get("description", "No Description")
        if len(description) > 2000:
            description = description[:2000]  # Truncate description to 2000 characters

        book_details = {
            "title": book_info.get("title", "No Title"),
            "authors": book_info.get("authors", []),
            "published_date": book_info.get("publishedDate", "No Date"),
            "description": description,
            "publisher": book_info.get("publisher", "No Publisher"),
            "page_count": book_info.get("pageCount", 0),
            "categories": book_info.get("categories", [])
        }
        return book_details
    return None

# Function to find or create an entry in a related database
def find_or_create_entry(database_id, name):
    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    query_data = {
        "filter": {
            "property": "Name",  # Ensure this matches the property name in your Notion database
            "text": {
                "equals": name
            }
        }
    }
    print(f"Querying Notion database {database_id} for name: {name}")
    response = requests.post(query_url, headers=HEADERS, data=json.dumps(query_data))
    if response.status_code == 200:
        results = response.json().get("results")
        if results:
            entry_id = results[0]["id"]
            print(f"Found existing entry: {entry_id}")
            return entry_id
        else:
            create_url = "https://api.notion.com/v1/pages"
            create_data = {
                "parent": {"database_id": database_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": name}}]}  # Ensure this matches the property name in your Notion database
                }
            }
            print(f"Creating new entry in Notion database {database_id} for name: {name}")
            create_response = requests.post(create_url, headers=HEADERS, data=json.dumps(create_data))
            if create_response.status_code == 200:
                entry_id = create_response.json()["id"]
                print(f"Created new entry: {entry_id}")
                return entry_id
            else:
                print(f"Error creating entry: {create_response.status_code}, {create_response.text}")
    else:
        print(f"Error querying database: {response.status_code}, {response.text}")
    return None

# Function to update Notion database item
def update_notion_item(page_id, book_details):
    author_ids = []
    for author in book_details["authors"]:
        if author:
            author_id = find_or_create_entry(AUTHOR_DATABASE_ID, author)
            if author_id:
                author_ids.append(author_id)

    genre_ids = []
    for category in book_details["categories"]:
        if category:
            genre_id = find_or_create_entry(GENRE_DATABASE_ID, category)
            if genre_id:
                genre_ids.append(genre_id)

    update_url = f"https://api.notion.com/v1/pages/{page_id}"
    update_data = {
        "properties": {
            "Title": {"title": [{"text": {"content": book_details["title"]}}]},  # Ensure this matches your property name
            "Authors": {"relation": [{"id": author_id} for author_id in author_ids]},  # Ensure this matches your property name
            "Published Date": {"date": {"start": book_details["published_date"]}},  # Ensure this matches your property name
            "Description": {"rich_text": [{"text": {"content": book_details["description"]}}]},  # Ensure this matches your property name
            "Publisher": {"rich_text": [{"text": {"content": book_details["publisher"]}}]},  # Ensure this matches your property name
            "Page Count": {"number": book_details["page_count"]},  # Ensure this matches your property name
            "Genres": {"relation": [{"id": genre_id} for genre_id in genre_ids]}  # Ensure this matches your property name
        }
    }
    print(f"Updating Notion page with data: {json.dumps(update_data, indent=2)}")
    response = requests.patch(update_url, headers=HEADERS, data=json.dumps(update_data))
    if response.status_code != 200:
        print(f"Error updating Notion page {page_id}: {response.status_code}, {response.text}")
    return response.status_code

# Function to get new entries from Notion database
def get_new_entries():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching data from Notion API: {response.status_code}, {response.text}")
        return []

    data = response.json()
    new_entries = []
    for result in data["results"]:
        if "properties" in result:
            properties = result["properties"]
            title = properties.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "No Title")
            new_entries.append({"id": result["id"], "title": title})

    return new_entries

# Main function
def main():
    while True:
        print("Checking for new entries...")
        new_entries = get_new_entries()
        print(f"New entries found: {len(new_entries)}")
        for entry in new_entries:
            print(f"Fetching details for: {entry['title']}")
            book_details = get_book_details(entry["title"])
            if book_details:
                print(f"Updating Notion entry: {entry['title']}")
                update_status = update_notion_item(entry["id"], book_details)
                if update_status == 200:
                    print(f"Successfully updated entry {entry['title']}")
                else:
                    print(f"Failed to update entry {entry['title']} with status code {update_status}")
            else:
                print(f"Could not find details for {entry['title']}")

        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    main()
