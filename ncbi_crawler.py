# encoding: utf-8
"""
@author: yen-nan ho
@contact: aaron1aaron2@gmail.com
@gitHub: https://github.com/aaron1aaron2
@Create Date: 2021/12/5
"""
import re
import os
import time
import tqdm
import random
import argparse
import requests
import pandas as pd

from datetime import datetime
from bs4 import BeautifulSoup

from utils import set_log, get_error_message

def get_args():
    parser = argparse.ArgumentParser()

    # file
    parser.add_argument('--output_path', type=str, default = 'output/result.csv',
                        help = '爬取結果儲存路徑')
    parser.add_argument('--log_path', type=str, default = 'output/log.txt',
                        help = 'log 儲存路徑')

    # search
    parser.add_argument('--keyword', type=str, default = 'IVF',
                        help = '搜尋關鍵字')
    parser.add_argument('--start_year', type=int, default = 2021,
                        help = '開始年分(>= 1963)')
    parser.add_argument('--end_year', type=int, default = 2022,
                        help = '結束年分')
    parser.add_argument('--page_size', type=int, default = 10,
                        help = '一頁搜尋結果數量(10、20、50、100、200)')

    # control
    parser.add_argument('--wait_time', type=int, default = 1,
                        help = '每次 request 最低間隔時間(秒)')
    parser.add_argument('--show_freq', type=int, default = 1000,
                        help = '爬多少筆論文時顯示一次進度')
    parser.add_argument('--retry_time', type=int, default = 10,
                        help = '重複測試的次數(連續爬取失敗的次數)')
    parser.add_argument('--retry_wait_min', type=int, default = 5,
                        help = '每次 retry 等待時間(分鐘)')

    args = parser.parse_args()

    return args

def check_args(args):
    # 結束年分不超過現在年分+1
    current_year = int(datetime.now().strftime('%Y')) + 1 # datetime.now().strftime('%Y%m%d%H%M%S')
    assert (args.end_year <= current_year+1), f"End year must <= {current_year}"
    # 開始年分不小於1963
    assert (args.start_year >= 1963), "'--start_year' must >= 1963"
    # 開始年分不能大於結束年分
    assert (args.end_year >= args.start_year), "'--end_year' must >= Start year"

    # 每一頁顯示論文數只能固定數量(網站限制)
    assert (args.page_size in [10, 20, 50, 100, 200]), \
        "'--page_size' can only be set to the following numbers: 10, 20, 50, 100, 200"

    return args

class Cralwer(object):
    def __init__(self, **kwargs):
        # file
        self.output_path = kwargs.pop('output_path')
        self.log = kwargs.pop('log')

        # search
        self.headers = kwargs.pop('headers')
        self.keyword = kwargs.pop('keyword')
        self.start_year = kwargs.pop('start_year')
        self.end_year = kwargs.pop('end_year')
        self.page_size = kwargs.pop('page_size')

        # control
        self.wait_time = kwargs.pop('wait_time')
        self.show_freq = kwargs.pop('show_freq')
        self.retry_time = kwargs.pop('retry_time')
        self.retry_wait_min = kwargs.pop('retry_wait_min')

        super(Cralwer, self).__init__(**kwargs)

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def generate_url(self, keyword, page=1, start_year='', end_year='', page_size=10):
        url = f"https://pubmed.ncbi.nlm.nih.gov/?term={keyword}&format=abstract"
        if (start_year!='') & (end_year!=''):
            url = url + f"&filter=years.{start_year}-{end_year}"
        if page_size != 10:
            url = url + f"&size={page_size}"
        if page != 1:
            url = url + f"&page={page}"

        return url
    
    def get_search_result_info(self, soup):
        results_amount = soup.find("div", class_="results-amount")
        try:
            total_articles = results_amount.span.text
            total_articles = total_articles.replace(',','')
            self.log.info(f'Results amount: {total_articles}')
        except:
            self.log.warning('Cannot find results amount')

        total_page = soup.find("label", class_="of-total-pages")
        try:
            total_page = re.match('of (\d+)', total_page.text)[1]
            self.log.info(f'Total page: {total_page}')
        except:
            self.log.warning('Cannot find total page')

        return total_articles, total_page
    
    def get_info_in_page(self, article_ls):
        result = {}
        # 題目
        result["title"] = [i.find("h1", class_="heading-title").text.strip() 
                            if (i.find("h1", class_="heading-title") != None) else '' 
                            for i in article_ls]
        # 引用
        result["citation"] = [i.find("div", class_="article-citation").text.strip() 
                                if (i.find("div", class_="article-citation") != None) else '' 
                                for i in article_ls]
        # 類型
        result["type"] = [i.find("div", class_="publication-type").text 
                            if (i.find("div", class_="publication-type") != None) else '' 
                            for i in article_ls]
        # 作者
        result["authors"] = ['||'.join([author.text.strip() for author in i.find_all("a", class_="full-name")])
                            if (len(i.find_all("a", class_="full-name")) != 0) else '' 
                            for i in article_ls]
        # 聯絡資訊
        result["affiliation"] = [i.find("div", class_="affiliations").text.strip()
                                if (i.find("div", class_="affiliations") != None) else '' 
                                for i in article_ls]
        # 識別碼 
        result["identifier"] = ['||'.join([xid.text.strip() for xid in i.find("ul", class_="identifiers").find_all("li")])
                                if (i.find("ul", class_="identifiers") != None) else '' 
                                for i in article_ls]
        # 摘要
        result["abstract"] = [i.find("div", class_="abstract-content").text.strip()
                                if (i.find("div", class_="abstract-content") != None) else '' 
                                for i in article_ls]
        # 關鍵字
        result["keyword"] = [i.find("strong", class_="sub-title", text=re.compile('Keywords:')).parent.text.strip()
                                if (i.find("strong", class_="sub-title", text=re.compile('Keywords:')) != None) else '' 
                                for i in article_ls]
        # 被引用狀態
        result["stats"] = ['||'.join([xid.text.strip() for xid in i.find("div", class_="stats").find_all("li")])
                            if (i.find("div", class_="stats") != None) else '' 
                            for i in article_ls]
        # full text link
        result["fulltext_url"] = ['||'.join(['{}({})'.format(xid.text.strip(), xid["href"]) for xid in i.find("div", class_="full-text-links-list").find_all("a")])
                                    if (i.find("div", class_="full-text-links-list") != None) else '' 
                                    for i in article_ls]
        # paper page url
        result["paper_url"] = ['https://pubmed.ncbi.nlm.nih.gov' + i.find("a", class_="details-link")["href"].strip()
                                if (i.find("a", class_="details-link") != None) else '' 
                                for i in article_ls]
        
        return result

    def request_session(self, url):
        retry_count = 0 
        while retry_count <= self.retry_time:
            try:
                respond = requests.get(url, headers = self.headers)
                return respond
            except Exception as e:
                retry_count+=1
                self.log.warning(get_error_message(e))
                time.sleep(self.retry_wait_min*60)

        self.log.error(f"retry {retry_count} time， no respond from link({url})")
        exit()

    def clean_data(self, df):
        # 不調整 -> title、type、abstract、paper_url、fulltext_url

        # abstract
        df['abstract'] = df['abstract'].str.replace('\s\s+', '', regex=True)

        # citation
        df['citation'] = df['citation'].astype(str)
        df['citation'] = df.apply(lambda df: re.sub(df['type'], '', df['citation']), axis=1) # citation 開頭會有 type
        
        def muti_remove(x):
            remove_ls = ['Actions', 'Search in PubMed', 'Search in NLM Catalog', 'Add to Search']
            remove_pattern = '|'.join(remove_ls)
            return re.sub(remove_pattern, '', x)

        df['citation'] = df['citation'].apply(muti_remove) # 在 tag 裡多餘的 text
        df['citation'] = df['citation'].str.replace('\n', '') # 換行
        df['citation'] = df['citation'].str.replace('\s\s+', '', regex=True) # 移除多餘的空白

        df['year'] = df['citation'].str.extract('. (\d+)')

        # authors
        def drop_duplicate(mylist):
            seen = {}
            new_list = [seen.setdefault(x, x) for x in mylist if x not in seen]
            return new_list

        df['authors'] = df['authors'].apply(lambda x: '、'.join(drop_duplicate(x.split('||')))) # 去掉重複的作者(用set 順序會亂)

        # keyword
        df['keyword'] = df['keyword'].str.replace('Keywords:', '').str.strip()

        # Affiliations
        df['affiliation'] = df['affiliation'].str.replace('Affiliations', '').str.strip()

        # identifier -> PMID、PMCID、DOI
        df['identifier'] = df['identifier'].str.replace('\n', '')
        df['identifier'] = df['identifier'].str.replace('\s\s+', '', regex=True)

        id_extract = df['identifier'].str.extract('PMID:(?P<PMID>\d+)\|\|PMCID:(?P<PMCID>.+)\|\|DOI:(?P<DOI>.+)')
        un_match_id = id_extract['DOI'].isna()
        id_extract.loc[un_match_id, ['PMID', 'DOI']] = df.loc[un_match_id, 'identifier'].str.extract('PMID:(?P<PMID>\d+)\|\|DOI:(?P<DOI>.+)')
        df = df.join(id_extract)

        # stats
        df['stats'] = df['stats'].str.replace('\n', '') 
        df['stats'] = df['stats'].str.replace('\s\s+', '', regex=True)
        df['Cited_num'] = df['stats'].str.extract('Cited by (\d+)articles')
        df['references_num'] = df['stats'].str.extract('\|\|(\d+)references')
        df['figures_num'] = df['stats'].str.extract('\|\|(\d+)figures')

        return df

    def output_data(self, result):
        page_result_df = pd.DataFrame(result)
        page_result_df = self.clean_data(page_result_df)

        cols_order = ['title', 'year', 'type', 'keyword', 'Cited_num', 'references_num', 'figures_num',
                    'authors', 'abstract', 'paper_url', 'fulltext_url', 'PMID',
                    'PMCID', 'DOI', 'citation', 'affiliation', 'identifier', 'stats']

        if os.path.exists(self.output_path):
            page_result_df[cols_order].to_csv(self.output_path, mode='a', index=False, header=None)
        else:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            page_result_df[cols_order].to_csv(self.output_path, mode='w', index=False)

    def run(self):
        url = self.generate_url(
                            keyword=self.keyword, 
                            start_year=self.start_year,
                            end_year=self.end_year,
                            page_size=self.page_size)
        self.log.info(f'URL: {url}')

        respond = self.request_session(url)
        soup = BeautifulSoup(respond.text, "lxml")

        total_articles, total_page = self.get_search_result_info(soup)
        
        articles_Crawled = 0
        milestone = self.show_freq
        for page in tqdm.tqdm(range(1, int(total_page)+1)):
            start_time = time.time()
            # step1: 獲取網址
            if page > 1:
                url = self.generate_url(
                                    keyword=self.keyword, 
                                    page=page,
                                    start_year=self.start_year,
                                    end_year=self.end_year,
                                    page_size=self.page_size)

                respond = self.request_session(url)
                soup = BeautifulSoup(respond.text, "lxml")

            # step2: 爬取該 page 資訊
            article_ls = soup.find_all(class_="article-overview") # get articles in page (主要爬取的物件)
            result = self.get_info_in_page(article_ls)

            # step3: 整理與輸出資料
            self.output_data(result)

            # 進度顯示
            articles_Crawled += len(article_ls)

            if articles_Crawled > milestone:
                self.log.info('leftove articles: {}'.format(int(total_articles)-articles_Crawled))
                milestone += self.show_freq

            # if (articles_Crawled % 100) == 0:
            #     break
            
            # 時間控制
            timeuse =  time.time() - start_time
            if timeuse < self.wait_time:
                time.sleep(round(random.uniform(self.wait_time - timeuse, 1), 3))

def main():
    args = get_args()
    args = check_args(args)
    log = set_log(args.log_path)

    ncibCralwer = Cralwer(
                log = log,
                output_path = args.output_path,
                keyword = args.keyword,
                start_year = args.start_year,
                end_year = args.end_year,
                page_size = args.page_size,
                wait_time = args.wait_time,
                show_freq = args.show_freq,
                retry_time = args.retry_time,
                retry_wait_min = args.retry_wait_min,
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'}
    )
    ncibCralwer.run()

if __name__ == '__main__':
    main()