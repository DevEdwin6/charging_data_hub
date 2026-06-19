import requests

url = "https://user.csenergytech.com/api/oms-operation-service/v1/campaign/get_campaign_exist_info"

params = {
  'oprPkId': "0001",
  'displayPage': "1",
  'isAuthenticated': "false"
}

headers = {
  'User-Agent': "okhttp/4.12.0",
  'Accept': "application/json, text/plain, */*",
  'Accept-Encoding': "gzip",
  'accept-language': "zh-CN",
  'version': "11001301",
  'ostype': "android",
  'x-device-id': "android-560c2f971b3122af"
}

response = requests.get(url, params=params, headers=headers)

print(response.text)