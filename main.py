from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import requests
import traceback
from logzero import setup_logger
import json

with open("creds.json") as f:
    creds = json.load(f)

github_pat = creds["github_pat"]
log = setup_logger(logfile="fast_api_github_assignment.log")

app = FastAPI()

client = MongoClient("mongodb://localhost:27017/")
db = client["fastapi_assignment"]
collection = db["github_data"]

class RepoInfo(BaseModel):
    owner: str
    repo: str


def get_contributors_from_github(owner, repo):
    log.info(f"Trying to reach GH for info regarding {owner}/{repo}")
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {github_pat}',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    try:
        response = requests.get(f'https://api.github.com/repos/{owner}/{repo}/contributors', headers=headers)
        if response.ok:
            log.info(f"response from GH is {response.json()}")
            return response.json()
        log.error(f"response code is {response.status_code} and response content is {response.text}")
        return []
    except:
        log.error(traceback.format_exc())
        return []


@app.post("/ingest-contributors")
def process_data(repo_info: RepoInfo):
    try:
        api_response = get_contributors_from_github(repo=repo_info.repo, owner=repo_info.owner)
        _key = f"{repo_info.owner}_{repo_info.repo}"
        collection.insert_one({_key: {"contributors": api_response}})
        return {"message": f"Successfully ingested {len(api_response)} contributors into {_key}.contributors"}
    except Exception:
        raise HTTPException(status_code=500, detail=f"Error processing data: {traceback.format_exc()}")

@app.get("/contributors")
def get_data(owner: str, repo: str, username:str, type:str):
    try:
        result = collection.find({f"{owner}_{repo}.contributors.login": username,f"{owner}_{repo}.contributors.type": type})
        if not result:
            raise HTTPException(status_code=404, detail="Data not found")
        try:
            for x in result:
                
                for y in x[f"{owner}_{repo}"]["contributors"]:
                    if y["login"] == username and y["type"] == type:
                        return {"username": y["login"], "avatar_url": y["avatar_url"], "site_admin": y["site_admin"], "contributions": y["contributions"]}
        except:
            return {}
        return {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")
