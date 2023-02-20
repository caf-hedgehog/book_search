from fastapi import (
    FastAPI,
    status,
)
from fastapi.responses import JSONResponse
from bs4 import BeautifulSoup
from elasticsearch import AsyncElasticsearch, Elasticsearch, helpers
from elasticsearch.client import IndicesClient

import asyncio
import requests
import pandas as pd
import json
import csv

app = FastAPI()

#Elasticsearchクライアント作成
ES_URL = 'http://elasticsearch:9200'
ES_USER = ''
ES_PASS = ''
# es = Elasticsearch(ES_URL, http_auth=(ES_USER, ES_PASS))
es = AsyncElasticsearch(ES_URL)
indices_client = IndicesClient(es)

#スレイピング先URLの指定
BOOK_URL = "https://www.kinokuniya.co.jp/disp/CSfDispListPage_001.jsp?qs=true&ptk=01&q=湊かなえ" #今回はサンプルデータとして湊かなえの本を複数検索

#Invoke-RestMethod -Uri "http://localhost:8002" -Method GET (windows power shell)
#curl -X GET "http://localhost:8002"
@app.get("/")
async def index():
    return {"Hello" : "World!!!"}

#Invoke-RestMethod -Uri "http://localhost:8002/dummy_data" -Method GET (windows power shell)
#curl -X GET "http://localhost:8002/dummy_data"
@app.get("/dummy_data")
def index():
    res = requests.get(BOOK_URL)
    
    #文字化け防止
    res.encoding = res.apparent_encoding
    
    html_data = BeautifulSoup(res.text, "html.parser")
    item_list = html_data.select('[class="list_area_wrap"] [class="heightLine-2"] a')
    
    id = 0
    books = []

    for i in item_list:
        #本の情報を格納するdictを用意
        book_data = {
            "id": id,
            "title": "",
            "writer": "",
            "description": ""
        }

        #本のタイトルを格納
        book_data["title"] = i.text

        url = i.get('href')
        res = requests.get(url)
        #文字化け防止
        res.encoding = res.apparent_encoding
        html_data = BeautifulSoup(res.text, "html.parser")
        
        #著者情報を格納
        book_data["writer"] = (html_data.select('[class="infobox ml10 mt10"] > ul > li > a'))[0].text

        #本の詳細（あらすじ）を格納 :予約商品や電子版などたまにデータが存在しない場合あり:
        try:
            book_data["description"] = (html_data.select('[itemprop="description"]'))[0].text
        except:
            book_data["description"] = "None"
        
        books.append(book_data)
        id += 1

    pd.set_option('display.unicode.east_asian_width', True)
    df = pd.io.json.json_normalize(books)
    df.to_csv('data/result.csv', index=False)

    return JSONResponse(
        content={"msg": "input data OK"}, status_code=status.HTTP_200_OK
    )

#Invoke-RestMethod -Uri "http://localhost:8002/create_test_data" -Method GET (windows power shell)
#curl -X GET "http://localhost:8002/create_test_data"
@app.get("/create_test_data", status_code=status.HTTP_200_OK)
async def create_test_data():
    saveSize = 10
    
    try:
        with open('./data/result.csv', encoding='utf-8') as data:
            print("csv read")
            csvReader = csv.DictReader(data)
            actions = []
            for row in csvReader:
                source = row
                action = {
                    "_index": "product-index",
                    "_op_type": "index",
                    "_id": row.get("id"),
                    "_source": source
                }
                actions.append(action)
                if len(actions) >= saveSize:
                    await helpers.async_bulk(es, actions)
                    del actions[0:len(actions)]

            if len(actions) > 0:
                print("Writing data to es")
                await helpers.async_bulk(es, actions)
                
            return JSONResponse(
                content={"msg": "Data created successfully!"}, status_code=status.HTTP_200_OK
            )
    except Exception as e:
        return JSONResponse(content=to_json(e), status_code=status.HTTP_400_BAD_REQUEST)


########## index ##################################################

# curl -X POST -H "Content-Type: application/json" localhost:8002/indices/product-index
@app.post("/indices/{index_name}", status_code=status.HTTP_200_OK)
async def create_index(index_name):

    #kuromoji settings
    setting = {
        "settings": {
            "analysis": {
                "tokenizer": {
                    "kuromoji_search": {
                        "type": "kuromoji_tokenizer",
                        "mode": "search"
                    }
                },

                "analyzer": {
                    "my_kuromoji_analyzer": {
                        "type": "custom",
                        "tokenizer": "kuromoji_search",
                        "char_filter": [
                            "kuromoji_iteration_mark"
                        ],
                        "filter": [
                            "kuromoji_part_of_speech",
                            "kuromoji_number",
                            "kuromoji_baseform",
                            "ja_stop"
                        ]
                    }
                },

                "filter": {
                    "kuromoji_part_of_speech": {
                        "type": "kuromoji_part_of_speech"
                    }
                }
            }
        }
    }
    try:
        headers = {
            'Content-Type': 'application/json',
        }
        res = await es.indices.create(index=index_name, body=setting)
        return JSONResponse(content=to_json(res), status_code=status.HTTP_200_OK)
    except Exception as e:
        return JSONResponse(content=to_json(e), status_code=status.HTTP_400_BAD_REQUEST)

# curl localhost:8002/indices/{index_name} -H "Content-Type: application/json"
@app.get("/indices/{index_name}")
async def get_index(index_name):
    mapping = {
        "mapping": {
            "properties": {
                "content": {
                    "type": "text",
                    "analyzer": "my_kuromoji_analyzer",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 8191
                        }
                    }
                }
            }
        }
    }

    try:
        res = await es.indices.get_mapping(index=index_name, body=mapping)
        return JSONResponse(content=to_json(res), status_code=status.HTTP_200_OK)
    except Exception as e:
        return JSONResponse(content=to_json(e), status_code=status.HTTP_400_BAD_REQUEST)

# curl -X DELETE localhost:8002/indices/product-index
@app.delete("/indices/{index_name}")
async def delete_index(index_name):
    try:
        res = await es.indices.delete(index=index_name)
        return JSONResponse(content=to_json(res), status_code=status.HTTP_200_OK)
    except Exception as e:
        return JSONResponse(content=to_json(e), status_code=status.HTTP_400_BAD_REQUEST)

def to_json(content):
    return json.loads(json.dumps(content, default=str))