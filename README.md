# Project 4: Find the Octopus Village

## Introduction

This project, “Find the Octopus Village,” analyzes the 2024 Presidential Election polling station data from [Taiwan's Central Election Commission (CEC)](https://db.cec.gov.tw/ElecTable/Election/ElecTickets?dataType=tickets&typeId=ELC&subjectId=P0&legisId=00&themeId=4d83db17c1707e3defae5dc4d4e9c800&dataLevel=N&prvCode=00&cityCode=000&areaCode=00&deptCode=000&liCode=0000). We compute the vote distribution across 7,700 villages in Taiwan, comparing each village's vote share to the national distribution, and highlight anomalies often reported by media outlets as “octopus villages” — areas where voting patterns appear statistically improbable.

Two key investigative questions:

1. Will villages with stable "Octopus Village" vote distributions still exist over time, even with demographic shifts and changing voter preferences?
2. The definition of “vote share closely matching the national result” is often vague — can we provide a clearer statistical basis for detecting anomalies?

> 🛠️ We use `pandas` and `sqlite3` to build the database, `numpy` for vector calculations, and develop an interactive Gradio app to present the findings.

## ⚙️ How to Reproduce

* Install [Miniconda](https://docs.anaconda.com/miniconda)
* Create the environment from `environment.yml`:

```bash
conda env create -f environment.yml
```

* Place the 22 Excel files (`總統-A05-4-候選人得票數一覽表-各投開票所`) into the `data/` folder.
* Activate the environment and run the following script to build the SQLite database:

```bash
python create_taiwan_presidential_election_2024_db.py
```

* Then run the app interface to browse the interactive result:

```bash
python app.py
```

Visit `http://127.0.0.1:7860` in your browser to interact with the app.

## 📁 Project Structure

```
TAIWAN_PRESIDENTIAL_ELECTION_2024/
├── .gradio/
├── data/
│   ├── 總統-A05-4-候選人得票數一覽表-各投開票所(南投縣).xlsx
│   ├── 總統-A05-4-候選人得票數一覽表-各投開票所(嘉義市).xlsx
│   └── ... (20 more files)
├── app.py
├── create_taiwan_presidential_election_2024_db.py
├── proof_of_concept.py
├── environment.yml
└── README.md
```

## 🚀  Live Demo (Hugging Face Spaces)

You can try out the interactive version of this app deployed on Hugging Face Spaces:

🔗 **[Launch the Octopus Village Finder 🔍](https://huggingface.co/spaces/AustinKang66666/taiwan_presidential_election_2024)**

No local setup needed — explore directly in your browser!


## 🧪 Environment Setup (environment.yml)

```yaml
name: taiwan_presidental_election_2024
channels:
  - conda-forge
dependencies:
  - python=3.12.11
  - pandas=2.3.1
  - numpy=2.0.1
  - openpyxl=3.1.5
  - sqlite=3.50.2
  - pip=25.1
  - pip:
      - gradio==5.39.0
```

## 🖥️ Output Result (Gradio App)

* Input the county, town, and village you want to investigate.
* The app will query the dataset and display the matching village's vote share and cosine similarity index.
* The national vote distribution percentages for each candidate are also displayed on the interface.
