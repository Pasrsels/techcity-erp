import requests

url = "https://zimra.co.zw/Device/v1/23265/getConfig"
headers = {
    "Content-Type": "application/json",
    "DeviceModelName": "Server",
    "DeviceModelVersionNo": "v1"
}

cert = ("device_cert.pem", "device_key.pem")
response = requests.get(url, headers=headers, cert=cert)
print(response.json())
