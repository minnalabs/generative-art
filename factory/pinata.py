import os
from pinatapy import PinataPy

import requests

API_ENDPOINT: str = "https://api.pinata.cloud/"

class PinataClient:
    def __init__(self):
        self._auth_headers = {
            "pinata_api_key": os.getenv("PINATA_API_KEY"),
            "pinata_secret_api_key": os.getenv("PINATA_API_SECRET"),
        }
        self.jwt = os.getenv("PINATA_JWT")

    def upload_folder(self, folder_path, upload_name, options=None):
        url = API_ENDPOINT + "pinning/pinFileToIPFS"
        headers = {k: self._auth_headers[k] for k in ["pinata_api_key", "pinata_secret_api_key"]}

        def get_all_files(directory):
            paths= []
            for root, _, files_ in os.walk(os.path.abspath(directory)):
                for file in files_:
                    paths.append(os.path.join(root, file))
            return paths
    
        files = [("file",(file[file.index("images/"):].replace("images/", upload_name + "/"), open(file, "rb"))) for file in get_all_files(folder_path)] if os.path.isdir(folder_path) else [     ("file", open(folder_path, "rb"))]

        # if options != None:
        #     if "pinataMetadata" in options:
        #         headers["pinataMetadata"] = options["pinataMetadata"]
        
        response = requests.post(url=url, files=files, headers=headers)
        return response.json() if response.ok else self._error(response)
