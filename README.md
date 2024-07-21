Python project to scrape website https://dentalstall.com/shop/page/1/

1. Used FastApi for routing
2. Used Redis for caching products
3. Data storage is done in json file which can be used for further usage and memory
4. Retry mechanism of 3 retries
5. Authenticate using simple token

To run the project first install
pip install fastapi uvicorn requests beautifulsoup4 pydantic redis

Run Redis on 127.0.0.1:6379 and ensure it is running

Start server using 
uvicorn main:app --reload



curl --location 'http://127.0.0.1:8000/scrape' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Authorization: Basic dXNlcjpteXNlY3JldHRva2Vu' \
--data-urlencode 'pages=1' \
--data-urlencode 'proxy=https'
