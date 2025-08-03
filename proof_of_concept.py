 
import sqlite3
import pandas as pd
import numpy as np

connection = sqlite3.connect("data/taiwan_presidential_election_2024.db")
votes_by_village = pd.read_sql("""SELECT * FROM votes_by_village;""", con=connection)
connection.close()

# 計算全國總票數
total_votes = votes_by_village["sum_votes"].sum()

# 計算每位候選人在全國的得票率 (百分比向量)
country_percentage = votes_by_village.groupby(["id"])["sum_votes"].sum() / total_votes
vector_a = country_percentage.to_numpy() # 將得票率轉為 numpy array (作為餘弦相似度的比較基準向量)

# 計算每個村里的總得票數
groupby_variables = ["county", "town", "village"]
village_total_votes = votes_by_village.groupby(groupby_variables)["sum_votes"].sum()

# 將 votes_by_village 與 village_total_votes 合併 => 為了計算各村里每位候選人的得票率 (百分比)
# 合併後 sum_votes 會變成 sum_votes_x (候選人得票數)，sum_votes_y (村里總票數)
merged = pd.merge(votes_by_village, village_total_votes, left_on=groupby_variables, right_on=groupby_variables, how="left")
merged["village_percentage"] = merged["sum_votes_x"] / merged["sum_votes_y"]  # 計算每位候選人在該村里的得票率 (村里得票數 / 村里總票數)
merged = merged[["county", "town", "village", "id", "village_percentage"]]  # 只保留必要欄位，準備做 pivot 操作

# 將每位候選人的得票率展開為欄位 (長轉寬)
pivot_df = merged.pivot(index=["county", "town", "village"], columns="id", values="village_percentage").reset_index()
pivot_df = pivot_df.rename_axis(None, axis=1) # 將 columns 軸的名稱 (原先是 'id') 移除，保持欄位乾淨好讀


# 儲存各村里的餘弦相似度 (各村里 與 全國 的得票率進行 餘弦相似度 計算)
cosine_similarities = []  
 
for _, row in pivot_df.iterrows():

    vector_bi = row.iloc[3:].to_numpy()  # 這裡 iloc[3:] 是從第4欄(得票率)開始抓到最後 => EX: [0.22650796491856096 0.4530159298371219 0.3204761052443172]
                                                                                 #   => 三位候選人得票率         
    # 計算 cosine similarity
    vector_a_dot_vector_bi = np.dot(vector_a, vector_bi)
    length_vector_a = np.linalg.norm(vector_a)  
    length_vector_bi = np.linalg.norm(vector_bi)

    cosine_similarity = vector_a_dot_vector_bi / (length_vector_a * length_vector_bi)
    cosine_similarities.append(float(cosine_similarity))  # 將np.float64 轉成一般 float (美觀而已，功能沒影響)

# 準備將餘弦相似度加入 pivot_df 中
cosine_similarity_df = pivot_df.copy()
cosine_similarity_df["cosine_similarity"] = cosine_similarities

# 依照 cosine_similarity 降序排序(為了後續ranking)，相同相似度時依照 縣市、鄉鎮、村里 升序排序
cosine_similarity_df = cosine_similarity_df.sort_values(by=["cosine_similarity", "county", "town", "village"], 
                                                        ascending=[False, True, True, True])

# 重設 index，並加上 similarity_rank 欄位 (從 1 開始編號)
cosine_similarity_df = cosine_similarity_df.reset_index(drop=True).reset_index()
cosine_similarity_df["index"] = cosine_similarity_df["index"] + 1

# 重新命名欄位名稱，使表格語意清晰
column_names_to_revise = {
    "index": "similarity_rank",   # 排名
    1: "candidates_1",            # 第一位候選人的得票率欄位
    2: "candidates_2",            # 第二位候選人的得票率欄位
    3: "candidates_3"             # 第三位候選人的得票率欄位
}

cosine_similarity_df = cosine_similarity_df.rename(columns=column_names_to_revise)
# print(cosine_similarity_df.head(10))


def filter_county_town_village(df, county_name: str, town_name: str, village_name: str):
    """
    根據指定的 county_name、town_name、village_name 篩選資料。
    條件會同時滿足縣市、鄉鎮、市里名稱 (全符合才會被篩選出來)。

    參數：
        df (pd.DataFrame): 欲篩選的資料表。
        county_name (str): 縣市名稱 (如: "台北市")。
        town_name (str): 鄉鎮名稱 (如: "信義區")。
        village_name (str): 村里名稱 (如: "世貿里")。

    回傳：
        pd.DataFrame: 符合篩選條件的資料表。
    """
    
    condition = (
        (df["county"] == county_name) &
        (df["town"] == town_name) &
        (df["village"] == village_name)
    )

    return df[condition]


# print(filter_county_town_village(cosine_similarity_df, county_name="臺北市", town_name="士林區", village_name="天玉里"))