
import pandas as pd
import os
import re
import sqlite3


class CreateTaiwanPresidentialElection2024DB:

    """
    建立 2024 總統大選資料庫的處理類別。
    - 讀取 data 資料夾下的所有 Excel 開票所資料。
    - 整理成投票所 (polling_places)、候選人 (candidates)、投票明細 (votes)。
    - 匯入 SQLite 資料庫並建立檢視表 votes_by_village。
    """

    def __init__(self):
        """
        初始化時自動掃描 data 資料夾，取得所有縣市名稱 (county_names)。
        - 只抓檔名中含「各投開票所」且副檔名為 .xlsx 的檔案。
        - 透過正則表達式取得括號內的縣市名稱。
        """
        county_names = []
        file_names = os.listdir("data")  # 讀取 data 資料夾下所有檔案名稱
        
        for file_name in file_names:
            if "各投開票所" in file_name and file_name.endswith(".xlsx"):
                match = re.search(r"\((.*?)\)", file_name)  # 抓取括號內縣市名稱
                if match:
                    county_names.append(match.group(1)) # 把縣市名稱加入名單

        self.county_names = county_names


    def tidy_county_dataframe(self, county_name: str):
        """
        處理單一縣市的開票所 Excel 檔案：
        - 讀取並清理鄉鎮、市里、投開票所與候選人票數資訊。
        - 將欄位轉為長格式 (每行代表一個候選人的得票數)。
        - 回傳處理後的 DataFrame。
        """
        file_path = f"data/總統-A05-4-候選人得票數一覽表-各投開票所({county_name}).xlsx"
        df = pd.read_excel(file_path, skiprows=[0, 3, 4])  # 讀取並跳過多餘標題列
        df = df.iloc[:, :6]  # 只保留前六欄 (鄉鎮、市里、投開票所與三位候選人資訊)
        candidates_info = df.iloc[0, 3:].to_list()  # 抓取第一行的候選人資訊
        df.columns = ["town", "village", "polling_place"] + candidates_info  # 設定新欄位名稱
        df["town"] = df["town"].ffill().str.strip() # 鄉鎮名稱若有缺漏則向下填補，並去除名稱前後空白
        df = df.dropna()  # 移除任何有缺失值的列 (避免空白列影響資料處理)
        df["polling_place"] = df["polling_place"].astype(int)  # 投開票所編號轉為整數
        id_variables = ["town", "village", "polling_place"]  # 不需要展開的識別欄位 
        melted_df = pd.melt(df, id_vars=id_variables, var_name="candidate_info", value_name="votes") # 將候選人票數展平成長格式
        melted_df["county"] = county_name  # 新增縣市欄位以利辨識
        return melted_df


    def concat_country_dataframe(self):
        """
        將所有縣市的票數資料整理合併成一張完整 DataFrame (presidential_votes)：
        - 解析候選人資訊 (號碼 / 姓名)。
        - 統一欄位名稱格式。
        - 回傳總表 DataFrame。
        """
        country_df = pd.DataFrame()
        for county_name in self.county_names:
            county_df = self.tidy_county_dataframe(county_name)  # 處理該縣市的相關資訊
            country_df = pd.concat([country_df, county_df])  # 合併進總表

        country_df = country_df.reset_index(drop=True) # 重設索引

        numbers = []  # 候選人號碼清單
        candidates = [] # 候選人姓名清單

        # 解析 candidate_info 欄位 (格式EX：(1)\n柯文哲\n吳欣盈)
        for elem in country_df["candidate_info"]:
            parts = elem.strip().split("\n")   # 以換行符號拆開
            number = int(parts[0].strip("()"))  # 取號碼並去掉括號
            candidate = f"{parts[1]}/{parts[2]}"   # 將正副手姓名以 '/' 連接
            numbers.append(number)
            candidates.append(candidate)

        # 建立投票明細 DataFrame
        presidential_votes =  country_df.loc[:, ["county", "town", "village", "polling_place"]]
        presidential_votes["number"] = numbers  # 加入候選人號碼
        presidential_votes["candidate"] = candidates  # 加入候選人姓名
        presidential_votes["votes"] = country_df["votes"]  # 加入票數欄位
        return presidential_votes


    def create_database(self):
        """
        將所有資料轉為三張資料表並匯入 SQLite 資料庫：
        - polling_places (投票所)
        - candidates (候選人)
        - votes (投票明細)
        並建立檢視表 votes_by_village (以村里為單位統計各候選人總得票數)。
        """
        presidential_votes = self.concat_country_dataframe()  # 整理全國票數明細

        # 產生投票所表 polling_places_df
        polling_places_df = presidential_votes.groupby(["county", "town", "village", "polling_place"]).count().reset_index()
        polling_places_df = polling_places_df[["county", "town", "village", "polling_place"]]  # 移除多餘欄位
        polling_places_df = polling_places_df.reset_index()  # 用 index 產生新的 id
        polling_places_df["index"] = polling_places_df["index"] + 1  # 從 1 開始編號
        polling_places_df = polling_places_df.rename(columns={"index": "id"})   # 將 index 改為 id

        # 產生候選人表 candidates_df
        candidates_df = presidential_votes.groupby(["number", "candidate"]).count().reset_index()
        candidates_df = candidates_df[["number", "candidate"]]  # 只保留號碼與姓名
        candidates_df = candidates_df.rename(columns={"number": "id"}) # 因為 number 已經是1、2、3了 => 將號碼直接設為 id

        # 產生投票明細表 votes_df
        join_keys = ["county", "town", "village", "polling_place"]  # 連接用的主鍵
        votes_df = pd.merge(presidential_votes, polling_places_df, left_on=join_keys, right_on=join_keys, how="left")
        votes_df = votes_df[["id", "number", "votes"]]  # 只保留投票關聯欄位
        votes_df = votes_df.rename(columns={"id": "polling_place_id", "number": "candidate_id"})  # 欄位名稱標準化

        # 將三張表組成字典以便寫入 SQLite
        election_info = {
            "polling_places":  polling_places_df,
            "candidates": candidates_df,
            "votes":  votes_df
        }

        # 寫入 SQLite 資料庫
        connection = sqlite3.connect("data/taiwan_presidential_election_2024.db")
        for k, v in election_info.items():
            v.to_sql(name=k, con=connection, index=False, if_exists="replace")

        # 建立檢視表 votes_by_village (村里統計)
        cur = connection.cursor()
        drop_view_sql = """
        DROP VIEW IF EXISTS votes_by_village;
        """
        create_view_sql = """
        CREATE VIEW votes_by_village AS
        SELECT polling_places.county,
               polling_places.town,
               polling_places.village,
               candidates.id,
               candidates.candidate,
               SUM(votes.votes) AS sum_votes
          FROM votes
          LEFT JOIN polling_places
            ON votes.polling_place_id = polling_places.id
          LEFT JOIN candidates
            ON votes.candidate_id = candidates.id
         GROUP BY polling_places.county,
                  polling_places.town,
                  polling_places.village,
                  candidates.id; 
        """
        cur.execute(drop_view_sql)
        cur.execute(create_view_sql)    
        connection.close()

def test():
    create_taiwan_presidential_election_2024_db = CreateTaiwanPresidentialElection2024DB()
    create_taiwan_presidential_election_2024_db.create_database()

if __name__ == "__main__":
    test()
