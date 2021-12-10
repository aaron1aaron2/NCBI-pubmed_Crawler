# NCBI pubmed Crawler
[NCBI pubmed](https://pubmed.ncbi.nlm.nih.gov/) (National Center for Biotechnology Information)

![](imgCrawl-target-example.png)

## How to use 
**Step 1**: install packages
```shell
pip install -r requirements.txt
```
**Step 2**: Start crawler on the command line
```shell
python ncbi_crawler.py 
```

## Custom parameters
**file**
- `--output_path` : 爬取結果儲存路徑
- `--log_pathlog` : log 儲存路徑
  
**search**
- `--keyword` : 搜尋關鍵字
- `--start_year` : 開始年分(>= 1963)
- `--end_year` : 結束年分
- `--page_size` : 一頁搜尋結果數量(10、20、50、100、200)

**control**
- `--wait_time` : 每次 request 最低間隔時間(秒)
- `--show_freq` : 爬多少筆論文時顯示一次進度
- `--retry_time` : 重複測試的次數(連續爬取失敗的次數)
- `--retry_wait_min` : 每次 retry 等待時間(分鐘)

## Example
Use keyword `IVF` to find published literature for `2010` ~ `2022`
```shell
python ncbi_crawler.py --keyword IVF --start_year 2010 --end_year 2022
```
