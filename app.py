
import gradio as gr
import pandas as pd
import numpy as np
import sqlite3 

def create_gradio_dataframe():
    """
    從 SQLite 資料庫讀取 votes_by_village 檢視表，計算：
    1. 全國各候選人的得票率向量 (作為餘弦相似度比較基準)
    2. 各村里與全國得票率的餘弦相似度表格 (cosine_similarity_df)

    回傳：
        dict: 包含 'country_percentage' (全國得票率向量) 及 'cosine_similarity_df' (相似度排序表格)
    """
    connection = sqlite3.connect("data/taiwan_presidential_election_2024.db")
    votes_by_village = pd.read_sql("""SELECT * FROM votes_by_village;""", con=connection)
    connection.close()

    # 計算全國總票數
    total_votes = votes_by_village["sum_votes"].sum()

    # 計算每位候選人在全國的得票率: vector_a (百分比向量)
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

    # 回傳全國得票率向量 與 計算後的餘弦相似度 DataFrame
    return {
        "country_percentage": vector_a,  # 全國得票率向量
        "cosine_similarity_df": cosine_similarity_df  # 計算後的餘弦相似度 DataFrame
    }



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


# 呼叫 create_gradio_dataframe() 計算所需資料
data = create_gradio_dataframe()
country_percentage = data["country_percentage"]  # 全國得票率向量
gradio_df = data["cosine_similarity_df"]   # 村里相似度 DataFrame

# 將全國得票率向量拆成各候選人的得票率變數 (便於顯示)
ko_wu, lai_hsiao, hou_chao = country_percentage

# 建立 Gradio 介面
interface = gr.Interface( fn=filter_county_town_village,  # 點擊執行的 function
                          inputs=[gr.DataFrame(gradio_df), "text", "text", "text"],   # 輸入：DataFrame + 縣市 + 鄉鎮 + 村里
                          outputs="dataframe",  # 指定 function 回傳的結果是 DataFrame，Gradio 會根據 DataFrame 欄位數自動生成表格欄位
                          title="找出章魚里",
                          description=f"輸⼊你想篩選的縣市、鄉鎮市區與村鄰⾥。(柯吳, 賴蕭, 侯趙) = ({ko_wu:.6f},{lai_hsiao:.6f},{hou_chao:.6f})"
                          # 介面說明文字，會顯示在標題下方
                          # 說明中將全國三位候選人的得票率（四捨五入到小數點後6位）顯示給使用者參考
            )

# 啟動 Gradio 介面
interface.launch()