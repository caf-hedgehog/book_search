from fastapi import FastAPI
from bs4 import BeautifulSoup
import requests
import pandas as pd

app = FastAPI()

#スレイピング先URLの指定
BOOK_URL = "https://www.kinokuniya.co.jp/disp/CSfDispListPage_001.jsp?qs=true&ptk=01&q=湊かなえ" #今回はサンプルデータとして湊かなえの本を複数検索

#Invoke-RestMethod -Uri "http://localhost:8002" -Method GET (windows power shell)
#curl -X GET "http://localhost:8002"
@app.get("/")
def index():
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
    

    books = []

    for i in item_list:
        #本の情報を格納するdictを用意
        book_data = {
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

    # print(books)
    pd.set_option('display.unicode.east_asian_width', True)
    df = pd.io.json.json_normalize(books)
    df.to_csv('data/result.csv')

    return "Done."